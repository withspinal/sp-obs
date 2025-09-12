import typing
import logging
import uuid

from opentelemetry import baggage, context, trace

from ._internal import SPINAL_NAMESPACE

logger = logging.getLogger(__name__)


class tag:
    """
    Add custom tags to the current context for Spinal tracing.
    Can be used both as a context manager and as a regular function.

    Note: OpenTelemetry's baggage system works independently of active spans.

    Args:
        aggregation_id: Optional aggregation ID for distributed tracing
        org_id: Optional organization ID useful for representing a group of users
        user_id: Optional user ID used to represent a single user
        workflow_id: Optional workflow ID useful for tracking a single workflow
        **kwargs: Any number of keyword arguments to be added as tags

    All keyword arguments are added as tags to the baggage with the 'spinal.tag.' prefix.

    Examples:
        # As a context manager
        with add_tag(aggregation_id="agg123", workflow_id="123", user_id="456"):
            # Your code here

        # As a function call
        add_tag(workflow_id="123", user_id="456", custom_field="value")
    """

    def __init__(
        self,
        aggregation_id: typing.Union[int, str, uuid.UUID] = None,
        org_id: typing.Union[int, str, uuid.UUID] = None,
        user_id: typing.Union[int, str, uuid.UUID] = None,
        workflow_id: typing.Union[int, str, uuid.UUID] = None,
        **kwargs,
    ):
        self.aggregation_id = aggregation_id
        self.org_id = org_id
        self.user_id = user_id
        self.workflow_id = workflow_id
        self.kwargs = kwargs
        self.token = None
        self.span = None
        self.is_context_manager = False
        self._apply_tags()

    def _apply_tags(self):
        """Apply tags to the current context baggage"""
        current_context = context.get_current()
        baggage_to_add = {}

        if self.aggregation_id:
            baggage_to_add[f"{SPINAL_NAMESPACE}_aggregation_id"] = str(self.aggregation_id)

        if self.org_id:
            baggage_to_add[f"{SPINAL_NAMESPACE}_org_id"] = str(self.org_id)

        if self.user_id:
            baggage_to_add[f"{SPINAL_NAMESPACE}_user_id"] = str(self.user_id)

        if self.workflow_id:
            baggage_to_add[f"{SPINAL_NAMESPACE}_workflow_id"] = str(self.workflow_id)

        for key, value in self.kwargs.items():
            baggage_key = f"{SPINAL_NAMESPACE}.tag.{key}"
            baggage_to_add[baggage_key] = str(value)

        # Set all baggage items
        for key, value in baggage_to_add.items():
            current_context = baggage.set_baggage(key, value, current_context)

        # Attach the updated context and save the token
        self.token = context.attach(current_context)
        logger.debug(f"Added tags to baggage: {baggage_to_add}")

    def __enter__(self):
        """Enter the context manager"""
        current_span = trace.get_current_span()
        if not current_span or not current_span.is_recording():
            # No active span - create one to establish trace context
            tracer = trace.get_tracer(__name__)
            self.span_context_manager = tracer.start_as_current_span("spinal.tag_context")
            self.span_context_manager.__enter__()
            logger.debug("Created new span for tag context manager")

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the context manager"""
        if self.span_context_manager:
            self.span_context_manager.__exit__(exc_type, exc_val, exc_tb)
            logger.debug("Ended span for tag context manager")

        # Detach the baggage context
        if self.token:
            context.detach(self.token)
        return False

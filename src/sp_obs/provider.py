import contextlib
import typing
import logging
import uuid

from opentelemetry import baggage, context

from ._internal import SPINAL_NAMESPACE
from .utils import deprecated

logger = logging.getLogger(__name__)


@deprecated("add_tag()")
@contextlib.contextmanager
def add_context(
    *,
    workflow_id: typing.Union[int, str, uuid.UUID],
    user_id: typing.Union[int, str, uuid.UUID],
    aggregation_id: typing.Union[int, str, uuid.UUID] = None,
):
    """
    Utility function to allow a user to add context to a trace so that spinal can trace what is happening across the stack.
    Baggage will need to be set here so that distributed tracking can take effect.
    The aggregation id is an optional id given that aggregates traces together.
    """
    current_context = context.get_current()

    baggage_to_add = {
        f"{SPINAL_NAMESPACE}.workflow_id": str(workflow_id),
        f"{SPINAL_NAMESPACE}.user_context.id": user_id,
    }
    if aggregation_id:
        baggage_to_add[f"{SPINAL_NAMESPACE}.aggregation_id"] = str(aggregation_id)

    for key, value in baggage_to_add.items():
        current_context = baggage.set_baggage(key, value, current_context)
    token = context.attach(current_context)

    try:
        yield
    finally:
        context.detach(token)


class tag:
    """
    Add custom tags to the current context for Spinal tracing.
    Can be used both as a context manager and as a regular function.

    Note: OpenTelemetry's baggage system works independently of active spans.

    Args:
        aggregation_id: Optional aggregation ID for distributed tracing
        **kwargs: Any number of keyword arguments to be added as tags

    All keyword arguments are added as tags to the baggage with the 'spinal.' prefix.

    Examples:
        # As a context manager
        with add_tag(aggregation_id="agg123", workflow_id="123", user_id="456"):
            # Your code here

        # As a function call
        add_tag(workflow_id="123", user_id="456", custom_field="value")
    """

    def __init__(self, aggregation_id: typing.Union[int, str, uuid.UUID] = None, **kwargs):
        self.aggregation_id = aggregation_id
        self.kwargs = kwargs
        self.token = None
        self._apply_tags()

    def _apply_tags(self):
        """Apply tags to the current context baggage"""
        current_context = context.get_current()

        baggage_to_add = {}

        # Handle aggregation_id if provided
        if self.aggregation_id:
            baggage_to_add[f"{SPINAL_NAMESPACE}_aggregation_id"] = str(self.aggregation_id)

        # Add all other keyword arguments
        for key, value in self.kwargs.items():
            baggage_key = f"{SPINAL_NAMESPACE}.{key}"
            baggage_to_add[baggage_key] = str(value)

        # Set all baggage items
        for key, value in baggage_to_add.items():
            current_context = baggage.set_baggage(key, value, current_context)

        # Attach the updated context and save the token
        self.token = context.attach(current_context)

        logger.debug(f"Added tags to baggage: {baggage_to_add}")

    def __enter__(self):
        """Enter the context manager"""
        # Tags are already applied in __init__
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the context manager"""
        # Detach the context if we have a token
        if self.token:
            context.detach(self.token)
        return False

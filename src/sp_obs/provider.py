"""
SP-OBS: OpenTelemetry Span Interceptor
Automatically attaches to existing TracerProvider to duplicate spans to custom endpoints
"""

import contextlib
import typing
import contextvars
import logging
import uuid
from opentelemetry import baggage, trace, context

logger = logging.getLogger(__name__)

# Create a context key for user data that propagates with traces
TRACE_CONTEXT = contextvars.ContextVar("spinal_context", default={})
SPINAL_NAMESPACE = "spinal"


BILLING_EVENT_SPAN_NAME = "spinal_billable_event"
USER_CONTEXT_SPAN_NAME = "spinal_user_context"
WORKFLOW_CONTEXT_SPAN_NAME = "spinal_workflow_context"


def spinal_add_as_billable(
    attributes: typing.Optional[dict[str, typing.Any]] = None, aggregation_id: typing.Union[int, str, uuid.UUID] = None
):
    """
    Add information on the trace that allows us to track it across our billing engine
    """
    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span(BILLING_EVENT_SPAN_NAME) as billing_span:
        # Mark this as a billable span
        trace_id = billing_span.get_span_context().trace_id

        billing_span.set_attribute("billable", True)
        billing_span.set_attribute("billing_trace_id", format(trace_id, "032x"))
        billing_span.set_attribute("billing_aggregation_id", str(aggregation_id) if aggregation_id else "")

        # Add any custom attributes
        if attributes:
            for key, value in attributes.items():
                billing_span.set_attribute(f"user_attr.{key}", value)

        # This span will auto-end and be sent to your processor
        logger.debug(f"Created billable event span with attributes: {attributes}")


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

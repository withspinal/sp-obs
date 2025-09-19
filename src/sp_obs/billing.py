import logging

from opentelemetry.trace import ProxyTracerProvider

from ._internal.config import get_tracer_provider
from ._internal import SPINAL_BILLING_SPAN_NAME, SPINAL_NAMESPACE


logger = logging.getLogger(__name__)


def add_billing_event(success: bool, **kwargs):
    """
    Adds a billing event to the tracing system with associated attributes.

    This function is used to record billing-related events and their metadata
    in the system's tracing provider. It tags the span with attributes provided
    via keyword arguments and specifies whether the billing operation was
    successful.

    Parameters:
        success: bool
            Indicates whether the billing operation was successful.
        **kwargs
            Additional metadata related to the billing event. Keys represent
            attribute names and their values are stringified before being set
            as attributes in the tracing span.

    Raises:
        ValueError
            Raised if the global tracing provider is not set.
    """
    provider = get_tracer_provider().provider
    if isinstance(provider, ProxyTracerProvider):
        raise ValueError(
            "Cannot add billing event - spinal tracing provider is not set. Please call sp_obs.configure() first"
        )

    with provider.get_tracer(__name__).start_as_current_span(SPINAL_BILLING_SPAN_NAME) as billing_span:
        for key, value in kwargs.items():
            namespaced_key = f"{SPINAL_NAMESPACE}.billing.{key}"
            billing_span.set_attribute(f"{namespaced_key}", str(value))

        billing_span.set_attribute("is_billing_span", True)
        billing_span.set_attribute("billing_success", success)

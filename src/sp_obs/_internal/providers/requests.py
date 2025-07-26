import logging

from sp_obs._internal.providers.base import instrument_library

logger = logging.getLogger(__name__)


def instrument_requests():
    """
    Instrument Requests library to send traces to Spinal.

    This function will:
    - Check if requests is already instrumented
    - If not, create an isolated provider and instrument it
    - If yes, attempt to attach to the existing provider

    Raises:
        ImportError: If opentelemetry-instrumentation-requests is not installed
    """
    try:
        from opentelemetry.instrumentation.requests import RequestsInstrumentor
    except ImportError as e:
        raise ImportError(
            "RequestsInstrumentor instrumentation is not installed. "
            "Install it with: pip install 'sp-obs[all]' or "
            "pip install opentelemetry-instrumentation-requests"
        ) from e

    instrument_library("Requests", RequestsInstrumentor, logger)

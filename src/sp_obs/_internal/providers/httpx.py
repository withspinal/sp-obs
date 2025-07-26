import logging

from sp_obs._internal.providers.base import instrument_library

logger = logging.getLogger(__name__)


def instrument_httpx():
    """
    Instrument httpx library to send traces to Spinal.

    This function will:
    - Check if httpx is already instrumented
    - If not, create an isolated provider and instrument it
    - If yes, attempt to attach to the existing provider

    Raises:
        ImportError: If opentelemetry-instrumentation-httpx is not installed
    """
    try:
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
    except ImportError as e:
        raise ImportError(
            "HTTPXClientInstrumentor instrumentation is not installed. "
            "Install it with: pip install 'sp-obs[all]' or "
            "pip install opentelemetry-instrumentation-httpx"
        ) from e

    instrument_library("httpx", HTTPXClientInstrumentor, logger)

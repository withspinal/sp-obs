import logging

from sp_obs._internal.providers.base import instrument_library


logger = logging.getLogger(__name__)


def instrument_openai():
    """
    Instrument OpenAI library to send traces to Spinal.

    This function will:
    - Check if OpenAI is already instrumented
    - If not, create an isolated provider and instrument it
    - If yes, attempt to attach to the existing provider

    Raises:
        ImportError: If opentelemetry-instrumentation-openai is not installed
    """
    try:
        from opentelemetry.instrumentation.openai import OpenAIInstrumentor
    except ImportError as e:
        raise ImportError(
            "OpenAI instrumentation is not installed. "
            "Install it with: pip install 'sp-obs[openai]' or "
            "pip install opentelemetry-instrumentation-openai"
        ) from e

    instrument_library("OpenAI", OpenAIInstrumentor, logger, extra_args={"enrich_token_usage": True})

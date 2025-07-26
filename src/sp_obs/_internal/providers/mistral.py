import logging

from sp_obs._internal.providers.base import instrument_library

logger = logging.getLogger(__name__)


def instrument_mistral():
    """
    Instrument Mistral library to send traces to Spinal.

    This function will:
    - Check if Mistral is already instrumented
    - If not, create an isolated provider and instrument it
    - If yes, attempt to attach to the existing provider

    Raises:
        ImportError: If opentelemetry-instrumentation-mistralai is not installed
    """
    try:
        from opentelemetry.instrumentation.mistralai import MistralAiInstrumentor
    except ImportError as e:
        raise ImportError(
            "MistralAiInstrumentor instrumentation is not installed. "
            "Install it with: pip install 'sp-obs[mistral]' or "
            "pip install opentelemetry-instrumentation-mistralai"
        ) from e

    instrument_library("Mistral", MistralAiInstrumentor, logger)

import logging

from sp_obs._internal.providers.base import instrument_library

logger = logging.getLogger(__name__)


def instrument_anthropic():
    """
    Instrument Anthropic library to send traces to Spinal.

    This function will:
    - Check if Anthropic is already instrumented
    - If not, create an isolated provider and instrument it
    - If yes, attempt to attach to the existing provider

    Raises:
        ImportError: If opentelemetry-instrumentation-anthropic is not installed
    """
    try:
        from opentelemetry.instrumentation.anthropic import AnthropicInstrumentor
    except ImportError as e:
        raise ImportError(
            "AnthropicInstrumentor instrumentation is not installed. "
            "Install it with: pip install 'sp-obs[anthropic]' or "
            "pip install opentelemetry-instrumentation-anthropic"
        ) from e

    instrument_library("Anthropic", AnthropicInstrumentor, logger, extra_args={"enrich_token_usage": True})

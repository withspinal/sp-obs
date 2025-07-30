import logging

from sp_obs._internal.providers.base import instrument_library


logger = logging.getLogger(__name__)


def instrument_openai_agents():
    """
    Instrument OpenAI Agents library to send traces to Spinal.

    This function will:
    - Check if OpenAI is already instrumented
    - If not, create an isolated provider and instrument it
    - If yes, attempt to attach to the existing provider

    Raises:
        ImportError: If opentelemetry-instrumentation-openai-agents is not installed
    """
    try:
        from opentelemetry.instrumentation.openai_agents import OpenAIAgentsInstrumentor
    except ImportError as e:
        raise ImportError(
            "OpenAI Agents instrumentation is not installed. "
            "Install it with: pip install 'sp-obs[openai]' or "
            "pip install opentelemetry-instrumentation-openai-agents"
        ) from e

    instrument_library("OpenAIAgents", OpenAIAgentsInstrumentor, logger)

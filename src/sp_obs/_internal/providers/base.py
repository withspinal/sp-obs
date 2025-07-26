import logging
import typing
from opentelemetry.instrumentation.instrumentor import BaseInstrumentor


def instrument_library(
    name: str,
    instrumentation_class: typing.Type[BaseInstrumentor],
    logger: logging.Logger,
    extra_args: dict[str, typing.Any] | None = None,
):
    """
    Instrument a library to send traces to Spinal.
    """
    from sp_obs._internal.tracer import SpinalTracerProvider
    from sp_obs._internal.config import get_config

    tracer_provider = SpinalTracerProvider()

    config = get_config()
    if not config:
        raise RuntimeError("Spinal SDK not configured. Call sp_obs.configure() first.")

    extra_args = extra_args or {}
    instrumentor = instrumentation_class(**extra_args)

    if getattr(instrumentor, "spinal_instrumented", False):
        logger.debug("%s is already instrumented by Spinal", name)
        return

    if instrumentor.is_instrumented_by_opentelemetry:
        logger.error("%s is already instrumented by OpenTelemetry", name)
        # if not SpinalTracerProvider.attach_to_existing_provider():
        #     logger.error("Failed to attach to existing provider. Spinal will not be setup for %s", name)
        #     return

    logger.debug("Creating isolated tracer provider for %s", name)
    instrumentor.instrument(tracer_provider=tracer_provider.provider)

    setattr(instrumentor, "spinal_instrumented", True)

    logger.debug("%s instrumentation completed with Spinal", name)

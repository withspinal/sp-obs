"""
Tracer module for managing isolated tracer providers
"""

import logging
import typing

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace.sampling import ALWAYS_ON
from opentelemetry.trace import ProxyTracerProvider

if typing.TYPE_CHECKING:
    from .config import SpinalConfig

logger = logging.getLogger(__name__)


class SpinalTracerProvider:
    """Manages isolated tracer providers for Spinal"""

    _instance = None
    _provider: TracerProvider | None = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(SpinalTracerProvider)
        return cls._instance

    def __init__(self, config: "SpinalConfig"):
        self._config = config
        self._provider = self.create_isolated_provider("spinal-tracer")

    @property
    def provider(self) -> TracerProvider:
        return self._provider

    def create_isolated_provider(self, service_name: str) -> TracerProvider:
        """
        Create an isolated TracerProvider that only sends to Spinal

        Args:
            service_name: Name for the service in traces

        Returns:
            A new TracerProvider instance
        """
        from sp_obs._internal.processor import SpinalSpanProcessor

        if not self._config:
            raise RuntimeError("Spinal SDK not configured")

        # Create a new provider that's not the global one
        provider = TracerProvider(sampler=ALWAYS_ON, resource=Resource.create({"service.name": service_name}))

        # Add only Spinal processor
        provider.add_span_processor(SpinalSpanProcessor(self._config))

        if self._config.set_global_tracer:
            global_provider = trace.get_tracer_provider()
            if isinstance(global_provider, ProxyTracerProvider):
                trace.set_tracer_provider(provider)

        logger.debug(f"Created isolated tracer provider for service: {service_name}")
        return provider

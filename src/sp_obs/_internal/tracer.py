"""
Tracer module for managing isolated tracer providers
"""

import logging
from typing import Dict

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace.sampling import ALWAYS_ON
from .config import get_config

logger = logging.getLogger(__name__)

# Track which libraries have been instrumented
_instrumented_libraries: Dict[str, bool] = {}


class SpinalTracerProvider:
    """Manages isolated tracer providers for Spinal"""

    _instance = None
    _provider: TracerProvider | None = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(SpinalTracerProvider)
            cls._instance._provider = cls.create_isolated_provider("spinal-tracer")
        return cls._instance

    @property
    def provider(self) -> TracerProvider:
        if not self._provider:
            self._provider = self.create_isolated_provider("spinal-tracer")
        return self._provider

    @staticmethod
    def create_isolated_provider(service_name: str) -> TracerProvider:
        """
        Create an isolated TracerProvider that only sends to Spinal

        Args:
            service_name: Name for the service in traces

        Returns:
            A new TracerProvider instance
        """
        from sp_obs._internal.processor import SpinalSpanProcessor

        config = get_config()
        if not config:
            raise RuntimeError("Spinal SDK not configured. Call sp_obs.configure() first.")

        # Create a new provider that's not the global one
        provider = TracerProvider(sampler=ALWAYS_ON, resource=Resource.create({"service.name": service_name}))

        # Add only Spinal processor
        provider.add_span_processor(
            SpinalSpanProcessor(
                max_queue_size=config.max_queue_size,
                schedule_delay_millis=config.schedule_delay_millis,
                max_export_batch_size=config.max_export_batch_size,
                export_timeout_millis=config.export_timeout_millis,
            )
        )

        logger.debug(f"Created isolated tracer provider for service: {service_name}")
        return provider

    @staticmethod
    def attach_to_existing_provider() -> bool:
        """
        Attempt to attach Spinal processor to an existing provider

        Returns:
            True if successfully attached, False otherwise
        """
        from sp_obs._internal.processor import SpinalSpanProcessor

        config = get_config()
        if not config:
            raise RuntimeError("Spinal SDK not configured. Call sp_obs.configure() first.")

        # Get the current global tracer provider
        current_provider = trace.get_tracer_provider()

        # Check if it's a real TracerProvider (not the default ProxyTracerProvider)
        if hasattr(current_provider, "add_span_processor"):
            try:
                current_provider.add_span_processor(SpinalSpanProcessor(config))
                return True
            except Exception as e:
                logger.warning(f"Failed to attach to existing provider: {e}")
                return False

        return False

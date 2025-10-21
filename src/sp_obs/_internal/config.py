import threading
import typing
from os import environ
import logging
from typing import Protocol, Optional

from sp_obs._internal.core.aiohttp.aiohttp import SpinalAioHttpClientInstrumentor
from sp_obs._internal.core.httpx.httpx import SpinalHTTPXClientInstrumentor
from sp_obs._internal.core.requests.requests import SpinalRequestsInstrumentor
from sp_obs._internal.core.grpc.grpc import SpinalGrpcClientInstrumentor
from sp_obs._internal.core.grpc.grpc_aio import SpinalGrpcAioClientInstrumentor
from sp_obs._internal.scrubbing import DefaultScrubber
from sp_obs._internal.tracer import SpinalTracerProvider
from opentelemetry.util.http import PARAMS_TO_REDACT

logger = logging.getLogger(__name__)


class SpinalScrubber(Protocol):
    """Protocol for scrubbing sensitive data from span attributes"""

    def scrub_attributes(self, attributes: dict[str, typing.Any]) -> dict[str, typing.Any]:
        """Scrub sensitive data from span attributes"""
        ...


_DEFAULT_SCHEDULE_DELAY_MILLIS = 5000
_DEFAULT_MAX_EXPORT_BATCH_SIZE = 512
_DEFAULT_EXPORT_TIMEOUT_MILLIS = 30000
_DEFAULT_MAX_QUEUE_SIZE = 2048
_ENV_VAR_INT_VALUE_ERROR_MESSAGE = "Unable to parse value for %s as integer. Defaulting to %s."

SPINAL_PROCESS_MAX_QUEUE_SIZE = "SPINAL_PROCESS_MAX_QUEUE_SIZE"
SPINAL_PROCESS_SCHEDULE_DELAY = "SPINAL_PROCESS_SCHEDULE_DELAY"
SPINAL_PROCESS_MAX_EXPORT_BATCH_SIZE = "SPINAL_PROCESS_MAX_EXPORT_BATCH_SIZE"
SPINAL_PROCESS_EXPORT_TIMEOUT = "SPINAL_PROCESS_EXPORT_TIMEOUT"


class SpinalConfig:
    """
    Configuration for Spinal observability integration

    Args:
        endpoint: HTTP endpoint to send spans to. Can also be set via SPINAL_TRACING_ENDPOINT env var
        api_key: API key for authentication. Can also be set via SPINAL_API_KEY env var
        headers: Optional custom headers for the HTTP request
        timeout: Request timeout in seconds (default: 30)
        scrubber: Optional scrubber instance for sensitive data redaction
    """

    def __init__(
        self,
        endpoint: typing.Optional[str] = None,
        api_key: typing.Optional[str] = None,
        headers: typing.Optional[dict[str, str]] = None,
        timeout: int = 5,
        max_queue_size: int | None = None,
        max_export_batch_size: int | None = None,
        schedule_delay_millis: float | None = None,
        export_timeout_millis: float | None = None,
        scrubber: Optional[SpinalScrubber] = None,
        opentelemetry_log_level: str = logging.ERROR,
        set_global_tracer: bool = True,
    ):
        self.endpoint = endpoint or environ.get("SPINAL_TRACING_ENDPOINT") or "https://cloud.withspinal.com"
        self.api_key = api_key or environ.get("SPINAL_API_KEY", "")
        self.headers = headers or {}
        self.timeout = timeout
        self.scrubber = scrubber or DefaultScrubber()

        self.headers = self.headers | {"X-SPINAL-API-KEY": self.api_key}

        self.max_queue_size = max_queue_size or SpinalConfig._default_max_queue_size()
        self.max_export_batch_size = max_export_batch_size or SpinalConfig._default_max_export_batch_size()
        self.schedule_delay_millis = schedule_delay_millis or SpinalConfig._default_schedule_delay_millis()
        self.export_timeout_millis = export_timeout_millis or SpinalConfig._default_export_timeout_millis()

        self.set_global_tracer = set_global_tracer

        if not self.endpoint:
            raise ValueError("Spinal endpoint must be provided either via parameter or SPINAL_TRACING_ENDPOINT env var")

        if not self.api_key:
            raise ValueError("No API key provided. Set via parameter or SPINAL_API_KEY env var")

        if not opentelemetry_log_level:
            opentelemetry_log_level = environ.get("OTEL_PYTHON_LOG_LEVEL", logging.ERROR)
        logging.getLogger("opentelemetry").setLevel(opentelemetry_log_level)

    @staticmethod
    def _default_max_queue_size():
        try:
            return int(environ.get(SPINAL_PROCESS_MAX_QUEUE_SIZE, _DEFAULT_MAX_QUEUE_SIZE))
        except ValueError:
            logger.exception(
                _ENV_VAR_INT_VALUE_ERROR_MESSAGE,
                SPINAL_PROCESS_MAX_QUEUE_SIZE,
                _DEFAULT_MAX_QUEUE_SIZE,
            )
            return _DEFAULT_MAX_QUEUE_SIZE

    @staticmethod
    def _default_schedule_delay_millis():
        try:
            return int(environ.get(SPINAL_PROCESS_SCHEDULE_DELAY, _DEFAULT_SCHEDULE_DELAY_MILLIS))
        except ValueError:
            logger.exception(
                _ENV_VAR_INT_VALUE_ERROR_MESSAGE,
                SPINAL_PROCESS_SCHEDULE_DELAY,
                _DEFAULT_SCHEDULE_DELAY_MILLIS,
            )
            return _DEFAULT_SCHEDULE_DELAY_MILLIS

    @staticmethod
    def _default_max_export_batch_size():
        try:
            return int(
                environ.get(
                    SPINAL_PROCESS_MAX_EXPORT_BATCH_SIZE,
                    _DEFAULT_MAX_EXPORT_BATCH_SIZE,
                )
            )
        except ValueError:
            logger.exception(
                _ENV_VAR_INT_VALUE_ERROR_MESSAGE,
                SPINAL_PROCESS_MAX_EXPORT_BATCH_SIZE,
                _DEFAULT_MAX_EXPORT_BATCH_SIZE,
            )
            return _DEFAULT_MAX_EXPORT_BATCH_SIZE

    @staticmethod
    def _default_export_timeout_millis():
        try:
            return int(environ.get(SPINAL_PROCESS_EXPORT_TIMEOUT, _DEFAULT_EXPORT_TIMEOUT_MILLIS))
        except ValueError:
            logger.exception(
                _ENV_VAR_INT_VALUE_ERROR_MESSAGE,
                SPINAL_PROCESS_EXPORT_TIMEOUT,
                _DEFAULT_EXPORT_TIMEOUT_MILLIS,
            )
            return _DEFAULT_EXPORT_TIMEOUT_MILLIS


class SpinalSDK:
    """Singleton SDK instance that manages configuration and tracer provider"""

    _instance: Optional["SpinalSDK"] = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
                    cls._instance.config: SpinalConfig | None = None
                    cls._instance.tracer_provider: SpinalTracerProvider | None = None
        return cls._instance

    def configure(
        self,
        *,
        endpoint: str | None = None,
        api_key: str | None = None,
        headers: dict[str, str] | None = None,
        timeout: int = 5,
        max_queue_size: int | None = None,
        max_export_batch_size: int | None = None,
        schedule_delay_millis: float | None = None,
        export_timeout_millis: float | None = None,
        scrubber: SpinalScrubber | None = None,
        set_global_tracer: bool = True,
    ) -> SpinalConfig:
        """
        Configures the global Spinal SDK settings and initializes the Spinal configuration.

        This function allows setting up various configuration parameters such as the API endpoint,
        authentication details, request headers, timeout values, batch processing options,
        debugging mode, and a data scrubber. It also initializes auto instrumentation with a
        Spinal tracer provider and logs the configuration status.

        Parameters:
        endpoint: str | None
            The API endpoint to interact with. None if not specified.
        api_key: str | None
            The API key for authentication. None if not provided.
        headers: dict[str, str] | None
            Additional headers to include in requests. None by default.
        timeout: int
            The timeout in seconds for requests. Default is 5 seconds.
        max_queue_size: int | None
            Maximum size of the request queue. None for no limit.
        max_export_batch_size: int | None
            Maximum number of events to export at one time. None if not specified.
        schedule_delay_millis: float | None
            The delay in milliseconds between scheduled task executions. None if not set.
        export_timeout_millis: float | None
            Timeout in milliseconds for exporting operations. None if not configured.
        scrubber: SpinalScrubber | None
            A configuration scrubber for cleaning sensitive data. None to disable.
        set_global_tracer: bool
            If set, will configure the global tracer provider to Spinals. Default is True.
            Turn off if you are using an observability framework that already has a global tracer provider.

        Returns:
        SpinalConfig
            The updated Spinal configuration instance.

        """
        with self._lock:
            if self._initialized:
                logger.debug("SDK already configured, returning existing configuration")
                return self.config

            self.config = SpinalConfig(
                endpoint=endpoint,
                api_key=api_key,
                headers=headers,
                timeout=timeout,
                scrubber=scrubber,
                max_queue_size=max_queue_size,
                max_export_batch_size=max_export_batch_size,
                schedule_delay_millis=schedule_delay_millis,
                export_timeout_millis=export_timeout_millis,
                set_global_tracer=set_global_tracer,
            )

            # Setup auto instrumentation
            self.tracer_provider = SpinalTracerProvider(self.config)
            SpinalAioHttpClientInstrumentor().instrument(tracer_provider=self.tracer_provider.provider)
            SpinalHTTPXClientInstrumentor().instrument(tracer_provider=self.tracer_provider.provider)
            SpinalRequestsInstrumentor().instrument(tracer_provider=self.tracer_provider.provider)
            SpinalGrpcClientInstrumentor().instrument(tracer_provider=self.tracer_provider.provider)
            SpinalGrpcAioClientInstrumentor().instrument(tracer_provider=self.tracer_provider.provider)

            # Add to params to redact util
            PARAMS_TO_REDACT.append("api_key")
            PARAMS_TO_REDACT.append("serp_api_key")

            self._initialized = True
            logger.info(f"Spinal SDK configured with endpoint: {self.config.endpoint}")
            return self.config

    def get_config(self) -> SpinalConfig:
        """Get the global Spinal configuration"""
        if not self._initialized:
            return self.configure()
        return self.config

    def get_tracer_provider(self) -> Optional[SpinalTracerProvider]:
        """Get the tracer provider, returns None if not configured"""
        return self.tracer_provider

    def is_configured(self) -> bool:
        """Check if SDK is configured"""
        return self._initialized


# Create the singleton instance
_sdk = SpinalSDK()


def configure(**kwargs) -> SpinalConfig:
    """Configure the global Spinal SDK instance"""
    return _sdk.configure(**kwargs)


def get_tracer_provider():
    """Get the configured tracer provider"""
    return _sdk.get_tracer_provider()


def get_config() -> SpinalConfig:
    """Get the global Spinal configuration"""
    return _sdk.get_config()

import typing
from os import environ
import logging
from typing import Protocol, Optional

from sp_obs._internal.scrubbing import DefaultScrubber

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


_global_config: Optional[SpinalConfig] = None


def configure(
    endpoint: str | None = None,
    api_key: str | None = None,
    headers: dict[str, str] | None = None,
    timeout: int = 5,
    max_queue_size: int | None = None,
    max_export_batch_size: int | None = None,
    schedule_delay_millis: float | None = None,
    export_timeout_millis: float | None = None,
    scrubber: SpinalScrubber | None = None,
) -> SpinalConfig:
    """
    Configures the global Spinal SDK with the provided arguments to set up communication
    and behavior for data export. This method initializes and returns a global SpinalConfig
    object with the specified configuration.

    Parameters:
        endpoint (str | None): The endpoint URL for the Spinal SDK. Defaults to None.
        api_key (str | None): The API key for authenticating with the endpoint. Defaults to None.
        headers (dict[str, str] | None): A dictionary of custom headers to include in each request. Defaults to None.
        timeout (int): The timeout in seconds for requests to the endpoint. Defaults to 5.
        max_queue_size (int | None): The maximum allowed size of the internal queue. Defaults to None.
        max_export_batch_size (int | None): The maximum number of items to include in an export batch. Defaults to None.
        schedule_delay_millis (float | None): The delay in milliseconds between scheduled exports. Defaults to None.
        export_timeout_millis (float | None): The timeout in milliseconds for export operations. Defaults to None.
        scrubber (SpinalScrubber | None): An instance of SpinalScrubber to clean or preprocess data as required.
                                          Defaults to None.

    Returns:
        SpinalConfig: An instance of SpinalConfig with the provided configuration.
    """
    global _global_config

    _global_config = SpinalConfig(
        endpoint=endpoint,
        api_key=api_key,
        headers=headers,
        timeout=timeout,
        scrubber=scrubber,
        max_queue_size=max_queue_size,
        max_export_batch_size=max_export_batch_size,
        schedule_delay_millis=schedule_delay_millis,
        export_timeout_millis=export_timeout_millis,
    )
    logger.info(f"Spinal SDK configured with endpoint: {_global_config.endpoint}")
    return _global_config


def get_config() -> SpinalConfig:
    """Get the global Spinal configuration"""
    if not _global_config:
        return configure()
    return _global_config

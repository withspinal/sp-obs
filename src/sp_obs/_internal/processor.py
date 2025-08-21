import logging
import typing
from enum import StrEnum

from opentelemetry import baggage, trace
from opentelemetry.sdk.trace import ReadableSpan, Span
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from sp_obs._internal import SPINAL_NAMESPACE
from sp_obs._internal.exporter import SpinalSpanExporter

logger = logging.getLogger(__name__)


class SpanType(StrEnum):
    """Enum for the different types of spans"""

    GEN_AI = "gen_ai"
    HTTPX = "httpx"
    UNKNOWN = "unknown"


EXCLUDED_URLS = {
    "api.openai.com",
    "api.anthropic.com",
    "api.azure.com/openai",
}


class SpinalSpanProcessor(BatchSpanProcessor):
    """Processes spans and forwards them to the custom exporter"""

    def __init__(
        self,
        max_queue_size: int,
        schedule_delay_millis: float,
        max_export_batch_size: int,
        export_timeout_millis: float,
    ):
        """
        Parameters:
            max_queue_size: int
                The maximum number of spans allowed in the queue. When the queue is full, additional spans are dropped.

            schedule_delay_millis: float
                The delay in milliseconds before processing the batch of spans. Only triggers if max_export_batch_size is not reached

            max_export_batch_size: int
                The maximum number of spans to be exported in a single batch. When this number is reached, an export is triggered.

            export_timeout_millis: float
                The timeout in milliseconds for exporting spans.
        """

        self.exporter = SpinalSpanExporter()
        super().__init__(
            self.exporter,
            max_queue_size=max_queue_size,
            schedule_delay_millis=schedule_delay_millis,
            max_export_batch_size=max_export_batch_size,
            export_timeout_millis=export_timeout_millis,
        )

    def _should_process(self, span: ReadableSpan | Span) -> bool:
        """
        Determines whether a given span should be processed or not based on its type
        and attributes.
        """
        if not span.name.startswith("spinal"):
            return False

        if not span.attributes.get("spinal.provider"):
            return False
        return True

    def on_start(self, span: Span, parent_context: typing.Optional[trace.Context] = None) -> None:
        """Called when a span is started"""
        if not self._should_process(span):
            return

        # Ensure we add baggage
        current_baggage = baggage.get_all(parent_context)
        if current_baggage:
            for key, value in current_baggage.items():
                if key.startswith(f"{SPINAL_NAMESPACE}"):
                    span.set_attribute(f"{key}", str(value))

    def on_end(self, span: ReadableSpan) -> None:
        """Called when a span is ended - this is where we intercept"""
        if not self._should_process(span):
            return

        # Do not call the super().on_end as that function respects the sampling rate.
        self._batch_processor.emit(span)

    def shutdown(self) -> None:
        """Shutdown the processor"""
        self.force_flush()

        self.exporter.shutdown()
        super().shutdown()

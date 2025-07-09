"""
SP-OBS: OpenTelemetry Span Interceptor
Automatically attaches to existing TracerProvider to duplicate spans to custom endpoints
"""

import typing
import contextvars
import logging
import uuid
import requests
from opentelemetry import trace, baggage
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult
import os
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import Span
from logfire import set_baggage

logger = logging.getLogger(__name__)

# Create a context key for user data that propagates with traces
TRACE_CONTEXT = contextvars.ContextVar("spinal_context", default={})


class SpinalConfig:
    """
    Configuration for Spinal observability integration

    Args:
        endpoint: HTTP endpoint to send spans to. Can also be set via SPINAL_TRACING_ENDPOINT env var
        api_key: API key for authentication. Can also be set via SPINAL_API_KEY env var
        headers: Optional custom headers for the HTTP request
        timeout: Request timeout in seconds (default: 30)
        batch_size: Batch size for span export (default: 100)
    """

    def __init__(
        self,
        endpoint: typing.Optional[str] = None,
        api_key: typing.Optional[str] = None,
        headers: typing.Optional[dict[str, str]] = None,
        timeout: int = 5,
        batch_size: int = 100,
    ):
        self.endpoint = endpoint or os.getenv("SPINAL_TRACING_ENDPOINT", "")
        self.api_key = api_key or os.getenv("SPINAL_API_KEY", "")
        self.headers = headers or {}
        self.timeout = timeout
        self.batch_size = batch_size

        self.headers = self.headers | {"X-SPINAL-API-KEY": os.getenv("SPINAL_API_KEY", "")}

        if not self.endpoint:
            raise ValueError("Spinal endpoint must be provided either via parameter or SPINAL_TRACING_ENDPOINT env var")

        if not self.api_key:
            logger.warning("No API key provided. Set via parameter or SPINAL_API_KEY env var")


BILLING_EVENT_SPAN_NAME = "spinal_billable_event"
USER_CONTEXT_SPAN_NAME = "spinal_user_context"
WORKFLOW_CONTEXT_SPAN_NAME = "spinal_workflow_context"


class SpinalSpanExporter(SpanExporter):
    """Exports spans to a custom HTTP endpoint"""

    def __init__(self, config: SpinalConfig | None):
        self.endpoint = config.endpoint
        self.headers = config.headers
        self.timeout = config.timeout
        self.batch_size = config.batch_size
        self._shutdown = False

    def export(self, spans: list[ReadableSpan]) -> SpanExportResult:
        if self._shutdown:
            return SpanExportResult.FAILURE

        try:
            # Convert spans to JSON-serializable format
            span_data = []
            for span in spans:
                # Extract baggage context from the current context
                current_baggage = {}
                try:
                    # Get workflow_id from baggage if available
                    if workflow_id := baggage.get_baggage("workflow_id"):
                        current_baggage["workflow_id"] = workflow_id

                    # Get user context from baggage if available
                    if user_context := baggage.get_baggage("spinal_user_context"):
                        current_baggage["spinal_user_context"] = user_context
                except Exception as e:
                    logger.debug(f"Could not extract baggage context: {e}")

                # Merge span attributes with baggage context
                combined_attributes = dict(span.attributes) if span.attributes else {}
                if current_baggage:
                    combined_attributes.update({f"baggage.{k}": v for k, v in current_baggage.items()})

                span_dict = {
                    "name": span.name,
                    "trace_id": format(span.get_span_context().trace_id, "032x"),
                    "span_id": format(span.get_span_context().span_id, "016x"),
                    "parent_span_id": format(span.parent.span_id, "016x") if span.parent else None,
                    "start_time": span.start_time,
                    "end_time": span.end_time,
                    "status": {"status_code": span.status.status_code.name, "description": span.status.description}
                    if span.status
                    else None,
                    "attributes": combined_attributes,
                    "events": [
                        {
                            "name": event.name,
                            "timestamp": event.timestamp,
                            "attributes": dict(event.attributes) if event.attributes else {},
                        }
                        for event in span.events
                    ]
                    if span.events
                    else [],
                    "links": [
                        {
                            "context": {
                                "trace_id": format(link.context.trace_id, "032x"),
                                "span_id": format(link.context.span_id, "016x"),
                            },
                            "attributes": dict(link.attributes) if link.attributes else {},
                        }
                        for link in span.links
                    ]
                    if span.links
                    else [],
                    "resource": dict(span.resource.attributes) if span.resource else {},
                    "instrumentation_info": {
                        "name": span.instrumentation_scope.name,
                        "version": span.instrumentation_scope.version,
                    }
                    if span.instrumentation_scope
                    else None,
                }
                span_data.append(span_dict)

            response = requests.post(
                self.endpoint, json={"spans": span_data}, headers=self.headers, timeout=self.timeout
            )

            if 200 <= response.status_code < 300:
                logger.debug(f"Successfully exported {len(spans)} spans to {self.endpoint}")
                return SpanExportResult.SUCCESS
            else:
                logger.error(f"Failed to export spans. Status: {response.status_code}, Response: {response.text}")
                return SpanExportResult.FAILURE

        except Exception as e:
            logger.error(f"Error exporting spans: {e}")
            return SpanExportResult.FAILURE

    def shutdown(self) -> None:
        self._shutdown = True


class SpinalSpanProcessor(BatchSpanProcessor):
    """Processes spans and forwards them to the custom exporter"""

    def __init__(self, config: SpinalConfig | None = None, **kwargs):
        if not config:
            config = SpinalConfig()

        self.exporter = SpinalSpanExporter(config)
        super().__init__(self.exporter, **kwargs)

    def _should_process(self, span: ReadableSpan | Span) -> bool:
        gen_ai_span = span.attributes.get("gen_ai.system") is not None
        billing_event = span.name == BILLING_EVENT_SPAN_NAME

        if any([gen_ai_span, billing_event]):
            return True

        logger.debug(f"Skipping span {span.name} - not a relevant spinal span")
        return False

    def on_start(self, span: Span, parent_context: typing.Optional[trace.Context] = None) -> None:
        """Called when a span is started"""
        if not self._should_process(span):
            return

    def on_end(self, span: ReadableSpan) -> None:
        """Called when a span is ended - this is where we intercept"""
        if not self._should_process(span):
            return
        self._batch_processor.emit(span)

    def shutdown(self) -> None:
        """Shutdown the processor"""
        super().shutdown()


def spinal_add_as_billable(attributes: typing.Optional[dict[str, typing.Any]] = None):
    """
    Add information on the trace that allows us to track it across our billing engine
    """
    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span(BILLING_EVENT_SPAN_NAME) as billing_span:
        # Mark this as a billable span
        trace_id = billing_span.get_span_context().trace_id

        billing_span.set_attribute("billable", True)
        billing_span.set_attribute("billing_trace_id", format(trace_id, "032x"))

        # Add any custom attributes
        if attributes:
            for key, value in attributes.items():
                billing_span.set_attribute(f"user_attr.{key}", value)

        # This span will auto-end and be sent to your processor
        logger.debug(f"Created billable event span with attributes: {attributes}")


def spinal_add_context(*, workflow_id: typing.Union[int, str, uuid.UUID], user_id: typing.Union[int, str, uuid.UUID]):
    """
    Utility function to allow a user to add context to a trace so that spinal can trace what is happening across the stack.
    Baggage will need to be set here so that distributed tracking can take effect.
    """

    baggage_to_add = {"workflow_id": str(workflow_id), "spinal_user_context.id": user_id}
    return set_baggage(**baggage_to_add)


def _init_logfire(api_key: str | None = None, tracing_endpoint: str | None = None):
    import logfire

    if logfire.DEFAULT_LOGFIRE_INSTANCE.config._initialized:
        logger.debug("Logfire is already initialized - attaching Spinal span processor")
        tracing_provider = logfire.DEFAULT_LOGFIRE_INSTANCE.config.get_tracer_provider()
        tracing_provider.add_span_processor(
            SpinalSpanProcessor(SpinalConfig(endpoint=tracing_endpoint, api_key=api_key))
        )
        return

    else:
        logfire.configure(
            send_to_logfire=False,
            additional_span_processors=[SpinalSpanProcessor(SpinalConfig(endpoint=tracing_endpoint, api_key=api_key))],
        )


def configure_for_openai_agents(api_key: str | None = None, tracing_endpoint: str | None = None):
    """
    Configure Spinal to trace OpenAI agents
    """
    import logfire

    _init_logfire(api_key=api_key, tracing_endpoint=tracing_endpoint)

    logfire.instrument_openai_agents()

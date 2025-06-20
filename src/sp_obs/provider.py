"""
SP-OBS: OpenTelemetry Span Interceptor
Automatically attaches to existing TracerProvider to duplicate spans to custom endpoints
"""

import typing
import atexit
import contextvars
import logging
import uuid
from threading import Lock
import functools
import asyncio
import requests
from opentelemetry import trace
from opentelemetry.sdk.trace import SpanProcessor, ReadableSpan
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult
import os

if typing.TYPE_CHECKING:
    pass

from opentelemetry.trace import Span

logger = logging.getLogger(__name__)

# Create a context key for user data that propagates with traces
TRACE_USER_CONTEXT = contextvars.ContextVar("spinal_user_context", default={})

BILLING_EVENT_SPAN_NAME = "spinal_billable_event"
USER_CONTEXT_SPAN_NAME = "spinal_user_context"
WORKFLOW_CONTEXT_SPAN_NAME = "spinal_workflow_context"


class SpinalSpanExporter(SpanExporter):
    """Exports spans to a custom HTTP endpoint"""

    def __init__(
        self, endpoint: str, headers: typing.Optional[dict[str, str]] = None, timeout: int = 30, batch_size: int = 100
    ):
        self.endpoint = endpoint
        self.headers = (headers or {}) | {"X-SPINAL-API-KEY": os.getenv("SPINAL_API_KEY", "")}
        self.timeout = timeout
        self.batch_size = batch_size
        self._shutdown = False

    def export(self, spans: list[ReadableSpan]) -> SpanExportResult:
        if self._shutdown:
            return SpanExportResult.FAILURE

        try:
            # Convert spans to JSON-serializable format
            span_data = []
            for span in spans:
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
                    "attributes": dict(span.attributes) if span.attributes else {},
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

            # Send to endpoint
            print(f"span_data: {span_data}")
            return
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


class SpinalSpanProcessor(SpanProcessor):
    """Processes spans and forwards them to the custom exporter"""

    def __init__(self, exporter: SpinalSpanExporter):
        self.exporter = exporter
        self._lock = Lock()
        self._span_buffer: list[ReadableSpan] = []

    def on_start(self, span: Span, parent_context: typing.Optional[trace.Context] = None) -> None:
        """Called when a span is started"""
        trace_id = span.get_span_context().trace_id
        all_contexts = TRACE_USER_CONTEXT.get()

        spinal_context = all_contexts.get(trace_id, {})
        if spinal_context:
            if workflow := spinal_context.get("workflow_id"):
                span.set_attribute("spinal.workflow_id", workflow)

    def on_end(self, span: ReadableSpan) -> None:
        """Called when a span is ended - this is where we intercept"""
        # We only care about spans from gen_ai sources right now.
        # opentel semantics can be found here https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-spans/

        # Allow gen.ai and billable events to be exported
        gen_ai_span = span.attributes.get("gen_ai.system") is not None
        billing_event = span.name == BILLING_EVENT_SPAN_NAME
        user_context_span = span.name == USER_CONTEXT_SPAN_NAME

        if not any([gen_ai_span, billing_event, user_context_span]):
            logger.debug(f"Skipping span {span.name} - not a relevant spinal span")
            return

        with self._lock:
            self._span_buffer.append(span)

            # Export immediately (no batching)
            # For simplicity, we'll export immediately
            result = self.exporter.export([span])
            if result == SpanExportResult.SUCCESS:
                self._span_buffer.clear()

    def shutdown(self) -> None:
        """Shutdown the processor"""
        # Export any remaining spans
        with self._lock:
            if self._span_buffer:
                self.exporter.export(self._span_buffer)
                self._span_buffer.clear()
        self.exporter.shutdown()

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        """Force flush any pending spans"""
        with self._lock:
            if self._span_buffer:
                result = self.exporter.export(self._span_buffer)
                if result == SpanExportResult.SUCCESS:
                    self._span_buffer.clear()
                    return True
        return False


class SpanInterceptor:
    """Main class for intercepting spans"""

    _instance = None
    _lock = Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, "_initialized"):
            self._initialized = True
            self._processors: list[SpinalSpanProcessor] = []
            self._attached = False

    def attach_to_provider(
        self, *, endpoint: str, headers: typing.Optional[dict[str, str]] = None, api_key: str
    ) -> bool:
        """
        Attach custom span processor to existing TracerProvider

        Args:
            endpoint: HTTP endpoint to send spans to
            headers: Optional headers for the HTTP request
            api_key: Optional API key for authentication

        Returns:
            bool: True if successfully attached, False otherwise
        """
        try:
            tracer_provider = trace.get_tracer_provider()

            # Check for open telemetry providers
            if hasattr(tracer_provider, "add_span_processor"):
                exporter = SpinalSpanExporter(endpoint, headers)
                processor = SpinalSpanProcessor(exporter)

                # Add processor to provider - this processor will handle ALL spans from instrumentation tools
                tracer_provider.add_span_processor(processor)

                self._processors.append(processor)
                self._attached = True

                # Register shutdown handler
                atexit.register(self._shutdown)

                logger.info(f"Successfully attached span interceptor to TracerProvider. Endpoint: {endpoint}")
                return True
            else:
                logger.warning(
                    "Current TracerProvider doesn't support adding processors. "
                    "Make sure OpenTelemetry SDK is properly initialized."
                )
                return False

        except Exception as e:
            logger.error(f"Failed to attach span interceptor: {e}")
            return False

    def _shutdown(self):
        """Cleanup on exit"""
        for processor in self._processors:
            try:
                processor.shutdown()
            except Exception as e:
                logger.error(f"Error shutting down processor: {e}")

    def is_attached(self) -> bool:
        """Check if interceptor is attached to a provider"""
        return self._attached


# Singleton instance
_interceptor = SpanInterceptor()


def init(
    *, endpoint: str = "", headers: typing.Optional[dict[str, str]] = None, api_key: str = "", log_level: str = "INFO"
) -> SpanInterceptor:
    """
    Initialize the span interceptor

    Args:
        endpoint: HTTP endpoint to send spans to
        headers: Optional headers for the HTTP request
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)

    Returns:
        SpanInterceptor instance

    Example:
        import sp_obs

        # Initialize and auto-attach
        sp_obs.init("https://my-observability-endpoint.com/spans",
                   headers={"Authorization": "Bearer token"})
    """
    logging.basicConfig(level=getattr(logging, log_level.upper()))

    if not api_key:
        api_key = os.getenv("SPINAL_API_KEY", "")

    if not endpoint:
        endpoint = os.getenv("SPINAL_TRACING_ENDPOINT", "")

    _interceptor.attach_to_provider(endpoint=endpoint, headers=headers, api_key=api_key)

    return _interceptor


def is_attached() -> bool:
    """Check if the interceptor is attached"""
    return _interceptor.is_attached()


def add_user_context_1(mapped_user_id: str, attributes: typing.Optional[dict[str, typing.Any]] = None):
    """
    Add user context directly to the current span and all child spans

    Args:
        mapped_user_id: The user identifier to propagate
        attributes: Optional dictionary of additional user attributes
    """
    # Get the current span
    current_span = trace.get_current_span()

    if not current_span or current_span == trace.INVALID_SPAN:
        logger.warning("No active span found - user context will not be attached")
        return

    user_context = {"id": mapped_user_id, **(attributes or {})}
    trace_id = current_span.get_span_context().trace_id

    # Get current contexts and add this trace's context
    current_contexts = TRACE_USER_CONTEXT.get().copy()
    current_contexts[trace_id] = {"user": user_context}
    TRACE_USER_CONTEXT.set(current_contexts)
    logger.debug(f"Set user context on span: {mapped_user_id} with attributes: {attributes}")


def add_user_context(mapped_user_id: str, attributes: typing.Optional[dict[str, typing.Any]] = None):
    """
    Add user context directly to the current span and all child spans

    Args:
        mapped_user_id: The user identifier to propagate
        attributes: Optional dictionary of additional user attributes
    """
    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span(USER_CONTEXT_SPAN_NAME) as user_context_span:
        user_context_span.set_attribute("id", mapped_user_id)
        for key, value in (attributes or {}).items():
            user_context_span.set_attribute(f"attr.{key}", value)

    logger.debug("Created user context span")


def add_as_billable(attributes: typing.Optional[dict[str, typing.Any]] = None):
    """
    Add information on the trace that allows us to track it across our billing engine
    """
    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span("spinal_billable_event") as billing_span:
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


def spinal_tag_workflow(workflow_id: typing.Union[int, str, uuid.UUID]) -> typing.Callable:
    """
    Decorator to tag spans with a workflow ID

    Args:
        workflow_id: The workflow identifier to attach to the trace context

    Example:
        @spinal_tag_workflow(workflow_id=12345)
        @app.post("/ask")
        async def ask_question(request: QuestionRequest):
            pass
    """

    def _add_workflow_to_context():
        tracer = trace.get_tracer(__name__)
        with tracer.start_as_current_span(WORKFLOW_CONTEXT_SPAN_NAME) as span:
            span.set_attribute("workflow_id", str(workflow_id))

    def decorator(func: typing.Callable) -> typing.Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            _add_workflow_to_context()
            return await func(*args, **kwargs)

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            _add_workflow_to_context()
            return func(*args, **kwargs)

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator

"""
Spinal's async gRPC client instrumentation.

Wraps OpenTelemetry's async gRPC instrumentation to create parallel Spinal spans
for supported gRPC services, capturing metadata only (no binary payloads).

This follows the same pattern as sync gRPC and HTTP instrumentors:
1. Check if the service matches known patterns
2. Create child spans only for matched services
3. Capture metadata: service name, method, status, headers
4. Set spinal.provider attribute for processor filtering
"""

import logging
from weakref import WeakKeyDictionary

from opentelemetry import context, trace
from opentelemetry.instrumentation.grpc import GrpcAioInstrumentorClient
from opentelemetry.trace import Status, StatusCode, get_tracer

from sp_obs._internal.constants import SPINAL_GRPC_ASYNC_REQUEST_SPAN_NAME
from sp_obs._internal.core.grpc.grpc_integrations import match_grpc_service
from sp_obs._internal.core.grpc.grpc_utils import (
    _add_response_metadata,
    _extract_grpc_metadata,
    _extract_service_name,
)

logger = logging.getLogger(__name__)

_aio_child_spans: WeakKeyDictionary = WeakKeyDictionary()


class SpinalGrpcAioClientInstrumentor(GrpcAioInstrumentorClient):
    """
    Spinal's async gRPC client instrumentor that wraps OpenTelemetry's async gRPC instrumentation.

    Creates parallel child spans for supported gRPC services (identified via service
    pattern matching), capturing metadata only without binary request/response data.

    Supports UnaryUnary and StreamUnary call patterns (both return single responses).
    """

    def _instrument(self, **kwargs):
        """Instrument async gRPC client using request_hook and response_hook"""
        provider = kwargs.get("tracer_provider")
        tracer = get_tracer(__name__, tracer_provider=provider)

        user_request_hook = kwargs.get("request_hook")
        user_response_hook = kwargs.get("response_hook")

        def spinal_request_hook(span, request):
            """
            Hook called on request start.

            Creates a Spinal child span only for supported gRPC services,
            capturing metadata (service, method, etc.) but no binary payloads.
            """
            # Call user's hook first if provided
            if user_request_hook:
                try:
                    user_request_hook(span, request)
                except Exception as e:
                    logger.warning(f"User request_hook failed: {e}")

            try:
                service_name = _extract_service_name(span)
                if not service_name:
                    return

                # Check if this service matches any known pattern
                provider_name = match_grpc_service(service_name)
                if not provider_name:
                    return

                # Get current context and parent span timing
                parent_context = context.get_current()
                parent_span = trace.get_current_span(parent_context)
                parent_start_time = (
                    parent_span.start_time if parent_span and hasattr(parent_span, "start_time") else None
                )
                parent_attrs = _extract_grpc_metadata(span, provider_name)

                spinal_span = tracer.start_span(
                    SPINAL_GRPC_ASYNC_REQUEST_SPAN_NAME,
                    context=parent_context,
                    start_time=parent_start_time,
                    attributes=parent_attrs,
                )

                # Store child span reference for completion in response_hook/callback
                _aio_child_spans[span] = spinal_span

            except Exception as e:
                logger.error(f"Spinal async request_hook error: {e}", exc_info=True)

        def spinal_response_hook(span, response):
            """
            Hook called on response.

            Completes the Spinal child span by adding response metadata
            (status, error messages) and ending the span.

            Note: For async calls, this is typically called from the done_callback
            after the RPC completes.
            """
            child_span = _aio_child_spans.get(span)

            if child_span:
                try:
                    # _add_response_metadata sets the status based on gRPC status code
                    _add_response_metadata(child_span, span)
                    child_span.end()

                except Exception as e:
                    logger.error(f"Spinal async response_hook error: {e}", exc_info=True)
                    child_span.set_status(Status(StatusCode.ERROR, str(e)))
                    child_span.end()
                finally:
                    del _aio_child_spans[span]

            if user_response_hook:
                try:
                    user_response_hook(span, response)
                except Exception as e:
                    logger.warning(f"User response_hook failed: {e}")

        # Replace hooks in kwargs with our wrapped versions
        kwargs["request_hook"] = spinal_request_hook
        kwargs["response_hook"] = spinal_response_hook
        super()._instrument(**kwargs)

    def _uninstrument(self, **kwargs):
        """Remove instrumentation"""
        super()._uninstrument(**kwargs)

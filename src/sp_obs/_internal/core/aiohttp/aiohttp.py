"""aiohttp client instrumentation for Spinal observability."""

import types
from urllib.parse import urlparse

import aiohttp
import opentelemetry.instrumentation.aiohttp_client
from opentelemetry import trace, context
from opentelemetry.trace import SpanKind, Status, StatusCode, get_tracer
from opentelemetry.util.http import redact_url

from sp_obs._internal.core.recognised_integrations import supported_host
from sp_obs.utils import add_request_params_to_span


class SpinalAioHttpClientInstrumentor(opentelemetry.instrumentation.aiohttp_client.AioHttpClientInstrumentor):
    """Custom aiohttp client instrumentor that creates parallel Spinal spans."""

    def _instrument(self, **kwargs):
        """
        Instrument aiohttp client by wrapping create_trace_config.

        This approach creates parallel Spinal spans alongside OpenTelemetry spans,
        allowing us to capture data and filter by supported integrations without
        interfering with existing instrumentation.
        """
        provider = kwargs.get("tracer_provider")
        tracer = get_tracer(__name__, tracer_provider=provider)

        # Store reference to original create_trace_config
        original_create_trace_config = opentelemetry.instrumentation.aiohttp_client.create_trace_config

        def wrapped_create_trace_config(*args, **kwargs):
            """
            Wrapper for create_trace_config that adds Spinal-specific callbacks.

            Calls the original create_trace_config first, then enhances the returned
            TraceConfig with our own callbacks for supported integrations.
            """
            # Call original to get base trace_config with all OTel functionality
            base_trace_config = original_create_trace_config(*args, **kwargs)

            # Define our Spinal-specific callbacks
            async def spinal_on_request_start(
                session: aiohttp.ClientSession,
                trace_config_ctx: types.SimpleNamespace,
                params: aiohttp.TraceRequestStartParams,
            ):
                """Create Spinal span for supported integrations at request start."""
                # Get URL and check if this is a supported integration
                url = str(params.url)
                redacted_url = redact_url(url)
                location = urlparse(redacted_url)

                integration_provider = supported_host(location.hostname)
                if not integration_provider:
                    # Not a supported integration, skip Spinal span creation
                    trace_config_ctx.spinal_span = None
                    trace_config_ctx.spinal_token = None
                    return

                parent_context = context.get_current()
                parent_span = trace.get_current_span(parent_context)
                parent_start_time = (
                    parent_span.start_time if parent_span and hasattr(parent_span, "start_time") else None
                )

                span_attributes = {
                    "http.url": redacted_url,
                    "http.host": location.hostname,
                    "spinal.provider": integration_provider,
                    "http.method": params.method,
                }
                spinal_span = tracer.start_span(
                    "spinal.aiohttp",
                    kind=SpanKind.CLIENT,
                    attributes=span_attributes,
                    context=parent_context,
                    start_time=parent_start_time,
                )

                # Add request parameters to span
                add_request_params_to_span(spinal_span, redacted_url)

                if hasattr(params, "data") and params.data:
                    if isinstance(params.data, bytes):
                        spinal_span.set_attribute("spinal.request.binary_data", memoryview(params.data))
                    elif isinstance(params.data, str):
                        spinal_span.set_attribute("spinal.request.binary_data", memoryview(params.data.encode()))

                # Store span in context for later callbacks
                trace_config_ctx.spinal_span = spinal_span
                trace_config_ctx.spinal_token = context.attach(trace.set_span_in_context(spinal_span))

                # Initialize response chunks storage and tracking
                trace_config_ctx.spinal_response_chunks = []
                trace_config_ctx.spinal_span_ended = False

            async def spinal_on_response_chunk_received(
                session: aiohttp.ClientSession,
                trace_config_ctx: types.SimpleNamespace,
                params: aiohttp.TraceResponseChunkReceivedParams,
            ):
                """Collect response body chunks as they arrive and end span when complete."""
                if not hasattr(trace_config_ctx, "spinal_span") or trace_config_ctx.spinal_span is None:
                    return

                if getattr(trace_config_ctx, "spinal_span_ended", False):
                    return

                spinal_span = trace_config_ctx.spinal_span
                stream_reader = trace_config_ctx.response_stream_reader

                # Collect chunk
                if hasattr(trace_config_ctx, "spinal_response_chunks"):
                    trace_config_ctx.spinal_response_chunks.append(params.chunk)

                if stream_reader.at_eof():
                    response_body = b"".join(trace_config_ctx.spinal_response_chunks)
                    spinal_span.set_attribute("spinal.response.binary_data", memoryview(response_body))
                    spinal_span.set_attribute("spinal.response.size", len(response_body))

                    # Set span status and end
                    spinal_span.set_status(Status(StatusCode.OK))
                    if hasattr(trace_config_ctx, "spinal_token") and trace_config_ctx.spinal_token:
                        context.detach(trace_config_ctx.spinal_token)
                    spinal_span.end()
                    trace_config_ctx.spinal_span_ended = True

            async def spinal_on_request_end(
                session: aiohttp.ClientSession,
                trace_config_ctx: types.SimpleNamespace,
                params: aiohttp.TraceRequestEndParams,
            ):
                """Capture response metadata when headers are received."""
                if not hasattr(trace_config_ctx, "spinal_span") or trace_config_ctx.spinal_span is None:
                    return

                if getattr(trace_config_ctx, "spinal_span_ended", False):
                    return

                trace_config_ctx.response_stream_reader = params.response.content
                spinal_span = trace_config_ctx.spinal_span

                if params.response:
                    spinal_span.set_attribute("http.status_code", params.response.status)

                    # Capture response headers
                    if hasattr(params.response, "headers"):
                        for header_name, header_value in params.response.headers.items():
                            spinal_span.set_attribute(f"spinal.http.response.header.{header_name}", header_value)

                        content_type = params.response.headers.get("content-type", "")
                        encoding = params.response.headers.get("content-encoding", "")
                        spinal_span.set_attribute("content-type", content_type)
                        spinal_span.set_attribute("content-encoding", encoding)

                # Check if there's no body expected (Content-Length: 0 or status 204/304)
                # In these cases, on_response_chunk_received won't be called, so end span here
                content_length = params.response.headers.get("content-length")
                if (content_length == "0") or (params.response and params.response.status in (204, 304)):
                    spinal_span.set_status(Status(StatusCode.OK))
                    if hasattr(trace_config_ctx, "spinal_token") and trace_config_ctx.spinal_token:
                        context.detach(trace_config_ctx.spinal_token)
                    spinal_span.end()
                    trace_config_ctx.spinal_span_ended = True

            async def spinal_on_request_exception(
                session: aiohttp.ClientSession,
                trace_config_ctx: types.SimpleNamespace,
                params: aiohttp.TraceRequestExceptionParams,
            ):
                """End Spinal span on request exception."""
                if not hasattr(trace_config_ctx, "spinal_span") or trace_config_ctx.spinal_span is None:
                    return

                # Skip if span already ended
                if getattr(trace_config_ctx, "spinal_span_ended", False):
                    return

                spinal_span = trace_config_ctx.spinal_span

                # Record exception
                if params.exception:
                    spinal_span.record_exception(params.exception)
                    spinal_span.set_status(Status(StatusCode.ERROR, str(params.exception)))

                # Detach context and end span
                if hasattr(trace_config_ctx, "spinal_token") and trace_config_ctx.spinal_token:
                    context.detach(trace_config_ctx.spinal_token)
                spinal_span.end()
                trace_config_ctx.spinal_span_ended = True

            # Append our callbacks to the trace config
            # These run alongside the original OTel callbacks
            base_trace_config.on_request_start.append(spinal_on_request_start)
            base_trace_config.on_response_chunk_received.append(spinal_on_response_chunk_received)
            base_trace_config.on_request_end.append(spinal_on_request_end)
            base_trace_config.on_request_exception.append(spinal_on_request_exception)

            return base_trace_config

        # Replace create_trace_config with our wrapper
        opentelemetry.instrumentation.aiohttp_client.create_trace_config = wrapped_create_trace_config

        # Call parent instrumentation to set up the base aiohttp instrumentation
        super()._instrument(**kwargs)

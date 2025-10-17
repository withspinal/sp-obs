import io
from functools import wraps
from urllib.parse import urlparse
import opentelemetry.instrumentation.requests
from opentelemetry.trace import Status, StatusCode, get_tracer
from opentelemetry.util.http import redact_url
from requests import PreparedRequest, Session

from sp_obs._internal.core.recognised_integrations import supported_host
from sp_obs.utils import add_request_params_to_span


class SpinalRequestsInstrumentor(opentelemetry.instrumentation.requests.RequestsInstrumentor):
    def _instrument(self, **kwargs):
        provider = kwargs.get("tracer_provider")
        tracer = get_tracer(__name__, tracer_provider=provider)

        def wrap_raw_stream(response, span):
            """Wrap the raw response stream for direct raw access"""
            original_raw = response.raw

            class CapturingRaw:
                def __init__(self, raw):
                    self._raw = raw
                    self._captured_data = io.BytesIO()

                def read(self, amt=None):
                    data = self._raw.read(amt)
                    if data:
                        self._captured_data.write(data)
                        if not hasattr(response, "_captured_chunks"):
                            response._captured_chunks = []
                        response._captured_chunks.append(data)
                    else:
                        # EOF reached - update span with captured content
                        response._captured_content = self._captured_data.getvalue()
                        response._capture_completed = True
                        # Update span with the captured data
                        span.set_attribute("spinal.response.binary_data", memoryview(response._captured_content))
                        span.set_attribute("spinal.response.size", len(response._captured_content))
                    return data

                def __getattr__(self, name):
                    return getattr(self._raw, name)

            response.raw = CapturingRaw(original_raw)

        def wrap_streaming_response(response, span):
            """Wrap streaming response methods to capture content as it's consumed"""

            # Store original methods
            original_iter_content = response.iter_content

            # Initialize capture storage
            response._captured_chunks = []
            response._capture_completed = False

            @wraps(original_iter_content)
            def wrapped_iter_content(chunk_size=1, decode_unicode=False):
                """Wrapped iter_content that captures chunks"""
                for chunk in original_iter_content(chunk_size, decode_unicode):
                    response._captured_chunks.append(chunk)
                    yield chunk

                response._captured_content = b"".join(response._captured_chunks)
                response._capture_completed = True
                response._captured_chunks = []

                span.set_attribute("spinal.response.binary_data", memoryview(response._captured_content))
                span.set_attribute("spinal.response.size", len(response._captured_content))
                span.set_attribute("spinal.response.capture_method", "iter_content")
                # End the span now that we have the complete response
                span.end()

            # Wrap raw access too
            if hasattr(response, "raw") and response.raw:
                wrap_raw_stream(response, span)
            response.iter_content = wrapped_iter_content

            # Also wrap the content property for mixed access patterns
            original_content_property = response.__class__.content.fget

            def content_getter(self):
                content = original_content_property(self)
                if not span.is_recording():
                    return content

                span.set_attribute("spinal.response.binary_data", memoryview(content))
                span.set_attribute("spinal.response.size", len(content))
                span.set_attribute("spinal.response.capture_method", "content_property")
                return content

            # Create a new property descriptor for this specific response instance
            response.__class__.content = property(content_getter)

        def wrap_session_send(original_send):
            @wraps(original_send)
            def wrapped_send(self, request: PreparedRequest, **kwargs):
                redacted_url = redact_url(request.url)
                url = urlparse(redacted_url)

                span = tracer.start_span(
                    "spinal.requests",
                    attributes={"http.url": redacted_url, "spinal.provider": supported_host(url.hostname)},
                )
                span.__enter__()  # Manually enter the span context
                try:
                    response = original_send(self, request, **kwargs)
                    headers = response.headers
                    content_type = headers.get("content-type", "")
                    encoding = headers.get("content-encoding", "")

                    # Save response headers
                    for headers, values in headers.items():
                        span.set_attribute(f"spinal.http.response.header.{headers}", values)

                    span.set_attribute("content-type", content_type)
                    span.set_attribute("content-encoding", encoding)
                    span.set_attribute("http.status_code", response.status_code)
                    span.set_attribute("http.url", redacted_url)
                    span.set_attribute("http.host", url.hostname)
                    add_request_params_to_span(span, redacted_url)

                    if request.body:
                        span.set_attribute("spinal.request.binary_data", memoryview(request.body))

                    is_streaming = kwargs.get("stream", self.stream)
                    if is_streaming:
                        wrap_streaming_response(response, span)
                        span.set_attribute("spinal.response.streaming", True)
                        # Ensure cleanup if the stream is not consumed
                        response._spinal_span = span

                        def cleanup_span():
                            if hasattr(response, "_spinal_span"):
                                response._spinal_span.end()
                                delattr(response, "_spinal_span")

                        import weakref

                        weakref.finalize(response, cleanup_span)
                        # Don't end the span here - let the streaming wrapper or finalizer handle it
                        span.set_status(Status(StatusCode.OK))
                        return response
                    else:
                        if hasattr(response, "_content") and response._content is not None:
                            span.set_attribute("spinal.response.binary_data", memoryview(response._content))
                            span.set_attribute("spinal.response.size", len(response._content))
                            span.set_attribute("spinal.response.streaming", False)
                        span.set_status(Status(StatusCode.OK))
                        span.end()  # End span for non-streaming responses
                        return response

                except Exception as e:
                    span.record_exception(e)
                    span.set_status(Status(StatusCode.ERROR))
                    span.end()  # End span on exception
                    raise

            return wrapped_send

        def wrap_session_request(original_request):
            """Wrapper for Session.request to ensure instrumentation for thread-local sessions"""

            @wraps(original_request)
            def wrapped_request(self, method, url, **kwargs):
                # The request() method internally calls send(), which is already patched.
                # This wrapper ensures the patch is applied even for thread-local sessions
                # created before instrumentation (like Voyage AI's _thread_context.session)
                return original_request(self, method, url, **kwargs)

            return wrapped_request

        # Call parent instrumentation first to avoid conflicts
        super()._instrument(**kwargs)

        # Apply our custom patches on top
        Session.send = wrap_session_send(Session.send)
        Session.request = wrap_session_request(Session.request)

import logging
from urllib.parse import urlparse

import httpx
from httpx import SyncByteStream
from opentelemetry import trace
from opentelemetry.context import Context
from opentelemetry.trace import Tracer, Status, StatusCode

logger = logging.getLogger(__name__)


class SyncStreamWrapper(SyncByteStream):
    def __init__(
        self,
        response: httpx.Response,
        wrapped_stream: SyncByteStream,
        tracer: Tracer,
        parent_context: Context,
        parent_attributes: dict[str, str],
    ):
        self._response = response
        self._stream = wrapped_stream
        self._tracer = tracer
        self._parent_context = parent_context
        self._parent_attributes = parent_attributes
        self._chunks = []

    def __iter__(self):
        for chunk in self._stream:
            self._chunks.append(chunk)
            yield chunk
        self._process_complete()

    def _process_complete(self):
        """
        Processed the saved chunks and attach information to the span that will be sent to Spinal
        """
        if not self._chunks:
            return

        try:
            response_data = b"".join(self._chunks)  # Clones data
            headers = self._response.headers
            request = self._response.request
            url = urlparse(str(request.url))
            status_code = self._response.status_code
            parent_span = trace.get_current_span(self._parent_context)
            parent_start_time = parent_span.start_time if parent_span and hasattr(parent_span, "start_time") else None

            with self._tracer.start_as_current_span(
                "spinal.httpx.sync.response",
                context=self._parent_context,
                attributes=self._parent_attributes,
                start_time=parent_start_time,
            ) as span:
                content_type = headers.get("content-type", "")
                encoding = headers.get("content-encoding", "")

                span.set_attribute("content-type", content_type)
                span.set_attribute("content-encoding", encoding)
                span.set_attribute("http.status_code", status_code)
                span.set_attribute("http.url", str(request.url))
                span.set_attribute("http.host", url.hostname)

                if hasattr(request, "stream") and not isinstance(request.stream, httpx._multipart.MultipartStream):
                    span.set_attribute("spinal.request.binary_data", memoryview(request.content))

                span.set_attribute("spinal.response.binary_data", memoryview(response_data))
                span.set_status(Status(StatusCode.OK))

        except Exception as e:
            logger.error(f"Spinal error processing response: {e}")

        return

    def __getattr__(self, name):
        return getattr(self._stream, name)

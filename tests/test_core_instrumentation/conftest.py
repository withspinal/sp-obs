"""Shared fixtures for core instrumentation tests."""

import io
from typing import AsyncIterator, Dict, List
from unittest.mock import Mock

import pytest
from opentelemetry import trace
from opentelemetry.context import Context
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import Tracer


@pytest.fixture
def mock_tracer_provider():
    """Create a mock TracerProvider for testing."""
    provider = Mock(spec=TracerProvider)
    return provider


@pytest.fixture
def mock_tracer():
    """Create a mock Tracer for testing."""
    tracer = Mock(spec=Tracer)
    return tracer


@pytest.fixture
def mock_span():
    """Create a mock Span for testing."""
    span = Mock()
    span.attributes = {}
    span.set_attribute = Mock(side_effect=lambda k, v: span.attributes.update({k: v}))
    span.is_recording.return_value = True
    span.end = Mock()
    return span


@pytest.fixture
def mock_context():
    """Create a mock OpenTelemetry Context."""
    context = Mock(spec=Context)
    return context


@pytest.fixture
def in_memory_span_exporter():
    """Create an InMemorySpanExporter for collecting spans."""
    return InMemorySpanExporter()


@pytest.fixture
def tracer_provider_with_exporter(in_memory_span_exporter):
    """Create a real TracerProvider with InMemorySpanExporter."""
    provider = TracerProvider()
    processor = SimpleSpanProcessor(in_memory_span_exporter)
    provider.add_span_processor(processor)
    return provider


@pytest.fixture
def real_tracer(tracer_provider_with_exporter):
    """Create a real Tracer for integration testing."""
    return tracer_provider_with_exporter.get_tracer(__name__)


class MockSyncByteStream:
    """Mock SyncByteStream for testing."""

    def __init__(self, chunks: List[bytes]):
        self.chunks = chunks
        self._iter = iter(chunks)

    def __iter__(self):
        return self

    def __next__(self):
        return next(self._iter)


class MockAsyncByteStream:
    """Mock AsyncByteStream for testing."""

    def __init__(self, chunks: List[bytes]):
        self.chunks = chunks

    def __aiter__(self) -> AsyncIterator[bytes]:
        return self._async_iter()

    async def _async_iter(self) -> AsyncIterator[bytes]:
        for chunk in self.chunks:
            yield chunk


class MockHttpxResponse:
    """Mock httpx.Response for testing."""

    def __init__(self, url: str, status_code: int = 200, headers: Dict[str, str] = None, stream=None, request=None):
        self.url = url
        self.status_code = status_code
        self.headers = headers or {}
        self.stream = stream
        self.request = request or MockHttpxRequest(url=url)


class MockHttpxRequest:
    """Mock httpx.Request for testing."""

    def __init__(self, url: str, content: bytes = b""):
        self.url = url
        self.content = content


class MockRequestsResponse:
    """Mock requests.Response for testing."""

    def __init__(
        self,
        url: str,
        status_code: int = 200,
        headers: Dict[str, str] = None,
        content: bytes = b"",
        stream: bool = False,
    ):
        self.url = url
        self.status_code = status_code
        self.headers = headers or {}
        self._content = content if not stream else False
        self._content_consumed = not stream
        self.request = MockRequestsPreparedRequest(url=url)
        self.raw = MockRawResponse(content) if stream else None

        # Store original methods for wrapping tests
        self._original_iter_content = self.iter_content

    def iter_content(self, chunk_size=1024, decode_unicode=False):
        """Mock iter_content that yields chunks."""
        if self._content_consumed:
            if isinstance(self._content, bytes):
                # Split content into chunks
                for i in range(0, len(self._content), chunk_size):
                    yield self._content[i : i + chunk_size]
        else:
            # Stream mode - yield from raw
            while True:
                chunk = self.raw.read(chunk_size)
                if not chunk:
                    break
                yield chunk
            self._content_consumed = True

    @property
    def content(self):
        """Mock content property."""
        if self._content is False:
            # Load content from raw if streaming
            if not self._content_consumed and self.raw:
                chunks = []
                for chunk in self.iter_content():
                    chunks.append(chunk)
                self._content = b"".join(chunks)
            else:
                self._content = b""
        return self._content


class MockRequestsPreparedRequest:
    """Mock requests.PreparedRequest for testing."""

    def __init__(self, url: str, body: bytes = b""):
        self.url = url
        self.body = body


class MockRawResponse:
    """Mock raw response for requests streaming."""

    def __init__(self, content: bytes):
        self._stream = io.BytesIO(content)

    def read(self, amt=None):
        return self._stream.read(amt)


@pytest.fixture
def mock_sync_stream():
    """Create a mock sync byte stream with test data."""
    chunks = [b"chunk1", b"chunk2", b"chunk3"]
    return MockSyncByteStream(chunks)


@pytest.fixture
def mock_async_stream():
    """Create a mock async byte stream with test data."""
    chunks = [b"async1", b"async2", b"async3"]
    return MockAsyncByteStream(chunks)


@pytest.fixture
def mock_httpx_response(mock_sync_stream):
    """Create a mock httpx response with sync stream."""
    return MockHttpxResponse(
        url="https://api.openai.com/v1/test",
        status_code=200,
        headers={"content-type": "application/json"},
        stream=mock_sync_stream,
    )


@pytest.fixture
def mock_httpx_async_response(mock_async_stream):
    """Create a mock httpx response with async stream."""
    return MockHttpxResponse(
        url="https://api.openai.com/v1/test",
        status_code=200,
        headers={"content-type": "application/json"},
        stream=mock_async_stream,
    )


@pytest.fixture
def mock_requests_response():
    """Create a mock requests response."""
    return MockRequestsResponse(
        url="https://api.openai.com/v1/test",
        status_code=200,
        headers={"content-type": "application/json"},
        content=b"test response content",
    )


@pytest.fixture
def mock_requests_streaming_response():
    """Create a mock streaming requests response."""
    return MockRequestsResponse(
        url="https://api.openai.com/v1/test",
        status_code=200,
        headers={"content-type": "application/json"},
        content=b"streaming response content",
        stream=True,
    )


@pytest.fixture
def integration_urls():
    """Test URLs for different integrations."""
    return {
        "openai": "https://api.openai.com/v1/chat/completions",
        "anthropic": "https://api.anthropic.com/v1/messages",
        "elevenlabs": "https://api.elevenlabs.io/v1/text-to-speech",
        "non_integration": "https://httpbin.org/get",
    }


@pytest.fixture(autouse=True)
def reset_opentelemetry():
    """Reset OpenTelemetry state between tests."""
    # Clear any existing tracer providers
    trace._TRACER_PROVIDER = None
    yield
    # Clean up after test
    trace._TRACER_PROVIDER = None

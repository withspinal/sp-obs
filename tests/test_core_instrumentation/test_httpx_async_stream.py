"""Tests for HTTPX async stream wrapper."""

import asyncio
import pytest
from unittest.mock import Mock, AsyncMock
from sp_obs._internal.core.httpx.async_stream import AsyncStreamWrapper

from .utils.span_helpers import (
    assert_span_attributes,
    assert_binary_data_captured,
    assert_request_data_captured,
    assert_span_name,
)


class TestAsyncStreamWrapper:
    """Test the HTTPX async stream wrapper."""

    def test_init(self, mock_async_stream, mock_httpx_response, mock_tracer, mock_context):
        """Test AsyncStreamWrapper initialization.

        Tests wrapper initialization, verifying all internal attributes are set correctly.
        """
        parent_attributes = {"test_attr": "test_value"}

        wrapper = AsyncStreamWrapper(
            response=mock_httpx_response,
            wrapped_stream=mock_async_stream,
            tracer=mock_tracer,
            parent_context=mock_context,
            parent_attributes=parent_attributes,
        )

        assert wrapper._response == mock_httpx_response
        assert wrapper._stream == mock_async_stream
        assert wrapper._tracer == mock_tracer
        assert wrapper._parent_context == mock_context
        assert wrapper._parent_attributes == parent_attributes
        assert wrapper._chunks == []

    @pytest.mark.asyncio
    async def test_aiter_returns_async_iterator(
        self, mock_async_stream, mock_httpx_response, mock_tracer, mock_context
    ):
        """Test that __aiter__ returns an async iterator.

        Confirms `__aiter__` returns an async iterator with `__anext__` method.
        """
        wrapper = AsyncStreamWrapper(
            response=mock_httpx_response,
            wrapped_stream=mock_async_stream,
            tracer=mock_tracer,
            parent_context=mock_context,
            parent_attributes={},
        )

        async_iter = wrapper.__aiter__()
        assert hasattr(async_iter, "__anext__")

    @pytest.mark.asyncio
    async def test_aiter_collects_chunks(self, mock_httpx_response, mock_tracer, mock_context):
        """Test that async iteration collects all chunks from the wrapped stream.

        Tests that async iteration collects all chunks from wrapped stream and stores them
        internally, then calls `_process_complete`.
        """
        # Create a test async stream
        test_chunks = [b"async1", b"async2", b"async3"]

        class TestAsyncStream:
            def __init__(self, chunks):
                self.chunks = chunks

            def __aiter__(self):
                return self._async_iter__()

            async def _async_iter__(self):
                for chunk in self.chunks:
                    yield chunk

        test_stream = TestAsyncStream(test_chunks)

        wrapper = AsyncStreamWrapper(
            response=mock_httpx_response,
            wrapped_stream=test_stream,
            tracer=mock_tracer,
            parent_context=mock_context,
            parent_attributes={},
        )

        # Mock _process_complete to avoid span creation during test
        wrapper._process_complete = AsyncMock()

        # Iterate through wrapper
        collected_chunks = []
        async for chunk in wrapper:
            collected_chunks.append(chunk)

        # Verify chunks were yielded correctly
        assert collected_chunks == test_chunks

        # Verify chunks were stored internally
        assert wrapper._chunks == test_chunks

        # Verify _process_complete was called
        wrapper._process_complete.assert_called_once()

    @pytest.mark.asyncio
    async def test_aiter_handles_empty_stream(self, mock_httpx_response, mock_tracer, mock_context):
        """Test async iteration with empty stream.

        Tests behavior with empty streams (no chunks yielded).
        """

        class EmptyAsyncStream:
            def __aiter__(self):
                return self._async_iter__()

            async def _async_iter__(self):
                # Yield nothing
                return
                yield  # Unreachable, but makes this a generator

        empty_stream = EmptyAsyncStream()

        wrapper = AsyncStreamWrapper(
            response=mock_httpx_response,
            wrapped_stream=empty_stream,
            tracer=mock_tracer,
            parent_context=mock_context,
            parent_attributes={},
        )

        # Mock _process_complete
        wrapper._process_complete = AsyncMock()

        # Iterate through wrapper
        collected_chunks = []
        async for chunk in wrapper:
            collected_chunks.append(chunk)

        # Verify no chunks collected
        assert collected_chunks == []
        assert wrapper._chunks == []

        # _process_complete should still be called
        wrapper._process_complete.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_complete_creates_span_with_correct_attributes(
        self, mock_async_stream, mock_httpx_response, real_tracer, mock_context, in_memory_span_exporter
    ):
        """Test that _process_complete creates a span with correct attributes.

        Tests that `_process_complete` creates spans with correct HTTP attributes,
        binary data, and parent attributes.
        """
        # Set up test data
        test_chunks = [b"async", b"test", b"data"]
        expected_response_data = b"".join(test_chunks)

        # Set up mock response with test data
        mock_httpx_response.headers = {"content-type": "application/json", "content-encoding": "br"}
        mock_httpx_response.status_code = 201
        mock_httpx_response.request.url = "https://api.anthropic.com/v1/messages"

        # Mock request content handling (different for async)
        mock_httpx_response.request._content = b"async request data"
        mock_httpx_response.request.content = b"async request data"

        parent_attributes = {"async_parent": "async_value"}

        wrapper = AsyncStreamWrapper(
            response=mock_httpx_response,
            wrapped_stream=mock_async_stream,
            tracer=real_tracer,
            parent_context=mock_context,
            parent_attributes=parent_attributes,
        )

        # Simulate chunks being collected
        wrapper._chunks = test_chunks

        # Call _process_complete
        await wrapper._process_complete()

        # Get the created span
        finished_spans = in_memory_span_exporter.get_finished_spans()
        assert len(finished_spans) == 1

        span = finished_spans[0]
        assert_span_name(span, "spinal.httpx.async.response")

        # Verify all expected attributes
        expected_attributes = {
            "content-type": "application/json",
            "content-encoding": "br",
            "http.status_code": 201,
            "http.url": "https://api.anthropic.com/v1/messages",
            "http.host": "api.anthropic.com",
            "async_parent": "async_value",
        }

        assert_span_attributes(span, expected_attributes)
        assert_binary_data_captured(span, len(expected_response_data))
        assert_request_data_captured(span, len(b"async request data"))

    @pytest.mark.asyncio
    async def test_process_complete_handles_streaming_request_content(
        self, mock_async_stream, mock_httpx_response, real_tracer, mock_context, in_memory_span_exporter
    ):
        """Test _process_complete handles streaming request content correctly.

        Tests handling of streaming requests (no `_content` attribute) - should set
        content type as "streaming" and not capture request binary data.
        """
        test_chunks = [b"response_data"]

        # Set up response with streaming request (no _content)
        mock_httpx_response.headers = {"content-type": "text/plain"}
        mock_httpx_response.status_code = 200
        mock_httpx_response.request.url = "https://api.openai.com/v1/stream"

        # Mock streaming request (no _content attribute)
        mock_request = Mock()
        mock_request._content = None
        mock_httpx_response.request = mock_request

        wrapper = AsyncStreamWrapper(
            response=mock_httpx_response,
            wrapped_stream=mock_async_stream,
            tracer=real_tracer,
            parent_context=mock_context,
            parent_attributes={},
        )

        wrapper._chunks = test_chunks
        await wrapper._process_complete()

        # Should still create span
        finished_spans = in_memory_span_exporter.get_finished_spans()
        assert len(finished_spans) == 1

        span = finished_spans[0]
        span_attrs = dict(span.attributes) if span.attributes else {}

        # Should have streaming content type for request
        assert span_attrs.get("spinal.request.content_type") == "streaming"

        # Should not have request binary data
        assert "spinal.request.binary_data" not in span_attrs

    @pytest.mark.asyncio
    async def test_process_complete_handles_empty_chunks(
        self, mock_async_stream, mock_httpx_response, real_tracer, mock_context, in_memory_span_exporter
    ):
        """Test _process_complete with no chunks collected.

        Tests that no spans are created when no chunks were collected.
        """
        wrapper = AsyncStreamWrapper(
            response=mock_httpx_response,
            wrapped_stream=mock_async_stream,
            tracer=real_tracer,
            parent_context=mock_context,
            parent_attributes={},
        )

        # No chunks collected
        assert wrapper._chunks == []

        # Call _process_complete
        await wrapper._process_complete()

        # Should not create any spans
        finished_spans = in_memory_span_exporter.get_finished_spans()
        assert len(finished_spans) == 0

    @pytest.mark.asyncio
    async def test_process_complete_handles_exceptions(
        self, mock_async_stream, mock_httpx_response, mock_tracer, mock_context, caplog
    ):
        """Test that _process_complete handles exceptions gracefully.

        Tests graceful exception handling in `_process_complete` with error logging.
        """
        # Mock tracer to raise exception
        mock_tracer.start_as_current_span.side_effect = Exception("Async test exception")

        wrapper = AsyncStreamWrapper(
            response=mock_httpx_response,
            wrapped_stream=mock_async_stream,
            tracer=mock_tracer,
            parent_context=mock_context,
            parent_attributes={},
        )

        wrapper._chunks = [b"test"]

        # Should not raise exception
        await wrapper._process_complete()

        # Should log error
        assert "Spinal error processing response" in caplog.text

    def test_getattr_delegates_to_wrapped_stream(
        self, mock_async_stream, mock_httpx_response, mock_tracer, mock_context
    ):
        """Test that __getattr__ delegates to the wrapped stream.

        Tests that attribute access and method calls are properly delegated to the wrapped stream.
        """
        # Set up mock stream with a test attribute
        mock_async_stream.test_attribute = "async_test_value"
        mock_async_stream.test_method = Mock(return_value="async_method_result")

        wrapper = AsyncStreamWrapper(
            response=mock_httpx_response,
            wrapped_stream=mock_async_stream,
            tracer=mock_tracer,
            parent_context=mock_context,
            parent_attributes={},
        )

        # Test attribute access
        assert wrapper.test_attribute == "async_test_value"

        # Test method call
        result = wrapper.test_method("async_arg", kwarg="async_kwarg")
        assert result == "async_method_result"
        mock_async_stream.test_method.assert_called_once_with("async_arg", kwarg="async_kwarg")

    @pytest.mark.asyncio
    async def test_full_async_iteration_workflow(
        self, mock_httpx_response, real_tracer, mock_context, in_memory_span_exporter
    ):
        """Test the complete async workflow from iteration to span creation.

        End-to-end test of complete workflow: iteration → chunk collection → span creation
        with real async stream.
        """
        # Create a real async stream with test data
        test_chunks = [b"async_chunk1", b"async_chunk2", b"final_async_chunk"]

        class TestAsyncStream:
            def __init__(self, chunks):
                self.chunks = chunks

            def __aiter__(self):
                return self._async_iter()

            async def _async_iter(self):
                for chunk in self.chunks:
                    # Simulate async delay
                    await asyncio.sleep(0.001)
                    yield chunk

        test_stream = TestAsyncStream(test_chunks)

        # Set up response
        mock_httpx_response.headers = {"content-type": "application/stream"}
        mock_httpx_response.status_code = 200
        mock_httpx_response.request.url = "https://api.anthropic.com/v1/stream"
        mock_httpx_response.request._content = b"async_request_body"
        mock_httpx_response.request.content = b"async_request_body"

        wrapper = AsyncStreamWrapper(
            response=mock_httpx_response,
            wrapped_stream=test_stream,
            tracer=real_tracer,
            parent_context=mock_context,
            parent_attributes={"async_key": "async_val"},
        )

        # Iterate through wrapper (simulating normal async usage)
        collected_chunks = []
        async for chunk in wrapper:
            collected_chunks.append(chunk)

        # Verify chunks were collected correctly
        assert collected_chunks == test_chunks

        # Verify span was created
        finished_spans = in_memory_span_exporter.get_finished_spans()
        assert len(finished_spans) == 1

        span = finished_spans[0]
        assert_span_name(span, "spinal.httpx.async.response")

        # Verify response data was captured correctly
        expected_response_data = b"".join(test_chunks)
        assert_binary_data_captured(span, len(expected_response_data))

        # Verify request data was captured
        assert_request_data_captured(span, len(b"async_request_body"))

        # Verify parent attributes were preserved
        span_attrs = dict(span.attributes) if span.attributes else {}
        assert span_attrs["async_key"] == "async_val"

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "chunk_data",
        [
            [b""],  # Empty chunk
            [b"single_async"],  # Single chunk
            [b"a", b"b", b"c"],  # Multiple small chunks
            [b"x" * 500, b"y" * 1500],  # Large chunks
            [b"data", b"", b"more_data"],  # Mixed empty and non-empty
        ],
    )
    async def test_various_async_chunk_patterns(
        self, chunk_data, mock_httpx_response, real_tracer, mock_context, in_memory_span_exporter
    ):
        """Test async wrapper with various chunk patterns.

        Parametrized test with various chunk patterns (empty, single, multiple, large, mixed)
        to ensure robust handling.
        """

        class TestAsyncStream:
            def __init__(self, chunks):
                self.chunks = chunks

            def __aiter__(self):
                return self._async_iter()

            async def _async_iter(self):
                for chunk in self.chunks:
                    yield chunk

        test_stream = TestAsyncStream(chunk_data)

        # Minimal response setup
        mock_httpx_response.headers = {}
        mock_httpx_response.status_code = 200
        mock_httpx_response.request.url = "https://api.openai.com/v1/async_test"
        mock_httpx_response.request._content = b""
        mock_httpx_response.request.content = b""

        wrapper = AsyncStreamWrapper(
            response=mock_httpx_response,
            wrapped_stream=test_stream,
            tracer=real_tracer,
            parent_context=mock_context,
            parent_attributes={},
        )

        # Iterate and collect
        collected = []
        async for chunk in wrapper:
            collected.append(chunk)

        # Verify chunks match
        assert collected == chunk_data

        # If there were any chunks, should have created a span
        if chunk_data and any(chunk_data):
            finished_spans = in_memory_span_exporter.get_finished_spans()
            assert len(finished_spans) == 1

            span = finished_spans[0]
            expected_data = b"".join(chunk_data)
            assert_binary_data_captured(span, len(expected_data))

    @pytest.mark.asyncio
    async def test_async_exception_during_iteration(self, mock_httpx_response, mock_tracer, mock_context):
        """Test that exceptions during async iteration are handled properly.

        Verifies exceptions during iteration are properly propagated.
        """

        class ExceptionAsyncStream:
            async def __aiter__(self):
                yield b"chunk1"
                raise ValueError("Test async exception")

        exception_stream = ExceptionAsyncStream()

        wrapper = AsyncStreamWrapper(
            response=mock_httpx_response,
            wrapped_stream=exception_stream,
            tracer=mock_tracer,
            parent_context=mock_context,
            parent_attributes={},
        )

        # Should propagate the exception
        with pytest.raises(ValueError, match="Test async exception"):
            async for chunk in wrapper:
                pass

    @pytest.mark.asyncio
    async def test_concurrent_async_streams(
        self, mock_httpx_response, real_tracer, mock_context, in_memory_span_exporter
    ):
        """Test multiple async streams running concurrently.

        Tests multiple async streams running concurrently to verify thread safety
        and proper span isolation.
        """

        async def create_stream_and_iterate(stream_id, chunks):
            class TestAsyncStream:
                def __init__(self, chunks, stream_id):
                    self.chunks = chunks
                    self.stream_id = stream_id

                def __aiter__(self):
                    return self._async_iter()

                async def _async_iter(self):
                    for i, chunk in enumerate(self.chunks):
                        await asyncio.sleep(0.001)  # Small delay
                        yield f"{chunk.decode()}-{self.stream_id}-{i}".encode()

            test_stream = TestAsyncStream(chunks, stream_id)

            # Create response mock for this stream
            response = Mock()
            response.headers = {"content-type": f"stream-{stream_id}"}
            response.status_code = 200
            response.request.url = f"https://api.openai.com/stream-{stream_id}"
            response.request._content = f"request-{stream_id}".encode()
            response.request.content = f"request-{stream_id}".encode()

            wrapper = AsyncStreamWrapper(
                response=response,
                wrapped_stream=test_stream,
                tracer=real_tracer,
                parent_context=mock_context,
                parent_attributes={"stream_id": stream_id},
            )

            collected = []
            async for chunk in wrapper:
                collected.append(chunk)

            return collected

        # Run multiple streams concurrently
        chunk_sets = [[b"a", b"b"], [b"x", b"y", b"z"], [b"1", b"2"]]

        tasks = [create_stream_and_iterate(i, chunks) for i, chunks in enumerate(chunk_sets)]

        results = await asyncio.gather(*tasks)

        # Verify all streams completed
        assert len(results) == 3

        # Verify spans were created for each stream
        finished_spans = in_memory_span_exporter.get_finished_spans()
        assert len(finished_spans) == 3

        # Verify each span has correct stream_id
        stream_ids = [dict(span.attributes)["stream_id"] for span in finished_spans if span.attributes]
        assert sorted(stream_ids) == [0, 1, 2]

"""Tests for HTTPX sync stream wrapper."""

import pytest
from unittest.mock import Mock


from sp_obs._internal.core.httpx.sync_stream import SyncStreamWrapper

from .utils.span_helpers import (
    assert_span_attributes,
    assert_binary_data_captured,
    assert_request_data_captured,
    assert_span_name,
)


class TestSyncStreamWrapper:
    """Test the HTTPX sync stream wrapper."""

    def test_init(self, mock_sync_stream, mock_httpx_response, mock_tracer, mock_context):
        """Test SyncStreamWrapper initialization.

        Tests wrapper initialization with correct attribute assignment.
        """
        parent_attributes = {"test_attr": "test_value"}

        wrapper = SyncStreamWrapper(
            response=mock_httpx_response,
            wrapped_stream=mock_sync_stream,
            tracer=mock_tracer,
            parent_context=mock_context,
            parent_attributes=parent_attributes,
        )

        assert wrapper._response == mock_httpx_response
        assert wrapper._stream == mock_sync_stream
        assert wrapper._tracer == mock_tracer
        assert wrapper._parent_context == mock_context
        assert wrapper._parent_attributes == parent_attributes
        assert wrapper._chunks == []

    def test_iter_collects_chunks(self, mock_sync_stream, mock_httpx_response, mock_tracer, mock_context):
        """Test that __iter__ collects all chunks from the wrapped stream.

        Tests that iteration collects and stores all chunks, then calls _process_complete.
        """
        # Set up mock stream with test chunks
        test_chunks = [b"chunk1", b"chunk2", b"chunk3"]
        mock_sync_stream.chunks = test_chunks

        wrapper = SyncStreamWrapper(
            response=mock_httpx_response,
            wrapped_stream=mock_sync_stream,
            tracer=mock_tracer,
            parent_context=mock_context,
            parent_attributes={},
        )

        # Mock _process_complete to avoid span creation during test
        wrapper._process_complete = Mock()

        # Iterate through wrapper
        collected_chunks = list(wrapper)

        # Verify chunks were yielded correctly
        assert collected_chunks == test_chunks

        # Verify chunks were stored internally
        assert wrapper._chunks == test_chunks

        # Verify _process_complete was called
        wrapper._process_complete.assert_called_once()

    def test_iter_handles_empty_stream(self, mock_httpx_response, mock_tracer, mock_context):
        """Test iteration with empty stream.

        Tests behavior with empty streams (no chunks).
        """
        empty_stream = Mock()
        empty_stream.__iter__ = Mock(return_value=iter([]))

        wrapper = SyncStreamWrapper(
            response=mock_httpx_response,
            wrapped_stream=empty_stream,
            tracer=mock_tracer,
            parent_context=mock_context,
            parent_attributes={},
        )

        # Mock _process_complete
        wrapper._process_complete = Mock()

        # Iterate through wrapper
        collected_chunks = list(wrapper)

        # Verify no chunks collected
        assert collected_chunks == []
        assert wrapper._chunks == []

        # _process_complete should still be called
        wrapper._process_complete.assert_called_once()

    def test_process_complete_creates_span_with_correct_attributes(
        self, mock_sync_stream, mock_httpx_response, real_tracer, mock_context, in_memory_span_exporter
    ):
        """Test that _process_complete creates a span with correct attributes.

        Tests span creation with HTTP attributes, binary data, and parent attributes.
        """
        # Set up test data
        test_chunks = [b"test", b"data", b"chunks"]
        expected_response_data = b"".join(test_chunks)

        # Set up mock response with test data
        mock_httpx_response.headers = {"content-type": "application/json", "content-encoding": "gzip"}
        mock_httpx_response.status_code = 200
        mock_httpx_response.request.url = "https://api.openai.com/v1/test"
        mock_httpx_response.request.content = b"request data"
        mock_httpx_response.request.stream = b""

        parent_attributes = {"parent_attr": "parent_value"}

        wrapper = SyncStreamWrapper(
            response=mock_httpx_response,
            wrapped_stream=mock_sync_stream,
            tracer=real_tracer,
            parent_context=mock_context,
            parent_attributes=parent_attributes,
        )

        # Simulate chunks being collected
        wrapper._chunks = test_chunks

        # Call _process_complete
        wrapper._process_complete()

        # Get the created span
        finished_spans = in_memory_span_exporter.get_finished_spans()
        assert len(finished_spans) == 1

        span = finished_spans[0]
        assert_span_name(span, "spinal.httpx.sync.response")

        # Verify all expected attributes
        expected_attributes = {
            "content-type": "application/json",
            "content-encoding": "gzip",
            "http.status_code": 200,
            "http.url": "https://api.openai.com/v1/test",
            "http.host": "api.openai.com",
            "parent_attr": "parent_value",
        }

        assert_span_attributes(span, expected_attributes)
        assert_binary_data_captured(span, len(expected_response_data))
        assert_request_data_captured(span, len(b"request data"))

    def test_process_complete_handles_empty_chunks(
        self, mock_sync_stream, mock_httpx_response, real_tracer, mock_context, in_memory_span_exporter
    ):
        """Test _process_complete with no chunks collected.

        Tests that no spans are created when no chunks were collected.
        """
        wrapper = SyncStreamWrapper(
            response=mock_httpx_response,
            wrapped_stream=mock_sync_stream,
            tracer=real_tracer,
            parent_context=mock_context,
            parent_attributes={},
        )

        # No chunks collected
        assert wrapper._chunks == []

        # Call _process_complete
        wrapper._process_complete()

        # Should not create any spans
        finished_spans = in_memory_span_exporter.get_finished_spans()
        assert len(finished_spans) == 0

    def test_process_complete_handles_missing_headers(
        self, mock_sync_stream, mock_httpx_response, real_tracer, mock_context, in_memory_span_exporter
    ):
        """Test _process_complete gracefully handles missing headers.

        Tests graceful handling when HTTP headers are missing.
        """
        test_chunks = [b"test data"]

        # Set up response with minimal data (missing some headers)
        mock_httpx_response.headers = {}  # No headers
        mock_httpx_response.status_code = 200
        mock_httpx_response.request.url = "https://api.openai.com/v1/test"
        mock_httpx_response.request.content = b""

        wrapper = SyncStreamWrapper(
            response=mock_httpx_response,
            wrapped_stream=mock_sync_stream,
            tracer=real_tracer,
            parent_context=mock_context,
            parent_attributes={},
        )

        wrapper._chunks = test_chunks
        wrapper._process_complete()

        # Should still create span with available attributes
        finished_spans = in_memory_span_exporter.get_finished_spans()
        assert len(finished_spans) == 1

        span = finished_spans[0]
        span_attrs = dict(span.attributes) if span.attributes else {}

        # Should have default values for missing headers
        assert span_attrs.get("content-type") == ""
        assert span_attrs.get("content-encoding") == ""
        assert span_attrs["http.status_code"] == 200

    def test_process_complete_handles_exceptions(
        self, mock_sync_stream, mock_httpx_response, mock_tracer, mock_context, caplog
    ):
        """Test that _process_complete handles exceptions gracefully.

        Tests exception handling with error logging.
        """
        # Mock tracer to raise exception
        mock_tracer.start_as_current_span.side_effect = Exception("Test exception")

        wrapper = SyncStreamWrapper(
            response=mock_httpx_response,
            wrapped_stream=mock_sync_stream,
            tracer=mock_tracer,
            parent_context=mock_context,
            parent_attributes={},
        )

        wrapper._chunks = [b"test"]

        # Should not raise exception
        wrapper._process_complete()

        # Should log error
        assert "Spinal error processing response" in caplog.text

    def test_getattr_delegates_to_wrapped_stream(
        self, mock_sync_stream, mock_httpx_response, mock_tracer, mock_context
    ):
        """Test that __getattr__ delegates to the wrapped stream.

        Tests that attribute access is delegated to the wrapped stream.
        """
        # Set up mock stream with a test attribute
        mock_sync_stream.test_attribute = "test_value"
        mock_sync_stream.test_method = Mock(return_value="method_result")

        wrapper = SyncStreamWrapper(
            response=mock_httpx_response,
            wrapped_stream=mock_sync_stream,
            tracer=mock_tracer,
            parent_context=mock_context,
            parent_attributes={},
        )

        # Test attribute access
        assert wrapper.test_attribute == "test_value"

        # Test method call
        result = wrapper.test_method("arg1", kwarg="kwarg1")
        assert result == "method_result"
        mock_sync_stream.test_method.assert_called_once_with("arg1", kwarg="kwarg1")

    def test_full_iteration_workflow(self, mock_httpx_response, real_tracer, mock_context, in_memory_span_exporter):
        """Test the complete workflow from iteration to span creation.

        Tests complete end-to-end workflow from iteration to span creation.
        """
        # Create a real stream with test data
        test_chunks = [b"chunk1", b"chunk2", b"final_chunk"]

        class TestSyncStream:
            def __init__(self, chunks):
                self.chunks = chunks

            def __iter__(self):
                return iter(self.chunks)

        test_stream = TestSyncStream(test_chunks)

        # Set up response
        mock_httpx_response.headers = {"content-type": "text/plain"}
        mock_httpx_response.status_code = 200
        mock_httpx_response.request.url = "https://api.openai.com/v1/test"
        mock_httpx_response.request.content = b"request_body"
        mock_httpx_response.request.stream = b""

        wrapper = SyncStreamWrapper(
            response=mock_httpx_response,
            wrapped_stream=test_stream,
            tracer=real_tracer,
            parent_context=mock_context,
            parent_attributes={"parent_key": "parent_val"},
        )

        # Iterate through wrapper (simulating normal usage)
        collected_chunks = list(wrapper)

        # Verify chunks were collected correctly
        assert collected_chunks == test_chunks

        # Verify span was created
        finished_spans = in_memory_span_exporter.get_finished_spans()
        assert len(finished_spans) == 1

        span = finished_spans[0]
        assert_span_name(span, "spinal.httpx.sync.response")

        # Verify response data was captured correctly
        expected_response_data = b"".join(test_chunks)
        assert_binary_data_captured(span, len(expected_response_data))

        # Verify request data was captured
        assert_request_data_captured(span, len(b"request_body"))

        # Verify parent attributes were preserved
        span_attrs = dict(span.attributes) if span.attributes else {}
        assert span_attrs["parent_key"] == "parent_val"

    @pytest.mark.parametrize(
        "chunk_data",
        [
            [b""],  # Empty chunk
            [b"single"],  # Single chunk
            [b"a", b"b", b"c"],  # Multiple small chunks
            [b"x" * 1000, b"y" * 2000],  # Large chunks
            [b"data", b"", b"more"],  # Mixed empty and non-empty
        ],
    )
    def test_various_chunk_patterns(
        self, chunk_data, mock_httpx_response, real_tracer, mock_context, in_memory_span_exporter
    ):
        """Test wrapper with various chunk patterns.

        Tests parametrized scenarios with different chunk patterns (empty, single, multiple, large, mixed).
        """

        class TestSyncStream:
            def __init__(self, chunks):
                self.chunks = chunks

            def __iter__(self):
                return iter(self.chunks)

        test_stream = TestSyncStream(chunk_data)

        # Minimal response setup
        mock_httpx_response.headers = {}
        mock_httpx_response.status_code = 200
        mock_httpx_response.request.url = "https://api.openai.com/v1/test"
        mock_httpx_response.request.content = b""

        wrapper = SyncStreamWrapper(
            response=mock_httpx_response,
            wrapped_stream=test_stream,
            tracer=real_tracer,
            parent_context=mock_context,
            parent_attributes={},
        )

        # Iterate and collect
        collected = list(wrapper)

        # Verify chunks match
        assert collected == chunk_data

        # If there were any chunks, should have created a span
        if chunk_data and any(chunk_data):
            finished_spans = in_memory_span_exporter.get_finished_spans()
            assert len(finished_spans) == 1

            span = finished_spans[0]
            expected_data = b"".join(chunk_data)
            assert_binary_data_captured(span, len(expected_data))

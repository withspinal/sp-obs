"""Tests for aiohttp client instrumentation wrapper."""

import pytest
from unittest.mock import Mock, patch
import types

import opentelemetry.instrumentation.aiohttp_client
from sp_obs._internal.core.aiohttp.aiohttp import SpinalAioHttpClientInstrumentor


class TestSpinalAioHttpClientInstrumentor:
    """Test the aiohttp client instrumentation class."""

    def test_instrumentation_init(self, mock_tracer_provider):
        """Test that instrumentation initializes correctly.

        Tests basic initialization of the instrumentor.
        """
        instrumentor = SpinalAioHttpClientInstrumentor()
        assert instrumentor is not None

    def test_instrument_wraps_create_trace_config(self, mock_tracer_provider, mock_tracer):
        """Test that _instrument wraps create_trace_config.

        Tests that the instrumentor properly wraps the create_trace_config function.
        """
        with patch("sp_obs._internal.core.aiohttp.aiohttp.get_tracer", return_value=mock_tracer):
            # Store original create_trace_config
            original_create_trace_config = opentelemetry.instrumentation.aiohttp_client.create_trace_config

            with patch("opentelemetry.instrumentation.aiohttp_client.AioHttpClientInstrumentor._instrument"):
                instrumentor = SpinalAioHttpClientInstrumentor()
                instrumentor._instrument(tracer_provider=mock_tracer_provider)

                # Verify create_trace_config was wrapped
                current_create_trace_config = opentelemetry.instrumentation.aiohttp_client.create_trace_config
                assert current_create_trace_config != original_create_trace_config

    def test_wrapped_create_trace_config_calls_original(self, mock_tracer_provider, mock_tracer):
        """Test that wrapped create_trace_config calls the original.

        Tests that the wrapper calls the original create_trace_config function.
        """
        with patch("sp_obs._internal.core.aiohttp.aiohttp.get_tracer", return_value=mock_tracer):
            # Mock the original create_trace_config
            mock_base_trace_config = Mock()
            mock_base_trace_config.on_request_start = []
            mock_base_trace_config.on_request_end = []
            mock_base_trace_config.on_request_exception = []

            with patch(
                "opentelemetry.instrumentation.aiohttp_client.create_trace_config",
                return_value=mock_base_trace_config,
            ) as mock_original_create:
                with patch("opentelemetry.instrumentation.aiohttp_client.AioHttpClientInstrumentor._instrument"):
                    instrumentor = SpinalAioHttpClientInstrumentor()
                    instrumentor._instrument(tracer_provider=mock_tracer_provider)

                    # Get the wrapped create_trace_config
                    wrapped = opentelemetry.instrumentation.aiohttp_client.create_trace_config

                    # Call the wrapped function
                    result = wrapped()

                    # Verify original was called
                    mock_original_create.assert_called_once()

                    # Verify callbacks were appended
                    assert len(result.on_request_start) > 0
                    assert len(result.on_request_end) > 0
                    assert len(result.on_request_exception) > 0

    @pytest.mark.asyncio
    async def test_spinal_callbacks_filter_non_integrations(self, mock_tracer_provider, mock_tracer):
        """Test that Spinal callbacks skip non-integration URLs.

        Tests that no Spinal spans are created for non-supported integrations.
        """
        with patch("sp_obs._internal.core.aiohttp.aiohttp.get_tracer", return_value=mock_tracer):
            # Mock the base trace config
            mock_base_trace_config = Mock()
            mock_base_trace_config.on_request_start = []
            mock_base_trace_config.on_request_end = []
            mock_base_trace_config.on_response_chunk_received = []
            mock_base_trace_config.on_request_exception = []

            with patch(
                "opentelemetry.instrumentation.aiohttp_client.create_trace_config",
                return_value=mock_base_trace_config,
            ):
                with patch("opentelemetry.instrumentation.aiohttp_client.AioHttpClientInstrumentor._instrument"):
                    instrumentor = SpinalAioHttpClientInstrumentor()
                    instrumentor._instrument(tracer_provider=mock_tracer_provider)

                    # Get the wrapped create_trace_config
                    wrapped = opentelemetry.instrumentation.aiohttp_client.create_trace_config
                    trace_config = wrapped()

                    # Get the Spinal on_request_start callback (last one appended)
                    spinal_on_request_start = trace_config.on_request_start[-1]

                    # Create mock params for non-integration URL
                    mock_params = Mock()
                    mock_params.url = "https://httpbin.org/get"
                    mock_params.method = "GET"

                    trace_config_ctx = types.SimpleNamespace()

                    # Call the callback
                    await spinal_on_request_start(None, trace_config_ctx, mock_params)

                    # Verify no Spinal span was created
                    assert trace_config_ctx.spinal_span is None
                    assert trace_config_ctx.spinal_token is None

                    # Verify tracer.start_span was not called
                    mock_tracer.start_span.assert_not_called()

    @pytest.mark.asyncio
    async def test_spinal_callbacks_create_spans_for_integrations(
        self, mock_tracer_provider, real_tracer, in_memory_span_exporter
    ):
        """Test that Spinal callbacks create spans for supported integrations.

        Tests that Spinal spans are created for Voyage AI URLs.
        """
        with patch("sp_obs._internal.core.aiohttp.aiohttp.get_tracer", return_value=real_tracer):
            # Mock the base trace config
            mock_base_trace_config = Mock()
            mock_base_trace_config.on_request_start = []
            mock_base_trace_config.on_request_end = []
            mock_base_trace_config.on_response_chunk_received = []
            mock_base_trace_config.on_request_exception = []

            with patch(
                "opentelemetry.instrumentation.aiohttp_client.create_trace_config",
                return_value=mock_base_trace_config,
            ):
                with patch("opentelemetry.instrumentation.aiohttp_client.AioHttpClientInstrumentor._instrument"):
                    instrumentor = SpinalAioHttpClientInstrumentor()
                    instrumentor._instrument(tracer_provider=mock_tracer_provider)

                    # Get the wrapped create_trace_config
                    wrapped = opentelemetry.instrumentation.aiohttp_client.create_trace_config
                    trace_config = wrapped()

                    # Get the callbacks
                    spinal_on_request_start = trace_config.on_request_start[-1]
                    spinal_on_request_end = trace_config.on_request_end[-1]
                    spinal_on_response_chunk_received = trace_config.on_response_chunk_received[-1]

                    # Create mock params for Voyage AI URL
                    mock_start_params = Mock()
                    mock_start_params.url = "https://api.voyageai.com/v1/embeddings"
                    mock_start_params.method = "POST"
                    mock_start_params.data = b'{"input": ["test"]}'

                    mock_end_params = Mock()
                    mock_end_params.response = Mock()
                    mock_end_params.response.status = 200
                    mock_end_params.response.headers = {"content-type": "application/json"}

                    # Mock the StreamReader with at_eof() method
                    mock_stream_reader = Mock()
                    mock_stream_reader.at_eof.return_value = True
                    mock_end_params.response.content = mock_stream_reader

                    mock_chunk_params = Mock()
                    mock_chunk_params.chunk = b'{"result": "test"}'

                    trace_config_ctx = types.SimpleNamespace()

                    # Call on_request_start
                    await spinal_on_request_start(None, trace_config_ctx, mock_start_params)

                    # Verify Spinal span was created
                    assert trace_config_ctx.spinal_span is not None
                    assert trace_config_ctx.spinal_token is not None

                    # Call on_request_end to capture headers and store stream_reader
                    await spinal_on_request_end(None, trace_config_ctx, mock_end_params)

                    # Call on_response_chunk_received to collect chunk and end span
                    await spinal_on_response_chunk_received(None, trace_config_ctx, mock_chunk_params)

                    # Verify span was finished
                    finished_spans = in_memory_span_exporter.get_finished_spans()
                    assert len(finished_spans) == 1

                    span = finished_spans[0]
                    assert span.name == "spinal.aiohttp"

                    # Verify attributes
                    attributes = dict(span.attributes)
                    assert attributes.get("spinal.provider") == "voyageai"
                    assert attributes.get("http.host") == "api.voyageai.com"
                    assert attributes.get("http.status_code") == 200

    @pytest.mark.asyncio
    async def test_spinal_callbacks_handle_exceptions(self, mock_tracer_provider, real_tracer, in_memory_span_exporter):
        """Test that Spinal callbacks handle exceptions properly.

        Tests that Spinal spans record exceptions and set error status.
        """
        with patch("sp_obs._internal.core.aiohttp.aiohttp.get_tracer", return_value=real_tracer):
            # Mock the base trace config
            mock_base_trace_config = Mock()
            mock_base_trace_config.on_request_start = []
            mock_base_trace_config.on_request_end = []
            mock_base_trace_config.on_response_chunk_received = []
            mock_base_trace_config.on_request_exception = []

            with patch(
                "opentelemetry.instrumentation.aiohttp_client.create_trace_config",
                return_value=mock_base_trace_config,
            ):
                with patch("opentelemetry.instrumentation.aiohttp_client.AioHttpClientInstrumentor._instrument"):
                    instrumentor = SpinalAioHttpClientInstrumentor()
                    instrumentor._instrument(tracer_provider=mock_tracer_provider)

                    # Get the wrapped create_trace_config
                    wrapped = opentelemetry.instrumentation.aiohttp_client.create_trace_config
                    trace_config = wrapped()

                    # Get the callbacks
                    spinal_on_request_start = trace_config.on_request_start[-1]
                    spinal_on_request_exception = trace_config.on_request_exception[-1]

                    # Create mock params
                    mock_start_params = Mock()
                    mock_start_params.url = "https://api.voyageai.com/v1/embeddings"
                    mock_start_params.method = "POST"
                    mock_start_params.data = b'{"input": ["test"]}'

                    test_exception = Exception("Test network error")
                    mock_exception_params = Mock()
                    mock_exception_params.exception = test_exception

                    trace_config_ctx = types.SimpleNamespace()

                    # Call on_request_start
                    await spinal_on_request_start(None, trace_config_ctx, mock_start_params)

                    # Verify Spinal span was created
                    assert trace_config_ctx.spinal_span is not None

                    # Call on_request_exception
                    await spinal_on_request_exception(None, trace_config_ctx, mock_exception_params)

                    # Verify span was finished with error
                    finished_spans = in_memory_span_exporter.get_finished_spans()
                    assert len(finished_spans) == 1

                    span = finished_spans[0]
                    from opentelemetry.trace import StatusCode

                    assert span.status.status_code == StatusCode.ERROR

                    # Verify exception was recorded
                    assert len(span.events) > 0
                    exception_event = span.events[0]
                    assert exception_event.name == "exception"

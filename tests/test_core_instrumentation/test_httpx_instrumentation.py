"""Tests for HTTPX instrumentation wrapper."""

from unittest.mock import Mock, patch

import httpx
from httpx import AsyncByteStream, SyncByteStream
from opentelemetry.semconv.trace import SpanAttributes
from opentelemetry.semconv_ai import SpanAttributes as AISpanAttributes

from sp_obs._internal.core.httpx.httpx import SpinalHTTPXClientInstrumentor
from sp_obs._internal.core.httpx.sync_stream import SyncStreamWrapper
from sp_obs._internal.core.httpx.async_stream import AsyncStreamWrapper


class TestSpinalHTTPXClientInstrumentor:
    """Test the main HTTPX instrumentation class."""

    def test_instrumentation_init(self, mock_tracer_provider, mock_tracer):
        """Test that instrumentation initializes correctly.

        Tests basic initialization of the instrumentor.
        """
        with patch("sp_obs._internal.core.httpx.httpx.get_tracer", return_value=mock_tracer):
            instrumentor = SpinalHTTPXClientInstrumentor()
            assert instrumentor is not None

    def test_instrument_patches_extract_response(self, mock_tracer_provider, mock_tracer):
        """Test that _instrument patches the _extract_response function.

        Tests that the instrumentor properly patches OpenTelemetry's HTTPX _extract_response function.
        """
        with patch("sp_obs._internal.core.httpx.httpx.get_tracer", return_value=mock_tracer):
            instrumentor = SpinalHTTPXClientInstrumentor()

            # Store original function
            import opentelemetry.instrumentation.httpx

            original_extract = opentelemetry.instrumentation.httpx._extract_response

            # Instrument
            instrumentor._instrument(tracer_provider=mock_tracer_provider)

            # Verify the function was patched
            current_extract = opentelemetry.instrumentation.httpx._extract_response
            assert current_extract != original_extract

    def test_integration_domain_filtering(self, mock_tracer_provider, mock_tracer):
        """Test that only integration domains are processed.

        Tests that the instrumentor only processes requests to known AI provider domains
        and skips non-integration domains.
        """
        with patch("sp_obs._internal.core.httpx.httpx.get_tracer", return_value=mock_tracer):
            instrumentor = SpinalHTTPXClientInstrumentor()

            # Test the wrapped extract function directly

            # Create a mock response
            response = Mock(spec=httpx.Response)
            response.stream = Mock(spec=SyncByteStream)

            # Create mock span with integration URL
            mock_span = Mock()
            mock_span.attributes = {SpanAttributes.HTTP_URL: "https://api.openai.com/v1/test"}

            # Patch the necessary functions
            with patch("sp_obs._internal.core.httpx.httpx.context.get_current"):
                with patch("sp_obs._internal.core.httpx.httpx.trace.get_current_span", return_value=mock_span):
                    with patch(
                        "sp_obs._internal.core.httpx.httpx.opentelemetry.instrumentation.httpx._extract_response",
                        return_value="result",
                    ):
                        instrumentor._instrument(tracer_provider=mock_tracer_provider)

                        # Get the wrapped function and call it
                        import opentelemetry.instrumentation.httpx

                        wrapped_extract = opentelemetry.instrumentation.httpx._extract_response
                        _ = wrapped_extract(response)

                        # Verify integration domain was processed
                        mock_span.set_attribute.assert_any_call("http.host", "api.openai.com")
                        mock_span.set_attribute.assert_any_call(AISpanAttributes.LLM_SYSTEM, "openai")
                        mock_span.set_attribute.assert_any_call("provider", "openai")
                        assert isinstance(response.stream, SyncStreamWrapper)

            # Test with non-integration domain
            mock_span.reset_mock()
            response = Mock(spec=httpx.Response)
            response.stream = Mock(spec=SyncByteStream)
            mock_span.attributes = {SpanAttributes.HTTP_URL: "https://httpbin.org/get"}

            with patch("sp_obs._internal.core.httpx.httpx.context.get_current"):
                with patch("sp_obs._internal.core.httpx.httpx.trace.get_current_span", return_value=mock_span):
                    with patch(
                        "sp_obs._internal.core.httpx.httpx.opentelemetry.instrumentation.httpx._extract_response",
                        return_value="result",
                    ):
                        _ = wrapped_extract(response)

                        # Should skip non-integration domain
                        mock_span.set_attribute.assert_not_called()
                        assert not isinstance(response.stream, (SyncStreamWrapper, AsyncStreamWrapper))

    def test_stream_wrapper_selection(self, mock_tracer_provider, mock_tracer):
        """Test that correct wrapper classes are used for async vs sync streams.

        Tests that AsyncByteStream gets wrapped with AsyncStreamWrapper and
        SyncByteStream gets wrapped with SyncStreamWrapper.
        """
        with patch("sp_obs._internal.core.httpx.httpx.get_tracer", return_value=mock_tracer):
            instrumentor = SpinalHTTPXClientInstrumentor()

            mock_span = Mock()
            mock_span.attributes = {SpanAttributes.HTTP_URL: "https://api.openai.com/v1/test"}

            with patch("sp_obs._internal.core.httpx.httpx.context.get_current"):
                with patch("sp_obs._internal.core.httpx.httpx.trace.get_current_span", return_value=mock_span):
                    with patch(
                        "sp_obs._internal.core.httpx.httpx.opentelemetry.instrumentation.httpx._extract_response",
                        return_value="result",
                    ):
                        instrumentor._instrument(tracer_provider=mock_tracer_provider)

                        # Get the wrapped function
                        import opentelemetry.instrumentation.httpx

                        wrapped_extract = opentelemetry.instrumentation.httpx._extract_response

                        # Test sync stream wrapping
                        response = Mock(spec=httpx.Response)
                        response.stream = Mock(spec=SyncByteStream)

                        wrapped_extract(response)
                        assert isinstance(response.stream, SyncStreamWrapper)

                        # Test async stream wrapping
                        response = Mock(spec=httpx.Response)
                        response.stream = Mock(spec=AsyncByteStream)

                        wrapped_extract(response)
                        assert isinstance(response.stream, AsyncStreamWrapper)

                        # Test unknown stream type (should not be wrapped)
                        response = Mock(spec=httpx.Response)
                        unknown_stream = Mock()  # Not AsyncByteStream or SyncByteStream
                        response.stream = unknown_stream

                        wrapped_extract(response)
                        assert response.stream == unknown_stream
                        assert not isinstance(response.stream, (SyncStreamWrapper, AsyncStreamWrapper))

    def test_span_attributes_set(self, mock_tracer_provider, mock_tracer):
        """Test that netloc and LLM_SYSTEM attributes are set correctly.

        Tests that the instrumentor sets the correct span attributes for
        netloc and LLM_SYSTEM based on the request URL.
        """
        with patch("sp_obs._internal.core.httpx.httpx.get_tracer", return_value=mock_tracer):
            instrumentor = SpinalHTTPXClientInstrumentor()

            mock_span = Mock()
            mock_span.attributes = {SpanAttributes.HTTP_URL: "https://api.anthropic.com/v1/messages"}

            response = Mock(spec=httpx.Response)
            response.stream = Mock(spec=SyncByteStream)

            with patch("sp_obs._internal.core.httpx.httpx.context.get_current"):
                with patch("sp_obs._internal.core.httpx.httpx.trace.get_current_span", return_value=mock_span):
                    with patch(
                        "sp_obs._internal.core.httpx.httpx.opentelemetry.instrumentation.httpx._extract_response",
                        return_value="result",
                    ):
                        instrumentor._instrument(tracer_provider=mock_tracer_provider)

                        # Get the wrapped function
                        import opentelemetry.instrumentation.httpx

                        wrapped_extract = opentelemetry.instrumentation.httpx._extract_response

                        wrapped_extract(response)

                        # Verify correct attributes were set
                        mock_span.set_attribute.assert_any_call("http.host", "api.anthropic.com")
                        mock_span.set_attribute.assert_any_call(AISpanAttributes.LLM_SYSTEM, "anthropic")
                        mock_span.set_attribute.assert_any_call("provider", "anthropic")

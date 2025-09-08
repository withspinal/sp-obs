"""Tests for Requests instrumentation wrapper."""

import pytest
from unittest.mock import Mock, patch

import requests
from requests import PreparedRequest, Session
from opentelemetry.trace import StatusCode

from sp_obs._internal.core.requests.requests import SpinalRequestsInstrumentor

from .utils.span_helpers import assert_span_attributes, assert_binary_data_captured, assert_span_name


class TestSpinalRequestsInstrumentor:
    """Test the main Requests instrumentation class."""

    def test_instrumentation_init(self, mock_tracer_provider, mock_tracer):
        """Test that instrumentation initializes correctly.

        Tests basic initialization of the instrumentor.
        """
        with patch("sp_obs._internal.core.requests.requests.get_tracer", return_value=mock_tracer):
            instrumentor = SpinalRequestsInstrumentor()
            assert instrumentor is not None

    def test_instrument_wraps_session_send(self, mock_tracer_provider, mock_tracer):
        """Test that _instrument wraps Session.send method.

        Tests that the instrumentor properly wraps the Session.send method.
        """
        with patch("sp_obs._internal.core.requests.requests.get_tracer", return_value=mock_tracer):
            # Store original Session.send
            original_send = Session.send

            instrumentor = SpinalRequestsInstrumentor()

            # Mock the parent class instrumentation to avoid OTel setup
            with patch("opentelemetry.instrumentation.requests.RequestsInstrumentor._instrument"):
                instrumentor._instrument(tracer_provider=mock_tracer_provider)

                # Verify Session.send was wrapped
                current_send = Session.send
                assert current_send != original_send

    def test_wrapped_send_creates_spans(
        self, mock_tracer_provider, real_tracer, mock_requests_response, in_memory_span_exporter
    ):
        """Test that wrapped send creates spans for all requests.

        Tests that the wrapped Session.send method creates spans for all HTTP requests.
        """
        with patch("sp_obs._internal.core.requests.requests.get_tracer", return_value=real_tracer):
            instrumentor = SpinalRequestsInstrumentor()

            # Mock the response
            mock_requests_response.headers = {"content-type": "application/json"}
            mock_requests_response.status_code = 200
            mock_requests_response.url = "https://httpbin.org/get"
            mock_requests_response._content = b"response data"
            mock_requests_response._content_consumed = True

            # Mock the original send method
            original_send = Mock(return_value=mock_requests_response)

            with patch("opentelemetry.instrumentation.requests.RequestsInstrumentor._instrument"):
                with patch.object(Session, "send", original_send):
                    instrumentor._instrument(tracer_provider=mock_tracer_provider)

                    # Get the wrapped send method
                    wrapped_send = Session.send

                    # Create a test session and request
                    session = Session()
                    session.stream = False  # Non-streaming
                    request = PreparedRequest()
                    request.url = "https://httpbin.org/get"
                    request.body = b"test request body"

                    # Call wrapped send
                    _ = wrapped_send(session, request)

                    # Verify span was created
                    finished_spans = in_memory_span_exporter.get_finished_spans()
                    assert len(finished_spans) == 1

                    span = finished_spans[0]
                    assert_span_name(span, "spinal.requests")

                    # Verify basic attributes
                    expected_attrs = {"http.status_code": 200, "http.host": "httpbin.org"}
                    assert_span_attributes(span, expected_attrs)

    def test_response_data_capture(self, mock_tracer_provider, real_tracer, in_memory_span_exporter):
        """Test response content capture.

        Tests that response data is captured and stored in span attributes.
        """
        with patch("sp_obs._internal.core.requests.requests.get_tracer", return_value=real_tracer):
            instrumentor = SpinalRequestsInstrumentor()

            # Create mock response with content
            response = Mock()
            response.headers = {"content-type": "application/json"}
            response.status_code = 200
            response.url = "https://api.openai.com/v1/models"
            response._content = b"response content data"
            response._content_consumed = True

            original_send = Mock(return_value=response)

            with patch("opentelemetry.instrumentation.requests.RequestsInstrumentor._instrument"):
                with patch.object(Session, "send", original_send):
                    instrumentor._instrument(tracer_provider=mock_tracer_provider)

                    # Create session and request
                    session = Session()
                    session.stream = False  # Non-streaming
                    request = PreparedRequest()
                    request.url = "https://api.openai.com/v1/models"
                    request.body = b"request data"

                    # Call wrapped send
                    _ = Session.send(session, request)

                    # Verify span was created and data captured
                    finished_spans = in_memory_span_exporter.get_finished_spans()
                    assert len(finished_spans) == 1

                    span = finished_spans[0]

                    # Verify response data was captured
                    assert_binary_data_captured(span, len(b"response content data"))

                    # Verify streaming attribute
                    expected_attrs = {
                        "spinal.response.streaming": False,
                    }
                    assert_span_attributes(span, expected_attrs)

    def test_streaming_response_setup(self, mock_tracer_provider, real_tracer, in_memory_span_exporter):
        """Test streaming response setup.

        Tests that streaming responses are properly set up with wrapping.
        """
        with patch("sp_obs._internal.core.requests.requests.get_tracer", return_value=real_tracer):
            instrumentor = SpinalRequestsInstrumentor()

            # Create mock streaming response with content property
            response = Mock()
            response.headers = {"content-type": "text/event-stream"}
            response.status_code = 200
            response.url = "https://api.openai.com/v1/stream"
            response._content = False  # Indicates streaming
            response._content_consumed = False
            response.raw = Mock()

            # Mock iter_content
            response.iter_content = Mock(return_value=iter([b"chunk1", b"chunk2"]))

            # Mock content property to avoid AttributeError
            type(response).content = Mock()
            type(response).content.fget = Mock(return_value=b"streaming content")

            original_send = Mock(return_value=response)

            with patch("opentelemetry.instrumentation.requests.RequestsInstrumentor._instrument"):
                with patch.object(Session, "send", original_send):
                    instrumentor._instrument(tracer_provider=mock_tracer_provider)

                    # Create session and request with streaming
                    session = Session()
                    session.stream = False
                    request = PreparedRequest()
                    request.url = "https://api.openai.com/v1/stream"
                    request.body = None

                    # Call with stream=True
                    _ = Session.send(session, request, stream=True)

                    # Consume the stream so the span ends
                    _ = list(_.iter_content(chunk_size=1))

                    # Verify streaming setup was applied
                    # Note: For streaming, span is not ended immediately
                    finished_spans = in_memory_span_exporter.get_finished_spans()
                    assert len([s for s in finished_spans if s.name == "spinal.requests"]) == 1

    def test_exception_handling(self, mock_tracer_provider, real_tracer, in_memory_span_exporter):
        """Test exception handling and error status recording.

        Tests that exceptions are properly handled and recorded in spans.
        """
        with patch("sp_obs._internal.core.requests.requests.get_tracer", return_value=real_tracer):
            instrumentor = SpinalRequestsInstrumentor()

            # Mock send to raise exception
            test_exception = requests.RequestException("Test network error")
            original_send = Mock(side_effect=test_exception)

            with patch("opentelemetry.instrumentation.requests.RequestsInstrumentor._instrument"):
                with patch.object(Session, "send", original_send):
                    instrumentor._instrument(tracer_provider=mock_tracer_provider)

                    # Create session and request
                    session = Session()
                    request = PreparedRequest()
                    request.url = "https://api.openai.com/v1/error"
                    request.body = None

                    # Call wrapped send - should raise exception
                    with pytest.raises(requests.RequestException, match="Test network error"):
                        Session.send(session, request)

                    # Verify span was created with error status
                    finished_spans = in_memory_span_exporter.get_finished_spans()
                    assert len(finished_spans) == 1

                    span = finished_spans[0]
                    assert_span_name(span, "spinal.requests")

                    # Verify error status
                    assert span.status.status_code == StatusCode.ERROR

                    # Verify exception was recorded
                    assert len(span.events) > 0
                    exception_event = span.events[0]
                    assert exception_event.name == "exception"

    def test_url_redaction(self, mock_tracer_provider, real_tracer, mock_requests_response, in_memory_span_exporter):
        """Test URL redaction for security.

        Tests that sensitive information in URLs is properly redacted.
        """
        with patch("sp_obs._internal.core.requests.requests.get_tracer", return_value=real_tracer):
            instrumentor = SpinalRequestsInstrumentor()

            mock_requests_response.headers = {"content-type": "application/json"}
            mock_requests_response.status_code = 200
            mock_requests_response._content = b"response"
            mock_requests_response._content_consumed = True

            original_send = Mock(return_value=mock_requests_response)

            with patch("opentelemetry.instrumentation.requests.RequestsInstrumentor._instrument"):
                with patch.object(Session, "send", original_send):
                    # Mock redact_url to test it's being used
                    with patch("sp_obs._internal.core.requests.requests.redact_url") as mock_redact:
                        mock_redact.return_value = "https://api.openai.com/v1/***"

                        instrumentor._instrument(tracer_provider=mock_tracer_provider)

                        # Create session and request with sensitive URL
                        session = Session()
                        session.stream = False
                        request = PreparedRequest()
                        request.url = "https://api.openai.com/v1/secret?api_key=sk-123456"
                        request.body = None

                        # Call wrapped send
                        _ = Session.send(session, request)

                        # Verify redact_url was called
                        mock_redact.assert_called_once_with(request.url)

                        # Verify redacted URL in span
                        finished_spans = in_memory_span_exporter.get_finished_spans()
                        span = finished_spans[0]

                        expected_attrs = {"http.url": "https://api.openai.com/v1/***"}
                        assert_span_attributes(span, expected_attrs)

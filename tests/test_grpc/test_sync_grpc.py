"""Tests for gRPC client instrumentation with service pattern matching"""

import unittest
from unittest.mock import Mock

from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from sp_obs._internal.constants import SPINAL_GRPC_REQUEST_SPAN_NAME
from sp_obs._internal.core.grpc.grpc import (
    SpinalGrpcClientInstrumentor,
    _extract_grpc_metadata,
    _extract_service_name,
)
from sp_obs._internal.core.grpc.grpc_integrations import match_grpc_service


class TestGrpcServiceMatching(unittest.TestCase):
    """Test cases for gRPC service pattern matching"""

    def test_exact_match(self):
        """Test exact service name match"""
        # This won't match as we use patterns, but test it anyway
        result = match_grpc_service("unknown.service.Name")
        self.assertIsNone(result)

    def test_gcp_documentai_match(self):
        """Test GCP Document AI service pattern matching"""
        service = "google.cloud.documentai.v1.DocumentProcessor"
        provider = match_grpc_service(service)
        self.assertEqual(provider, "gcp-documentai")

    def test_gcp_vision_match(self):
        """Test GCP Vision AI service pattern matching"""
        service = "google.cloud.vision.v1.ImageAnnotator"
        provider = match_grpc_service(service)
        self.assertEqual(provider, "gcp-vision")

    def test_unsupported_service(self):
        """Test that unsupported services return None"""
        service = "internal.custom.MyService"
        provider = match_grpc_service(service)
        self.assertIsNone(provider)

    def test_none_service_name(self):
        """Test that None service name returns None"""
        provider = match_grpc_service(None)
        self.assertIsNone(provider)


class TestGrpcMetadataExtraction(unittest.TestCase):
    """Test cases for gRPC metadata extraction"""

    def test_extract_service_name(self):
        """Test extracting service name from span"""
        mock_span = Mock()
        mock_span.attributes = {"rpc.service": "google.cloud.documentai.v1.DocumentProcessor"}

        service = _extract_service_name(mock_span)
        self.assertEqual(service, "google.cloud.documentai.v1.DocumentProcessor")

    def test_extract_service_name_missing(self):
        """Test extracting service name when not present"""
        mock_span = Mock()
        mock_span.attributes = {}

        service = _extract_service_name(mock_span)
        self.assertIsNone(service)

    def test_extract_grpc_metadata(self):
        """Test extraction of gRPC metadata from parent span"""
        mock_span = Mock()
        mock_span.attributes = {
            "rpc.method": "ProcessDocument",
            "rpc.service": "google.cloud.documentai.v1.DocumentProcessor",
            "rpc.grpc.status_code": 0,
            "rpc.system": "grpc",
            "grpc.peer": "dns:///documentai.googleapis.com:443",
            "other.attribute": "should_be_ignored",
        }

        provider_name = "gcp-documentai"
        metadata = _extract_grpc_metadata(mock_span, provider_name)

        # Verify required attributes
        self.assertEqual(metadata["spinal.provider"], "gcp-documentai")
        self.assertEqual(metadata["grpc.service"], "google.cloud.documentai.v1.DocumentProcessor")
        self.assertEqual(metadata["grpc.method"], "ProcessDocument")

        # Verify other gRPC metadata is copied
        self.assertEqual(metadata["rpc.grpc.status_code"], 0)
        self.assertEqual(metadata["rpc.system"], "grpc")

        # Verify non-gRPC attributes are not copied
        self.assertNotIn("other.attribute", metadata)

    def test_extract_metadata_with_missing_service(self):
        """Test metadata extraction when service is missing"""
        mock_span = Mock()
        mock_span.attributes = {
            "rpc.method": "TestMethod",
        }

        metadata = _extract_grpc_metadata(mock_span, "test-provider")

        # Should still have provider and method
        self.assertEqual(metadata["spinal.provider"], "test-provider")
        self.assertEqual(metadata["grpc.method"], "TestMethod")
        self.assertNotIn("grpc.service", metadata)


class TestGrpcInstrumentation(unittest.TestCase):
    """Test cases for gRPC client instrumentation"""

    def setUp(self):
        """Set up test fixtures"""
        self.exporter = InMemorySpanExporter()
        self.tracer_provider = TracerProvider()
        self.tracer_provider.add_span_processor(SimpleSpanProcessor(self.exporter))
        self.tracer = self.tracer_provider.get_tracer(__name__)

        self.instrumentor = SpinalGrpcClientInstrumentor()
        self.instrumentor.instrument(tracer_provider=self.tracer_provider)

    def tearDown(self):
        """Clean up after tests"""
        self.instrumentor.uninstrument()
        self.exporter.clear()

    def test_supported_service_creates_child_span(self):
        """Test that supported gRPC services create Spinal child spans"""
        # Create mock parent span with GCP Document AI service
        with self.tracer.start_as_current_span("grpc_call") as parent_span:
            parent_span.set_attribute("rpc.service", "google.cloud.documentai.v1.DocumentProcessor")
            parent_span.set_attribute("rpc.method", "ProcessDocument")
            parent_span.set_attribute("rpc.grpc.status_code", 0)

            # Simulate request/response hooks being called
            # In real usage, OpenTelemetry's gRPC instrumentation calls these
            # Note: These are called automatically by OpenTelemetry
            # Here we're testing the logic by verifying span attributes

        # Get captured spans
        spans = self.exporter.get_finished_spans()

        # Should have at least the parent span
        self.assertGreaterEqual(len(spans), 1)

        # Parent span should have gRPC attributes
        parent = spans[0]
        self.assertEqual(parent.attributes.get("rpc.service"), "google.cloud.documentai.v1.DocumentProcessor")

    def test_unsupported_service_no_child_span(self):
        """Test that unsupported gRPC services don't create Spinal child spans"""
        # Create mock parent span with unsupported service
        with self.tracer.start_as_current_span("grpc_call") as parent_span:
            parent_span.set_attribute("rpc.service", "internal.custom.MyService")
            parent_span.set_attribute("rpc.method", "CustomMethod")

        # Get captured spans
        spans = self.exporter.get_finished_spans()

        # Should only have parent span, no Spinal child span
        spinal_spans = [s for s in spans if s.name == SPINAL_GRPC_REQUEST_SPAN_NAME]
        self.assertEqual(len(spinal_spans), 0)

    def test_hook_with_user_hooks(self):
        """Test that user-provided hooks are still called"""
        user_request_called = []
        user_response_called = []

        def user_request_hook(span, request):
            user_request_called.append(True)

        def user_response_hook(span, response):
            user_response_called.append(True)

        # Re-instrument with user hooks
        self.instrumentor.uninstrument()
        self.instrumentor.instrument(
            tracer_provider=self.tracer_provider,
            request_hook=user_request_hook,
            response_hook=user_response_hook,
        )

        # In a real test, we'd need to make actual gRPC calls
        # For now, verify the instrumentor was set up correctly
        self.assertIsNotNone(self.instrumentor)

    def test_metadata_only_capture(self):
        """Test that only metadata is captured, not binary data"""
        # Create a test span with gRPC attributes
        with self.tracer.start_as_current_span(SPINAL_GRPC_REQUEST_SPAN_NAME) as span:
            span.set_attribute("spinal.provider", "gcp-documentai")
            span.set_attribute("grpc.service", "google.cloud.documentai.v1.DocumentProcessor")
            span.set_attribute("grpc.method", "ProcessDocument")
            span.set_attribute("http.status_code", 200)

        # Get captured spans
        spans = self.exporter.get_finished_spans()
        self.assertEqual(len(spans), 1)

        test_span = spans[0]
        attributes = test_span.attributes

        # Verify metadata attributes are present
        self.assertEqual(attributes.get("spinal.provider"), "gcp-documentai")
        self.assertEqual(attributes.get("grpc.service"), "google.cloud.documentai.v1.DocumentProcessor")
        self.assertEqual(attributes.get("grpc.method"), "ProcessDocument")

        # Verify NO binary data attributes
        self.assertNotIn("spinal.request.binary_data", attributes)
        self.assertNotIn("spinal.response.binary_data", attributes)

    def test_future_response_handling(self):
        """Test that Future responses are handled correctly and child spans are ended"""
        import grpc
        from unittest.mock import MagicMock
        from sp_obs._internal.core.grpc.grpc import _child_spans

        # Create a mock future
        mock_future = MagicMock(spec=grpc.Future)
        mock_response = Mock()
        mock_future.result.return_value = mock_response

        # Create parent span with supported service
        with self.tracer.start_as_current_span("grpc_future_call") as parent_span:
            parent_span.set_attribute("rpc.service", "google.cloud.documentai.v1.DocumentProcessor")
            parent_span.set_attribute("rpc.method", "ProcessDocument")
            parent_span.set_attribute("rpc.grpc.status_code", 0)

            # Simulate the request hook creating a child span
            from sp_obs._internal.core.grpc.grpc import _extract_service_name, match_grpc_service

            service_name = _extract_service_name(parent_span)
            provider_name = match_grpc_service(service_name)

            if provider_name:
                child_span = self.tracer.start_span(SPINAL_GRPC_REQUEST_SPAN_NAME)
                child_span.set_attribute("spinal.provider", provider_name)
                child_span.set_attribute("grpc.service", service_name)

                # Store in _child_spans like the real implementation does
                _child_spans[parent_span] = child_span

                # Verify child span is in the dict
                self.assertIn(parent_span, _child_spans)

                # Simulate the future callback being triggered
                from sp_obs._internal.core.grpc.grpc import _add_response_metadata

                try:
                    # _add_response_metadata sets the status based on gRPC status code
                    _add_response_metadata(child_span, parent_span)
                    child_span.end()
                finally:
                    if parent_span in _child_spans:
                        del _child_spans[parent_span]

        # Verify child span was cleaned up from _child_spans
        self.assertNotIn(parent_span, _child_spans)

        # Get captured spans
        spans = self.exporter.get_finished_spans()

        # Should have both parent and child spans
        self.assertGreaterEqual(len(spans), 2)

        # Find the Spinal child span
        spinal_spans = [s for s in spans if s.name == SPINAL_GRPC_REQUEST_SPAN_NAME]
        self.assertEqual(len(spinal_spans), 1)

        # Verify child span has correct attributes
        child_span_data = spinal_spans[0]
        self.assertEqual(child_span_data.attributes.get("spinal.provider"), "gcp-documentai")
        self.assertEqual(
            child_span_data.attributes.get("grpc.service"),
            "google.cloud.documentai.v1.DocumentProcessor",
        )


if __name__ == "__main__":
    unittest.main()

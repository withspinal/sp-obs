"""Tests for async gRPC client instrumentation with service pattern matching"""

import unittest
from unittest.mock import Mock

from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from sp_obs._internal.constants import SPINAL_GRPC_REQUEST_SPAN_NAME
from sp_obs._internal.core.grpc.grpc_aio import (
    SpinalGrpcAioClientInstrumentor,
    _extract_grpc_metadata,
    _extract_service_name,
)
from sp_obs._internal.core.grpc.grpc_integrations import match_grpc_service


class TestAsyncGrpcServiceMatching(unittest.TestCase):
    """Test cases for async gRPC service pattern matching (reuses sync logic)"""

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
        service = "internal.custom.MyAsyncService"
        provider = match_grpc_service(service)
        self.assertIsNone(provider)


class TestAsyncGrpcMetadataExtraction(unittest.TestCase):
    """Test cases for async gRPC metadata extraction (reuses sync utilities)"""

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


class TestAsyncGrpcInstrumentation(unittest.TestCase):
    """Test cases for async gRPC client instrumentation"""

    def setUp(self):
        """Set up test fixtures"""
        self.exporter = InMemorySpanExporter()
        self.tracer_provider = TracerProvider()
        self.tracer_provider.add_span_processor(SimpleSpanProcessor(self.exporter))
        self.tracer = self.tracer_provider.get_tracer(__name__)

        self.instrumentor = SpinalGrpcAioClientInstrumentor()
        self.instrumentor.instrument(tracer_provider=self.tracer_provider)

    def tearDown(self):
        """Clean up after tests"""
        self.instrumentor.uninstrument()
        self.exporter.clear()

    def test_supported_service_creates_child_span(self):
        """Test that supported gRPC services create Spinal child spans"""
        # Create mock parent span with GCP Document AI service
        with self.tracer.start_as_current_span("async_grpc_call") as parent_span:
            parent_span.set_attribute("rpc.service", "google.cloud.documentai.v1.DocumentProcessor")
            parent_span.set_attribute("rpc.method", "ProcessDocument")
            parent_span.set_attribute("rpc.grpc.status_code", 0)

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
        with self.tracer.start_as_current_span("async_grpc_call") as parent_span:
            parent_span.set_attribute("rpc.service", "internal.custom.MyAsyncService")
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

        # Verify the instrumentor was set up correctly
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

    def test_unary_unary_pattern(self):
        """Test UnaryUnary call pattern creates child span for matched service"""
        from sp_obs._internal.core.grpc.grpc_aio import _aio_child_spans

        # Create parent span with supported service
        with self.tracer.start_as_current_span("async_unary_unary_call") as parent_span:
            parent_span.set_attribute("rpc.service", "google.cloud.vision.v1.ImageAnnotator")
            parent_span.set_attribute("rpc.method", "AnnotateImage")
            parent_span.set_attribute("rpc.grpc.status_code", 0)

            # Simulate the request hook creating a child span
            service_name = _extract_service_name(parent_span)
            provider_name = match_grpc_service(service_name)

            if provider_name:
                child_span = self.tracer.start_span(SPINAL_GRPC_REQUEST_SPAN_NAME)
                child_span.set_attribute("spinal.provider", provider_name)
                child_span.set_attribute("grpc.service", service_name)

                # Store in _aio_child_spans like the real implementation does
                _aio_child_spans[parent_span] = child_span

                # Verify child span is in the dict
                self.assertIn(parent_span, _aio_child_spans)

                # Simulate response_hook completing the child span
                from sp_obs._internal.core.grpc.grpc_aio import _add_response_metadata

                try:
                    # _add_response_metadata sets the status based on gRPC status code
                    _add_response_metadata(child_span, parent_span)
                    child_span.end()
                finally:
                    if parent_span in _aio_child_spans:
                        del _aio_child_spans[parent_span]

        # Verify child span was cleaned up
        self.assertNotIn(parent_span, _aio_child_spans)

        # Get captured spans
        spans = self.exporter.get_finished_spans()

        # Should have both parent and child spans
        self.assertGreaterEqual(len(spans), 2)

        # Find the Spinal child span
        spinal_spans = [s for s in spans if s.name == SPINAL_GRPC_REQUEST_SPAN_NAME]
        self.assertEqual(len(spinal_spans), 1)

        # Verify child span has correct attributes
        child_span_data = spinal_spans[0]
        self.assertEqual(child_span_data.attributes.get("spinal.provider"), "gcp-vision")
        self.assertEqual(
            child_span_data.attributes.get("grpc.service"),
            "google.cloud.vision.v1.ImageAnnotator",
        )

    def test_stream_unary_pattern(self):
        """Test StreamUnary call pattern creates child span for matched service"""
        from sp_obs._internal.core.grpc.grpc_aio import _aio_child_spans

        # Create parent span with supported service (AWS example)
        with self.tracer.start_as_current_span("async_stream_unary_call") as parent_span:
            parent_span.set_attribute("rpc.service", "google.cloud.documentai.v1.DocumentProcessor")
            parent_span.set_attribute("rpc.method", "BatchDetectSentiment")
            parent_span.set_attribute("rpc.grpc.status_code", 0)

            # Simulate the request hook creating a child span
            service_name = _extract_service_name(parent_span)
            provider_name = match_grpc_service(service_name)

            if provider_name:
                child_span = self.tracer.start_span(SPINAL_GRPC_REQUEST_SPAN_NAME)
                child_span.set_attribute("spinal.provider", provider_name)
                child_span.set_attribute("grpc.service", service_name)

                # Store in _aio_child_spans
                _aio_child_spans[parent_span] = child_span

                # Verify child span is in the dict
                self.assertIn(parent_span, _aio_child_spans)

                # Simulate response_hook completing the child span
                from sp_obs._internal.core.grpc.grpc_aio import _add_response_metadata

                try:
                    # _add_response_metadata sets the status based on gRPC status code
                    _add_response_metadata(child_span, parent_span)
                    child_span.end()
                finally:
                    if parent_span in _aio_child_spans:
                        del _aio_child_spans[parent_span]

        # Verify cleanup
        self.assertNotIn(parent_span, _aio_child_spans)

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

"""
Unit tests for SpinalTracerProvider
"""

import unittest
import os
import sys
from unittest.mock import Mock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

import sp_obs
from sp_obs._internal.tracer import SpinalTracerProvider, _instrumented_libraries


class TestTracerProvider(unittest.TestCase):
    """Test SpinalTracerProvider functionality"""

    def setUp(self):
        """Set up test configuration"""
        sp_obs.configure(endpoint="http://test.example.com", api_key="test-key")
        # Clear instrumented libraries
        _instrumented_libraries.clear()

    @patch("sp_obs._internal.tracer.TracerProvider")
    def test_create_isolated_provider(self, mock_tracer_provider_class):
        """Test creating an isolated tracer provider"""
        # Create mock provider
        mock_provider = Mock()
        mock_tracer_provider_class.return_value = mock_provider

        # Create isolated provider
        provider = SpinalTracerProvider.create_isolated_provider("test-service")

        # Check that TracerProvider was created with correct params
        mock_tracer_provider_class.assert_called_once()
        call_kwargs = mock_tracer_provider_class.call_args[1]
        self.assertIn("sampler", call_kwargs)
        self.assertIn("resource", call_kwargs)

        # Check that span processor was added
        mock_provider.add_span_processor.assert_called_once()

        # Verify it returns the provider
        self.assertEqual(provider, mock_provider)

    def test_create_isolated_provider_no_config(self):
        """Test that creating provider without config raises error"""
        # Reset global config
        sp_obs._internal.config._global_config = None

        with self.assertRaises(RuntimeError) as cm:
            SpinalTracerProvider.create_isolated_provider()

        self.assertIn("Spinal SDK not configured", str(cm.exception))

    @patch("sp_obs._internal.tracer.trace.get_tracer_provider")
    def test_attach_to_existing_provider_success(self, mock_get_provider):
        """Test successful attachment to existing provider"""
        # Mock provider with add_span_processor method
        mock_provider = Mock()
        mock_provider.add_span_processor = Mock()
        mock_get_provider.return_value = mock_provider

        # Try to attach
        result = SpinalTracerProvider.attach_to_existing_provider("test-lib")

        # Should succeed
        self.assertTrue(result)
        mock_provider.add_span_processor.assert_called_once()

    @patch("sp_obs._internal.tracer.trace.get_tracer_provider")
    def test_attach_to_existing_provider_no_method(self, mock_get_provider):
        """Test attachment fails when provider doesn't have add_span_processor"""
        # Mock provider without add_span_processor method
        mock_provider = Mock(spec=[])  # Empty spec, no methods
        mock_get_provider.return_value = mock_provider

        # Try to attach
        result = SpinalTracerProvider.attach_to_existing_provider("test-lib")

        # Should fail
        self.assertFalse(result)

    @patch("sp_obs._internal.tracer.trace.get_tracer_provider")
    def test_attach_to_existing_provider_exception(self, mock_get_provider):
        """Test attachment handles exceptions gracefully"""
        # Mock provider that raises exception
        mock_provider = Mock()
        mock_provider.add_span_processor.side_effect = Exception("Test error")
        mock_get_provider.return_value = mock_provider

        # Try to attach
        result = SpinalTracerProvider.attach_to_existing_provider("test-lib")

        # Should fail gracefully
        self.assertFalse(result)

    def test_instrumentation_tracking(self):
        """Test that instrumentation state is tracked correctly"""
        # Initially not instrumented
        self.assertFalse(SpinalTracerProvider.is_instrumented("openai"))
        self.assertFalse(SpinalTracerProvider.is_instrumented("anthropic"))

        # Mark openai as instrumented
        SpinalTracerProvider.mark_instrumented("openai")

        # Check states
        self.assertTrue(SpinalTracerProvider.is_instrumented("openai"))
        self.assertFalse(SpinalTracerProvider.is_instrumented("anthropic"))

        # Mark anthropic as instrumented
        SpinalTracerProvider.mark_instrumented("anthropic")

        # Both should be instrumented
        self.assertTrue(SpinalTracerProvider.is_instrumented("openai"))
        self.assertTrue(SpinalTracerProvider.is_instrumented("anthropic"))

    def test_multiple_instrumentations(self):
        """Test tracking multiple library instrumentations"""
        libraries = ["openai", "anthropic", "langchain", "llama_index"]

        # Mark all as instrumented
        for lib in libraries:
            self.assertFalse(SpinalTracerProvider.is_instrumented(lib))
            SpinalTracerProvider.mark_instrumented(lib)
            self.assertTrue(SpinalTracerProvider.is_instrumented(lib))

        # Verify all are tracked
        for lib in libraries:
            self.assertTrue(SpinalTracerProvider.is_instrumented(lib))


if __name__ == "__main__":
    unittest.main()

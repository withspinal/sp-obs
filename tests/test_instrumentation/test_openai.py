"""
Unit tests for OpenAI instrumentation
"""

import unittest
import os
import sys
from unittest.mock import Mock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

import sp_obs


class TestOpenAIInstrumentation(unittest.TestCase):
    """Test OpenAI instrumentation functionality"""

    def setUp(self):
        """Set up test configuration"""
        # Reset global config
        sp_obs._internal.config._global_config = None
        # Configure SDK
        sp_obs.configure(endpoint="http://test.example.com", api_key="test-key")

    @patch("sp_obs.provider.OpenAIInstrumentor")
    @patch("sp_obs._internal.tracer.logger")
    def test_instrument_openai_fresh(self, mock_logger, mock_instrumentor_class):
        """Test instrumenting OpenAI when it's not already instrumented"""
        # Create mock instrumentor instance
        mock_instrumentor = Mock()
        mock_instrumentor.is_instrumented_by_opentelemetry = False
        mock_instrumentor_class.return_value = mock_instrumentor

        # Call instrument_openai
        sp_obs.instrument_openai()

        # Check that instrumentor was called
        mock_instrumentor.instrument.assert_called_once()

        # Check that isolated provider was created
        self.assertTrue(mock_logger.info.called)
        self.assertIn("Creating isolated tracer provider", str(mock_logger.info.call_args_list))

    @patch("sp_obs.provider.OpenAIInstrumentor")
    @patch("sp_obs._internal.tracer.SpinalTracerProvider.attach_to_existing_provider")
    def test_instrument_openai_already_instrumented(self, mock_attach, mock_instrumentor_class):
        """Test instrumenting OpenAI when it's already instrumented"""
        # Create mock instrumentor instance
        mock_instrumentor = Mock()
        mock_instrumentor.is_instrumented_by_opentelemetry = True
        mock_instrumentor_class.return_value = mock_instrumentor

        # Mock successful attachment
        mock_attach.return_value = True

        # Call instrument_openai
        sp_obs.instrument_openai()

        # Check that we tried to attach to existing
        mock_attach.assert_called_once_with("openai")

        # Check that instrument was NOT called (already instrumented)
        mock_instrumentor.instrument.assert_not_called()

    @patch("sp_obs.provider.OpenAIInstrumentor")
    @patch("sp_obs._internal.tracer.SpinalTracerProvider.attach_to_existing_provider")
    def test_instrument_openai_attach_fails(self, mock_attach, mock_instrumentor_class):
        """Test instrumenting OpenAI when attachment to existing provider fails"""
        # Create mock instrumentor instance
        mock_instrumentor = Mock()
        mock_instrumentor.is_instrumented_by_opentelemetry = True
        mock_instrumentor_class.return_value = mock_instrumentor

        # Mock failed attachment
        mock_attach.return_value = False

        # Call instrument_openai
        sp_obs.instrument_openai()

        # Check that we tried to attach
        mock_attach.assert_called_once_with("openai")

        # Check that we fell back to creating isolated provider
        mock_instrumentor.instrument.assert_called_once()

    def test_instrument_without_configuration(self):
        """Test that instrumenting without configuration raises error"""
        # Reset global config
        sp_obs._internal.config._global_config = None

        with self.assertRaises(RuntimeError) as cm:
            sp_obs.instrument_openai()

        self.assertIn("Spinal SDK not configured", str(cm.exception))


if __name__ == "__main__":
    unittest.main()

"""
Unit tests for billing functionality
"""

import pytest
from unittest.mock import patch, MagicMock
from opentelemetry.trace import ProxyTracerProvider

from sp_obs.billing import add_billing_event


class TestAddBillingEvent:
    """Test add_billing_event function"""

    def test_add_billing_event_with_configured_provider(self):
        """Test add_billing_event creates span with correct attributes when provider is configured.

        Tests that the billing event creates a span with proper attributes including:
        - The billing success status
        - Custom attributes with spinal.billing namespace
        - The is_billing_span marker
        """
        # Create mock objects
        mock_span = MagicMock()
        mock_tracer = MagicMock()
        mock_tracer.start_as_current_span.return_value.__enter__.return_value = mock_span
        mock_provider = MagicMock()
        mock_provider.get_tracer.return_value = mock_tracer
        mock_tracer_provider = MagicMock()
        mock_tracer_provider.provider = mock_provider

        with patch("sp_obs.billing.get_tracer_provider", return_value=mock_tracer_provider):
            # Call the function with test data
            add_billing_event(
                success=True, user_id="test-user-123", amount=99.99, currency="USD", subscription_tier="premium"
            )

            # Verify tracer was obtained correctly
            mock_provider.get_tracer.assert_called_once_with("sp_obs.billing")

            # Verify span was started with correct name
            mock_tracer.start_as_current_span.assert_called_once_with("spinal.billing_span")

            # Verify attributes were set correctly
            expected_calls = [
                ("spinal.billing.user_id", "test-user-123"),
                ("spinal.billing.amount", "99.99"),
                ("spinal.billing.currency", "USD"),
                ("spinal.billing.subscription_tier", "premium"),
                ("is_billing_span", True),
                ("billing_success", True),
            ]

            # Check all expected attributes were set
            actual_calls = [(call[0][0], call[0][1]) for call in mock_span.set_attribute.call_args_list]
            for expected_key, expected_value in expected_calls:
                assert (expected_key, expected_value) in actual_calls

    def test_add_billing_event_with_failure_status(self):
        """Test add_billing_event correctly records failed billing events.

        Tests that the billing_success attribute is set to False when
        a billing operation fails.
        """
        # Create mock objects
        mock_span = MagicMock()
        mock_tracer = MagicMock()
        mock_tracer.start_as_current_span.return_value.__enter__.return_value = mock_span
        mock_provider = MagicMock()
        mock_provider.get_tracer.return_value = mock_tracer
        mock_tracer_provider = MagicMock()
        mock_tracer_provider.provider = mock_provider

        with patch("sp_obs.billing.get_tracer_provider", return_value=mock_tracer_provider):
            # Call with failure status
            add_billing_event(success=False, error_code="INSUFFICIENT_FUNDS", user_id="test-user-456")

            # Check that billing_success was set to False
            mock_span.set_attribute.assert_any_call("billing_success", False)

            # Check error code was recorded
            mock_span.set_attribute.assert_any_call("spinal.billing.error_code", "INSUFFICIENT_FUNDS")

    def test_add_billing_event_without_configured_provider(self):
        """Test add_billing_event raises ValueError when provider is not configured.

        Tests that calling add_billing_event without first configuring the
        tracing provider raises an appropriate error message.
        """
        # Mock get_tracer_provider to return a ProxyTracerProvider (indicating unconfigured state)
        mock_tracer_provider = MagicMock()
        mock_tracer_provider.provider = ProxyTracerProvider()

        with patch("sp_obs.billing.get_tracer_provider", return_value=mock_tracer_provider):
            with pytest.raises(ValueError) as exc_info:
                add_billing_event(success=True, amount=50.0)

            assert "Cannot add billing event - spinal tracing provider is not set" in str(exc_info.value)
            assert "Please call sp_obs.configure() first" in str(exc_info.value)

    def test_add_billing_event_with_empty_kwargs(self):
        """Test add_billing_event works with no additional attributes.

        Tests that the function works correctly when called with only
        the required success parameter and no additional kwargs.
        """
        # Create mock objects
        mock_span = MagicMock()
        mock_tracer = MagicMock()
        mock_tracer.start_as_current_span.return_value.__enter__.return_value = mock_span
        mock_provider = MagicMock()
        mock_provider.get_tracer.return_value = mock_tracer
        mock_tracer_provider = MagicMock()
        mock_tracer_provider.provider = mock_provider

        with patch("sp_obs.billing.get_tracer_provider", return_value=mock_tracer_provider):
            # Call with only success parameter
            add_billing_event(success=True)

            # Verify minimal required attributes were set
            mock_span.set_attribute.assert_any_call("is_billing_span", True)
            mock_span.set_attribute.assert_any_call("billing_success", True)

            # Should only have the two required attributes
            assert mock_span.set_attribute.call_count == 2

    def test_add_billing_event_converts_values_to_strings(self):
        """Test add_billing_event converts all attribute values to strings.

        Tests that numeric, boolean, and other non-string values are
        properly converted to strings before being set as span attributes.
        """
        # Create mock objects
        mock_span = MagicMock()
        mock_tracer = MagicMock()
        mock_tracer.start_as_current_span.return_value.__enter__.return_value = mock_span
        mock_provider = MagicMock()
        mock_provider.get_tracer.return_value = mock_tracer
        mock_tracer_provider = MagicMock()
        mock_tracer_provider.provider = mock_provider

        with patch("sp_obs.billing.get_tracer_provider", return_value=mock_tracer_provider):
            # Call with various data types
            add_billing_event(success=True, integer_value=42, float_value=3.14159, boolean_value=False, none_value=None)

            # Verify values were converted to strings
            mock_span.set_attribute.assert_any_call("spinal.billing.integer_value", "42")
            mock_span.set_attribute.assert_any_call("spinal.billing.float_value", "3.14159")
            mock_span.set_attribute.assert_any_call("spinal.billing.boolean_value", "False")
            mock_span.set_attribute.assert_any_call("spinal.billing.none_value", "None")

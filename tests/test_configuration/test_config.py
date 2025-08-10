"""
Unit tests for configuration module
"""

import pytest
import os
from unittest.mock import patch

from sp_obs._internal.config import SpinalConfig, configure, get_config
from sp_obs import DefaultScrubber


class TestSpinalConfig:
    """Test SpinalConfig class"""

    def test_config_with_explicit_values(self):
        """Test configuration with explicit values.

        Tests SpinalConfig initialization with all parameters explicitly provided.
        """
        config = SpinalConfig(
            endpoint="https://api.example.com",
            api_key="test-key",
            timeout=10,
            max_export_batch_size=256,
            max_queue_size=1024,
            schedule_delay_millis=2000,
            export_timeout_millis=15000,
        )

        assert config.endpoint == "https://api.example.com"
        assert config.api_key == "test-key"
        assert config.timeout == 10
        assert config.max_export_batch_size == 256
        assert config.max_queue_size == 1024
        assert config.schedule_delay_millis == 2000
        assert config.export_timeout_millis == 15000
        assert "X-SPINAL-API-KEY" in config.headers
        assert config.headers["X-SPINAL-API-KEY"] == "test-key"

    @patch.dict(os.environ, {"SPINAL_TRACING_ENDPOINT": "https://env.example.com", "SPINAL_API_KEY": "env-key"})
    def test_config_from_environment(self):
        """Test configuration from environment variables.

        Tests SpinalConfig loading endpoint and API key from environment variables.
        """
        config = SpinalConfig()

        assert config.endpoint == "https://env.example.com"
        assert config.api_key == "env-key"
        assert config.timeout == 5  # default
        assert config.max_export_batch_size == 512  # default
        assert config.max_queue_size == 2048  # default
        assert config.schedule_delay_millis == 5000  # default
        assert config.export_timeout_millis == 30000  # default

    def test_config_with_default_endpoint(self):
        """Test configuration with default endpoint.

        Tests that SpinalConfig uses default endpoint when none provided.
        """
        with patch.dict(os.environ, {"SPINAL_API_KEY": "test-key"}, clear=True):
            config = SpinalConfig()
            assert config.endpoint == "https://cloud.withspinal.com"
            assert config.api_key == "test-key"

    def test_config_missing_api_key(self):
        """Test configuration raises error when API key is missing.

        Tests that SpinalConfig raises ValueError when no API key is available.
        """
        with patch.dict(os.environ, {"SPINAL_TRACING_ENDPOINT": "https://test.com"}, clear=True):
            with pytest.raises(ValueError) as exc_info:
                SpinalConfig()
            assert "No API key provided" in str(exc_info.value)

    def test_config_missing_endpoint_and_api_key(self):
        """Test configuration raises error for missing API key first.

        Tests that missing API key error takes precedence over missing endpoint.
        """
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError) as exc_info:
                SpinalConfig()
            assert "No API key provided" in str(exc_info.value)

    def test_config_with_scrubber(self):
        """Test configuration with scrubber.

        Tests SpinalConfig accepts and stores custom scrubber instances.
        """
        scrubber = DefaultScrubber()
        config = SpinalConfig(endpoint="https://api.example.com", api_key="test-key", scrubber=scrubber)

        assert config.scrubber == scrubber

    def test_config_default_scrubber(self):
        """Test configuration creates default scrubber.

        Tests that SpinalConfig creates DefaultScrubber when none provided.
        """
        config = SpinalConfig(endpoint="https://api.example.com", api_key="test-key")
        assert isinstance(config.scrubber, DefaultScrubber)

    @patch.dict(
        os.environ,
        {
            "SPINAL_PROCESS_MAX_QUEUE_SIZE": "4096",
            "SPINAL_PROCESS_MAX_EXPORT_BATCH_SIZE": "1024",
            "SPINAL_PROCESS_SCHEDULE_DELAY": "10000",
            "SPINAL_PROCESS_EXPORT_TIMEOUT": "60000",
            "SPINAL_API_KEY": "test-key",
        },
    )
    def test_config_batch_processing_env_vars(self):
        """Test configuration loads batch processing parameters from environment.

        Tests SpinalConfig loads batch processing settings from environment variables.
        """
        config = SpinalConfig()

        assert config.max_queue_size == 4096
        assert config.max_export_batch_size == 1024
        assert config.schedule_delay_millis == 10000
        assert config.export_timeout_millis == 60000

    @patch.dict(os.environ, {"SPINAL_PROCESS_MAX_QUEUE_SIZE": "invalid", "SPINAL_API_KEY": "test-key"})
    def test_config_handles_invalid_env_vars(self):
        """Test configuration handles invalid environment variable values.

        Tests SpinalConfig falls back to defaults for invalid environment variable values.
        """
        config = SpinalConfig()

        # Should fall back to default when env var is invalid
        assert config.max_queue_size == 2048  # default

    def test_config_headers_merge(self):
        """Test configuration properly merges custom headers.

        Tests that SpinalConfig merges custom headers with API key header.
        """
        custom_headers = {"Custom-Header": "custom-value"}
        config = SpinalConfig(endpoint="https://api.example.com", api_key="test-key", headers=custom_headers)

        assert config.headers["Custom-Header"] == "custom-value"
        assert config.headers["X-SPINAL-API-KEY"] == "test-key"


class TestGlobalConfiguration:
    """Test global configuration functions"""

    def setup_method(self):
        """Reset global config before each test"""
        global _global_config
        _global_config = None

    def test_configure_function(self):
        """Test the global configure function.

        Tests that configure() creates and returns a global SpinalConfig instance.
        """
        # Mock the instrumentation to avoid actual setup
        with patch("sp_obs._internal.config.SpinalTracerProvider"):
            with patch("sp_obs._internal.config.SpinalHTTPXClientInstrumentor"):
                with patch("sp_obs._internal.config.SpinalRequestsInstrumentor"):
                    config = configure(
                        endpoint="https://api.example.com",
                        api_key="test-key",
                        timeout=15,
                        max_export_batch_size=256,
                        scrubber=DefaultScrubber(),
                    )

        assert isinstance(config, SpinalConfig)
        assert config.endpoint == "https://api.example.com"
        assert config.api_key == "test-key"
        assert config.timeout == 15
        assert config.max_export_batch_size == 256
        assert isinstance(config.scrubber, DefaultScrubber)

    @patch.dict(os.environ, {"SPINAL_API_KEY": "test-key"})
    def test_get_config_initially_none(self):
        """Test get_config calls configure when no global config exists.

        Tests that get_config() calls configure() when no global config exists.
        """
        # Mock the instrumentation to avoid actual setup
        with patch("sp_obs._internal.config.SpinalTracerProvider"):
            with patch("sp_obs._internal.config.SpinalHTTPXClientInstrumentor"):
                with patch("sp_obs._internal.config.SpinalRequestsInstrumentor"):
                    # Patch the global config to None to simulate first call
                    with patch("sp_obs._internal.config._global_config", None):
                        config = get_config()

                        # Should return a configured SpinalConfig instance
                        assert isinstance(config, SpinalConfig)
                        assert config.endpoint == "https://cloud.withspinal.com"  # default
                        assert config.api_key == "test-key"

    def test_get_config_returns_existing(self):
        """Test get_config returns existing configuration.

        Tests that get_config() returns the global configuration when it exists.
        """
        # Mock the instrumentation to avoid actual setup
        with patch("sp_obs._internal.config.SpinalTracerProvider"):
            with patch("sp_obs._internal.config.SpinalHTTPXClientInstrumentor"):
                with patch("sp_obs._internal.config.SpinalRequestsInstrumentor"):
                    # Set up global config first by calling configure
                    test_config = configure(endpoint="https://test.com", api_key="test-key")

                    # Now get_config should return the same instance
                    config = get_config()
                    assert config is test_config

    def test_reconfigure(self):
        """Test reconfiguring overwrites previous config.

        Tests that calling configure() multiple times overwrites the global configuration.
        """
        # Mock the instrumentation to avoid actual setup
        with patch("sp_obs._internal.config.SpinalTracerProvider"):
            with patch("sp_obs._internal.config.SpinalHTTPXClientInstrumentor"):
                with patch("sp_obs._internal.config.SpinalRequestsInstrumentor"):
                    # First configuration
                    config1 = configure(endpoint="https://api1.example.com", api_key="key1")

                    # Second configuration
                    config2 = configure(endpoint="https://api2.example.com", api_key="key2")

        # Should be different instances
        assert config1 != config2
        assert config2.endpoint == "https://api2.example.com"
        assert config2.api_key == "key2"

        # Global config should be the latest
        assert get_config() == config2

    def test_configure_sets_up_instrumentation(self):
        """Test configure function sets up instrumentation.

        Tests that configure() properly initializes tracer provider and instrumentors.
        """
        with patch("sp_obs._internal.config.SpinalTracerProvider") as mock_tracer_provider:
            with patch("sp_obs._internal.config.SpinalHTTPXClientInstrumentor") as mock_httpx_instrumentor:
                with patch("sp_obs._internal.config.SpinalRequestsInstrumentor") as mock_requests_instrumentor:
                    mock_httpx_instance = mock_httpx_instrumentor.return_value
                    mock_requests_instance = mock_requests_instrumentor.return_value

                    configure(endpoint="https://api.example.com", api_key="test-key")

                    # Verify tracer provider was created with config
                    mock_tracer_provider.assert_called_once()

                    # Verify instrumentors were created and instrumented
                    mock_httpx_instrumentor.assert_called_once()
                    mock_requests_instrumentor.assert_called_once()
                    mock_httpx_instance.instrument.assert_called_once()
                    mock_requests_instance.instrument.assert_called_once()

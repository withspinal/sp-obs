"""
Unit tests for configuration module
"""

import unittest
import os
from unittest.mock import patch
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

import sp_obs
from sp_obs import SpinalConfig, DefaultScrubber


class TestSpinalConfig(unittest.TestCase):
    """Test SpinalConfig class"""

    def test_config_with_explicit_values(self):
        """Test configuration with explicit values"""
        config = SpinalConfig(endpoint="https://api.example.com", api_key="test-key", timeout=10, batch_size=50)

        self.assertEqual(config.endpoint, "https://api.example.com")
        self.assertEqual(config.api_key, "test-key")
        self.assertEqual(config.timeout, 10)
        self.assertEqual(config.batch_size, 50)
        self.assertIn("X-SPINAL-API-KEY", config.headers)
        self.assertEqual(config.headers["X-SPINAL-API-KEY"], "test-key")

    @patch.dict(os.environ, {"SPINAL_TRACING_ENDPOINT": "https://env.example.com", "SPINAL_API_KEY": "env-key"})
    def test_config_from_environment(self):
        """Test configuration from environment variables"""
        config = SpinalConfig()

        self.assertEqual(config.endpoint, "https://env.example.com")
        self.assertEqual(config.api_key, "env-key")
        self.assertEqual(config.timeout, 5)  # default
        self.assertEqual(config.batch_size, 100)  # default

    def test_config_missing_endpoint(self):
        """Test configuration raises error when endpoint is missing"""
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ValueError) as cm:
                SpinalConfig()
            self.assertIn("endpoint must be provided", str(cm.exception))

    def test_config_with_scrubber(self):
        """Test configuration with scrubber"""
        scrubber = DefaultScrubber()
        config = SpinalConfig(endpoint="https://api.example.com", api_key="test-key", scrubber=scrubber)

        self.assertEqual(config.scrubber, scrubber)


class TestGlobalConfiguration(unittest.TestCase):
    """Test global configuration functions"""

    def setUp(self):
        """Reset global config before each test"""
        sp_obs._internal.config._global_config = None

    def test_configure_function(self):
        """Test the global configure function"""
        config = sp_obs.configure(
            endpoint="https://api.example.com",
            api_key="test-key",
            timeout=15,
            batch_size=200,
            scrubber=DefaultScrubber(),
        )

        self.assertIsInstance(config, SpinalConfig)
        self.assertEqual(config.endpoint, "https://api.example.com")
        self.assertEqual(config.api_key, "test-key")
        self.assertEqual(config.timeout, 15)
        self.assertEqual(config.batch_size, 200)
        self.assertIsInstance(config.scrubber, DefaultScrubber)

    def test_get_config(self):
        """Test getting the global configuration"""
        # Initially None
        self.assertIsNone(sp_obs.get_config())

        # Configure
        sp_obs.configure(endpoint="https://api.example.com", api_key="test-key")

        # Now should return config
        config = sp_obs.get_config()
        self.assertIsNotNone(config)
        self.assertEqual(config.endpoint, "https://api.example.com")

    def test_reconfigure(self):
        """Test reconfiguring overwrites previous config"""
        # First configuration
        sp_obs.configure(endpoint="https://api1.example.com", api_key="key1")
        config1 = sp_obs.get_config()

        # Second configuration
        sp_obs.configure(endpoint="https://api2.example.com", api_key="key2")
        config2 = sp_obs.get_config()

        # Should be different
        self.assertNotEqual(config1.endpoint, config2.endpoint)
        self.assertEqual(config2.endpoint, "https://api2.example.com")


if __name__ == "__main__":
    unittest.main()

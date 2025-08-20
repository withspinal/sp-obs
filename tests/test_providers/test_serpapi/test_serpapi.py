from typing import Any, Dict
import pytest

from sp_obs._internal.core.providers import get_provider


class TestSerpapiProvider:
    """Test Serpapi provider functionality"""

    @pytest.fixture
    def sample_response_attributes(self) -> Dict[str, Any]:
        """Provide sample Serpapi response attributes from actual span"""
        return {
            "spinal.provider": "serpapi",
            "content-type": "application/json; charset=utf-8",
            "content-encoding": "gzip",
            "http.status_code": 200,
            "http.url": "https://serpapi.com/search?q=Coffee&engine=google&serp_api_key=REDACTED&output=json&source=python",
            "http.host": "serpapi.com",
            "spinal.http.request.query.q": "Coffee",
            "spinal.http.request.query.engine": "google",
            "spinal.http.request.query.output": "json",
            "spinal.http.request.query.source": "python",
            "spinal.response.size": 96256,
            "spinal.response.streaming": False,
        }

    def test_provider_identification(self, sample_response_attributes):
        """Test that the correct provider is identified"""
        provider = get_provider(sample_response_attributes["spinal.provider"])

        # Verify it's the SerpapiProvider provider
        from sp_obs._internal.core.providers.serpapi import SerpapiProvider

        assert isinstance(provider, SerpapiProvider), f"Expected SerpapiProvider instance, got {type(provider)}"

    def test_parse_response_attributes(self, sample_response_attributes):
        """Test that the response attributes are parsed correctly"""
        provider = get_provider(sample_response_attributes["spinal.provider"])
        parsed = provider.parse_response_attributes(sample_response_attributes)

        # Test that the response attributes are parsed correctly
        assert parsed == {}

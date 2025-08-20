from typing import Any, Dict
import pytest

from sp_obs._internal.core.providers import get_provider


class TestScrapingBeeProvider:
    """Test ScrapingBee provider functionality"""

    @pytest.fixture
    def sample_response_attributes(self) -> Dict[str, Any]:
        """Provide sample ScrapingBee response attributes from actual span"""
        return {
            "spinal.provider": "scrapingbee",
            "content-type": "text/html; charset=UTF-8",
            "content-encoding": "gzip",
            "http.status_code": 200,
            "http.url": "https://app.scrapingbee.com/api/v1/?api_key=REDACTED&url=https%3A%2F%2Fwww.geeksforgeeks.org%2Fpython%2Fself-in-python-class%2F&render_js=true",
            "http.host": "app.scrapingbee.com",
            "spinal.http.request.query.url": "https://www.geeksforgeeks.org/python/self-in-python-class/",
            "spinal.http.request.query.render_js": "true",
            "spinal.response.size": 215688,
            "spinal.response.streaming": False,
            "spinal.http.response.header.Spb-cost": "5",
        }

    def test_provider_identification(self, sample_response_attributes):
        """Test that the correct provider is identified"""
        provider = get_provider(sample_response_attributes["spinal.provider"])

        # Verify it's the ScrapingBeeProvider provider
        from sp_obs._internal.core.providers.scrapingbee import ScrapingBeeProvider

        assert isinstance(provider, ScrapingBeeProvider), f"Expected ScrapingBeeProvider instance, got {type(provider)}"

    def test_provider_parse_header_attributes(self, sample_response_attributes):
        """Test that the provider parses the header attributes correctly"""
        provider = get_provider("scrapingbee")

        headers = {"cost": "5"}

        parsed = provider.parse_response_headers(sample_response_attributes)
        # Verify it's returning the expected output
        assert parsed == headers

    def test_provider_parse_response_attributes(self, sample_response_attributes):
        """Test that the provider parses the response attributes correctly"""
        provider = get_provider("scrapingbee")
        # test that the provider returns an empty dict
        parsed = provider.parse_response_attributes(sample_response_attributes)
        assert parsed == {}

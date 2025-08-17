from typing import Any, Dict
import pytest

from sp_obs._internal.core.providers import get_provider


class TestFirecrawlProvider:
    """Test Firecrawl provider functionality"""

    @pytest.fixture
    def sample_response_attributes(self) -> Dict[str, Any]:
        """Provide sample Anthropic response attributes from actual span"""
        return {
            "spinal.provider": "firecrawl",
            "content-type": "application/json; charset=utf-8",
            "content-encoding": "",
            "http.status_code": 200,
            "http.url": "https://api.firecrawl.dev/v1/scrape",
            "http.host": "api.firecrawl.dev",
            "spinal.response.size": 313014,
            "spinal.response.streaming": False,
            "url": "firecrawl.dev",
            "origin": "python-sdk@2.16.5",
            "formats": ["markdown", "html"],
            "success": True,
            "data": {"random": "data", "more": {"test": "data"}},
        }

    def test_provider_identification(self, sample_response_attributes):
        """Test that the correct provider is identified"""
        provider = get_provider(sample_response_attributes["spinal.provider"])

        # Verify it's the FirecrawlProvider provider
        from sp_obs._internal.core.providers.firecrawl import FirecrawlProvider

        assert isinstance(provider, FirecrawlProvider), f"Expected FirecrawlProvider instance, got {type(provider)}"

    def test_parse_response_attributes_removes_text_content(self, sample_response_attributes):
        """Test that parse_response_attributes removes thinking and text content"""
        provider = get_provider(sample_response_attributes["spinal.provider"])

        # Parse the attributes
        parsed = provider.parse_response_attributes(sample_response_attributes)

        # Verify structure is preserved
        assert "success" in parsed
        assert "url" in parsed
        assert "origin" in parsed
        assert "formats" in parsed

        # Verify content items have their text/thinking removed
        assert "data" not in parsed

    def test_parse_response_attributes_empty_content(self):
        """Test parse_response_attributes handles empty or missing content gracefully"""
        provider = get_provider("firecrawl")

        # Test with missing content key
        response_attributes = {"metadata": "some_value"}
        parsed = provider.parse_response_attributes(response_attributes)
        assert parsed == {"metadata": "some_value"}

from typing import Any, Dict
import pytest

from sp_obs._internal.core.providers import get_provider


class TestElevenLabsProvider:
    """Test ElevenLabs provider functionality"""

    @pytest.fixture
    def sample_response_attributes(self) -> Dict[str, Any]:
        """Provide sample ElevenLabs response attributes from actual span"""
        return {
            "http.method": "POST",
            "spinal.provider": "elevenlabs",
            "gen_ai.system": "elevenlabs",
            "content-type": "application/json",
            "content-encoding": "",
            "spinal.response.size": 1000,
            "spinal.response.streaming": False,
            "http.status_code": 200,
            "http.url": "https://api.elevenlabs.io/v1/speech-to-text",
            "http.host": "api.elevenlabs.io",
            "language_code": "eng",
            "language_probability": 1,
            "text": "Hello, world!",
            "words": ["Hello", "world"],
        }

    def test_provider_identification(self, sample_response_attributes):
        """Test that the correct provider is identified"""
        provider = get_provider(sample_response_attributes["spinal.provider"])

        # Verify it's the ElevenLabsProvider provider
        from sp_obs._internal.core.providers.elevenlabs import ElevenLabsProvider

        assert isinstance(provider, ElevenLabsProvider), f"Expected ElevenLabsProvider instance, got {type(provider)}"

    def test_parse_response_attributes_removes_content(self, sample_response_attributes):
        """Test that the provider parses the response attributes correctly"""
        provider = get_provider(sample_response_attributes["spinal.provider"])

        # Parse the attributes
        parsed = provider.parse_response_attributes(sample_response_attributes)

        # Verify structure is preserved
        assert "http.method" in parsed
        assert "http.url" in parsed

        # assert private user data is not included
        assert "text" not in parsed
        assert "words" not in parsed

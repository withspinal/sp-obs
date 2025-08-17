from typing import Any, Dict
import pytest

from sp_obs._internal.core.providers import get_provider


class TestAnthropicProvider:
    """Test Anthropic provider functionality"""

    @pytest.fixture
    def sample_response_attributes(self) -> Dict[str, Any]:
        """Provide sample Anthropic response attributes from actual span"""
        return {
            "http.method": "POST",
            "spinal.provider": "anthropic",
            "gen_ai.system": "anthropic",
            "spinal.workflow_id": "con1",
            "spinal.user_id": "x123",
            "content-type": "application/json",
            "content-encoding": "gzip",
            "http.status_code": 200,
            "http.url": "https://api.anthropic.com/v1/messages",
            "http.host": "api.anthropic.com",
            "max_tokens": 16000,
            "messages": [
                {"role": "user", "content": "Are there an infinite number of prime numbers such that n mod 4 == 3?"}
            ],
            "model": "claude-sonnet-4-20250514",
            "thinking": {"type": "enabled", "budget_tokens": 10000},
            "id": "msg_01HbqZWdZnVt8MEGJAyCKUvb",
            "type": "message",
            "role": "assistant",
            "content": [
                {
                    "type": "thinking",
                    "thinking": "This is asking about primes that are congruent to 3 modulo 4...",
                },
                {"type": "text", "text": "Yes, there are infinitely many prime numbers such that n ≡ 3 (mod 4)..."},
            ],
            "stop_reason": "end_turn",
            "stop_sequence": None,
            "usage": {
                "input_tokens": 54,
                "cache_creation_input_tokens": 0,
                "cache_read_input_tokens": 0,
                "cache_creation": {"ephemeral_5m_input_tokens": 0, "ephemeral_1h_input_tokens": 0},
                "output_tokens": 1857,
                "service_tier": "standard",
            },
        }

    def test_provider_identification(self):
        """Test that the correct provider is identified"""
        provider = get_provider("anthropic")

        # Verify it's the Anthropic provider
        from sp_obs._internal.core.providers.anthropic import AnthropicProvider

        assert isinstance(provider, AnthropicProvider), f"Expected AnthropicProvider instance, got {type(provider)}"

    def test_parse_response_attributes_removes_text_content(self, sample_response_attributes):
        """Test that parse_response_attributes removes thinking and text content"""
        provider = get_provider("anthropic")

        # Parse the attributes
        parsed = provider.parse_response_attributes(sample_response_attributes)

        # Verify structure is preserved
        assert "id" in parsed
        assert "type" in parsed
        assert "role" in parsed
        assert "model" in parsed
        assert "stop_reason" in parsed
        assert "usage" in parsed

        # Verify content items have their text/thinking removed
        assert "content" not in parsed

    def test_parse_response_attributes_empty_content(self):
        """Test parse_response_attributes handles empty or missing content gracefully"""
        provider = get_provider("anthropic")

        # Test with missing content key
        response_attributes = {"metadata": "some_value"}
        parsed = provider.parse_response_attributes(response_attributes)
        assert parsed == {"metadata": "some_value"}

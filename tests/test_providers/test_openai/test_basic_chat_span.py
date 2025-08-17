from typing import Any, Dict
import pytest

from sp_obs._internal.core.providers import get_provider


class TestOpenAIProvider:
    """Test OpenAI provider functionality"""

    @pytest.fixture
    def sample_response_attributes(self) -> Dict[str, Any]:
        """Provide the sample span data"""
        return {
            "http.method": "POST",
            "spinal.provider": "openai",
            "gen_ai.system": "openai",
            "spinal_aggregation_id": "session-123",
            "spinal.workflow_id": "workflow-123",
            "spinal.user_id": "user-123",
            "spinal.candidate_uuid": "c20078c3-ffd2-429f-90ea-978c56473c85",
            "spinal.client_code": "test-client",
            "spinal.environment": "development",
            "content-type": "application/json",
            "content-encoding": "gzip",
            "http.status_code": 200,
            "http.url": "https://api.openai.com/v1/chat/completions",
            "http.host": "api.openai.com",
            "messages": [{"role": "system", "content": "write a short sentence"}],
            "model": "o3-mini-2025-01-31",
            "id": "chatcmpl-C5ZLK4lrn8opSmx4myaGhFXXe0Y1P",
            "object": "chat.completion",
            "created": 1755443534,
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "Stars twinkle brightly in the night sky.",
                        "refusal": None,
                        "annotations": [],
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 214,
                "total_tokens": 224,
                "prompt_tokens_details": {"cached_tokens": 0, "audio_tokens": 0},
                "completion_tokens_details": {
                    "reasoning_tokens": 192,
                    "audio_tokens": 0,
                    "accepted_prediction_tokens": 0,
                    "rejected_prediction_tokens": 0,
                },
            },
        }

    def test_provider_identification(self, sample_response_attributes):
        """Test that the correct provider is identified"""
        provider = get_provider(sample_response_attributes["spinal.provider"])

        # Verify it's the OpenAIProvider provider
        from sp_obs._internal.core.providers.openai import OpenAIProvider

        assert isinstance(provider, OpenAIProvider), f"Expected OpenAIProvider instance, got {type(provider)}"

    def test_parse_response_attributes_with_text_content(self, sample_response_attributes):
        """Test parse_response_attributes removes text fields from content"""
        provider = get_provider(sample_response_attributes["spinal.provider"])

        # Parse the attributes
        parsed = provider.parse_response_attributes(sample_response_attributes)

        # test that some fields are still there
        assert "usage" in parsed
        assert "object" in parsed
        assert "created" in parsed
        assert "model" in parsed
        assert "id" in parsed
        assert "http.status_code" in parsed
        assert "http.url" in parsed
        assert "http.host" in parsed
        assert "messages" in parsed
        assert "content-type" in parsed

        # choices should not be there!
        assert "choices" not in parsed

    def test_parse_response_attributes_empty_output(self):
        """Test parse_response_attributes handles empty or missing output gracefully"""
        provider = get_provider("openai")

        # Test with missing output key
        response_attributes = {"metadata": "some_value"}
        parsed = provider.parse_response_attributes(response_attributes)
        assert parsed == {"metadata": "some_value"}

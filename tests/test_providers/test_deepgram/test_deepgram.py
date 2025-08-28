from typing import Any, Dict
import pytest

from sp_obs._internal.core.providers import get_provider


class TestDeepgramProvider:
    """Test Deepgram provider functionality"""

    @pytest.fixture
    def sample_response_attributes_tts(self) -> Dict[str, Any]:
        """Provide sample Deepgram TTS response attributes from actual span"""
        return {
            "http.method": "POST",
            "spinal.provider": "deepgram",
            "gen_ai.system": "deepgram",
            "spinal.http.request.query.model": "aura-2-thalia-en",
            "content-type": "audio/mpeg",
            "content-encoding": "",
            "http.status_code": 200,
            "http.url": "https://api.deepgram.com/v1/speak?model=aura-2-thalia-en",
            "http.host": "api.deepgram.com",
            "text": "Hello world!",
            "audio_size_bytes": 7776,
            "audio_format": "audio/mpeg",
        }

    @pytest.fixture
    def sample_response_attributes_stt(self) -> Dict[str, Any]:
        """Provide sample Deepgram response attributes from actual span"""
        return {
            "http.method": "POST",
            "spinal.provider": "deepgram",
            "gen_ai.system": "deepgram",
            "spinal.http.request.query.model": "nova-3",
            "content-type": "application/json",
            "content-encoding": "",
            "http.status_code": 200,
            "http.url": "https://api.deepgram.com/v1/listen?model=nova-3",
            "http.host": "api.deepgram.com",
            "url": "https://dpgr.am/spacewalk.wav",
            "metadata": {
                "transaction_key": "deprecated",
                "request_id": "4bda55e2-4327-472c-ab7f-9933bf326c2a",
                "sha256": "154e291ecfa8be6ab8343560bcc109008fa7853eb5372533e8efdefc9b504c33",
                "created": "2025-08-27T17:10:10.135Z",
                "duration": 25.933313,
                "channels": 1,
                "models": ["2187e11a-3532-4498-b076-81fa530bdd49"],
                "model_info": {
                    "2187e11a-3532-4498-b076-81fa530bdd49": {
                        "name": "general-nova-3",
                        "version": "2025-07-31.0",
                        "arch": "nova-3",
                    }
                },
                "summary_info": {
                    "model_uuid": "67875a7f-c9c4-48a0-aa55-5bdb8a91c34a",
                    "input_tokens": 83,
                    "output_tokens": 64,
                },
                "intents_info": {
                    "model_uuid": "80ab3179-d113-4254-bd6b-4a2f96498695",
                    "input_tokens": 82,
                    "output_tokens": 10,
                },
                "sentiment_info": {
                    "model_uuid": "80ab3179-d113-4254-bd6b-4a2f96498695",
                    "input_tokens": 82,
                    "output_tokens": 82,
                },
                "topics_info": {
                    "model_uuid": "80ab3179-d113-4254-bd6b-4a2f96498695",
                    "input_tokens": 82,
                    "output_tokens": 7,
                },
                "extra": {"experiment": "max", "customer_id": "12345"},
            },
            "results": {
                "channels": [
                    {
                        "alternatives": [
                            {
                                "transcript": "yeah as as much as it's worth celebrating the first spacewalk with an all female team i think many of us are looking forward to it just being normal and i think if it signifies anything it is to honor the the women who came before us who were skilled and qualified and didn't get the same opportunities that we have today",
                                "confidence": 0.9984262,
                                "words": [
                                    {"word": "yeah", "start": 0, "end": 0.48, "confidence": 0.9959291},
                                    {"word": "as", "start": 0.48, "end": 0.64, "confidence": 0.9941525},
                                    {"word": "as", "start": 0.64, "end": 1.12, "confidence": 0.99290705},
                                    {"word": "have", "start": 24.875, "end": 25.035, "confidence": 0.99969804},
                                    {"word": "today", "start": 25.035, "end": 25.355, "confidence": 0.985095},
                                ],
                            }
                        ]
                    }
                ]
            },
            "events": [],
            "links": [],
            "instrumentation_info": {"name": "sp_obs._internal.core.httpx.httpx", "version": ""},
        }

    def test_provider_identification(self, sample_response_attributes_stt):
        """Test that the provider is identified correctly"""
        provider = get_provider(sample_response_attributes_stt["spinal.provider"])

        from sp_obs._internal.core.providers import DeepgramProvider

        assert isinstance(provider, DeepgramProvider), f"Expected DeepgramProvider instance, got {type(provider)}"

    def test_parse_stt_response_attributes(self, sample_response_attributes_stt):
        """Test that the STT response is scrubbed and duration is extracted"""
        provider = get_provider(sample_response_attributes_stt["spinal.provider"])

        parsed = provider.parse_response_attributes(sample_response_attributes_stt)

        assert "results" not in parsed
        assert "metadata" not in parsed
        assert "extra" not in parsed

        assert parsed["duration"] == 25.933313
        assert parsed["summary_info"] == {
            "model_uuid": "67875a7f-c9c4-48a0-aa55-5bdb8a91c34a",
            "input_tokens": 83,
            "output_tokens": 64,
        }

        assert parsed["sentiment_info"] == {
            "model_uuid": "80ab3179-d113-4254-bd6b-4a2f96498695",
            "input_tokens": 82,
            "output_tokens": 82,
        }

        assert parsed["topics_info"] == {
            "model_uuid": "80ab3179-d113-4254-bd6b-4a2f96498695",
            "input_tokens": 82,
            "output_tokens": 7,
        }

        assert parsed["intents_info"] == {
            "model_uuid": "80ab3179-d113-4254-bd6b-4a2f96498695",
            "input_tokens": 82,
            "output_tokens": 10,
        }

    def test_handle_tts_response(self, sample_response_attributes_tts):
        """Test that the provider handles a response with no words correctly"""
        provider = get_provider(sample_response_attributes_tts["spinal.provider"])

        parsed = provider.parse_response_attributes(sample_response_attributes_tts)

        assert "words" not in parsed
        assert "sentiment_info" not in parsed
        assert "topics_info" not in parsed
        assert "intents_info" not in parsed
        assert "summary_info" not in parsed


# we do not need to test text intelligence as responses are structured the same as audio intelligence for stt

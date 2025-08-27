from typing import Any, Dict
import pytest

from sp_obs._internal.core.providers import get_provider


class TestDeepgramProvider:
    """Test Deepgram provider functionality"""

    @pytest.fixture
    def sample_response_attributes(self) -> Dict[str, Any]:
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
                "request_id": "4bdfce43-cb5a-402f-bedf-d07bd361becf",
                "sha256": "154e291ecfa8be6ab8343560bcc109008fa7853eb5372533e8efdefc9b504c33",
                "created": "2025-08-26T15:27:05.207Z",
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

    def test_provider_identification(self, sample_response_attributes):
        """Test that the provider is identified correctly"""
        provider = get_provider(sample_response_attributes["spinal.provider"])

        from sp_obs._internal.core.providers import DeepgramProvider

        assert isinstance(provider, DeepgramProvider), f"Expected DeepgramProvider instance, got {type(provider)}"

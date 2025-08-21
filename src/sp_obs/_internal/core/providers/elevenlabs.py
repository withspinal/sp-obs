from typing import Any

from sp_obs._internal.core.providers import BaseProvider


class ElevenLabsProvider(BaseProvider):
    """Provider for ElevenLabs API for text-to-speech and speech-to-text end points"""

    def parse_response_attributes(self, response_attributes: dict[str, Any]) -> dict[str, Any]:
        # remove the 'text' field. Contains output from model
        response_attributes.pop("text", None)
        response_attributes.pop("words", None)
        return response_attributes

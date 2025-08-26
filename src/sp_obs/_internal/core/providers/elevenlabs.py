from typing import Any

from sp_obs._internal.core.providers import BaseProvider


class ElevenLabsProvider(BaseProvider):
    """Provider for ElevenLabs API for text-to-speech and speech-to-text end points"""

    def parse_response_attributes(self, response_attributes: dict[str, Any]) -> dict[str, Any]:
        """Parse response attributes to extract timing information for speech to text"""

        # Check if words exist and extract the end timestamp of the last word for speech to text
        words = response_attributes.get("words")
        if words and len(words) > 0:
            # Get the last word and extract its end timestamp
            last_word = words[-1]
            # print(f"last_word: {last_word}")

            if isinstance(last_word, dict) and "end" in last_word and last_word["end"] is not None:
                # Dictionary with 'end' key
                response_attributes["elevenlabs.last_word_end"] = last_word["end"]

        # Remove the words field after processing
        response_attributes.pop("words", None)
        response_attributes.pop("text", None)

        return response_attributes

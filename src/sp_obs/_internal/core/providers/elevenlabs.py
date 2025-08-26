from typing import Any

from sp_obs._internal.core.providers import BaseProvider


class ElevenLabsProvider(BaseProvider):
    """Provider for ElevenLabs API for text-to-speech and speech-to-text end points"""

    def parse_response_attributes(self, response_attributes: dict[str, Any]) -> dict[str, Any]:
        """Parse response attributes to extract timing information for speech to text"""

        # Check if words exist and extract the end timestamp of the last word for speech to text
        if words := response_attributes.get("words"):
            # Sort words by start time to ensure chronological order
            if isinstance(words, list) and len(words) > 0:
                # Sort by end time, extract end of last word
                last_word = max(words, key=lambda w: w["end"])

                if isinstance(last_word, dict) and "end" in last_word and last_word["end"] is not None:
                    # Dictionary with 'end' key
                    response_attributes["elevenlabs.last_word_end"] = last_word["end"]

        # Remove the words field after processing
        response_attributes.pop("words", None)
        response_attributes.pop("text", None)

        return response_attributes

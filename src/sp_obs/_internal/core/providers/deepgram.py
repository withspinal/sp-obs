from typing import Any

from sp_obs._internal.core.providers import BaseProvider


class DeepgramProvider(BaseProvider):
    """Provider for Deepgram API"""

    def parse_response_attributes(self, response_attributes: dict[str, Any]) -> dict[str, Any]:
        """Parse response attributes to extract timing information for speech to text"""

        # can pop results as duration is provided in metadata

        # keep only duration and token information from metadata, then remove metadata entirely
        if metadata := response_attributes.get("metadata"):
            # Extract duration
            if duration := metadata.get("duration"):
                response_attributes["duration"] = duration

            # Extract additional cost information if they exist
            if summary_info := metadata.get("summary_info"):
                response_attributes["summary_info"] = summary_info

            if sentiment_info := metadata.get("sentiment_info"):
                response_attributes["sentiment_info"] = sentiment_info

            if topics_info := metadata.get("topics_info"):
                response_attributes["topics_info"] = topics_info

            if intents_info := metadata.get("intents_info"):
                response_attributes["intents_info"] = intents_info

        # remove full metadata object to avoid storing sensitive/unnecessary fields
        response_attributes.pop("metadata", None)
        response_attributes.pop("results", None)

        return response_attributes

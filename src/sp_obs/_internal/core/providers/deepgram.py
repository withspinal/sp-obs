from typing import Any

from sp_obs._internal.core.providers import BaseProvider


class DeepgramProvider(BaseProvider):
    """Provider for Deepgram API"""

    def parse_response_attributes(self, response_attributes: dict[str, Any]) -> dict[str, Any]:
        """Parse response attributes to extract timing information for speech to text"""

        # can pop results as duration is provided in metadata
        response_attributes.pop("results", None)

        # keep only duration from metadata, then remove metadata entirely
        metadata = response_attributes.get("metadata")
        if isinstance(metadata, dict):
            duration = metadata.get("duration")
            if duration is not None:
                # store duration at top-level for cost calculation
                response_attributes["duration"] = duration
        # remove full metadata object to avoid storing sensitive/verbose fields
        response_attributes.pop("metadata", None)

        return response_attributes

    def handle_event_stream(self, event_stream: str) -> dict[str, Any]:
        """Handle event stream from Deepgram API"""

        return 0

from typing import Any

from sp_obs._internal.core.providers import BaseProvider


class DeepgramProvider(BaseProvider):
    """Provider for Deepgram API"""

    def parse_response_attributes(self, response_attributes: dict[str, Any]) -> dict[str, Any]:
        """Parse response attributes to extract timing information for speech to text"""

        # can pop results as duration is provided in metadata

        # keep only valuable field from metadata if they exist , then delkete the metadata field
        if metadata := response_attributes.get("metadata"):
            # Extract duration
            if duration := metadata.get("duration"):
                response_attributes["duration"] = duration

            # Extract model name and architecture from model_info if its given
            if model_info := metadata.get("model_info"):
                for model_id, model_details in model_info.items():
                    if model_name := model_details.get("name"):
                        arch = model_details.get("arch", "")

                        # Concatenate model name and architecture
                        if arch:
                            full_model_name = f"{model_name}-{arch}"
                        else:
                            full_model_name = model_name

                        response_attributes["model_name"] = full_model_name
                        break

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

from typing import Any
from orjson import orjson
from sp_obs._internal.core.providers.base import BaseProvider


class PerplexityProvider(BaseProvider):
    def parse_response_attributes(self, response_attributes: dict[str, Any]) -> dict[str, Any]:
        # keep only the usage and model fields
        final_response_attributes = {
            "usage": response_attributes.get("usage", {}),
            "model": response_attributes.get("model"),
        }

        return final_response_attributes

    def handle_event_stream(self, event_stream: str) -> dict[str, Any]:
        """
        Parse Server-Sent Events format and extract the final response.
        """
        usage = None
        model = None
        lines = event_stream.split("\n")

        for line in lines:
            if not line or not line.startswith("data:"):
                continue
            data = line[5:].strip()  # Remove "data: " prefix
            if data == "[DONE]":
                break

            obj = orjson.loads(data)
            if obj.get("usage"):
                usage = obj["usage"]
            if obj.get("model"):
                model = obj["model"]

        final_response_attributes = {
            "usage": usage,
            "model": model,
        }

        return final_response_attributes

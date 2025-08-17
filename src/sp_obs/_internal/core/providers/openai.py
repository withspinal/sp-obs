from typing import Any
from orjson import orjson

from sp_obs._internal.core.providers.base import BaseProvider


class OpenAIProvider(BaseProvider):
    """Provider for OpenAI API"""

    def parse_response_attributes(self, response_attributes: dict[str, Any]) -> dict[str, Any]:
        """
        Parses and processes the response attributes by removing unnecessary fields.
        """
        # remove the 'choices' field. Contains output from model
        response_attributes.pop("choices", None)

        for output in response_attributes.get("output", []):
            content = output.get("content", {})
            for c in content:
                c.pop("text", None)
            output.pop("result", None)  # handles images
        return response_attributes

    def handle_event_stream(self, event_stream: str) -> dict[str, Any]:
        """
        Parse Server-Sent Events format and extract the final response.
        """
        lines = event_stream.strip().split("\n")
        events = []
        current_event = {}

        for line in lines:
            if line.startswith("event:"):
                if current_event:
                    events.append(current_event)
                current_event = {"event": line[6:].strip()}
            elif line.startswith("data:"):
                data_str = line[5:].strip()
                try:
                    current_event["data"] = orjson.loads(data_str)
                except:  # noqa: E722
                    current_event["data"] = data_str
            elif line == "" and current_event:
                events.append(current_event)
                current_event = {}

        if current_event:
            events.append(current_event)

        # Find the completed response
        for event in reversed(events):
            if event.get("event") == "response.completed" and isinstance(event.get("data"), dict):
                return event["data"].get("response", {})

        # If no completed response, try to reconstruct from output items
        response_attributes = {"output": []}

        for event in events:
            if event.get("event") == "response.output_item.done" and isinstance(event.get("data"), dict):
                item = event["data"].get("item")
                if item:
                    response_attributes["output"].append(item)
        return response_attributes

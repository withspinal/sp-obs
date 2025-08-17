from typing import Any
from orjson import orjson

from sp_obs._internal.core.providers.base import BaseProvider


class AnthropicProvider(BaseProvider):
    """Provider for Anthropic API"""

    def parse_response_attributes(self, response_attributes: dict[str, Any]) -> dict[str, Any]:
        """
        Parses and processes the response attributes by removing unnecessary fields.
        """
        response_attributes.pop("content", None)
        return response_attributes

    def handle_event_stream(self, event_stream: str) -> dict[str, Any]:
        """
        Parse Anthropic Server-Sent Events format and extract the complete message.
        """
        lines = event_stream.strip().split("\n")
        events = []
        current_event = {}

        # Parse SSE lines into events
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

        # Initialize response structure
        response = {
            "id": None,
            "type": "message",
            "role": "assistant",
            "model": None,
            "content": [],
            "stop_reason": None,
            "stop_sequence": None,
            "usage": {},
        }

        # Track content blocks
        content_blocks = {}

        # Process events
        for event in events:
            event_type = event.get("event")
            data = event.get("data", {})

            if event_type == "message_start":
                message = data.get("message", {})
                response["id"] = message.get("id")
                response["model"] = message.get("model")
                response["role"] = message.get("role", "assistant")
                response["usage"] = message.get("usage", {})

            elif event_type == "content_block_start":
                index = data.get("index", 0)
                content_block = data.get("content_block", {})
                content_blocks[index] = {
                    "type": content_block.get("type", "text"),
                    "text": content_block.get("text", ""),
                }

            elif event_type == "content_block_delta":
                index = data.get("index", 0)
                delta = data.get("delta", {})
                if delta.get("type") == "text_delta":
                    if index not in content_blocks:
                        content_blocks[index] = {"type": "text", "text": ""}
                    content_blocks[index]["text"] += delta.get("text", "")

            elif event_type == "message_delta":
                delta = data.get("delta", {})
                if "stop_reason" in delta:
                    response["stop_reason"] = delta["stop_reason"]
                if "stop_sequence" in delta:
                    response["stop_sequence"] = delta["stop_sequence"]
                # Update usage if provided
                usage = data.get("usage", {})
                if usage:
                    response["usage"].update(usage)

        # Build content array from content blocks
        for index in sorted(content_blocks.keys()):
            block = content_blocks[index]
            response["content"].append({"type": block["type"], "text": block["text"]})

        return response

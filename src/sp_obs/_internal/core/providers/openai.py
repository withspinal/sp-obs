from typing import Any
from orjson import orjson


def parse_sse_data(sse_text: str) -> dict[str, Any]:
    """
    Parse Server-Sent Events format and extract the final response.
    """
    lines = sse_text.strip().split("\n")
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

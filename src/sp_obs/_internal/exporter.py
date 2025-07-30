import logging
import orjson

import httpx
from typing import Any, Optional

from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SpanExportResult, SpanExporter

from sp_obs._internal.config import get_config

logger = logging.getLogger(__name__)


class SpinalSpanExporter(SpanExporter):
    """Exports spans to a custom HTTP endpoint (Singleton)"""

    _instance: Optional["SpinalSpanExporter"] = None
    _initialized: bool = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self.config = get_config()
            self._shutdown = False
            self._session = httpx.Client(
                headers=self.config.headers,
                timeout=self.config.timeout,
            )
            self.__class__._initialized = True

    def export(self, spans: list[ReadableSpan]) -> SpanExportResult:
        if self._shutdown:
            return SpanExportResult.FAILURE

        try:
            span_data = []
            for span in spans:
                attributes = dict(span.attributes)
                attributes = self.remove_traceloop_entity_output(attributes)
                attributes.pop("traceloop.entity.input", None)
                if self.config.scrubber:
                    attributes = self.config.scrubber.scrub_attributes(attributes)

                span_dict = {
                    "name": span.name,
                    "trace_id": format(span.get_span_context().trace_id, "032x"),
                    "span_id": format(span.get_span_context().span_id, "016x"),
                    "parent_span_id": format(span.parent.span_id, "016x") if span.parent else None,
                    "start_time": span.start_time,
                    "end_time": span.end_time,
                    "status": {"status_code": span.status.status_code.name, "description": span.status.description}
                    if span.status
                    else None,
                    "attributes": attributes,
                    "events": [
                        {
                            "name": event.name,
                            "timestamp": event.timestamp,
                            "attributes": dict(event.attributes) if event.attributes else {},
                        }
                        for event in span.events
                    ]
                    if span.events
                    else [],
                    "links": [
                        {
                            "context": {
                                "trace_id": format(link.context.trace_id, "032x"),
                                "span_id": format(link.context.span_id, "016x"),
                            },
                            "attributes": dict(link.attributes) if link.attributes else {},
                        }
                        for link in span.links
                    ]
                    if span.links
                    else [],
                    "instrumentation_info": {
                        "name": span.instrumentation_scope.name,
                        "version": span.instrumentation_scope.version,
                    }
                    if span.instrumentation_scope
                    else None,
                }
                span_data.append(span_dict)

            response = self._session.post(self.config.endpoint, json={"spans": span_data})

            if 200 <= response.status_code < 300:
                logger.debug(f"Successfully exported {len(spans)} spans to {self.config.endpoint}")
                return SpanExportResult.SUCCESS
            else:
                logger.error(f"Failed to export spans. Status: {response.status_code}, Response: {response.text}")
                return SpanExportResult.FAILURE

        except Exception as e:
            logger.error(f"Error exporting spans: {e}")
            return SpanExportResult.FAILURE

    def remove_traceloop_entity_output(self, attributes: dict[str, Any]) -> dict[str, Any]:
        """
        From the attributes dictionary, fetch the traceloop.entity.output attribute.
        The entity output is a JSON string. It contains some very valuable cost information BUT can also contain the entire
        output for images. This content is saved in output.result
        """
        entity_output = attributes.get("traceloop.entity.output")
        if not entity_output:
            return attributes

        try:
            parsed = orjson.loads(entity_output)

            # Modify in place
            if "output" in parsed and isinstance(parsed["output"], list):
                for i, item_str in enumerate(parsed["output"]):
                    item = orjson.loads(item_str)
                    if item.get("type") == "image_generation_call" and "result" in item:
                        del item["result"]
                        parsed["output"][i] = orjson.dumps(item).decode("utf-8")
                        break

            attributes["traceloop.entity.output"] = orjson.dumps(parsed).decode("utf-8")

        except Exception as e:
            logger.error(f"Error parsing traceloop.entity.output: {e}")

        return attributes

    def shutdown(self) -> None:
        self.force_flush()

        self._shutdown = True
        if hasattr(self, "_session"):
            self._session.close()

import gzip
import logging
import typing

import orjson

import httpx
from typing import Any, Optional

if typing.TYPE_CHECKING:
    from sp_obs._internal.config import SpinalConfig

from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SpanExportResult, SpanExporter
from opentelemetry.instrumentation.utils import suppress_instrumentation
from sp_obs._internal.core.providers import get_provider

logger = logging.getLogger(__name__)


class SpinalSpanExporter(SpanExporter):
    """Exports spans to a custom HTTP endpoint (Singleton)"""

    _instance: Optional["SpinalSpanExporter"] = None
    _initialized: bool = False

    def __new__(cls, config: "SpinalConfig"):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, config: "SpinalConfig"):
        if not self._initialized:
            self.config = config
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
                attributes = self.decode_request_binary_data(attributes)
                attributes = self.decode_response_binary_data(attributes)
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

            with suppress_instrumentation():
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

    def decode_request_binary_data(self, attributes: dict[str, Any]) -> dict[str, Any]:
        """
        Decode the binary data from the request attributes and update the attributes with the resultant data.

        This method extracts and decodes binary data associated with a specific key from the provided
        attributes. It deserializes the binary data into a dictionary and updates the original attributes
        with the deserialized request parameters. If the specified binary data does not exist in the
        attributes, the original attributes are returned without modification.

        Parameters:
            attributes (dict[str, Any]): A dictionary of attributes that may contain the binary data
            to decode.

        Returns:
            dict[str, Any]: The updated attributes dictionary containing the decoded binary data as
            request parameters. If no binary data is found, the original attributes are returned.
        """
        raw_data_mv: memoryview | None = attributes.pop("spinal.request.binary_data", None)
        if not raw_data_mv:
            return attributes

        binary_data = bytes(raw_data_mv)
        request_attributes = orjson.loads(binary_data)
        request_input = request_attributes.get("input", [])
        if isinstance(request_input, list):
            for i in request_attributes.get("input", []):
                # We do not want to accept content from like images (OpenAI specific)
                if (d := i.get("id")) and d.startswith("ig_"):
                    del i["result"]

        provider = get_provider(attributes.get("spinal.provider"))
        parsed_attributes = provider.parse_request_attributes(request_attributes)
        attributes.update(parsed_attributes)
        return attributes

    def decode_response_binary_data(self, attributes: dict[str, Any]) -> dict[str, Any]:
        """
        Attributes will have a field called 'raw_binary_data'. This is a memoryview, and we need to change into
        a list of attributes. Bear in mind, these bytes could also be compressed.
        """
        raw_data_mv: memoryview | None = attributes.pop("spinal.response.binary_data", None)
        if not raw_data_mv:
            return attributes

        binary_data = bytes(raw_data_mv)
        content_encoding = attributes.get("content-encoding", "")
        if content_encoding == "gzip":
            try:
                binary_data = gzip.decompress(binary_data)
            except gzip.BadGzipFile:
                # Not gzipped despite header
                pass

        response_attributes = {}
        provider = get_provider(attributes.get("spinal.provider"))
        content_type = attributes.get("content-type", "")
        if any(
            audio_type in content_type
            for audio_type in ["audio/mpeg", "audio/mp3", "audio/wav", "audio/ogg", "audio/pcm", "audio/flac"]
        ):
            # For audio, we don't decode to text - store metadata instead
            response_attributes = {
                "audio_size_bytes": len(binary_data),
                "audio_format": content_type,
            }

        elif "text/event-stream" in content_type:
            text_data = safe_decode(binary_data)
            response_attributes = provider.handle_event_stream(event_stream=text_data)

        elif "application/json" in content_type:
            text_data = safe_decode(binary_data)
            try:
                response_attributes = orjson.loads(text_data)
            except Exception as e:
                response_attributes = {"raw_content": text_data, "parse_error": str(e), "content_type": content_type}

        response_attributes = provider.parse_response_attributes(response_attributes)

        # Lets scrub response headers for this provider
        all_response_headers = {
            k: attributes.pop(k) for k in list(attributes.keys()) if k.startswith("spinal.http.response.header.")
        }
        response_headers = provider.parse_response_headers(all_response_headers)

        return attributes | response_attributes | response_headers

    def shutdown(self) -> None:
        self.force_flush()

        self._shutdown = True
        if hasattr(self, "_session"):
            self._session.close()


def safe_decode(binary_data: bytes) -> str:
    """
    Safely decode binary data to string, trying multiple encodings if UTF-8 fails.

    Args:
        binary_data: The bytes to decode

    Returns:
        Decoded string (may contain replacement characters if decoding fails)
    """
    try:
        return binary_data.decode("utf-8")
    except UnicodeDecodeError:
        try:
            return binary_data.decode("windows-1252")
        except UnicodeDecodeError:
            pass

        # If all encodings fail, use latin-1 which accepts all byte values
        text_data = binary_data.decode("latin-1", errors="replace")
        return text_data

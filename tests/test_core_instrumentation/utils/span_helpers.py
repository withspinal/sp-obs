"""Utilities for testing spans and assertions."""

from typing import Dict, Any, Optional, List
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter


def assert_span_attributes(span: ReadableSpan, expected_attrs: Dict[str, Any]):
    """Assert that a span contains the expected attributes."""
    span_attrs = dict(span.attributes) if span.attributes else {}

    for key, expected_value in expected_attrs.items():
        assert key in span_attrs, f"Attribute '{key}' not found in span attributes: {list(span_attrs.keys())}"

        actual_value = span_attrs[key]

        # Handle memoryview comparisons
        if isinstance(expected_value, (bytes, memoryview)) and isinstance(actual_value, memoryview):
            assert bytes(actual_value) == bytes(expected_value), (
                f"Binary data mismatch for '{key}': expected {bytes(expected_value)}, got {bytes(actual_value)}"
            )
        else:
            assert actual_value == expected_value, (
                f"Attribute '{key}' mismatch: expected {expected_value}, got {actual_value}"
            )


def assert_span_name(span: ReadableSpan, expected_name: str):
    """Assert that a span has the expected name."""
    assert span.name == expected_name, f"Span name mismatch: expected '{expected_name}', got '{span.name}'"


def assert_binary_data_captured(span: ReadableSpan, expected_size: Optional[int] = None):
    """Assert that binary data was captured in the span."""
    span_attrs = dict(span.attributes) if span.attributes else {}

    assert "spinal.response.binary_data" in span_attrs, "Binary data not captured in span attributes"

    binary_data = span_attrs["spinal.response.binary_data"]
    # OpenTelemetry converts memoryview to tuple when storing as span attributes
    assert isinstance(binary_data, (memoryview, tuple)), (
        f"Binary data should be memoryview or tuple (after OTel processing), got {type(binary_data)}"
    )

    if expected_size is not None:
        actual_size = len(binary_data)
        assert actual_size == expected_size, f"Binary data size mismatch: expected {expected_size}, got {actual_size}"


def assert_request_data_captured(span: ReadableSpan, expected_size: Optional[int] = None):
    """Assert that request data was captured in the span."""
    span_attrs = dict(span.attributes) if span.attributes else {}

    assert "spinal.request.binary_data" in span_attrs, "Request binary data not captured in span attributes"

    binary_data = span_attrs["spinal.request.binary_data"]
    assert isinstance(binary_data, (memoryview, tuple)), (
        f"Binary data should be memoryview or tuple (after OTel processing), got {type(binary_data)}"
    )

    if expected_size is not None:
        actual_size = len(binary_data)
        assert actual_size == expected_size, (
            f"Request binary data size mismatch: expected {expected_size}, got {actual_size}"
        )


def find_spans_by_name(exporter: InMemorySpanExporter, name: str) -> List[ReadableSpan]:
    """Find all spans with the given name from the exporter."""
    return [span for span in exporter.get_finished_spans() if span.name == name]


def find_span_by_name(exporter: InMemorySpanExporter, name: str) -> Optional[ReadableSpan]:
    """Find a single span with the given name from the exporter."""
    spans = find_spans_by_name(exporter, name)
    if not spans:
        return None
    if len(spans) > 1:
        raise AssertionError(f"Expected 1 span with name '{name}', found {len(spans)}")
    return spans[0]


def assert_span_count(exporter: InMemorySpanExporter, expected_count: int):
    """Assert the total number of spans in the exporter."""
    actual_count = len(exporter.get_finished_spans())
    assert actual_count == expected_count, f"Expected {expected_count} spans, got {actual_count}"


def assert_span_hierarchy(parent_span: ReadableSpan, child_spans: List[ReadableSpan]):
    """Assert that child spans are properly nested under parent span."""
    parent_span_id = parent_span.context.span_id

    for child_span in child_spans:
        assert child_span.parent is not None, f"Child span '{child_span.name}' has no parent"
        assert child_span.parent.span_id == parent_span_id, f"Child span '{child_span.name}' parent mismatch"


def get_span_attributes_summary(span: ReadableSpan) -> Dict[str, Any]:
    """Get a summary of span attributes for debugging."""
    attrs = dict(span.attributes) if span.attributes else {}

    # Convert memoryview objects to bytes for readable output
    summary = {}
    for key, value in attrs.items():
        if isinstance(value, memoryview):
            summary[key] = f"<memoryview: {len(value)} bytes>"
        else:
            summary[key] = value

    return summary


def print_span_debug_info(span: ReadableSpan):
    """Print detailed debug information about a span."""
    print(f"Span: {span.name}")
    print(f"Status: {span.status}")
    print(f"Attributes: {get_span_attributes_summary(span)}")
    if span.parent:
        print(f"Parent: {span.parent}")
    print("---")


def assert_url_attributes(span: ReadableSpan, expected_url: str, expected_netloc: str):
    """Assert URL-related attributes in a span."""
    span_attrs = dict(span.attributes) if span.attributes else {}

    assert "http.url" in span_attrs, "http.url not found in span attributes"
    assert span_attrs["http.url"] == expected_url, (
        f"URL mismatch: expected {expected_url}, got {span_attrs['http.url']}"
    )

    assert "netloc" in span_attrs, "netloc not found in span attributes"
    assert span_attrs["netloc"] == expected_netloc, (
        f"Netloc mismatch: expected {expected_netloc}, got {span_attrs['netloc']}"
    )


def assert_http_attributes(span: ReadableSpan, expected_status: int, expected_content_type: Optional[str] = None):
    """Assert HTTP-related attributes in a span."""
    span_attrs = dict(span.attributes) if span.attributes else {}

    assert "http.status_code" in span_attrs, "http.status_code not found in span attributes"
    assert span_attrs["http.status_code"] == expected_status, (
        f"Status code mismatch: expected {expected_status}, got {span_attrs['http.status_code']}"
    )

    if expected_content_type:
        assert "content-type" in span_attrs, "content-type not found in span attributes"
        assert span_attrs["content-type"] == expected_content_type, (
            f"Content-type mismatch: expected {expected_content_type}, got {span_attrs['content-type']}"
        )

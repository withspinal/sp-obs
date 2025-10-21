"""
Shared utility functions for gRPC instrumentation (sync and async).

These utilities handle metadata extraction and response processing
for both sync and async gRPC client instrumentors.
"""

from typing import Any

from opentelemetry.semconv._incubating.attributes.rpc_attributes import (
    RPC_GRPC_STATUS_CODE,
    RPC_METHOD,
    RPC_SERVICE,
)
from opentelemetry.trace import Status, StatusCode


def _extract_service_name(span) -> str | None:
    """Extract gRPC service name from span attributes"""
    if not span or not hasattr(span, "attributes"):
        return None

    attributes = span.attributes or {}
    return attributes.get(RPC_SERVICE)


def _extract_grpc_metadata(span, provider_name: str) -> dict[str, Any]:
    """
    Extract relevant gRPC metadata from the parent span.

    Args:
        span: The parent gRPC span created by OpenTelemetry
        provider_name: The identified provider (e.g., "gcp-documentai")

    Returns:
        Dictionary of metadata attributes to set on the child span
    """
    if not span or not hasattr(span, "attributes"):
        return {}

    attributes = span.attributes or {}
    metadata = {
        "spinal.provider": provider_name,  # Required for processor filtering
    }

    # Copy gRPC-specific metadata
    if RPC_SERVICE in attributes:
        metadata["grpc.service"] = attributes[RPC_SERVICE]

    if RPC_METHOD in attributes:
        metadata["grpc.method"] = attributes[RPC_METHOD]

    # Add any other relevant metadata from span attributes
    # (e.g., timeout, peer address, etc.)
    for key, value in attributes.items():
        if key.startswith("rpc.") or key.startswith("grpc."):
            # Only copy metadata, skip binary data attributes
            if isinstance(value, (str, int, float, bool)):
                metadata[key] = value

    return metadata


def _add_response_metadata(child_span, parent_span):
    """
    Add response metadata to the child span from the parent span.

    Also sets the child span status based on the gRPC status code:
    - Status code 0 (OK) -> StatusCode.OK
    - Status code != 0 (Error) -> StatusCode.ERROR

    Args:
        child_span: The Spinal child span to add metadata to
        parent_span: The parent OpenTelemetry gRPC span
    """
    if not parent_span or not hasattr(parent_span, "attributes"):
        return

    attributes = parent_span.attributes or {}

    # Check gRPC status code and set span status accordingly
    grpc_status_code = attributes.get(RPC_GRPC_STATUS_CODE)
    if grpc_status_code is not None:
        child_span.set_attribute("grpc.status_code", grpc_status_code)

        # gRPC status code 0 = OK, non-zero = error
        if grpc_status_code == 0:
            child_span.set_status(Status(StatusCode.OK))
        else:
            # Map gRPC status codes to meaningful error descriptions
            error_desc = f"gRPC call failed with status code {grpc_status_code}"
            child_span.set_status(Status(StatusCode.ERROR, error_desc))
            child_span.set_attribute("error", True)

    # Add any error messages from parent span events
    if hasattr(parent_span, "events") and parent_span.is_recording():
        for event in parent_span.events:
            if event.name == "exception" and event.attributes:
                # Record exception details from event attributes
                exc_type = event.attributes.get("exception.type")
                exc_message = event.attributes.get("exception.message")
                if exc_type or exc_message:
                    child_span.set_attribute("error", True)
                    if exc_type:
                        child_span.set_attribute("error.type", exc_type)
                    if exc_message:
                        child_span.set_attribute("error.message", exc_message)

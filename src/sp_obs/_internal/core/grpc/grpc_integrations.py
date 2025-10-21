"""
gRPC service pattern registry for identifying providers.

Similar to recognised_integrations.py for HTTP hosts, this module provides
pattern matching for gRPC service names to identify which provider/service
is being called.
"""

import fnmatch

# Map gRPC service name patterns to provider identifiers
GRPC_SERVICE_PATTERNS = {
    # Google Cloud Platform Services
    "google.cloud.documentai.*": "gcp-documentai",
    "google.cloud.vision.*": "gcp-vision",
    "google.cloud.aiplatform.*": "gcp-vertexai",
    # AWS Services
    "aws.textract.*": "aws-textract",
    # Add more service patterns as needed
}


def match_grpc_service(service_name: str | None) -> str | None:
    """
    Match a gRPC service name against known patterns to identify the provider.

    Args:
        service_name: The gRPC service name from RPC metadata (e.g., "google.cloud.documentai.v1.DocumentProcessor")

    Returns:
        Provider identifier string (e.g., "gcp-documentai") if matched, None otherwise

    Examples:
        >>> match_grpc_service("google.cloud.documentai.v1.DocumentProcessor")
        'gcp-documentai'
        >>> match_grpc_service("google.cloud.vision.v1.ImageAnnotator")
        'gcp-vision'
        >>> match_grpc_service("unknown.service.Name")
        None
    """
    if not service_name:
        return None

    # Sort patterns by specificity (more specific patterns first)
    # This ensures "google.cloud.documentai.*" matches before "google.cloud.*"
    sorted_patterns = sorted(GRPC_SERVICE_PATTERNS.items(), key=lambda x: (-x[0].count("."), -len(x[0])))

    for pattern, provider in sorted_patterns:
        if fnmatch.fnmatch(service_name, pattern):
            return provider

    return None

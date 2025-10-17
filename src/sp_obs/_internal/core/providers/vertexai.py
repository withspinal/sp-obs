import logging
from typing import Any

from sp_obs._internal.core.providers import BaseProvider

logger = logging.getLogger(__name__)


class VertexAIProvider(BaseProvider):
    """Provider for GCP Vertex AI API"""

    def parse_request_attributes(self, request_attributes: dict[str, Any]) -> dict[str, Any]:
        request_attributes.pop("document", None)  # For Mistral OCR content
        request_attributes.pop("messages", None)  # For Mistral chat completion
        request_attributes.pop("response_format", None)  # For Mistral chat completion
        return request_attributes

    def parse_response_attributes(self, response_attributes: dict[str, Any]) -> dict[str, Any]:
        response_attributes.pop("candidates", None)
        response_attributes.pop("candidatesTokensDetails", None)
        return response_attributes

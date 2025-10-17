from typing import Any
from sp_obs._internal.core.providers import BaseProvider


class MistralProvider(BaseProvider):
    """Provider for Mistal API"""

    def parse_request_attributes(self, request_attributes: dict[str, Any]) -> dict[str, Any]:
        request_attributes.pop("document", None)  # For OCR content
        request_attributes.pop("messages", None)  # For chat completion
        request_attributes.pop("response_format", None)  # For chat completion
        return request_attributes

    def parse_response_attributes(self, response_attributes: dict[str, Any]) -> dict[str, Any]:
        """
        We only really care about the usage and model fields.
        """
        response_attributes.pop("pages", None)  # For OCR content
        response_attributes.pop("choices", None)  # For chat completion
        return response_attributes

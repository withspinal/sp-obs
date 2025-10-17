from typing import Any
from sp_obs._internal.core.providers import BaseProvider


class MistralProvider(BaseProvider):
    """Provider for Mistal API"""

    def parse_response_attributes(self, response_attributes: dict[str, Any]) -> dict[str, Any]:
        """
        We only really care about the usage and model fields.
        """
        response_attributes.pop("pages", None)  # For OCR content
        response_attributes.pop("choices", None)  # For chat completion
        return response_attributes

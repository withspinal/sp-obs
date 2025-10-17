from typing import Any

from sp_obs._internal.core.providers import BaseProvider


class VoyageAIProvider(BaseProvider):
    """Provider for Voyage AI API"""

    def parse_response_attributes(self, response_attributes: dict[str, Any]) -> dict[str, Any]:
        response_attributes.pop("data", None)  # returned data from embeddings and reranking
        response_attributes.pop("object", None)  # object type
        return response_attributes

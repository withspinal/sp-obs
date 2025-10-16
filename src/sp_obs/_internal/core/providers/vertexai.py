import logging
from typing import Any

from sp_obs._internal.core.providers import BaseProvider

logger = logging.getLogger(__name__)


class VertexAIProvider(BaseProvider):
    """Provider for GCP Vertex AI API"""

    def parse_response_attributes(self, response_attributes: dict[str, Any]) -> dict[str, Any]:
        response_attributes.pop("candidates", None)
        response_attributes.pop("candidatesTokensDetails", None)
        return response_attributes

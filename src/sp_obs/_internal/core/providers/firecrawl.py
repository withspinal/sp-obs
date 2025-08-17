from typing import Any

from sp_obs._internal.core.providers import BaseProvider


class FirecrawlProvider(BaseProvider):
    """Provider for Firecrawl API"""

    def parse_response_attributes(self, response_attributes: dict[str, Any]) -> dict[str, Any]:
        response_attributes.pop("data", None)
        return response_attributes

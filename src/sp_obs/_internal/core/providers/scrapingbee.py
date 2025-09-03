from typing import Any


from sp_obs._internal.core.providers.base import BaseProvider


class ScrapingBeeProvider(BaseProvider):
    """Provider for ScrapingBee API"""

    def parse_response_headers(self, response_attributes: dict[str, Any]) -> dict[str, Any]:
        """
        Parses and processes the response attributes by removing unnecessary fields.
        """

        cost = response_attributes.get("spinal.http.response.header.Spb-cost")

        if cost is not None:
            return {"cost": cost}

        return {}

    def parse_response_attributes(self, response_attributes: dict[str, Any]) -> dict[str, Any]:
        """
        Parses and processes the response attributes by removing unnecessary fields.
        """
        return {}

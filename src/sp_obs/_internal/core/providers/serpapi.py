from typing import Any

from sp_obs._internal.core.providers import BaseProvider


class SerpapiProvider(BaseProvider):
    def parse_response_attributes(self, response_attributes: dict[str, Any]) -> dict[str, Any]:
        """
        Parse the response attributes for Serpapi.
        """

        return response_attributes

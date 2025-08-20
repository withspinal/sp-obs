from typing import Any

from sp_obs._internal.core.providers import BaseProvider


class SerpapiProvider(BaseProvider):
    def parse_response_attributes(self, response_attributes: dict[str, Any]) -> dict[str, Any]:
        """
        Parse the response attributes for Serpapi. We do not keep any response attributes, as pricing is independant of the response content
        """

        return {}

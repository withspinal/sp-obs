from typing import Any 


from sp_obs._internal.core.providers.base import BaseProvider 


class ScrapingBeeProvider(BaseProvider):
    """Provider for ScrapingBee API"""

    def parse_response_attributes(self, response_attributes: dict[str, Any]) -> dict[str, Any]:
        """
        Parses and processes the response attributes by removing unnecessary fields.
        """
        if response_attributes and response_attributes.get('cost'): 
            return {"cost" : response_attributes.get('cost')}
        
        return response_attributes;

   


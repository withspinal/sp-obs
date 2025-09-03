import logging
from typing import Any
from sp_obs._internal.core.providers.base import BaseProvider

logger = logging.getLogger(__name__)


class ScrapingBeeProvider(BaseProvider):
    """Provider for ScrapingBee API"""

    def parse_response_headers(self, response_attributes: dict[str, Any]) -> dict[str, Any]:
        """
        Parses and processes the response headers.
        """
        cost = response_attributes.get("spinal.http.response.header.Spb-cost")

        if cost is not None:
            return {"cost": cost}

        return {}

    def parse_response_attributes(self, response_attributes: dict[str, Any]) -> dict[str, Any]:
        """
        Parses and processes the response attributes with better error handling.
        """
        try:
            # Log the content type and content length for debugging
            content_type = response_attributes.get("content-type", "unknown")
            content_length = (
                len(response_attributes.get("spinal.response.binary_data", b""))
                if "spinal.response.binary_data" in response_attributes
                else 0
            )

            logger.debug(f"ScrapingBee response - Content-Type: {content_type}, Length: {content_length}")

            # Check for content type mismatch
            if "application/json" in content_type and content_length > 0:
                # Try to parse as JSON to validate
                try:
                    import json

                    content = response_attributes.get("spinal.response.binary_data", b"")
                    if content:
                        # Try to decode and parse as JSON
                        decoded = content.decode("utf-8", errors="ignore")
                        json.loads(decoded)  # Validate JSON
                        logger.debug("ScrapingBee response is valid JSON")
                except (json.JSONDecodeError, UnicodeDecodeError) as e:
                    logger.warning(f"ScrapingBee response claims to be JSON but isn't: {e}")
                    logger.warning(f"Content preview: {decoded[:200] if 'decoded' in locals() else 'N/A'}")

                    # Add a flag to indicate content type mismatch
                    return {"content_type_mismatch": True, "raw_content_length": content_length}

            return {}

        except Exception as e:
            logger.error(f"Error parsing ScrapingBee response attributes: {e}")
            return {"parse_error": str(e)}

import re
import typing


class DefaultScrubber:
    """Default implementation of SpinalScrubber with basic sensitive patterns"""

    SENSITIVE_PATTERNS = [
        r"password",
        r"passwd",
        r"secret",
        r"api[._-]?key",
        r"apikey",
        r"auth[._-]?token",
        r"access[._-]?token",
        r"private[._-]?key",
        r"encryption[._-]?key",
        r"bearer",
        r"credential",
        r"user[._-]?name",
        r"first[._-]?name",
        r"last[._-]?name",
        r"email",
        r"email[._-]?address",
        r"phone[._-]?number",
        r"ip[._-]?address",
    ]

    PROTECTED_PATTERNS = [
        r"\battributes\b",  # Needed to preserve the Span attributes.
        r"spinal",  # Needed to preserve attached Spinal attributes
    ]

    def __init__(self, extra_patterns: list[str] | None = None):
        """
        Initialize the scrubber with optional extra patterns

        Args:
            extra_patterns: Additional regex patterns to match sensitive keys
        """
        self.patterns = self.SENSITIVE_PATTERNS.copy()

        if extra_patterns:
            self._compiled_protected_patterns = re.compile("|".join(self.PROTECTED_PATTERNS), re.IGNORECASE)
            for attrib in extra_patterns:
                if bool(self._compiled_protected_patterns.search(attrib)):
                    raise ValueError(f"Attribute name '{attrib}' is protected and cannot be scrubbed")

            self.patterns.extend(extra_patterns)

        # Compile all patterns into a single regex, and ensure case is ignored
        self._compiled_pattern = re.compile("|".join(f"({pattern})" for pattern in self.patterns), re.IGNORECASE)

    def scrub_attributes(self, attributes: dict[str, typing.Any]) -> dict[str, typing.Any]:
        """
        Scrub sensitive data from span attributes

        Args:
            attributes: Original span attributes

        Returns:
            Scrubbed attributes with sensitive values redacted
        """
        if not attributes:
            return attributes

        scrubbed = {}
        for key, value in attributes.items():
            if self._is_sensitive_key(key):
                scrubbed[key] = f"[Scrubbed due to {self._get_matched_pattern(key)}]"
            elif isinstance(value, dict):
                scrubbed[key] = self.scrub_attributes(value)
            elif isinstance(value, list):
                scrubbed[key] = [self.scrub_attributes(item) if isinstance(item, dict) else item for item in value]
            else:
                scrubbed[key] = value

        return scrubbed

    def _is_sensitive_key(self, key: str) -> bool:
        return bool(self._compiled_pattern.search(key))

    def _get_matched_pattern(self, key: str) -> str:
        """Get the attribute name that matched the sensitive key"""
        match = self._compiled_pattern.search(key)
        if match:
            return match.string
        return "sensitive pattern"


class NoOpScrubber:
    """A no-op scrubber that passes through all attributes unchanged"""

    def scrub_attributes(self, attributes: dict[str, typing.Any]) -> dict[str, typing.Any]:
        return attributes

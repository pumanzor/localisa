"""Text anonymizer — strips PII before sending to cloud APIs."""

import re
import logging
from typing import Dict, Tuple

log = logging.getLogger("localisa.router.anonymizer")


class TextAnonymizer:
    """Masks personal data before sending to cloud LLMs, unmasks on return."""

    def __init__(self):
        self.mappings: Dict[str, str] = {}
        self.counter = 0

    def _next_token(self, prefix: str) -> str:
        self.counter += 1
        return f"[{prefix}_{self.counter}]"

    def anonymize(self, text: str) -> str:
        """Replace PII with tokens. Returns anonymized text."""
        self.mappings = {}
        self.counter = 0

        patterns = [
            # Email
            (r'\b[\w.-]+@[\w.-]+\.\w+\b', 'EMAIL'),
            # Phone (international formats)
            (r'\b\+?\d{1,3}[-.\s]?\(?\d{1,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}\b', 'PHONE'),
            # IP addresses
            (r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', 'IP'),
            # Chilean RUT
            (r'\b\d{1,2}\.\d{3}\.\d{3}[-]?[0-9kK]\b', 'ID'),
            # Credit card numbers
            (r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b', 'CARD'),
            # URLs
            (r'https?://\S+', 'URL'),
            # MAC addresses
            (r'\b([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}\b', 'MAC'),
        ]

        result = text
        for pattern, prefix in patterns:
            for match in re.finditer(pattern, result):
                original = match.group()
                if original not in self.mappings.values():
                    token = self._next_token(prefix)
                    self.mappings[token] = original
                    result = result.replace(original, token, 1)

        if self.mappings:
            log.info(f"Anonymized {len(self.mappings)} items")

        return result

    def deanonymize(self, text: str) -> str:
        """Restore original values from tokens."""
        result = text
        for token, original in self.mappings.items():
            result = result.replace(token, original)
        return result

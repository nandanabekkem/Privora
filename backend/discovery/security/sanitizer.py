import re
from typing import Any, Dict, List


class DataSanitizer:
    """
    Removes or masks sensitive personal information before discovered
    account data is passed to downstream AI components.
    """

    EMAIL_PATTERN = re.compile(
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
    )

    PHONE_PATTERN = re.compile(
        r"(?<!\d)(?:\+?\d[\d\s().-]{7,}\d)(?!\d)"
    )

    DOB_PATTERN = re.compile(
        r"\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2})\b"
    )

    def sanitize_text(self, text: str) -> str:
        """
        Replace common PII patterns with non-identifying placeholders.
        """
        sanitized = self.EMAIL_PATTERN.sub("[EMAIL]", text)
        sanitized = self.PHONE_PATTERN.sub("[PHONE]", sanitized)
        sanitized = self.DOB_PATTERN.sub("[DATE]", sanitized)

        return sanitized

    def sanitize_record(
        self,
        record: Dict[str, Any],
        allowed_fields: List[str] | None = None,
    ) -> Dict[str, Any]:
        """
        Create a sanitized copy of a discovery record.

        Only explicitly allowed fields are retained when allowed_fields
        is provided.
        """
        if allowed_fields is None:
            allowed_fields = [
                "service_name",
                "domain",
                "relationship",
                "source",
                "first_seen",
                "last_activity",
                "data_categories",
                "account_status",
            ]

        sanitized: Dict[str, Any] = {}

        for field in allowed_fields:
            if field not in record:
                continue

            value = record[field]

            if isinstance(value, str):
                sanitized[field] = self.sanitize_text(value)
            else:
                sanitized[field] = value

        return sanitized
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from ...core.constants import (
    ACCOUNT_DISCOVERY_KEYWORDS,
    DATA_CATEGORY_KEYWORDS,
    MAX_EMAIL_BODY_LENGTH,
    RELATIONSHIP_KEYWORDS,
)


class EmailParser:
    """
    Extracts account discovery signals from raw email records.

    The parser performs deterministic first-pass extraction.
    More advanced semantic classification belongs to the AI layer.
    """

    def parse(self, email: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Parse a single email into a normalized discovery record.

        Returns None when the email does not contain useful
        account discovery signals.
        """
        subject = str(email.get("subject", "")).strip()
        sender = str(email.get("sender", "")).strip()
        body = str(email.get("body", "")).strip()

        body = body[:MAX_EMAIL_BODY_LENGTH]

        timestamp = self._parse_timestamp(email.get("timestamp"))

        combined_text = f"{subject} {sender} {body}".lower()

        if not self._is_account_related(combined_text):
            return None

        domain = self._extract_domain(sender, body)

        if not domain:
            return None

        return {
            "subject": subject,
            "sender": sender,
            "domain": domain,
            "timestamp": timestamp,
            "body": body,
            "relationship": self._detect_relationship(combined_text),
            "data_categories": self._detect_data_categories(
                combined_text
            ),
        }

    def parse_many(
        self,
        emails: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Parse multiple emails and discard irrelevant records.
        """
        records = []

        for email in emails:
            parsed = self.parse(email)

            if parsed is not None:
                records.append(parsed)

        return records

    def _is_account_related(self, text: str) -> bool:
        """
        Determine whether an email contains account-related signals.
        """
        return any(
            keyword in text
            for keyword in ACCOUNT_DISCOVERY_KEYWORDS
        )

    def _detect_relationship(self, text: str) -> Optional[str]:
        """
        Detect the most likely purpose of an account using
        deterministic keyword matching.
        """
        for relationship, keywords in RELATIONSHIP_KEYWORDS.items():
            if any(keyword in text for keyword in keywords):
                return relationship

        return None

    def _detect_data_categories(
        self,
        text: str,
    ) -> List[str]:
        """
        Detect broad categories of personal data mentioned
        in the email.
        """
        categories = []

        for category, keywords in DATA_CATEGORY_KEYWORDS.items():
            if any(keyword in text for keyword in keywords):
                categories.append(category)

        return categories

    def _extract_domain(
        self,
        sender: str,
        body: str,
    ) -> Optional[str]:
        """
        Extract a domain from the sender address first, then
        from URLs present in the email body.
        """
        sender_match = re.search(
            r"@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})",
            sender,
        )

        if sender_match:
            return sender_match.group(1).lower()

        url_match = re.search(
            r"https?://(?:www\.)?([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})",
            body,
        )

        if url_match:
            return url_match.group(1).lower()

        return None

    def _parse_timestamp(
        self,
        value: Any,
    ) -> Optional[datetime]:
        """
        Convert supported timestamp formats into datetime objects.
        """
        if isinstance(value, datetime):
            return value

        if not value:
            return None

        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value)
            except ValueError:
                return None

        return None
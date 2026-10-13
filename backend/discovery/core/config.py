from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class DiscoveryConfig:
    max_emails: int = int(
        os.getenv("PRIVORA_MAX_EMAILS", "100")
    )

    max_email_body_length: int = int(
        os.getenv(
            "PRIVORA_MAX_EMAIL_BODY_LENGTH",
            "10000",
        )
    )

    enable_email_discovery: bool = (
        os.getenv(
            "PRIVORA_ENABLE_EMAIL_DISCOVERY",
            "true",
        ).lower()
        == "true"
    )

    enable_identity_vault: bool = (
        os.getenv(
            "PRIVORA_ENABLE_IDENTITY_VAULT",
            "true",
        ).lower()
        == "true"
    )

    gmail_credentials_path: str = os.getenv(
        "PRIVORA_GMAIL_CREDENTIALS_PATH",
        "credentials.json",
    )

    gmail_token_path: str = os.getenv(
        "PRIVORA_GMAIL_TOKEN_PATH",
        "token.json",
    )


config = DiscoveryConfig()
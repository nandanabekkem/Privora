from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import dotenv_values


BACKEND_DIR = Path(__file__).resolve().parents[2]
BACKEND_ENV = BACKEND_DIR / ".env"
_FILE_SETTINGS = dotenv_values(BACKEND_ENV)


def _setting(name: str, default: str) -> str:
    """Read backend .env defaults while letting deployment env vars win."""
    process_value = os.getenv(name)
    if process_value is not None:
        return process_value
    file_value = _FILE_SETTINGS.get(name)
    return str(file_value if file_value is not None else default)


@dataclass(frozen=True)
class DiscoveryConfig:
    max_emails: int = int(
        _setting("PRIVORA_MAX_EMAILS", "100")
    )

    max_email_body_length: int = int(
        _setting(
            "PRIVORA_MAX_EMAIL_BODY_LENGTH",
            "10000",
        )
    )

    enable_email_discovery: bool = (
        _setting(
            "PRIVORA_ENABLE_EMAIL_DISCOVERY",
            "true",
        ).lower()
        == "true"
    )

    enable_identity_vault: bool = (
        _setting(
            "PRIVORA_ENABLE_IDENTITY_VAULT",
            "true",
        ).lower()
        == "true"
    )

    gmail_oauth_client_id: str = _setting("PRIVORA_GMAIL_CLIENT_ID", "")
    gmail_oauth_client_secret: str = _setting("PRIVORA_GMAIL_CLIENT_SECRET", "")
    gmail_oauth_redirect_uri: str = _setting("PRIVORA_GMAIL_REDIRECT_URI", "")
    gmail_token_encryption_key: str = _setting("PRIVORA_GMAIL_TOKEN_ENCRYPTION_KEY", "")
    frontend_url: str = _setting("PRIVORA_FRONTEND_URL", "http://localhost:8443")


config = DiscoveryConfig()

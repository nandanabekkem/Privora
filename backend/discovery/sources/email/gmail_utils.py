from __future__ import annotations

import base64


def decode_gmail_body(data: str) -> str:
    """Decode a Gmail base64url-encoded message body."""
    padding = "=" * (-len(data) % 4)

    decoded = base64.urlsafe_b64decode(
        data + padding
    )

    return decoded.decode(
        "utf-8",
        errors="replace",
    )
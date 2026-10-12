
from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from ..base import DiscoverySource
from .gmail_utils import decode_gmail_body


class GmailProvider(DiscoverySource):
    """Read-only Gmail discovery provider."""

    SCOPES = [
        "https://www.googleapis.com/auth/gmail.readonly",
    ]

    def __init__(
        self,
        credentials_path: str = "credentials.json",
        token_path: str = "token.json",
        max_results: int = 20,
    ) -> None:
        self.credentials_path = Path(credentials_path)
        self.token_path = Path(token_path)
        self.max_results = max(1, min(max_results, 100))

    def fetch_records(self) -> list[dict[str, Any]]:
        return self._fetch_records()

    def fetch_discovery_records(
        self,
        query: str = "",
    ) -> list[dict[str, Any]]:
        """Fetch a bounded set of messages matching a Gmail query."""
        return self._fetch_records(query=query or None)

    def _fetch_records(
        self,
        query: str | None = None,
    ) -> list[dict[str, Any]]:
        service = self._authenticate()

        arguments: dict[str, Any] = {
            "userId": "me",
            "maxResults": self.max_results,
        }
        if query:
            arguments["q"] = query

        response = self._execute_with_retry(
            lambda: (
                service.users()
                .messages()
                .list(**arguments)
                .execute()
            )
        )

        records: list[dict[str, Any]] = []

        for message in response.get("messages", []):
            message_id = message.get("id")
            if not message_id:
                continue

            full_message = self._execute_with_retry(
                lambda message_id=message_id: (
                    service.users()
                    .messages()
                    .get(
                        userId="me",
                        id=message_id,
                        format="full",
                    )
                    .execute()
                )
            )
            records.append(self._convert_message(full_message))

        return records

    @staticmethod
    def _execute_with_retry(request: Any) -> Any:
        """Retry transient rate-limit errors with bounded backoff."""
        from googleapiclient.errors import HttpError

        for attempt in range(4):
            try:
                return request()
            except HttpError as exc:
                status = getattr(exc.resp, "status", None)
                content = str(exc.content).lower()

                retryable = (
                    status == 429
                    or "ratelimitexceeded" in content
                    or "userratelimitexceeded" in content
                )

                if not retryable or attempt == 3:
                    raise

                time.sleep(2**attempt)

        raise RuntimeError("Gmail request failed after retries.")

    def _authenticate(self) -> Any:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build

        credentials = None

        if self.token_path.exists():
            credentials = Credentials.from_authorized_user_file(
                str(self.token_path),
                self.SCOPES,
            )

        if credentials is None or not credentials.valid:
            if (
                credentials
                and credentials.expired
                and credentials.refresh_token
            ):
                credentials.refresh(Request())
            else:
                if not self.credentials_path.exists():
                    raise FileNotFoundError(
                        f"Gmail credentials not found: "
                        f"{self.credentials_path}"
                    )

                flow = InstalledAppFlow.from_client_secrets_file(
                    str(self.credentials_path),
                    self.SCOPES,
                )
                credentials = flow.run_local_server(port=0)

            self.token_path.write_text(
                credentials.to_json(),
                encoding="utf-8",
            )

        return build(
            "gmail",
            "v1",
            credentials=credentials,
        )

    @staticmethod
    def _convert_message(
        message: dict[str, Any],
    ) -> dict[str, Any]:
        payload = message.get("payload", {})

        headers = {
            header["name"].lower(): header["value"]
            for header in payload.get("headers", [])
            if "name" in header and "value" in header
        }

        timestamp = headers.get("date", "")
        internal_date = message.get("internalDate")

        if internal_date:
            try:
                from datetime import datetime, timezone

                timestamp = datetime.fromtimestamp(
                    int(internal_date) / 1000,
                    tz=timezone.utc,
                ).isoformat()
            except (ValueError, TypeError, OSError):
                pass

        return {
            "id": message.get("id"),
            "thread_id": message.get("threadId"),
            "sender": headers.get("from", ""),
            "subject": headers.get("subject", ""),
            "timestamp": timestamp,
            "body": GmailProvider._extract_body(payload),
        }

    @staticmethod
    def _extract_body(payload: dict[str, Any]) -> str:
        """Recursively extract plain-text content from MIME parts."""
        mime_type = payload.get("mimeType", "")
        body_data = payload.get("body", {}).get("data")

        if mime_type == "text/plain" and body_data:
            return decode_gmail_body(body_data)

        for part in payload.get("parts", []):
            text = GmailProvider._extract_body(part)
            if text:
                return text

        if body_data and not payload.get("parts"):
            return decode_gmail_body(body_data)

        return ""

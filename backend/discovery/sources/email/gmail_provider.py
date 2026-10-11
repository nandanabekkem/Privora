from __future__ import annotations

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
        max_results: int = 100,
    ) -> None:
        self.credentials_path = Path(credentials_path)
        self.token_path = Path(token_path)
        self.max_results = max_results

    def fetch_records(self) -> list[dict[str, Any]]:
        service = self._authenticate()

        response = (
            service.users()
            .messages()
            .list(
                userId="me",
                maxResults=self.max_results,
            )
            .execute()
        )

        records: list[dict[str, Any]] = []

        for message in response.get("messages", []):
            full_message = (
                service.users()
                .messages()
                .get(
                    userId="me",
                    id=message["id"],
                    format="full",
                )
                .execute()
            )

            records.append(
                self._convert_message(full_message)
            )

        return records

    def fetch_discovery_records(
        self,
        query: str = "",
    ) -> list[dict[str, Any]]:
        """
        Fetch Gmail messages relevant to account discovery.
        """
        service = self._authenticate()

        response = (
            service.users()
            .messages()
            .list(
                userId="me",
                q=query,
                maxResults=self.max_results,
            )
            .execute()
        )

        records: list[dict[str, Any]] = []

        for message in response.get("messages", []):
            full_message = (
                service.users()
                .messages()
                .get(
                    userId="me",
                    id=message["id"],
                    format="full",
                )
                .execute()
            )

            records.append(
                self._convert_message(full_message)
            )

        return records

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

                credentials = flow.run_local_server(
                    port=0
                )

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
        }

        return {
            "id": message.get("id"),
            "thread_id": message.get("threadId"),
            "sender": headers.get("from", ""),
            "subject": headers.get("subject", ""),
            "timestamp": headers.get("date", ""),
            "body": GmailProvider._extract_body(payload),
        }

    @staticmethod
    def _extract_body(
        payload: dict[str, Any],
    ) -> str:
        body = payload.get("body", {})
        data = body.get("data")

        if data:
            return decode_gmail_body(data)

        for part in payload.get("parts", []):
            if part.get("mimeType") == "text/plain":
                part_body = part.get("body", {})
                data = part_body.get("data")

                if data:
                    return decode_gmail_body(data)

        return ""
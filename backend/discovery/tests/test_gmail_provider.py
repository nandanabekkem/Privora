from pathlib import Path

import pytest

from ..sources.email.gmail_provider import GmailProvider


def test_gmail_provider_configuration() -> None:
    provider = GmailProvider(
        credentials_path="credentials.json",
        token_path="token.json",
        max_results=25,
    )

    assert provider.credentials_path == Path("credentials.json")
    assert provider.token_path == Path("token.json")
    assert provider.max_results == 25


def test_gmail_provider_requires_credentials() -> None:
    provider = GmailProvider(
        credentials_path="missing_credentials.json",
        token_path="missing_token.json",
    )

    with pytest.raises(FileNotFoundError):
        provider.fetch_records()


def test_convert_gmail_message() -> None:
    message = {
        "id": "message-123",
        "threadId": "thread-456",
        "payload": {
            "headers": [
                {
                    "name": "From",
                    "value": "noreply@example.com",
                },
                {
                    "name": "Subject",
                    "value": "Welcome to Example",
                },
                {
                    "name": "Date",
                    "value": "Thu, 01 Oct 2026 10:30:00 +0530",
                },
            ],
            "body": {
                "data": "VGVzdCBib2R5",
            },
        },
    }

    record = GmailProvider._convert_message(message)

    assert record["id"] == "message-123"
    assert record["thread_id"] == "thread-456"
    assert record["sender"] == "noreply@example.com"
    assert record["subject"] == "Welcome to Example"
    assert record["body"] == "Test body"


def test_empty_gmail_body() -> None:
    payload = {
        "headers": [],
        "body": {},
    }

    assert GmailProvider._extract_body(payload) == ""


def test_gmail_discovery_query(monkeypatch) -> None:
    provider = GmailProvider(
        credentials_path="credentials.json",
        token_path="token.json",
    )

    class FakeMessages:
        def list(self, **kwargs):
            assert kwargs["userId"] == "me"
            assert "welcome" in kwargs["q"]
            assert kwargs["maxResults"] == 100

            class FakeRequest:
                def execute(self):
                    return {"messages": []}

            return FakeRequest()

    class FakeUsers:
        def messages(self):
            return FakeMessages()

    class FakeService:
        def users(self):
            return FakeUsers()

    monkeypatch.setattr(
        provider,
        "_authenticate",
        lambda: FakeService(),
    )

    records = provider.fetch_discovery_records(
        query="welcome OR registration"
    )

    assert records == []
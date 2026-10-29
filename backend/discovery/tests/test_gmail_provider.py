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


def test_gmail_provider_requires_user_authorization() -> None:
    provider = GmailProvider(
        credentials_path="missing_credentials.json",
        token_path="missing_token.json",
    )

    with pytest.raises(RuntimeError, match="Connect Gmail"):
        provider.fetch_records()


def test_gmail_uses_metadata_scope_and_never_fetches_message_bodies() -> None:
    assert GmailProvider.SCOPES == [
        "https://www.googleapis.com/auth/gmail.metadata",
        "https://www.googleapis.com/auth/gmail.send",
    ]

    provider = GmailProvider()

    class FakeRequest:
        def execute(self):
            return {
                "id": "message-1",
                "payload": {
                    "mimeType": "text/plain",
                    "headers": [
                        {"name": "From", "value": "Welcome <hello@example.com>"},
                        {"name": "Subject", "value": "Welcome to Example"},
                    ],
                    "body": {"data": "c2VjcmV0IGVtYWlsIGJvZHk="},
                },
            }

    class FakeMessages:
        def list(self, **kwargs):
            assert kwargs == {"userId": "me", "maxResults": 20}
            return type("ListRequest", (), {"execute": lambda self: {"messages": [{"id": "message-1"}]}})()

        def get(self, **kwargs):
            assert kwargs == {
                "userId": "me",
                "id": "message-1",
                "format": "metadata",
                "metadataHeaders": ["From", "Subject", "Date"],
            }
            return FakeRequest()

    class FakeUsers:
        def messages(self):
            return FakeMessages()

    class FakeService:
        def users(self):
            return FakeUsers()

    provider._authenticate = lambda: FakeService()
    records = provider.fetch_records()

    assert records[0]["subject"] == "Welcome to Example"
    assert records[0]["body"] == ""


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
    assert record["body"] == ""


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
            assert kwargs["maxResults"] == 20
            assert "q" not in kwargs

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


def test_gmail_send_encodes_a_single_message_and_returns_provider_ids():
    import base64
    from email import message_from_bytes
    from email.policy import default

    provider = GmailProvider(credentials=object())
    captured = {}

    class SendRequest:
        def execute(self):
            return {"id": "message-id", "threadId": "thread-id"}

    class Messages:
        def send(self, **kwargs):
            captured.update(kwargs)
            return SendRequest()

    class Users:
        def messages(self):
            return Messages()

    class Service:
        def users(self):
            return Users()

    provider._authenticate = lambda: Service()
    result = provider.send_message("privacy@example.org", "Delete my account", "Please delete my account.")
    encoded = captured["body"]["raw"]
    message = message_from_bytes(base64.urlsafe_b64decode(encoded), policy=default)

    assert captured["userId"] == "me"
    assert message["To"] == "privacy@example.org"
    assert message["Subject"] == "Delete my account"
    assert message.get_content().strip() == "Please delete my account."
    assert result == {"message_id": "message-id", "thread_id": "thread-id"}


def test_gmail_reply_check_reads_only_thread_headers():
    provider = GmailProvider(credentials=object())

    class Request:
        def execute(self):
            return {"messages": [{"id": "reply-1", "payload": {"headers": [{"name": "From", "value": "support@example.org"}]}}]}

    class Threads:
        def get(self, **kwargs):
            assert kwargs == {
                "userId": "me",
                "id": "thread-1",
                "format": "metadata",
                "metadataHeaders": ["From", "Date"],
            }
            return Request()

    class Users:
        def threads(self):
            return Threads()

    class Service:
        def users(self):
            return Users()

    provider._authenticate = lambda: Service()
    result = provider.fetch_thread_metadata("thread-1")
    assert result[0]["id"] == "reply-1"

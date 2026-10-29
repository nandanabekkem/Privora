from cryptography.fernet import Fernet
from google.oauth2.credentials import Credentials

from ..security import gmail_oauth
from ..security.gmail_oauth import _load_credentials, _save_credentials
from ..sources.email.gmail_provider import GmailProvider


def test_backend_dotenv_values_are_used_but_process_environment_wins(monkeypatch):
    from ..core import config as config_module

    monkeypatch.setattr(
        config_module,
        "_FILE_SETTINGS",
        {"PRIVORA_GMAIL_CLIENT_ID": "client-from-file"},
    )
    monkeypatch.delenv("PRIVORA_GMAIL_CLIENT_ID", raising=False)
    assert config_module._setting("PRIVORA_GMAIL_CLIENT_ID", "") == "client-from-file"

    monkeypatch.setenv("PRIVORA_GMAIL_CLIENT_ID", "client-from-process")
    assert config_module._setting("PRIVORA_GMAIL_CLIENT_ID", "") == "client-from-process"


def test_gmail_credentials_are_encrypted_and_isolated_by_firebase_uid(
    monkeypatch,
):
    records = {}

    class Snapshot:
        def __init__(self, value):
            self.exists = value is not None
            self.value = value

        def to_dict(self):
            return self.value

    class Document:
        def __init__(self, collection_name, document_id):
            self.collection_name = collection_name
            self.document_id = document_id

        def set(self, value):
            records[(self.collection_name, self.document_id)] = value

        def get(self):
            return Snapshot(records.get((self.collection_name, self.document_id)))

    class Collection:
        def __init__(self, name):
            self.name = name

        def document(self, document_id):
            return Document(self.name, document_id)

    monkeypatch.setattr(gmail_oauth, "collection", Collection)
    monkeypatch.setattr(
        gmail_oauth,
        "config",
        type(
            "TestConfig",
            (),
            {"gmail_token_encryption_key": Fernet.generate_key().decode("ascii")},
        )(),
    )
    credentials = Credentials(
        token="access-token-secret",
        refresh_token="refresh-token-secret",
        token_uri="https://oauth2.googleapis.com/token",
        client_id="test-client",
        client_secret="client-secret",
        scopes=GmailProvider.SCOPES,
    )

    _save_credentials("firebase-user-a", credentials)

    encrypted_record = records[("gmail_tokens", "firebase-user-a")]
    assert "access-token-secret" not in encrypted_record["encrypted_credentials"]
    assert "refresh-token-secret" not in encrypted_record["encrypted_credentials"]
    assert _load_credentials("firebase-user-a").refresh_token == "refresh-token-secret"
    assert _load_credentials("firebase-user-b", required=False) is None

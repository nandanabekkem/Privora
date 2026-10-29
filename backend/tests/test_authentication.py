from urllib.parse import parse_qs, urlparse

import pytest
from fastapi.testclient import TestClient
from cryptography.fernet import Fernet
from google.oauth2.credentials import Credentials

from app.core import authentication
from app.core.authentication import get_current_user
from app.main import app


@pytest.fixture
def auth_client(mock_firestore):
    app.dependency_overrides.pop(get_current_user, None)
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.pop(get_current_user, None)


def test_user_endpoint_rejects_missing_token(auth_client):
    response = auth_client.get("/data-map/1")

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


@pytest.mark.parametrize(
    "method,path",
    [
        ("post", "/analysis/1/accounts/1"),
        ("get", "/assistant/1/accounts/1/messages"),
        ("post", "/assistant/1/accounts/1/messages"),
        ("post", "/privacy-actions/1/accounts/1/deletion-draft"),
    ],
)
def test_new_account_features_require_authentication(auth_client, method, path):
    request = getattr(auth_client, method)
    response = (
        request(path, json={"message": "question"})
        if method == "post" and path.endswith("/messages")
        else request(path)
    )
    assert response.status_code == 401


def test_user_endpoint_rejects_invalid_token(auth_client, monkeypatch):
    monkeypatch.setattr(authentication, "get_firebase_app", lambda: object())

    def reject_token(*args, **kwargs):
        raise ValueError("invalid token")

    monkeypatch.setattr(authentication.auth, "verify_id_token", reject_token)
    response = auth_client.get(
        "/data-map/1",
        headers={"Authorization": "Bearer invalid-token"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or expired Firebase ID token"


def test_user_cannot_access_another_users_records(auth_client, monkeypatch):
    from app.core import firestore_store

    database = firestore_store.get_firestore_client()
    database.collection("users").document("2").set({
        "name": "Other User",
        "email": "other@example.com",
        "firebase_uid": "other-user-uid",
    })
    monkeypatch.setattr(authentication, "get_firebase_app", lambda: object())
    monkeypatch.setattr(
        authentication.auth,
        "verify_id_token",
        lambda *args, **kwargs: {
            "uid": "test-user-uid",
            "email": "test@example.com",
        },
    )

    response = auth_client.get(
        "/data-map/2",
        headers={"Authorization": "Bearer valid-test-token"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "User access denied"


@pytest.mark.parametrize(
    "method,path,payload",
    [
        ("get", "/data-map/2", None),
        ("get", "/dormant/2", None),
        ("get", "/policies/2", None),
        ("post", "/policies/2", {"policy_type": "KEEP", "policy_text": "Keep"}),
        ("get", "/rules/2", None),
        ("get", "/privacy-actions/2", None),
        (
            "post",
            "/privacy-actions/2",
            {"account_id": 1, "action_type": "REVIEW", "description": "Review"},
        ),
        ("post", "/privacy-actions/2/action-id/review", {"decision": "APPROVE"}),
        ("get", "/audit-logs/2", None),
        ("get", "/assistant/2/accounts/1/messages", None),
        ("post", "/analysis/2/accounts/1", {}),
        ("post", "/privacy-actions/2/accounts/1/deletion-draft", {}),
    ],
)
def test_cross_user_access_is_denied_across_user_routes(
    auth_client,
    monkeypatch,
    method,
    path,
    payload,
):
    from app.core import firestore_store

    firestore_store.get_firestore_client().collection("users").document("2").set({
        "firebase_uid": "other-user-uid",
    })
    monkeypatch.setattr(authentication, "get_firebase_app", lambda: object())
    monkeypatch.setattr(
        authentication.auth,
        "verify_id_token",
        lambda *args, **kwargs: {"uid": "test-user-uid"},
    )

    request = getattr(auth_client, method)
    response = (
        request(path, json=payload, headers={"Authorization": "Bearer valid-test-token"})
        if payload
        else request(path, headers={"Authorization": "Bearer valid-test-token"})
    )

    assert response.status_code == 403


def test_auth_me_provisions_a_uid_keyed_user(auth_client, monkeypatch):
    from app.core import firestore_store

    monkeypatch.setattr(authentication, "get_firebase_app", lambda: object())
    monkeypatch.setattr(
        authentication.auth,
        "verify_id_token",
        lambda *args, **kwargs: {
            "uid": "brand-new-uid",
            "email": "new@example.com",
            "name": "New User",
        },
    )

    response = auth_client.get(
        "/auth/me",
        headers={"Authorization": "Bearer valid-test-token"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "id": "brand-new-uid",
        "uid": "brand-new-uid",
        "name": "New User",
        "email": "new@example.com",
    }
    assert firestore_store.get_document("users", "brand-new-uid")["firebase_uid"] == "brand-new-uid"


def test_gmail_oauth_uses_scoped_pkce_state_and_encrypted_per_user_tokens(
    mock_firestore,
    monkeypatch,
):
    from app.core.firestore_store import collection
    from discovery.security import gmail_oauth

    monkeypatch.setattr(gmail_oauth, "get_firestore_client", lambda: mock_firestore)

    encryption_key = Fernet.generate_key().decode("ascii")
    monkeypatch.setattr(
        gmail_oauth,
        "config",
        type(
            "TestConfig",
            (),
            {
                "gmail_oauth_client_id": "client-id",
                "gmail_oauth_client_secret": "client-secret",
                "gmail_oauth_redirect_uri": "https://api.example.test/discovery/gmail/callback",
                "gmail_token_encryption_key": encryption_key,
                "frontend_url": "https://app.example.test",
            },
        )(),
    )

    authorization_url = gmail_oauth.begin_gmail_authorization("test-user-uid")
    parameters = parse_qs(urlparse(authorization_url).query)
    assert parameters["scope"] == [
        "https://www.googleapis.com/auth/gmail.metadata https://www.googleapis.com/auth/gmail.send"
    ]
    assert parameters["client_id"] == ["client-id"]
    assert parameters["redirect_uri"] == [
        "https://api.example.test/discovery/gmail/callback"
    ]
    assert parameters["response_type"] == ["code"]
    assert parameters["access_type"] == ["offline"]
    assert parameters["code_challenge_method"] == ["S256"]
    state = parameters["state"][0]
    state_record = collection("gmail_oauth_states").document(state).get().to_dict()
    assert state_record["uid"] == "test-user-uid"
    assert state_record["code_verifier"]
    import base64
    import hashlib

    expected_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(state_record["code_verifier"].encode("ascii")).digest()
    ).rstrip(b"=").decode("ascii")
    assert parameters["code_challenge"] == [expected_challenge]

    credentials = Credentials(
        token="short-lived-access-secret",
        refresh_token="long-lived-refresh-secret",
        token_uri="https://oauth2.googleapis.com/token",
        client_id="client-id",
        client_secret="client-secret",
        scopes=["https://www.googleapis.com/auth/gmail.metadata"],
    )

    class FakeFlow:
        @classmethod
        def from_client_config(cls, client_config, **kwargs):
            assert kwargs["state"] == state
            assert kwargs["code_verifier"] == state_record["code_verifier"]
            return cls()

        def fetch_token(self, code):
            assert code == "authorization-code"

        @property
        def credentials(self):
            return credentials

    monkeypatch.setattr(gmail_oauth, "Flow", FakeFlow)
    uid = gmail_oauth.complete_gmail_authorization("authorization-code", state)

    assert uid == "test-user-uid"
    token_record = mock_firestore.data["gmail_tokens"]["test-user-uid"]
    assert "short-lived-access-secret" not in token_record["encrypted_credentials"]
    assert "long-lived-refresh-secret" not in token_record["encrypted_credentials"]
    assert not collection("gmail_oauth_states").document(state).get().exists
    stored_credentials = gmail_oauth._load_credentials("test-user-uid")
    assert stored_credentials.refresh_token == "long-lived-refresh-secret"

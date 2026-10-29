from __future__ import annotations

import json
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from cryptography.fernet import Fernet, InvalidToken
from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow

if __package__.startswith("backend."):
    from ...app.core.firestore_store import collection, get_firestore_client
else:
    from app.core.firestore_store import collection, get_firestore_client
from ..core.config import config
from ..sources.email.gmail_provider import GmailAuthorizationError, GmailProvider


STATE_TTL = timedelta(minutes=10)
AUTH_URI = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URI = "https://oauth2.googleapis.com/token"


class GmailOAuthConfigurationError(RuntimeError):
    pass


def _client_config() -> dict[str, dict[str, str]]:
    if not (
        config.gmail_oauth_client_id
        and config.gmail_oauth_client_secret
        and config.gmail_oauth_redirect_uri
    ):
        raise GmailOAuthConfigurationError(
            "Gmail OAuth client ID, client secret, and redirect URI are required."
        )
    return {
        "web": {
            "client_id": config.gmail_oauth_client_id,
            "client_secret": config.gmail_oauth_client_secret,
            "auth_uri": AUTH_URI,
            "token_uri": TOKEN_URI,
            "redirect_uris": [config.gmail_oauth_redirect_uri],
        }
    }


def _cipher() -> Fernet:
    if not config.gmail_token_encryption_key:
        raise GmailOAuthConfigurationError(
            "PRIVORA_GMAIL_TOKEN_ENCRYPTION_KEY is required to store Gmail authorization securely."
        )
    try:
        return Fernet(config.gmail_token_encryption_key.encode("ascii"))
    except (ValueError, UnicodeEncodeError) as exc:
        raise GmailOAuthConfigurationError(
            "PRIVORA_GMAIL_TOKEN_ENCRYPTION_KEY is invalid."
        ) from exc


def begin_gmail_authorization(uid: str) -> str:
    client_config = _client_config()
    _cipher()  # Fail before sending a user through consent if storage isn't ready.
    state = secrets.token_urlsafe(32)
    verifier = secrets.token_urlsafe(64)
    flow = Flow.from_client_config(
        client_config,
        scopes=GmailProvider.SCOPES,
        state=state,
        code_verifier=verifier,
        autogenerate_code_verifier=False,
    )
    flow.redirect_uri = config.gmail_oauth_redirect_uri
    authorization_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
        code_challenge_method="S256",
    )
    collection("gmail_oauth_states").document(state).set(
        {
            "uid": uid,
            "code_verifier": verifier,
            "created_at": datetime.now(timezone.utc),
        }
    )
    return authorization_url


def _consume_state(state: str) -> dict[str, Any] | None:
    db = get_firestore_client()
    reference = collection("gmail_oauth_states").document(state)

    @__import__("google.cloud.firestore_v1", fromlist=["transactional"]).transactional
    def consume(transaction):
        snapshot = reference.get(transaction=transaction)
        if not snapshot.exists:
            return None
        value = snapshot.to_dict() or {}
        transaction.delete(reference)
        return value

    return consume(db.transaction())


def _save_credentials(uid: str, credentials: Credentials) -> None:
    cipher = _cipher()
    serialized = credentials.to_json().encode("utf-8")
    encrypted = cipher.encrypt(serialized).decode("ascii")
    collection("gmail_tokens").document(uid).set(
        {
            "encrypted_credentials": encrypted,
            "updated_at": datetime.now(timezone.utc),
        }
    )


def complete_gmail_authorization(code: str, state: str) -> str:
    client_config = _client_config()
    _cipher()
    state_record = _consume_state(state)
    if state_record is None:
        raise ValueError("Gmail OAuth state is invalid or already used.")

    created_at = state_record.get("created_at")
    if not isinstance(created_at, datetime):
        raise ValueError("Gmail OAuth state has expired.")
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) - created_at > STATE_TTL:
        raise ValueError("Gmail OAuth state has expired.")

    flow = Flow.from_client_config(
        client_config,
        scopes=GmailProvider.SCOPES,
        state=state,
        code_verifier=state_record.get("code_verifier"),
        autogenerate_code_verifier=False,
    )
    flow.redirect_uri = config.gmail_oauth_redirect_uri
    try:
        flow.fetch_token(code=code)
    except Exception as exc:
        # OAuth provider errors can include request details. Return a stable,
        # non-sensitive message to the browser and allow the user to retry.
        raise ValueError(
            "Google authorization could not be completed. Reconnect Gmail and try again."
        ) from exc
    credentials = flow.credentials

    # Google can omit a refresh token when the user has already consented.
    # Preserve an existing encrypted refresh token rather than replacing it
    # with a credential that cannot be renewed offline.
    if not credentials.refresh_token:
        previous = _load_credentials(state_record["uid"], required=False)
        if previous and previous.refresh_token:
            credentials.refresh_token = previous.refresh_token
    if not credentials.refresh_token:
        raise ValueError(
            "Google did not return offline access. Revoke Privora in your Google Account and reconnect."
        )

    _save_credentials(state_record["uid"], credentials)
    return str(state_record["uid"])


def _load_credentials(uid: str, required: bool = True) -> Credentials | None:
    snapshot = collection("gmail_tokens").document(uid).get()
    if not snapshot.exists:
        if required:
            raise LookupError("Gmail is not connected for this Privora account.")
        return None

    encrypted = (snapshot.to_dict() or {}).get("encrypted_credentials")
    if not encrypted:
        if required:
            raise LookupError("Gmail authorization data is unavailable.")
        return None
    try:
        payload = _cipher().decrypt(encrypted.encode("ascii"))
        return Credentials.from_authorized_user_info(
            json.loads(payload),
            scopes=GmailProvider.SCOPES,
        )
    except (InvalidToken, ValueError, TypeError, KeyError) as exc:
        raise GmailOAuthConfigurationError(
            "Stored Gmail authorization could not be decrypted. Check the token encryption key."
        ) from exc


def gmail_credentials(uid: str) -> Credentials:
    credentials = _load_credentials(uid)
    assert credentials is not None
    if not credentials.valid:
        if not credentials.expired or not credentials.refresh_token:
            raise LookupError("Gmail authorization expired. Reconnect Gmail.")
        try:
            credentials.refresh(Request())
        except RefreshError as exc:
            raise GmailAuthorizationError(
                "Gmail authorization expired or was revoked. Reconnect Gmail."
            ) from exc
        _save_credentials(uid, credentials)
    return credentials


def save_refreshed_credentials(uid: str, credentials: Credentials) -> None:
    _save_credentials(uid, credentials)

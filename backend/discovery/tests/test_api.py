from fastapi.testclient import TestClient

from ..api.routes import router
from fastapi import FastAPI
from app.core.authentication import get_current_user


app = FastAPI()
app.include_router(router)
app.dependency_overrides[get_current_user] = lambda: {
    "uid": "discovery-test-user",
    "email": "discovery@example.com",
}

client = TestClient(app)


def test_gmail_status_requires_authentication() -> None:
    unauthenticated_app = FastAPI()
    unauthenticated_app.include_router(router)

    with TestClient(unauthenticated_app) as unauthenticated_client:
        response = unauthenticated_client.get("/discovery/gmail/status")

    assert response.status_code == 401


def test_discovery_health() -> None:
    response = client.get("/discovery/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "discovery",
    }


def test_run_discovery() -> None:
    response = client.post("/discovery/run")

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "success"
    assert data["count"] > 0
    assert len(data["accounts"]) == data["count"]


def test_discovery_returns_sanitized_accounts() -> None:
    response = client.post("/discovery/run")

    assert response.status_code == 200

    accounts = response.json()["accounts"]

    for account in accounts:
        assert "service_name" in account
        assert "domain" in account
        assert "relationship" in account
        assert "source" in account

        # Evidence contains potentially sensitive/raw information
        # and must not leave the sanitized discovery layer.
        assert "evidence" not in account


def test_discovery_masks_sensitive_information() -> None:
    response = client.post("/discovery/run")

    assert response.status_code == 200

    accounts = response.json()["accounts"]

    serialized = str(accounts)

    assert "[EMAIL]" not in serialized
    assert "[PHONE]" not in serialized


def test_revoked_gmail_credentials_return_reconnect_status(monkeypatch) -> None:
    from ..api import routes
    from ..sources.email.gmail_provider import GmailAuthorizationError

    class FailedPipeline:
        def run(self):
            raise GmailAuthorizationError("Reconnect Gmail")

    monkeypatch.setattr(routes, "_get_gmail_pipeline", lambda _uid: FailedPipeline())
    response = client.post("/discovery/run?source=gmail")

    assert response.status_code == 409
    assert response.json()["detail"] == "Reconnect Gmail"

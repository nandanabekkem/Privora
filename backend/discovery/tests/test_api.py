from fastapi.testclient import TestClient

from ..api.routes import router
from fastapi import FastAPI


app = FastAPI()
app.include_router(router)

client = TestClient(app)


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
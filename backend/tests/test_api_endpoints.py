from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import app
from app.models import User, Service, Account, DataRecord


# Use a separate in-memory database for testing.
TEST_DATABASE_URL = "sqlite://"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)


@pytest.fixture
def client():
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    db = TestingSessionLocal()

    user = User(name="Test User", email="test@example.com")
    service = Service(name="Example Service", website="https://example.com")

    db.add_all([user, service])
    db.commit()
    db.refresh(user)
    db.refresh(service)

    account = Account(
        user_id=user.id,
        service_id=service.id,
        status="ACTIVE",
        last_activity=datetime.now(timezone.utc) - timedelta(days=150),
    )

    db.add(account)
    db.commit()
    db.refresh(account)

    record = DataRecord(
        account_id=account.id,
        category="Email",
        description="Email address stored by the service",
    )

    db.add(record)
    db.commit()
    db.close()

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.pop(get_db, None)
    Base.metadata.drop_all(bind=engine)


def test_data_map_returns_user_accounts(client):
    response = client.get("/data-map/1")

    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == 1
    assert data["account_count"] == 1
    assert data["accounts"][0]["service"] == "Example Service"
    assert data["accounts"][0]["data_record_count"] == 1


def test_data_map_returns_404_for_missing_user(client):
    response = client.get("/data-map/999")

    assert response.status_code == 404


def test_dormant_endpoint_detects_old_account(client):
    response = client.get("/dormant/1?days=90")

    assert response.status_code == 200
    data = response.json()
    assert data["dormant_count"] == 1
    assert data["accounts"][0]["is_dormant"] is True


def test_dormant_endpoint_rejects_invalid_threshold(client):
    response = client.get("/dormant/1?days=0")

    assert response.status_code == 422


def test_policies_endpoint_returns_empty_list(client):
    response = client.get("/policies/1")

    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == 1
    assert data["policy_count"] == 0


def test_policies_endpoint_creates_policy(client):
    response = client.post(
        "/policies/1",
        json={
            "policy_type": "INACTIVITY",
            "policy_text": "Review accounts inactive for more than 120 days.",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["policy"]["policy_type"] == "INACTIVITY"
    assert data["policy"]["user_id"] == 1


def test_policies_endpoint_rejects_missing_user(client):
    response = client.get("/policies/999")

    assert response.status_code == 404

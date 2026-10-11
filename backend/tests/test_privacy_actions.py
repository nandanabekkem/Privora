
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.database import Base, get_db
from app.models import User, Service, Account


# Separate in-memory database for privacy action tests
test_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(
    bind=test_engine,
    autoflush=False,
    autocommit=False,
)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def client():
    previous_override = app.dependency_overrides.get(get_db)

    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        if previous_override is None:
            app.dependency_overrides.pop(get_db, None)
        else:
            app.dependency_overrides[get_db] = previous_override

        Base.metadata.drop_all(bind=test_engine)


def setup_test_data():
    db = TestingSessionLocal()

    try:
        user = User(
            name="Test User",
            email="test@privora.test",
        )

        service = Service(
            name="Test Service",
            website="https://example.com",
        )

        db.add_all([user, service])
        db.commit()

        db.refresh(user)
        db.refresh(service)

        account = Account(
            user_id=user.id,
            service_id=service.id,
            status="ACTIVE",
        )

        db.add(account)
        db.commit()
        db.refresh(account)

        return user.id, account.id

    finally:
        db.close()


def create_test_action(client, user_id, account_id):
    return client.post(
        f"/privacy-actions/{user_id}",
        json={
            "account_id": account_id,
            "action_type": "REVIEW",
            "description": "Review this account's stored data",
        },
    )


def test_create_privacy_action(client):
    user_id, account_id = setup_test_data()

    response = create_test_action(client, user_id, account_id)

    assert response.status_code == 201
    assert response.json()["status"] == "PENDING"
    assert response.json()["requires_approval"] is True


def test_list_privacy_actions(client):
    user_id, account_id = setup_test_data()

    create_response = create_test_action(client, user_id, account_id)
    assert create_response.status_code == 201

    response = client.get(f"/privacy-actions/{user_id}")

    assert response.status_code == 200
    assert response.json()["count"] == 1
    assert response.json()["actions"][0]["status"] == "PENDING"


def test_reject_privacy_action(client):
    user_id, account_id = setup_test_data()

    create_response = create_test_action(client, user_id, account_id)
    assert create_response.status_code == 201

    action_id = create_response.json()["id"]

    response = client.post(
        f"/privacy-actions/{user_id}/{action_id}/review",
        json={"decision": "REJECT"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "REJECTED"


def test_approve_privacy_action(client):
    user_id, account_id = setup_test_data()

    create_response = create_test_action(client, user_id, account_id)
    assert create_response.status_code == 201

    action_id = create_response.json()["id"]

    response = client.post(
        f"/privacy-actions/{user_id}/{action_id}/review",
        json={"decision": "APPROVE"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "APPROVED"
    assert "No external account action was executed" in response.json()["message"]


def test_invalid_review_decision(client):
    user_id, account_id = setup_test_data()

    create_response = create_test_action(client, user_id, account_id)
    assert create_response.status_code == 201

    action_id = create_response.json()["id"]

    response = client.post(
        f"/privacy-actions/{user_id}/{action_id}/review",
        json={"decision": "MAYBE"},
    )

    assert response.status_code == 422


@pytest.mark.parametrize(
    "field,value",
    [
        ("action_type", "   "),
        ("description", "   "),
    ],
)
def test_blank_action_fields_are_rejected(client, field, value):
    user_id, account_id = setup_test_data()

    payload = {
        "account_id": account_id,
        "action_type": "REVIEW",
        "description": "Review this account's stored data",
    }
    payload[field] = value

    response = client.post(
        f"/privacy-actions/{user_id}",
        json=payload,
    )

    assert response.status_code == 422


def test_action_cannot_be_reviewed_twice(client):
    user_id, account_id = setup_test_data()

    create_response = create_test_action(client, user_id, account_id)
    assert create_response.status_code == 201

    action_id = create_response.json()["id"]
    review_url = f"/privacy-actions/{user_id}/{action_id}/review"

    first_response = client.post(
        review_url,
        json={"decision": "APPROVE"},
    )

    assert first_response.status_code == 200
    assert first_response.json()["status"] == "APPROVED"

    second_response = client.post(
        review_url,
        json={"decision": "REJECT"},
    )

    assert second_response.status_code == 409
    assert second_response.json()["detail"] == "Only pending actions can be reviewed"


def test_privacy_action_for_wrong_account(client):
    user_id, _ = setup_test_data()

    response = client.post(
        f"/privacy-actions/{user_id}",
        json={
            "account_id": 9999,
            "action_type": "REVIEW",
            "description": "This account should not exist",
        },
    )

    assert response.status_code == 404


@pytest.mark.parametrize(
    "path",
    [
        "/privacy-actions/0",
        "/privacy-actions/-1",
    ],
)
def test_non_positive_user_id_is_rejected(client, path):
    response = client.get(path)

    assert response.status_code == 422

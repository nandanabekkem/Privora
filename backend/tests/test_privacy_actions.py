
import pytest


def create_test_action(client, user_id=1, account_id=1):
    return client.post(
        f"/privacy-actions/{user_id}",
        json={
            "account_id": account_id,
            "action_type": "REVIEW",
            "description": "Review this account's stored data",
        },
    )


def test_create_privacy_action(client):
    response = create_test_action(client)

    assert response.status_code == 201
    assert response.json()["status"] == "PENDING"
    assert response.json()["requires_approval"] is True


def test_list_privacy_actions(client):
    create_response = create_test_action(client)
    assert create_response.status_code == 201

    response = client.get("/privacy-actions/1")

    assert response.status_code == 200
    assert response.json()["count"] == 1
    assert response.json()["actions"][0]["status"] == "PENDING"


def test_reject_privacy_action(client):
    create_response = create_test_action(client)
    assert create_response.status_code == 201

    action_id = create_response.json()["id"]
    response = client.post(
        f"/privacy-actions/1/{action_id}/review",
        json={"decision": "REJECT"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "REJECTED"


def test_approve_privacy_action(client):
    create_response = create_test_action(client)
    assert create_response.status_code == 201

    action_id = create_response.json()["id"]
    response = client.post(
        f"/privacy-actions/1/{action_id}/review",
        json={"decision": "APPROVE"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "APPROVED"
    assert "No external account action was executed" in response.json()["message"]


def test_invalid_review_decision(client):
    create_response = create_test_action(client)
    assert create_response.status_code == 201

    action_id = create_response.json()["id"]
    response = client.post(
        f"/privacy-actions/1/{action_id}/review",
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
    payload = {
        "account_id": 1,
        "action_type": "REVIEW",
        "description": "Review this account's stored data",
    }
    payload[field] = value

    response = client.post("/privacy-actions/1", json=payload)

    assert response.status_code == 422


def test_action_cannot_be_reviewed_twice(client):
    create_response = create_test_action(client)
    assert create_response.status_code == 201

    action_id = create_response.json()["id"]
    review_url = f"/privacy-actions/1/{action_id}/review"

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
    response = client.post(
        "/privacy-actions/1",
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

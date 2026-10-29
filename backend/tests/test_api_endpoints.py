
import pytest


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

    assert response.status_code == 403


def test_dormant_endpoint_detects_old_account(client):
    response = client.get("/dormant/1?days=90")

    assert response.status_code == 200
    data = response.json()
    assert data["dormant_count"] == 1
    assert data["accounts"][0]["is_dormant"] is True


def test_dormant_endpoint_rejects_invalid_threshold(client):
    response = client.get("/dormant/1?days=0")

    assert response.status_code == 422


def test_missing_activity_is_unknown_and_needs_review(client, mock_firestore):
    mock_firestore.collection("accounts").document("1").update({"last_activity": None})
    response = client.get("/dormant/1?days=90")

    assert response.status_code == 200
    data = response.json()
    assert data["dormant_count"] == 0
    assert data["accounts"][0]["is_dormant"] is None
    assert data["accounts"][0]["needs_review"] is True


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

    assert response.status_code == 403

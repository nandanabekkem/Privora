from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from app.services.rules_engine import evaluate_account


def make_account(last_activity=None, data_records=None):
    return SimpleNamespace(
        id=1,
        service=SimpleNamespace(name="Google"),
        last_activity=last_activity,
        data_records=data_records or [],
    )


def make_policy(policy_text, policy_type="GENERAL"):
    return SimpleNamespace(
        policy_type=policy_type,
        policy_text=policy_text,
    )


def test_old_account_is_recommended_for_review():
    activity = datetime.now(timezone.utc) - timedelta(days=120)

    result = evaluate_account(
        make_account(last_activity=activity)
    )

    assert result["recommendation"] == "REVIEW"
    assert result["days_threshold"] == 90
    assert result["requires_user_approval"] is True


def test_recent_account_with_mapped_data_is_kept():
    activity = datetime.now(timezone.utc) - timedelta(days=5)
    account = make_account(
        last_activity=activity,
        data_records=[SimpleNamespace()],
    )

    result = evaluate_account(account)

    assert result["recommendation"] == "KEEP"
    assert result["requires_user_approval"] is True


def test_recent_account_without_mapped_data_needs_review():
    activity = datetime.now(timezone.utc) - timedelta(days=5)

    result = evaluate_account(
        make_account(last_activity=activity)
    )

    assert result["recommendation"] == "REVIEW"


def test_missing_activity_needs_review():
    result = evaluate_account(make_account())

    assert result["recommendation"] == "REVIEW"
    assert "No last-activity date" in result["reason"]


def test_policy_can_change_inactivity_threshold():
    activity = datetime.now(timezone.utc) - timedelta(days=100)

    policy = make_policy(
        "Review accounts inactive for more than 120 days."
    )

    account = make_account(
        last_activity=activity,
        data_records=[SimpleNamespace()],
    )

    result = evaluate_account(
        account,
        policies=[policy],
    )

    assert result["days_threshold"] == 120
    assert result["recommendation"] == "KEEP"
    assert result["applied_policy_count"] == 1


def test_approval_is_required_even_without_approval_policy():
    activity = datetime.now(timezone.utc) - timedelta(days=5)
    policy = make_policy("Prefer keeping useful accounts.")

    result = evaluate_account(
        make_account(
            last_activity=activity,
            data_records=[SimpleNamespace()],
        ),
        policies=[policy],
    )

    assert result["requires_user_approval"] is True


@pytest.mark.parametrize(
    "invalid_days",
    [0, -1, 3651, True, 1.5],
)
def test_invalid_inactivity_threshold_is_rejected(invalid_days):
    account = make_account(
        last_activity=datetime.now(timezone.utc)
    )

    with pytest.raises(ValueError):
        evaluate_account(
            account,
            days_threshold=invalid_days,
        )

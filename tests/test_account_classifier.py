
from ai_agent.classifiers.account_classifier import classify_account


def test_banking_account_is_high_risk():
    account = {
        "name": "DemoBank",
        "service_type": "banking",
        "inactive_months": 1,
    }

    result = classify_account(account)

    assert result["risk_level"] == "high"
    assert result["account_name"] == "DemoBank"


def test_inactive_account_is_medium_risk():
    account = {
        "name": "DemoMusic",
        "service_type": "entertainment",
        "inactive_months": 18,
    }

    result = classify_account(account)

    assert result["risk_level"] == "medium"


def test_active_entertainment_account_is_low_risk():
    account = {
        "name": "StudyPortal",
        "service_type": "education",
        "inactive_months": 2,
    }

    result = classify_account(account)

    assert result["risk_level"] == "low"

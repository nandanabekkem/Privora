
from ai_agent.classifiers.account_classifier import classify_account
from ai_agent.classifiers.data_classifier import classify_personal_data
from ai_agent.policy.policy_analyzer import analyze_policy


def test_banking_account_is_high_priority():
    account = {
        "name": "DemoBank",
        "service_type": "banking",
        "inactive_months": 1,
    }
    result = classify_account(account)
    assert result["risk_level"] == "high"


def test_empty_data_categories_are_unknown():
    result = classify_personal_data([])
    assert result["sensitivity"] == "unknown"


def test_missing_policy_information_needs_review():
    result = analyze_policy({
        "shares_data": None,
        "deletion_available": None,
        "retention_period": None,
    })
    assert result["needs_review"] is True


def test_complete_policy_information_does_not_flag_missing_fields():
    result = analyze_policy({
        "shares_data": True,
        "deletion_available": True,
        "retention_period": "12 months",
    })
    assert result["needs_review"] is False

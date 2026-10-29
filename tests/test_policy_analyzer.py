
from ai_agent.policy.policy_analyzer import analyze_policy


def test_policy_with_complete_information():
    policy_facts = {
        "shares_data": True,
        "deletion_available": True,
        "retention_period": "12 months",
    }

    result = analyze_policy(policy_facts)

    assert result["needs_review"] is False
    assert len(result["findings"]) > 0
    assert any("shared with third parties" in finding
               for finding in result["findings"])


def test_missing_policy_information_needs_review():
    result = analyze_policy({})

    assert result["needs_review"] is True


def test_data_sharing_is_false():
    policy_facts = {
        "shares_data": False,
        "deletion_available": True,
        "retention_period": "6 months",
    }

    result = analyze_policy(policy_facts)

    assert any("not shared" in finding
               for finding in result["findings"])


def test_missing_retention_period_needs_review():
    policy_facts = {
        "shares_data": True,
        "deletion_available": False,
    }

    result = analyze_policy(policy_facts)

    assert result["needs_review"] is True



from ai_agent.classifiers.data_classifier import (
    classify_personal_data,
)


def test_financial_data_is_high_sensitivity():
    result = classify_personal_data(["financial"])

    assert result["sensitivity"] == "high"
    assert "financial" in result["sensitive_categories"]


def test_health_data_is_high_sensitivity():
    result = classify_personal_data(["health"])

    assert result["sensitivity"] == "high"
    assert "health" in result["sensitive_categories"]


def test_general_data_is_moderate_sensitivity():
    result = classify_personal_data(["email", "location"])

    assert result["sensitivity"] == "moderate"
    assert result["sensitive_categories"] == []


def test_empty_categories_are_unknown():
    result = classify_personal_data([])

    assert result["sensitivity"] == "unknown"
    assert result["data_categories"] == []

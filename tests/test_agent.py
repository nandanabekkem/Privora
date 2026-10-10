
from unittest.mock import Mock, patch

from ai_agent.agent import PrivoraAgent


@patch("ai_agent.agent.NemotronClient")
def test_agent_analyzes_account_and_returns_recommendation(mock_client):
    mock_nemotron = Mock()
    mock_nemotron.ask.return_value = (
        "Review the service's data-sharing practices."
    )
    mock_client.return_value = mock_nemotron

    agent = PrivoraAgent()

    result = agent.analyze_account(
        account={
            "name": "DemoMusic",
            "service_type": "entertainment",
            "inactive_months": 18,
        },
        data_categories=["email", "location"],
        policy_facts={
            "shares_data": True,
            "deletion_available": True,
            "retention_period": "12 months",
        },
    )

    assert result["account_analysis"]["risk_level"] == "medium"
    assert result["data_analysis"]["sensitivity"] == "moderate"
    assert result["policy_analysis"]["needs_review"] is False
    assert result["recommendation"] == (
        "Review the service's data-sharing practices."
    )
    assert result["action_performed"] is False
    mock_nemotron.ask.assert_called_once()


@patch("ai_agent.agent.NemotronClient")
def test_agent_flags_sensitive_data(mock_client):
    mock_nemotron = Mock()
    mock_nemotron.ask.return_value = "Review the handling of sensitive data."
    mock_client.return_value = mock_nemotron

    agent = PrivoraAgent()

    result = agent.analyze_account(
        account={
            "name": "DemoBank",
            "service_type": "banking",
            "inactive_months": 1,
        },
        data_categories=["financial"],
        policy_facts={},
    )

    assert result["account_analysis"]["risk_level"] == "high"
    assert result["data_analysis"]["sensitivity"] == "high"
    assert result["policy_analysis"]["needs_review"] is True
    assert result["action_performed"] is False

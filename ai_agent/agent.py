
from ai_agent.reasoning.nemotron import NemotronClient
from ai_agent.classifiers.account_classifier import classify_account
from ai_agent.classifiers.data_classifier import classify_personal_data
from ai_agent.policy.policy_analyzer import analyze_policy


class PrivoraAgent:
    """Coordinate Privora's privacy-analysis components."""

    def __init__(self):
        self.nemotron = NemotronClient()

    def analyze_account(
        self,
        account: dict,
        data_categories: list[str],
        policy_facts: dict,
    ) -> dict:
        """Analyze an account and return a privacy recommendation."""

        account_result = classify_account(account)

        data_result = classify_personal_data(data_categories)

        policy_result = analyze_policy(policy_facts)

        prompt = f"""
You are Privora, a privacy assistant.

Review the following fictional account information:
Account classification: {account_result}
Personal-data classification: {data_result}
Policy findings: {policy_result}

Give:
1. A short summary of the privacy concerns.
2. One practical next step for the account owner.

Do not claim that you verified a real policy or performed any action.
Keep the answer concise.
"""

        recommendation = self.nemotron.ask(prompt)

        return {
            "account_analysis": account_result,
            "data_analysis": data_result,
            "policy_analysis": policy_result,
            "recommendation": recommendation,
            "action_performed": False,
        }


from ai_agent.agent import PrivoraAgent


def main():
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

    print("\n--- Privora Full Agent Test ---")

    print("\nAccount Analysis:")
    print(result["account_analysis"])

    print("\nPersonal Data Analysis:")
    print(result["data_analysis"])

    print("\nPolicy Analysis:")
    for finding in result["policy_analysis"]["findings"]:
        print("-", finding)

    print("\nNemotron Recommendation:")
    print(result["recommendation"])

    print("\nAction performed:", result["action_performed"])


if __name__ == "__main__":
    main()

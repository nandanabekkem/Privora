
from ai_agent.policy.policy_analyzer import analyze_policy


def main():
    policy_facts = {
        "shares_data": True,
        "deletion_available": True,
        "retention_period": "12 months",
    }

    result = analyze_policy(policy_facts)

    print("\n--- Privora Policy Analyzer Test ---")

    for finding in result["findings"]:
        print("-", finding)

    print("Needs review:", result["needs_review"])


if __name__ == "__main__":
    main()

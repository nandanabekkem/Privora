
from ai_agent.classifiers.account_classifier import classify_account


def main():
    accounts = [
        {
            "name": "DemoMusic",
            "service_type": "entertainment",
            "inactive_months": 18,
        },
        {
            "name": "StudyPortal",
            "service_type": "education",
            "inactive_months": 2,
        },
        {
            "name": "DemoBank",
            "service_type": "banking",
            "inactive_months": 1,
        },
    ]

    for account in accounts:
        result = classify_account(account)
        print(result)


if __name__ == "__main__":
    main()

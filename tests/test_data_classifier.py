
from ai_agent.classifiers.data_classifier import (
    classify_personal_data,
)


def main():
    test_cases = [
        ["email", "location"],
        ["financial", "health"],
        [],
    ]

    for categories in test_cases:
        result = classify_personal_data(categories)
        print(result)


if __name__ == "__main__":
    main()

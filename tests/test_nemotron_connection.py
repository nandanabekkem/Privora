
from ai_agent.reasoning.nemotron import NemotronClient


def main():
    agent = NemotronClient()

    result = agent.ask(
    "A fictional account called DemoMusic has been inactive "
    "for 18 months. Recommend one privacy-conscious next step. "
    "Return only the final recommendation in 1-2 sentences. "
    "Do not include analysis, reasoning steps, or a numbered list. "
    "Do not claim that any action has been performed."
)

    print("\n--- Privora Nemotron Test ---")
    print(result)


if __name__ == "__main__":
    main()

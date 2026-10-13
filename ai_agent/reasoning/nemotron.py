
import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()


class NemotronClient:
    """Connect Privora's AI agent to NVIDIA Nemotron."""

    def __init__(self):
        api_key = os.getenv("NVIDIA_API_KEY")

        if not api_key:
            raise ValueError(
                "NVIDIA_API_KEY is missing. Check your .env file."
            )

        self.client = OpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=api_key,
        )

        self.model = "nvidia/nemotron-3.5-lightning-30b-a3b"

    def ask(self, prompt: str) -> str:
        """Send a prompt and return the model's response."""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are Privora's privacy assistant. "
                        "Return only a concise final recommendation. "
                        "Do not include analysis or reasoning steps. "
                        "Never claim an action was completed unless "
                        "the application confirms it."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=500,
            extra_body={
                "chat_template_kwargs": {
                    "enable_thinking": False
                }
            },
        )

        answer = response.choices[0].message.content

        if not answer:
            raise RuntimeError("Nemotron returned an empty response.")

        return answer.strip()

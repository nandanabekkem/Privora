
from unittest.mock import Mock, patch

import pytest

from ai_agent.reasoning.nemotron import NemotronClient


@patch.dict("os.environ", {}, clear=True)
@patch("ai_agent.reasoning.nemotron.load_dotenv")
def test_missing_api_key_raises_error(mock_load_dotenv):
    with pytest.raises(ValueError, match="NVIDIA_API_KEY is missing"):
        NemotronClient()


@patch("ai_agent.reasoning.nemotron.OpenAI")
def test_ask_returns_model_response(mock_openai):
    mock_client = Mock()
    mock_message = Mock()
    mock_message.content = "Review the account's privacy settings."
    mock_client.chat.completions.create.return_value.choices = [
        Mock(message=mock_message)
    ]
    mock_openai.return_value = mock_client

    with patch.dict(
        "os.environ",
        {"NVIDIA_API_KEY": "test-key"},
    ):
        agent = NemotronClient()

    result = agent.ask("Give one privacy-conscious recommendation.")

    assert result == "Review the account's privacy settings."
    mock_client.chat.completions.create.assert_called_once()

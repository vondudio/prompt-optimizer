"""Tests for the analyzer module (mocked Azure calls)."""

from unittest.mock import MagicMock, patch

from prompt_optimizer.analyzer import analyze_prompt, improve_prompt


def _mock_client(return_value: dict) -> MagicMock:
    """Create a mock AzureClient that returns the given dict from chat_json."""
    client = MagicMock()
    client.chat_json.return_value = return_value
    return client


def test_analyze_prompt_returns_expected_keys():
    """analyze_prompt should pass messages to client and return the result."""
    expected = {
        "summary": "A test prompt",
        "gaps": ["missing role", "no format specified"],
        "scores": {"clarity": 5, "specificity": 3, "structure": 4, "actionability": 6},
    }
    client = _mock_client(expected)

    result = analyze_prompt(client, "Tell me about Python")

    assert result == expected
    client.chat_json.assert_called_once()
    call_args = client.chat_json.call_args
    messages = call_args[0][0]
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"
    assert "Tell me about Python" in messages[1]["content"]


def test_improve_prompt_includes_analysis():
    """improve_prompt should include the analysis in the user message."""
    analysis = {"gaps": ["no role"], "scores": {"clarity": 5}}
    expected = {
        "improved_prompt": "You are an expert...",
        "changes_made": ["Added role"],
        "new_scores": {"clarity": 8},
    }
    client = _mock_client(expected)

    result = improve_prompt(client, "Tell me about Python", analysis)

    assert result["improved_prompt"] == "You are an expert..."
    call_args = client.chat_json.call_args
    messages = call_args[0][0]
    assert "no role" in messages[1]["content"]

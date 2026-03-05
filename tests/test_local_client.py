"""Tests for the LocalClient JSON extraction fallback."""

import json
from unittest.mock import MagicMock, patch

import pytest

from prompt_optimizer.local_client import LocalClient, _extract_json_from_text


# ── JSON extraction helper tests ─────────────────────────────────────────────


def test_extract_json_from_text_with_json_fence():
    """Should extract JSON from ```json ... ``` blocks."""
    text = 'Here is the result:\n```json\n{"key": "value"}\n```\nDone.'
    result = _extract_json_from_text(text)
    assert result == {"key": "value"}


def test_extract_json_from_text_with_plain_fence():
    """Should extract JSON from ``` ... ``` blocks (no language tag)."""
    text = 'Result:\n```\n{"a": 1, "b": 2}\n```'
    result = _extract_json_from_text(text)
    assert result == {"a": 1, "b": 2}


def test_extract_json_from_text_no_fence():
    """Should extract JSON even without code fences."""
    text = '{"key": "value"}'
    result = _extract_json_from_text(text)
    assert result == {"key": "value"}


def test_extract_json_from_text_unclosed_fence():
    """Should extract JSON from an unclosed code fence (truncated response)."""
    text = '```json\n{"key": "value", "num": 42}'
    result = _extract_json_from_text(text)
    assert result == {"key": "value", "num": 42}


def test_extract_json_from_text_embedded_in_prose():
    """Should find JSON object embedded in surrounding text."""
    text = 'Here is my answer:\n{"key": "value"}\nHope that helps!'
    result = _extract_json_from_text(text)
    assert result == {"key": "value"}


def test_extract_json_from_text_invalid_json():
    """Should return None when no valid JSON can be found."""
    text = 'not valid json at all'
    result = _extract_json_from_text(text)
    assert result is None


# ── LocalClient tests (mocked, no real Foundry needed) ──────────────────────


def _make_local_client() -> tuple[LocalClient, MagicMock]:
    """Create a LocalClient with mocked FoundryLocalManager and OpenAI client."""
    mock_openai = MagicMock()

    with (
        patch("prompt_optimizer.local_client.FoundryLocalManager", create=True) as mock_manager_cls,
        patch("prompt_optimizer.local_client.OpenAI", create=True) as mock_openai_cls,
    ):
        # Patch the imports inside local_client at module level
        import prompt_optimizer.local_client as lc_module

        # Temporarily inject the mocks
        original_init = LocalClient.__init__

        def patched_init(self, model="phi-4-mini-reasoning"):
            self._model = model
            self._manager = MagicMock()
            self._manager.endpoint = "http://localhost:5272"
            self._client = mock_openai

        LocalClient.__init__ = patched_init
        client = LocalClient()
        LocalClient.__init__ = original_init

    return client, mock_openai


def _mock_completion(content: str) -> MagicMock:
    """Create a mock OpenAI completion response."""
    choice = MagicMock()
    choice.message.content = content
    response = MagicMock()
    response.choices = [choice]
    return response


def test_chat_json_direct_parse():
    """chat_json should parse valid JSON directly."""
    client, mock_openai = _make_local_client()
    expected = {"summary": "test", "gaps": []}
    mock_openai.chat.completions.create.return_value = _mock_completion(json.dumps(expected))

    result = client.chat_json([{"role": "user", "content": "test"}])

    assert result == expected


def test_chat_json_markdown_fence_fallback():
    """chat_json should extract JSON from markdown fences when direct parse fails."""
    client, mock_openai = _make_local_client()
    expected = {"summary": "test"}
    markdown_response = f'Here is the result:\n```json\n{json.dumps(expected)}\n```'
    mock_openai.chat.completions.create.return_value = _mock_completion(markdown_response)

    result = client.chat_json([{"role": "user", "content": "test"}])

    assert result == expected


def test_chat_json_retry_on_failure():
    """chat_json should retry with stronger prompt when both direct and fence parse fail."""
    client, mock_openai = _make_local_client()
    expected = {"summary": "retry worked"}

    # First call returns unparseable text, second call (retry) returns valid JSON
    mock_openai.chat.completions.create.side_effect = [
        _mock_completion("This is not JSON at all, sorry!"),
        _mock_completion(json.dumps(expected)),
    ]

    result = client.chat_json([{"role": "user", "content": "test"}])

    assert result == expected
    assert mock_openai.chat.completions.create.call_count == 2


def test_chat_json_raises_on_total_failure():
    """chat_json should raise ValueError when all attempts fail."""
    client, mock_openai = _make_local_client()

    mock_openai.chat.completions.create.return_value = _mock_completion("not json at all")

    with pytest.raises(ValueError, match="Failed to parse JSON"):
        client.chat_json([{"role": "user", "content": "test"}])

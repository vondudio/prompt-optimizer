"""Tests for the optimizer orchestrator (mocked)."""

from unittest.mock import MagicMock, patch

from prompt_optimizer.optimizer import Optimizer


def _make_optimizer() -> tuple[Optimizer, MagicMock]:
    """Create an Optimizer with a mocked AzureClient."""
    client = MagicMock()
    optimizer = Optimizer(client, max_questions=3)
    return optimizer, client


def test_one_shot_returns_combined_result():
    """one_shot should combine analysis and improvement results."""
    optimizer, client = _make_optimizer()

    analysis = {
        "summary": "Test",
        "gaps": ["role"],
        "scores": {"clarity": 5, "specificity": 4, "structure": 3, "actionability": 6},
    }
    improvement = {
        "improved_prompt": "Better prompt",
        "changes_made": ["Added role"],
        "new_scores": {"clarity": 9, "specificity": 8, "structure": 8, "actionability": 9},
    }
    client.chat_json.side_effect = [analysis, improvement]

    result = optimizer.one_shot("Test prompt")

    assert result["improved_prompt"] == "Better prompt"
    assert result["changes_made"] == ["Added role"]
    assert result["original_scores"] == analysis["scores"]
    assert result["new_scores"] == improvement["new_scores"]
    assert client.chat_json.call_count == 2


def test_analyze_delegates_to_client():
    """analyze should call the client's chat_json."""
    optimizer, client = _make_optimizer()
    client.chat_json.return_value = {"summary": "Test", "gaps": [], "scores": {}}

    result = optimizer.analyze("Hello")

    assert result["summary"] == "Test"
    client.chat_json.assert_called_once()


def test_get_questions_returns_list():
    """get_questions should return the questions list."""
    optimizer, client = _make_optimizer()
    client.chat_json.return_value = {
        "questions": [
            {"id": "q1", "question": "What role?", "purpose": "role", "suggestions": ["expert"]}
        ]
    }

    questions = optimizer.get_questions("Test", {"gaps": ["role"]})

    assert len(questions) == 1
    assert questions[0]["question"] == "What role?"


def test_assemble_returns_optimized_prompt():
    """assemble should return the assembled prompt."""
    optimizer, client = _make_optimizer()
    client.chat_json.return_value = {
        "optimized_prompt": "Final prompt",
        "scores": {"clarity": 9},
        "summary": "A well-structured prompt",
    }

    result = optimizer.assemble("Test", [{"question": "Role?", "answer": "Expert"}])

    assert result["optimized_prompt"] == "Final prompt"

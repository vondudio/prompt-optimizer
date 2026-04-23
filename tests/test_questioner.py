"""Tests for the questioner module (mocked Azure calls)."""

from unittest.mock import MagicMock

from prompt_optimizer.questioner import generate_questions, assemble_from_answers


def _mock_client(json_return):
    client = MagicMock()
    client.chat_json.return_value = json_return
    return client


class TestGenerateQuestions:
    def test_generate_questions_returns_list(self):
        questions = [
            {"id": "q1", "question": "What role?", "purpose": "role", "suggestions": ["Dev"]},
        ]
        client = _mock_client({"questions": questions})
        result = generate_questions(client, "Write code", {"gaps": ["role"]})
        assert result == questions
        client.chat_json.assert_called_once()

    def test_generate_questions_empty_on_no_questions(self):
        client = _mock_client({"questions": []})
        result = generate_questions(client, "Write code", {"gaps": []})
        assert result == []

    def test_generate_questions_respects_max(self):
        client = _mock_client({"questions": []})
        generate_questions(client, "Write code", {"gaps": []}, max_questions=3)
        messages = client.chat_json.call_args[0][0]
        system_msg = messages[0]["content"]
        assert "3" in system_msg

    def test_assemble_from_answers_returns_dict(self):
        expected = {
            "optimized_prompt": "Better prompt",
            "scores": {"clarity": 8, "specificity": 7, "structure": 9, "actionability": 8},
            "summary": "A better prompt",
        }
        client = _mock_client(expected)
        qa = [{"question": "What role?", "answer": "Developer"}]
        result = assemble_from_answers(client, "Write code", qa)
        assert result == expected

    def test_assemble_includes_qa_in_message(self):
        client = _mock_client({"optimized_prompt": "x", "scores": {}, "summary": "x"})
        qa = [{"question": "What role?", "answer": "Developer"}]
        assemble_from_answers(client, "Write code", qa)
        messages = client.chat_json.call_args[0][0]
        user_msg = messages[1]["content"]
        assert "What role?" in user_msg
        assert "Developer" in user_msg

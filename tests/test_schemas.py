"""Tests for pydantic schema validation of LLM responses."""

from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from prompt_optimizer.schemas import (
    AnalysisResult,
    AssemblyResult,
    ImprovementResult,
    Question,
    QuestionSet,
    Scores,
)


# --------------- helpers ---------------

VALID_SCORES = {"clarity": 7, "specificity": 6, "structure": 8, "actionability": 5}


def _mock_client(return_value: dict) -> MagicMock:
    client = MagicMock()
    client.chat_json.return_value = return_value
    return client


# --------------- Scores ---------------

class TestScores:
    def test_valid(self):
        s = Scores(**VALID_SCORES)
        assert s.clarity == 7

    def test_score_too_low(self):
        with pytest.raises(ValidationError):
            Scores(clarity=0, specificity=5, structure=5, actionability=5)

    def test_score_too_high(self):
        with pytest.raises(ValidationError):
            Scores(clarity=11, specificity=5, structure=5, actionability=5)

    def test_missing_field(self):
        with pytest.raises(ValidationError):
            Scores(clarity=5, specificity=5, structure=5)  # missing actionability


# --------------- AnalysisResult ---------------

class TestAnalysisResult:
    def test_valid_minimal(self):
        data = {"summary": "test", "scores": VALID_SCORES}
        r = AnalysisResult.model_validate(data)
        assert r.summary == "test"
        assert r.gaps == []

    def test_valid_full(self):
        data = {
            "summary": "test",
            "detected_role": "developer",
            "detected_task": "write code",
            "detected_context": "python project",
            "detected_format": "markdown",
            "detected_audience": "engineers",
            "detected_tone": "professional",
            "detected_constraints": ["no external libs"],
            "gaps": ["missing examples"],
            "scores": VALID_SCORES,
            "score_explanations": {"clarity": "good", "specificity": "ok"},
            "improvement_suggestions": ["add examples"],
        }
        r = AnalysisResult.model_validate(data)
        assert r.detected_role == "developer"

    def test_missing_summary(self):
        with pytest.raises(ValidationError):
            AnalysisResult.model_validate({"scores": VALID_SCORES})

    def test_missing_scores(self):
        with pytest.raises(ValidationError):
            AnalysisResult.model_validate({"summary": "test"})

    def test_bad_scores(self):
        with pytest.raises(ValidationError):
            AnalysisResult.model_validate({
                "summary": "test",
                "scores": {"clarity": 0, "specificity": 5, "structure": 5, "actionability": 5},
            })


# --------------- ImprovementResult ---------------

class TestImprovementResult:
    def test_valid(self):
        data = {
            "improved_prompt": "Better prompt",
            "changes_made": ["added role"],
            "new_scores": VALID_SCORES,
        }
        r = ImprovementResult.model_validate(data)
        assert r.improved_prompt == "Better prompt"

    def test_missing_improved_prompt(self):
        with pytest.raises(ValidationError):
            ImprovementResult.model_validate({"new_scores": VALID_SCORES})

    def test_missing_new_scores(self):
        with pytest.raises(ValidationError):
            ImprovementResult.model_validate({"improved_prompt": "text"})


# --------------- QuestionSet ---------------

class TestQuestionSet:
    def test_valid(self):
        data = {
            "questions": [
                {"id": "q1", "question": "What role?", "purpose": "role", "suggestions": ["dev"]},
            ]
        }
        r = QuestionSet.model_validate(data)
        assert len(r.questions) == 1

    def test_empty_questions(self):
        r = QuestionSet.model_validate({"questions": []})
        assert r.questions == []

    def test_question_missing_id(self):
        with pytest.raises(ValidationError):
            QuestionSet.model_validate({
                "questions": [{"question": "What?"}]
            })

    def test_question_missing_question(self):
        with pytest.raises(ValidationError):
            QuestionSet.model_validate({
                "questions": [{"id": "q1"}]
            })


# --------------- AssemblyResult ---------------

class TestAssemblyResult:
    def test_valid(self):
        data = {
            "optimized_prompt": "Final prompt",
            "scores": VALID_SCORES,
            "summary": "A summary",
        }
        r = AssemblyResult.model_validate(data)
        assert r.optimized_prompt == "Final prompt"

    def test_missing_optimized_prompt(self):
        with pytest.raises(ValidationError):
            AssemblyResult.model_validate({"scores": VALID_SCORES})

    def test_missing_scores(self):
        with pytest.raises(ValidationError):
            AssemblyResult.model_validate({"optimized_prompt": "text"})


# --------------- Soft validation (warn, don't crash) ---------------

class TestSoftValidation:
    """Validation warnings must not crash the pipeline."""

    def test_analyzer_returns_raw_dict_on_bad_data(self):
        from prompt_optimizer.analyzer import analyze_prompt

        bad_result = {"summary": "ok"}  # missing scores
        client = _mock_client(bad_result)
        result = analyze_prompt(client, "test prompt")
        assert result == bad_result  # still returns the raw dict

    def test_improve_returns_raw_dict_on_bad_data(self):
        from prompt_optimizer.analyzer import improve_prompt

        bad_result = {"improved_prompt": "text"}  # missing new_scores
        client = _mock_client(bad_result)
        result = improve_prompt(client, "test", {"gaps": []})
        assert result == bad_result

    def test_generate_questions_returns_list_on_bad_data(self):
        from prompt_optimizer.questioner import generate_questions

        bad_result = {"questions": [{"bad": "data"}]}  # invalid question schema
        client = _mock_client(bad_result)
        result = generate_questions(client, "test", {"gaps": []})
        assert result == [{"bad": "data"}]  # still returns the list

    def test_assemble_returns_raw_dict_on_bad_data(self):
        from prompt_optimizer.questioner import assemble_from_answers

        bad_result = {"optimized_prompt": "text"}  # missing scores
        client = _mock_client(bad_result)
        result = assemble_from_answers(client, "test", [{"question": "q", "answer": "a"}])
        assert result == bad_result

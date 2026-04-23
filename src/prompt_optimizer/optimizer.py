"""Core optimizer — orchestrates analysis, questioning, and assembly."""

from typing import Any

from prompt_optimizer.analyzer import analyze_prompt, improve_prompt
from prompt_optimizer.azure_client import AzureClient
from prompt_optimizer.questioner import generate_questions, assemble_from_answers


class Optimizer:
    """Orchestrates the prompt optimization pipeline."""

    def __init__(self, client: AzureClient, max_questions: int = 5):
        self._client = client
        self._max_questions = max_questions

    def analyze(self, prompt_text: str) -> dict[str, Any]:
        """Analyze a prompt and return structured analysis."""
        return analyze_prompt(self._client, prompt_text)

    def one_shot(self, prompt_text: str) -> dict[str, Any]:
        """One-shot optimization: analyze and improve in one pass.

        Returns:
            Dict with keys: original_analysis, improved_prompt, changes_made,
            original_scores, new_scores, verified_scores.
        """
        analysis = self.analyze(prompt_text)
        improvement = improve_prompt(self._client, prompt_text, analysis)
        improved_text = improvement.get("improved_prompt", "")

        # Independent re-analysis of the improved prompt for verified scoring
        verified_scores = {}
        if improved_text:
            verification = analyze_prompt(self._client, improved_text)
            verified_scores = verification.get("scores", {})

        return {
            "original_analysis": analysis,
            "improved_prompt": improved_text,
            "changes_made": improvement.get("changes_made", []),
            "original_scores": analysis.get("scores", {}),
            "new_scores": improvement.get("new_scores", {}),
            "verified_scores": verified_scores,
        }

    def get_questions(self, prompt_text: str, analysis: dict[str, Any]) -> list[dict[str, Any]]:
        """Generate follow-up questions based on analysis gaps."""
        return generate_questions(
            self._client, prompt_text, analysis, self._max_questions
        )

    def assemble(
        self, prompt_text: str, questions_and_answers: list[dict[str, str]]
    ) -> dict[str, Any]:
        """Assemble the final optimized prompt from Q&A answers."""
        return assemble_from_answers(self._client, prompt_text, questions_and_answers)

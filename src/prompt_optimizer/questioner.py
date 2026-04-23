"""Follow-up question generator based on prompt analysis gaps."""

from typing import Any

from pydantic import ValidationError
from rich.console import Console

from prompt_optimizer.client import LLMClient
from prompt_optimizer.schemas import AssemblyResult, QuestionSet

console = Console(stderr=True)

QUESTION_SYSTEM_PROMPT = """\
You are an expert prompt engineer helping a user build a better prompt.
Based on the analysis of their initial prompt, generate targeted follow-up questions
to fill in the gaps.

Return a JSON object:
{
  "questions": [
    {
      "id": "q1",
      "question": "The question to ask the user",
      "purpose": "What gap this fills (e.g., 'role', 'context', 'format', 'constraints', 'audience', 'tone', 'examples')",
      "suggestions": ["suggested answer 1", "suggested answer 2"]
    }
  ]
}

Rules:
- Ask only questions that address real gaps — don't ask about things already clear in the prompt.
- Keep questions concise and easy to answer.
- Provide 2-3 helpful suggestions for each question.
- Order questions from most important to least important.
- Maximum {max_questions} questions.
Always return valid JSON.
"""


def generate_questions(
    client: LLMClient,
    prompt_text: str,
    analysis: dict[str, Any],
    max_questions: int = 5,
) -> list[dict[str, Any]]:
    """Generate follow-up questions to fill gaps in the user's prompt.

    Args:
        client: Azure OpenAI client.
        prompt_text: The user's original prompt.
        analysis: Analysis dict from analyzer.analyze_prompt().
        max_questions: Maximum number of questions to generate.

    Returns:
        List of question dicts with id, question, purpose, and suggestions.
    """
    system = QUESTION_SYSTEM_PROMPT.replace("{max_questions}", str(max_questions))
    messages = [
        {"role": "system", "content": system},
        {
            "role": "user",
            "content": (
                f"User's prompt:\n{prompt_text}\n\n"
                f"Analysis gaps: {analysis.get('gaps', [])}\n"
                f"Improvement suggestions: {analysis.get('improvement_suggestions', [])}"
            ),
        },
    ]
    result = client.chat_json(messages, temperature=0.5)
    try:
        QuestionSet.model_validate(result)
    except ValidationError as exc:
        console.print(f"[yellow]Warning: questions response failed validation: {exc}[/yellow]")
    return result.get("questions", [])


ASSEMBLY_SYSTEM_PROMPT = """\
You are an expert prompt engineer. Given the user's original prompt and their answers to
follow-up questions, assemble a polished, well-structured optimized prompt.

Return a JSON object:
{
  "optimized_prompt": "The final optimized prompt ready to use",
  "scores": {
    "clarity": <1-10>,
    "specificity": <1-10>,
    "structure": <1-10>,
    "actionability": <1-10>
  },
  "summary": "One-sentence summary of what the prompt does"
}

The optimized prompt should:
- Incorporate all answers naturally
- Follow a clear structure (role, context, task, format, constraints)
- Be ready to copy-paste into any AI assistant
Always return valid JSON.
"""


def assemble_from_answers(
    client: LLMClient,
    prompt_text: str,
    questions_and_answers: list[dict[str, str]],
) -> dict[str, Any]:
    """Assemble an optimized prompt from original input plus Q&A answers.

    Args:
        client: Azure OpenAI client.
        prompt_text: The user's original prompt.
        questions_and_answers: List of {"question": ..., "answer": ...} dicts.

    Returns:
        Dict with optimized_prompt, scores, and summary.
    """
    qa_text = "\n".join(
        f"Q: {qa['question']}\nA: {qa['answer']}" for qa in questions_and_answers
    )
    messages = [
        {"role": "system", "content": ASSEMBLY_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"Original prompt:\n{prompt_text}\n\n"
                f"Follow-up Q&A:\n{qa_text}\n\n"
                "Please assemble the optimized prompt."
            ),
        },
    ]
    result = client.chat_json(messages, temperature=0.5)
    try:
        AssemblyResult.model_validate(result)
    except ValidationError as exc:
        console.print(f"[yellow]Warning: assembly response failed validation: {exc}[/yellow]")
    return result

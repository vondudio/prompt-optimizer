"""Prompt analyzer — evaluates a prompt and identifies gaps."""

import json
from typing import Any

from pydantic import ValidationError
from rich.console import Console

from prompt_optimizer.client import LLMClient
from prompt_optimizer.schemas import AnalysisResult, ImprovementResult

console = Console(stderr=True)
from prompt_optimizer.templates import SCORING_DIMENSIONS

# Anchor examples for each scoring dimension (low / medium / high)
_SCORING_ANCHORS: dict[str, dict[str, str]] = {
    "clarity": {
        "2-3": "vague, multiple interpretations possible",
        "5-6": "main intent clear but some ambiguity",
        "8-9": "unambiguous, single clear interpretation",
    },
    "specificity": {
        "2-3": "generic request, could apply to anything",
        "5-6": "some details but key parameters missing",
        "8-9": "precise requirements, concrete parameters",
    },
    "structure": {
        "2-3": "stream of consciousness, no organization",
        "5-6": "some logical flow but could be clearer",
        "8-9": "clear sections, logical progression",
    },
    "actionability": {
        "2-3": "unclear what to produce",
        "5-6": "general direction clear but output underspecified",
        "8-9": "immediately executable, output fully defined",
    },
}


_SCORING_EXAMPLES = """\
Here are examples of scored prompts for calibration:

**Example 1 — Poor prompt:**
Prompt: "write something about dogs"
Scores: clarity=3, specificity=2, structure=2, actionability=3
- clarity (3): The intent to write is somewhat clear, but "something" is vague and open to many interpretations.
- specificity (2): No details on topic, length, format, or audience — an entirely generic request.
- structure (2): A single sentence with no organization or logical components.
- actionability (3): A writer could produce *something*, but the lack of parameters makes it nearly impossible to meet expectations.

**Example 2 — Decent prompt:**
Prompt: "Write a blog post about the benefits of adopting rescue dogs. Target audience is families."
Scores: clarity=6, specificity=5, structure=5, actionability=6
- clarity (6): The main task (blog post about rescue dog benefits) is clear, but details like length and tone are unspecified.
- specificity (5): Mentions topic and audience but lacks word count, formatting requirements, or source expectations.
- structure (5): Two logical pieces of information presented, but no explicit sections or role assignment.
- actionability (6): A writer can start working, but would need to make several assumptions about format and depth.

**Example 3 — Excellent prompt:**
Prompt: "You are a veterinarian and pet care blogger. Write a 1000-word blog post about the health and emotional benefits of adopting rescue dogs for families with children aged 5-12. Use an encouraging, warm tone. Format: markdown with H2 subheadings, at least 3 sections, include a call-to-action at the end. Constraints: cite at least 2 studies, avoid breed-specific recommendations."
Scores: clarity=9, specificity=9, structure=9, actionability=9
- clarity (9): Unambiguous task with a well-defined role, topic, and audience segment.
- specificity (9): Precise parameters including word count, audience age range, tone, formatting rules, and source requirements.
- structure (9): Logically organized with role, task, format, tone, and constraints clearly separated.
- actionability (9): Immediately executable — every requirement is explicit and verifiable.\
"""


def _build_scoring_rubric() -> str:
    """Build the scoring rubric from SCORING_DIMENSIONS and anchor examples."""
    lines: list[str] = ["Score each dimension on a 1-10 scale using this rubric:\n"]
    for dim, description in SCORING_DIMENSIONS.items():
        lines.append(f"- **{dim}**: {description}")
        anchors = _SCORING_ANCHORS[dim]
        for range_label, anchor_text in anchors.items():
            lines.append(f"    {range_label} = \"{anchor_text}\"")
    return "\n".join(lines)


ANALYSIS_SYSTEM_PROMPT = f"""\
You are an expert prompt engineer. Analyze the user's prompt and return a JSON object with the following structure:

{{
  "summary": "Brief summary of what the prompt is asking for",
  "detected_role": "The role/persona detected, or empty string if missing",
  "detected_task": "The core task detected",
  "detected_context": "Any context provided, or empty string if missing",
  "detected_format": "Any output format specified, or empty string if missing",
  "detected_audience": "Target audience if mentioned, or empty string if missing",
  "detected_tone": "Tone/style if mentioned, or empty string if missing",
  "detected_constraints": ["list of constraints found"],
  "gaps": ["list of missing elements that would improve the prompt"],
  "scores": {{
    "clarity": <1-10>,
    "specificity": <1-10>,
    "structure": <1-10>,
    "actionability": <1-10>
  }},
  "score_explanations": {{
    "clarity": "1-2 sentence explanation of why this score",
    "specificity": "1-2 sentence explanation of why this score",
    "structure": "1-2 sentence explanation of why this score",
    "actionability": "1-2 sentence explanation of why this score"
  }},
  "improvement_suggestions": ["list of specific suggestions to improve the prompt"]
}}

{_build_scoring_rubric()}

{_SCORING_EXAMPLES}

Be thorough. Common gaps include: missing role/persona, no output format, vague task description,
no constraints or boundaries, missing context, no examples, unclear audience, unspecified tone.
Always return valid JSON.
"""


def analyze_prompt(client: LLMClient, prompt_text: str) -> dict[str, Any]:
    """Analyze a prompt and return structured analysis with gaps and scores.

    Args:
        client: Azure OpenAI client.
        prompt_text: The user's raw prompt to analyze.

    Returns:
        Analysis dict with detected components, gaps, scores, and suggestions.
    """
    messages = [
        {"role": "system", "content": ANALYSIS_SYSTEM_PROMPT},
        {"role": "user", "content": f"Analyze this prompt:\n\n{prompt_text}"},
    ]
    result = client.chat_json(messages, temperature=0.3)
    try:
        AnalysisResult.model_validate(result)
    except ValidationError as exc:
        console.print(f"[yellow]Warning: analysis response failed validation: {exc}[/yellow]")
    return result


IMPROVEMENT_SYSTEM_PROMPT = f"""\
You are an expert prompt engineer. Given a prompt and its analysis, produce an improved version.
Return a JSON object:

{{
  "improved_prompt": "The full improved prompt text",
  "changes_made": ["list of changes/improvements applied"],
  "new_scores": {{
    "clarity": <1-10>,
    "specificity": <1-10>,
    "structure": <1-10>,
    "actionability": <1-10>
  }},
  "score_explanations": {{
    "clarity": "1-2 sentence explanation of why this score",
    "specificity": "1-2 sentence explanation of why this score",
    "structure": "1-2 sentence explanation of why this score",
    "actionability": "1-2 sentence explanation of why this score"
  }}
}}

{_build_scoring_rubric()}

The improved prompt should:
- Include a clear role/persona if appropriate
- Provide necessary context
- State the task clearly and specifically
- Specify the desired output format
- Include relevant constraints
- Be well-structured with clear sections
Always return valid JSON.
"""


def improve_prompt(client: LLMClient, prompt_text: str, analysis: dict[str, Any]) -> dict[str, Any]:
    """Generate an improved version of a prompt based on analysis.

    Args:
        client: Azure OpenAI client.
        prompt_text: The original prompt.
        analysis: The analysis dict from analyze_prompt().

    Returns:
        Dict with improved_prompt, changes_made, and new_scores.
    """
    messages = [
        {"role": "system", "content": IMPROVEMENT_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"Original prompt:\n{prompt_text}\n\n"
                f"Analysis:\n{json.dumps(analysis, indent=2)}\n\n"
                "Please produce an improved version."
            ),
        },
    ]
    result = client.chat_json(messages, temperature=0.5)
    try:
        ImprovementResult.model_validate(result)
    except ValidationError as exc:
        console.print(f"[yellow]Warning: improvement response failed validation: {exc}[/yellow]")
    return result

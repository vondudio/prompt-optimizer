"""Prompt analyzer — evaluates a prompt and identifies gaps."""

import json
from typing import Any

from prompt_optimizer.client import LLMClient

ANALYSIS_SYSTEM_PROMPT = """\
You are an expert prompt engineer. Analyze the user's prompt and return a JSON object with the following structure:

{
  "summary": "Brief summary of what the prompt is asking for",
  "detected_role": "The role/persona detected, or empty string if missing",
  "detected_task": "The core task detected",
  "detected_context": "Any context provided, or empty string if missing",
  "detected_format": "Any output format specified, or empty string if missing",
  "detected_audience": "Target audience if mentioned, or empty string if missing",
  "detected_tone": "Tone/style if mentioned, or empty string if missing",
  "detected_constraints": ["list of constraints found"],
  "gaps": ["list of missing elements that would improve the prompt"],
  "scores": {
    "clarity": <1-10>,
    "specificity": <1-10>,
    "structure": <1-10>,
    "actionability": <1-10>
  },
  "improvement_suggestions": ["list of specific suggestions to improve the prompt"]
}

Be thorough. Common gaps include: missing role/persona, no output format, vague task description,
no constraints or boundaries, missing context, no examples, unclear audience, unspecified tone.
Always return valid JSON.
"""


def analyze_prompt(client: LLMClient, prompt_text: str) -> dict[str, Any]:
    """Analyze a prompt and return structured analysis with gaps and scores.

    Args:
        client: LLM client (Azure or Local).
        prompt_text: The user's raw prompt to analyze.

    Returns:
        Analysis dict with detected components, gaps, scores, and suggestions.
    """
    messages = [
        {"role": "system", "content": ANALYSIS_SYSTEM_PROMPT},
        {"role": "user", "content": f"Analyze this prompt:\n\n{prompt_text}"},
    ]
    return client.chat_json(messages, temperature=0.3)


IMPROVEMENT_SYSTEM_PROMPT = """\
You are an expert prompt engineer. Given a prompt and its analysis, produce an improved version.
Return a JSON object:

{
  "improved_prompt": "The full improved prompt text",
  "changes_made": ["list of changes/improvements applied"],
  "new_scores": {
    "clarity": <1-10>,
    "specificity": <1-10>,
    "structure": <1-10>,
    "actionability": <1-10>
  }
}

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
        client: LLM client (Azure or Local).
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
    return client.chat_json(messages, temperature=0.5)

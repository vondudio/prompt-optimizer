"""Prompt templates and assembly logic.

Uses the structure: Role → Context → Task → Format → Constraints → Examples
"""

from dataclasses import dataclass, field


@dataclass
class PromptComponents:
    """Individual components that make up a well-structured prompt."""
    role: str = ""
    context: str = ""
    task: str = ""
    output_format: str = ""
    constraints: list[str] = field(default_factory=list)
    examples: list[str] = field(default_factory=list)
    tone: str = ""
    audience: str = ""


def assemble_prompt(components: PromptComponents) -> str:
    """Assemble a structured prompt from individual components.

    Args:
        components: The prompt building blocks.

    Returns:
        A formatted, optimized prompt string.
    """
    sections: list[str] = []

    if components.role:
        sections.append(f"You are {components.role}.")

    if components.context:
        sections.append(f"**Context:** {components.context}")

    if components.audience:
        sections.append(f"**Audience:** {components.audience}")

    if components.task:
        sections.append(f"**Task:** {components.task}")

    if components.output_format:
        sections.append(f"**Output Format:** {components.output_format}")

    if components.tone:
        sections.append(f"**Tone:** {components.tone}")

    if components.constraints:
        constraint_lines = "\n".join(f"- {c}" for c in components.constraints)
        sections.append(f"**Constraints:**\n{constraint_lines}")

    if components.examples:
        example_lines = "\n\n".join(
            f"**Example {i+1}:**\n{ex}" for i, ex in enumerate(components.examples)
        )
        sections.append(f"**Examples:**\n{example_lines}")

    return "\n\n".join(sections)


# Dimension descriptions used for scoring prompts
SCORING_DIMENSIONS = {
    "clarity": "How clear and unambiguous is the prompt? (1=very vague, 10=crystal clear)",
    "specificity": "How specific is the prompt about what it wants? (1=generic, 10=very detailed)",
    "structure": "How well-organized is the prompt? (1=stream of consciousness, 10=perfectly structured)",
    "actionability": "How actionable is the prompt for an AI? (1=unclear what to do, 10=immediately executable)",
}

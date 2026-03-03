"""Tests for the templates module."""

from prompt_optimizer.templates import PromptComponents, assemble_prompt


def test_assemble_empty_components():
    """Assembling with no components produces empty string."""
    components = PromptComponents()
    result = assemble_prompt(components)
    assert result == ""


def test_assemble_role_only():
    """A role-only prompt starts with 'You are ...'."""
    components = PromptComponents(role="a senior Python developer")
    result = assemble_prompt(components)
    assert result == "You are a senior Python developer."


def test_assemble_full_prompt():
    """Full prompt contains all sections in correct order."""
    components = PromptComponents(
        role="a technical writer",
        context="We are building a REST API for a todo app.",
        task="Write API documentation for the POST /todos endpoint.",
        output_format="Markdown with code examples",
        constraints=["Keep it under 500 words", "Include error responses"],
        audience="Junior developers",
        tone="Friendly and approachable",
    )
    result = assemble_prompt(components)

    assert "You are a technical writer." in result
    assert "**Context:**" in result
    assert "**Task:**" in result
    assert "**Output Format:** Markdown with code examples" in result
    assert "**Audience:** Junior developers" in result
    assert "**Tone:** Friendly and approachable" in result
    assert "- Keep it under 500 words" in result
    assert "- Include error responses" in result


def test_assemble_with_examples():
    """Examples are numbered correctly."""
    components = PromptComponents(
        task="Translate text",
        examples=["Input: Hello → Output: Hola", "Input: Goodbye → Output: Adiós"],
    )
    result = assemble_prompt(components)
    assert "**Example 1:**" in result
    assert "**Example 2:**" in result


def test_assemble_constraints_as_list():
    """Constraints render as bullet list."""
    components = PromptComponents(
        task="Summarize",
        constraints=["Max 100 words", "Use bullet points", "No jargon"],
    )
    result = assemble_prompt(components)
    assert result.count("- ") == 3

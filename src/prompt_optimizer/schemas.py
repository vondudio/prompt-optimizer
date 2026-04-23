"""Pydantic models for validating LLM response schemas."""

from pydantic import BaseModel, Field


class Scores(BaseModel):
    """Prompt quality scores across 4 dimensions."""
    clarity: int = Field(ge=1, le=10)
    specificity: int = Field(ge=1, le=10)
    structure: int = Field(ge=1, le=10)
    actionability: int = Field(ge=1, le=10)


class ScoreExplanations(BaseModel):
    """Per-dimension explanations for scores."""
    clarity: str = ""
    specificity: str = ""
    structure: str = ""
    actionability: str = ""


class AnalysisResult(BaseModel):
    """Response from prompt analysis."""
    summary: str
    detected_role: str = ""
    detected_task: str = ""
    detected_context: str = ""
    detected_format: str = ""
    detected_audience: str = ""
    detected_tone: str = ""
    detected_constraints: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    scores: Scores
    score_explanations: ScoreExplanations = Field(default_factory=ScoreExplanations)
    improvement_suggestions: list[str] = Field(default_factory=list)


class ImprovementResult(BaseModel):
    """Response from prompt improvement."""
    improved_prompt: str
    changes_made: list[str] = Field(default_factory=list)
    new_scores: Scores


class Question(BaseModel):
    """A single follow-up question."""
    id: str
    question: str
    purpose: str = ""
    suggestions: list[str] = Field(default_factory=list)


class QuestionSet(BaseModel):
    """Response from question generation."""
    questions: list[Question] = Field(default_factory=list)


class AssemblyResult(BaseModel):
    """Response from prompt assembly."""
    optimized_prompt: str
    scores: Scores
    summary: str = ""

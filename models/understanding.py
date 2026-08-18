"""Schemas for requirement understanding and clarification."""

from pydantic import BaseModel, Field


class ClarificationQuestion(BaseModel):
    """Represents a question used to clarify information that affects the product proposal."""

    question: str
    reason: str


class RequirementUnderstandingResult(BaseModel):
    """Captures the structured result of understanding an initial product requirement."""

    known_facts: list[str] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    need_clarification: bool
    questions: list[ClarificationQuestion] = Field(default_factory=list)

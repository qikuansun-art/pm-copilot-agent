"""Structured research planning models for PM Copilot."""

from pydantic import BaseModel, Field


class ResearchPlan(BaseModel):
    """Defines focused internal and external research for a product task."""

    internal_query: str
    external_query: str
    research_focus: list[str] = Field(default_factory=list)

"""Schema for the finalized PM Copilot product plan."""

from pydantic import BaseModel, Field


class FinalProductPlan(BaseModel):
    """Represents the review-ready final product MVP plan."""

    title: str
    summary: str
    problems: list[str] = Field(default_factory=list)
    target_users: list[str] = Field(default_factory=list)
    key_scenarios: list[str] = Field(default_factory=list)
    requirements: list[str] = Field(default_factory=list)
    solution: list[str] = Field(default_factory=list)
    mvp_scope: list[str] = Field(default_factory=list)
    future_scope: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    decisions: list[str] = Field(default_factory=list)

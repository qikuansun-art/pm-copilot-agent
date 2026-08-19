"""Schemas returned by the focused product-plan revision service."""

from pydantic import BaseModel, Field

from models.final_output import FinalProductPlan


class PlanRevisionResult(BaseModel):
    """Contains a revised plan and a concise explanation of its changes."""

    revised_plan: FinalProductPlan
    revision_summary: list[str] = Field(default_factory=list)

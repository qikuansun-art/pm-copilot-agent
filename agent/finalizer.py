"""Deterministic final product-plan generation for PM Copilot."""

from models.final_output import FinalProductPlan
from models.state import AgentState


class ProductPlanFinalizer:
    """Transforms reviewed product analysis into the final product plan."""

    def finalize(self, state: AgentState) -> FinalProductPlan:
        """Build a final plan from the task analysis and recorded decisions."""
        if state.analysis is None:
            raise ValueError("Product analysis is required before finalization")

        decisions = [
            (
                f"{item.decision}（原因：{item.reason}）"
                if item.reason
                else item.decision
            )
            for item in state.decisions
        ]

        return FinalProductPlan(
            title=state.task.title,
            summary="基于需求澄清、内部资料、外部调研和产品分析形成的 MVP 产品方案。",
            problems=state.analysis.problems,
            target_users=state.analysis.users,
            key_scenarios=state.analysis.scenarios,
            requirements=state.analysis.requirements,
            solution=state.analysis.solution,
            mvp_scope=state.analysis.mvp_scope,
            future_scope=state.analysis.future_scope,
            risks=state.analysis.risks,
            decisions=decisions,
        )

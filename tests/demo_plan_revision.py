"""Demonstrate focused V1-to-V3 plan revision without research reruns."""

import json

from agent.plan_reviser import ProductPlanReviser
from agent.runtime import PMCopilotRuntime
from models.final_output import FinalProductPlan
from models.state import (
    AgentStage,
    AgentState,
    Decision,
    Evidence,
    ProductAnalysis,
    TaskContext,
)


class SequenceLLMClient:
    """Return prepared revisions and retain prompts for lineage assertions."""

    def __init__(self, responses: list[dict]) -> None:
        self.responses = responses
        self.user_prompts: list[str] = []

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        self.user_prompts.append(user_prompt)
        return json.dumps(self.responses[len(self.user_prompts) - 1], ensure_ascii=False)


def plan(
    *,
    target_users: list[str] | None = None,
    mvp_scope: list[str] | None = None,
    future_scope: list[str] | None = None,
) -> FinalProductPlan:
    """Build a complete plan with stable unrelated fields."""
    return FinalProductPlan(
        title="刀具管理系统",
        summary="建立统一的刀具管理能力。",
        problems=["刀具状态不可追踪"],
        target_users=target_users or ["工艺人员", "设备操作员"],
        key_scenarios=["工艺配置", "加工执行"],
        requirements=["建立工艺和刀具关联", "统计刀具寿命"],
        solution=["建设刀具台账"],
        mvp_scope=mvp_scope or ["刀具管理", "刀具寿命", "自动换刀"],
        future_scope=future_scope or [],
        risks=["历史数据质量不一致"],
        decisions=["寿命按累计加工时长统计"],
    )


def revision_payload(revised_plan: FinalProductPlan, summary: list[str]) -> dict:
    return {
        "revised_plan": revised_plan.model_dump(),
        "revision_summary": summary,
    }


def main() -> None:
    """Cover scoped MVP edits, target-user edits, and sequential lineage."""
    v1 = plan()
    v2 = plan(
        mvp_scope=["刀具管理", "刀具寿命"],
        future_scope=["自动换刀"],
    )
    v3 = plan(
        target_users=["工艺人员", "设备操作员", "仓库管理员"],
        mvp_scope=["刀具管理", "刀具寿命"],
        future_scope=["自动换刀"],
    )
    client = SequenceLLMClient(
        [
            revision_payload(
                v2,
                ["自动换刀已从 MVP Scope 移至 Future Scope。"],
            ),
            revision_payload(
                v3,
                ["目标用户新增仓库管理员。"],
            ),
        ]
    )
    reviser = ProductPlanReviser.__new__(ProductPlanReviser)
    reviser.llm_client = client
    runtime = PMCopilotRuntime.__new__(PMCopilotRuntime)
    runtime.plan_reviser = reviser

    state = AgentState(
        task=TaskContext(
            task_id="plan-revision-demo",
            title="刀具管理系统",
            original_request="规划刀具管理系统",
            current_stage=AgentStage.WAITING_REVIEW,
        ),
        evidence=[
            Evidence(
                content="寿命按累计加工时长统计",
                source_type="uploaded_document",
                source="tool_management.md",
            )
        ],
        analysis=ProductAnalysis(
            problems=v1.problems,
            users=v1.target_users,
            requirements=v1.requirements,
            mvp_scope=v1.mvp_scope,
        ),
        decisions=[Decision(decision="寿命按累计加工时长统计")],
        final_output=v1,
    )

    feedback_a = "自动换刀第一版先不要做。"
    state = runtime.handle_review(state, approved=False, feedback=feedback_a)
    assert state.final_output is not None
    assert "自动换刀" not in state.final_output.mvp_scope
    assert "自动换刀" in state.final_output.future_scope
    assert all(item.decision != feedback_a for item in state.decisions)
    assert state.final_output.problems == v1.problems
    assert state.review_feedback[0].version_from == 1
    assert state.review_feedback[0].version_to == 2

    feedback_b = "目标用户增加仓库管理员。"
    state = runtime.handle_review(state, approved=False, feedback=feedback_b)
    assert state.task.plan_version == 3
    assert "仓库管理员" in state.final_output.target_users
    assert state.final_output.problems == v2.problems
    assert state.final_output.requirements == v2.requirements
    assert state.final_output.mvp_scope == v2.mvp_scope
    assert len(state.review_feedback) == 2
    assert state.review_feedback[1].version_from == 2
    assert state.review_feedback[1].version_to == 3
    assert state.review_feedback[1].revision_summary == ["目标用户新增仓库管理员。"]

    second_revision_context = client.user_prompts[1]
    assert '"future_scope": ["自动换刀"]' in second_revision_context
    assert '"mvp_scope": ["刀具管理", "刀具寿命"]' in second_revision_context

    print("V2 MVP:", v2.mvp_scope)
    print("V2 Future Scope:", v2.future_scope)
    print("V3 Target Users:", state.final_output.target_users)
    print("Review History:", state.review_feedback)


if __name__ == "__main__":
    main()

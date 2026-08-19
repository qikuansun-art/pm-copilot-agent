"""Demonstrate adding a condition to a completed plan without a new task."""

from models.final_output import FinalProductPlan
from models.revision import PlanRevisionResult
from models.state import AgentStage, AgentState, Evidence, TaskContext, ToolCall
from agent.runtime import PMCopilotRuntime


class AddedConditionReviser:
    """Return a deterministic targeted revision for the completed-task demo."""

    def revise(self, state, feedback):
        current = state.final_output.model_copy(deep=True)
        current.target_users.append("仓库管理员")
        current.key_scenarios.append("仓库管理员维护刀具出入库")
        current.requirements.append("支持仓库管理员维护刀具库存")
        return PlanRevisionResult(
            revised_plan=current,
            revision_summary=[
                "Target Users 新增仓库管理员。",
                "相关 Scenario 和 Requirements 已同步补充。",
            ],
        )


def main() -> None:
    """Verify COMPLETED V2 becomes review-ready V3 on the same task."""
    task_id = "completed-revision-demo"
    state = AgentState(
        task=TaskContext(
            task_id=task_id,
            title="刀具管理方案",
            original_request="规划刀具管理系统",
            current_stage=AgentStage.COMPLETED,
            plan_version=2,
        ),
        final_output=FinalProductPlan(
            title="刀具管理方案",
            summary="当前已批准方案",
            target_users=["工艺人员", "设备操作员"],
            key_scenarios=["工艺配置"],
            requirements=["工艺与刀具关联"],
            mvp_scope=["刀具管理", "刀具寿命"],
        ),
        evidence=[
            Evidence(
                content="刀具需要出入库管理",
                source_type="uploaded_document",
                source="tool_management.md",
            )
        ],
        tool_calls=[ToolCall(tool_name="knowledge_search", status="completed")],
    )
    original_evidence = list(state.evidence)
    original_tool_calls = list(state.tool_calls)
    runtime = PMCopilotRuntime.__new__(PMCopilotRuntime)
    runtime.plan_reviser = AddedConditionReviser()

    revised = runtime.revise_completed_task(
        state,
        "增加仓库管理员作为目标用户",
    )

    assert revised.task.task_id == task_id
    assert revised.task.plan_version == 3
    assert revised.task.current_stage == AgentStage.WAITING_REVIEW
    assert revised.evidence == original_evidence
    assert revised.tool_calls == original_tool_calls
    assert "仓库管理员" in revised.final_output.target_users
    assert revised.review_feedback[-1].revision_type == "added_condition"
    assert revised.review_feedback[-1].version_from == 2
    assert revised.review_feedback[-1].version_to == 3
    assert len(revised.review_feedback[-1].revision_summary) == 2

    print("task_id:", revised.task.task_id)
    print("stage:", revised.task.current_stage.value)
    print("version:", revised.task.plan_version)
    print("history:", revised.review_feedback[-1])


if __name__ == "__main__":
    main()

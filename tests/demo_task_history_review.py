"""Demonstrate persistent task history and iterative review versions."""

from pathlib import Path

from agent.finalizer import ProductPlanFinalizer
from agent.runtime import PMCopilotRuntime
from api.task_store import TaskStore
from models.state import AgentStage, AgentState, ProductAnalysis, TaskContext
from models.revision import PlanRevisionResult


class NoopReviser:
    """Return the current plan while exercising review history persistence."""

    def revise(self, state, feedback):
        return PlanRevisionResult(
            revised_plan=state.final_output,
            revision_summary=[f"已处理修改意见：{feedback}"],
        )


def main() -> None:
    """Verify V1-to-V3 review revisions and SQLite state restoration."""
    test_db_path = Path("data/test_tasks.db")
    if test_db_path.exists():
        test_db_path.unlink()

    try:
        store = TaskStore(test_db_path)
        state = AgentState(
            task=TaskContext(
                task_id="review-history-demo",
                title="刀具管理方案",
                original_request="规划刀具管理功能",
                current_stage=AgentStage.WAITING_REVIEW,
                knowledge_group_ids=["tooling-group"],
            ),
            analysis=ProductAnalysis(
                problems=["刀具状态不可追踪"],
                solution=["建立刀具台账与寿命管理"],
            ),
        )
        runtime = PMCopilotRuntime.__new__(PMCopilotRuntime)
        runtime.finalizer = ProductPlanFinalizer()
        runtime.plan_reviser = NoopReviser()
        state.final_output = runtime.finalizer.finalize(state)

        state = runtime.handle_review(state, False, "增加换刀审批流程")
        assert state.task.current_stage == AgentStage.WAITING_REVIEW
        assert state.task.plan_version == 2
        assert state.review_feedback[-1].version == 2

        state = runtime.handle_review(state, False, "补充寿命预警")
        assert state.task.current_stage == AgentStage.WAITING_REVIEW
        assert state.task.plan_version == 3
        assert len(state.review_feedback) == 2

        store.save(state)
        restored = TaskStore(test_db_path).get(state.task.task_id)
        assert restored is not None
        assert restored.task.plan_version == 3
        assert restored.task.knowledge_group_ids == ["tooling-group"]
        assert len(restored.review_feedback) == 2
        assert restored.final_output is not None

        restored = runtime.handle_review(restored, True)
        store.save(restored)
        assert restored.task.current_stage == AgentStage.COMPLETED
        assert TaskStore(test_db_path).get(restored.task.task_id) is not None
        print("restored stage:", restored.task.current_stage.value)
        print("plan version:", restored.task.plan_version)
        print("review feedback:", restored.review_feedback)
    finally:
        if test_db_path.exists():
            test_db_path.unlink()


if __name__ == "__main__":
    main()

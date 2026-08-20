"""Regression coverage for persisted task history and plan-step statuses."""

from pathlib import Path

from agent.finalizer import ProductPlanFinalizer
from agent.runtime import PMCopilotRuntime
from api.task_store import TaskStore
from models.revision import PlanRevisionResult
from models.state import AgentPlan, AgentStage, AgentState, PlanStep, ProductAnalysis, TaskContext


class NoopReviser:
    """Return the current plan while exercising revision transitions."""

    def revise(self, state, feedback):
        return PlanRevisionResult(
            revised_plan=state.final_output,
            revision_summary=[f"已处理修改意见：{feedback}"],
        )


def main() -> None:
    """Verify review and completed revisions survive SQLite restoration."""
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
            plan=AgentPlan(
                goal="创建刀具管理方案",
                steps=[
                    PlanStep(id=1, title="理解需求", status="completed"),
                    PlanStep(id=2, title="需求澄清", status="completed"),
                    PlanStep(id=3, title="资料调研", status="running"),
                    PlanStep(id=4, title="产品分析", status="pending"),
                    PlanStep(id=5, title="最终方案", status="running"),
                ],
            ),
        )
        runtime = PMCopilotRuntime.__new__(PMCopilotRuntime)
        runtime.finalizer = ProductPlanFinalizer()
        runtime.plan_reviser = NoopReviser()
        state.final_output = runtime.finalizer.finalize(state)

        state = runtime.handle_review(state, False, "增加换刀审批流程")
        assert state.task.current_stage == AgentStage.WAITING_REVIEW
        assert state.task.plan_version == 2
        assert [step.status for step in state.plan.steps] == [
            "completed", "completed", "completed", "completed", "running"
        ]

        state = runtime.handle_review(state, True)
        assert state.task.current_stage == AgentStage.COMPLETED
        assert all(step.status == "completed" for step in state.plan.steps)

        state = runtime.revise_completed_task(state, "补充寿命预警")
        assert state.task.current_stage == AgentStage.WAITING_REVIEW
        assert state.task.plan_version == 3
        assert state.review_feedback[-1].revision_type == "added_condition"
        assert [step.status for step in state.plan.steps] == [
            "completed", "completed", "completed", "completed", "running"
        ]
        state = runtime.handle_review(state, True)
        assert state.task.current_stage == AgentStage.COMPLETED
        assert all(step.status == "completed" for step in state.plan.steps)

        store.save(state)
        restored = TaskStore(test_db_path).get(state.task.task_id)
        assert restored is not None
        assert restored.task.current_stage == AgentStage.COMPLETED
        assert restored.task.plan_version == 3
        assert all(step.status == "completed" for step in restored.plan.steps)

        import api.main as api_main

        original_store = api_main.task_store
        original_tasks = api_main.tasks
        try:
            api_main.task_store = TaskStore(test_db_path)
            api_main.tasks = {}
            response = api_main.get_task(restored.task.task_id)
        finally:
            api_main.task_store = original_store
            api_main.tasks = original_tasks

        assert response["task"]["current_stage"] == "COMPLETED"
        assert response["task"]["plan_version"] == 3
        assert all(step["status"] == "completed" for step in response["plan"]["steps"])
        print("restored stage:", restored.task.current_stage.value)
        print("plan version:", restored.task.plan_version)
        print("plan statuses:", [step.status for step in restored.plan.steps])
    finally:
        if test_db_path.exists():
            test_db_path.unlink()


if __name__ == "__main__":
    main()

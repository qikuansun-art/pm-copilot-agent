"""Demonstrate approved and feedback-based human review finalization."""

from agent.runtime import PMCopilotRuntime
from models.state import AgentStage, AgentState, Message, TaskContext


def build_review_state(task_id: str) -> tuple[PMCopilotRuntime, AgentState]:
    """Build a complete CNC task in the waiting-review stage."""
    state = AgentState(
        task=TaskContext(
            task_id=task_id,
            title="CNC 刀具管理规划",
            original_request="帮我规划一个 CNC 刀具管理功能",
        ),
        messages=[
            Message(role="user", content="帮我规划一个 CNC 刀具管理功能")
        ],
    )
    runtime = PMCopilotRuntime()
    runtime.start_task(state)
    runtime.handle_clarification_response(
        state,
        "目前完全没有系统化刀具管理，主要想解决工艺和刀具关联以及寿命管理，"
        "主要使用者是工艺人员和设备操作员。",
    )
    runtime.create_plan(state)
    runtime.run_internal_research(state, "刀具 自动换刀 寿命")
    runtime.run_external_research(state, "CNC 刀具管理 tool life")
    runtime.run_product_analysis(state)
    assert state.task.current_stage == AgentStage.WAITING_REVIEW
    return runtime, state


def main() -> None:
    """Run and validate both requested human-review scenarios."""
    approved_runtime, approved_state = build_review_state("approved-demo")
    approved_result = approved_runtime.handle_review(approved_state, approved=True)
    approved_plan_step = next(
        step for step in approved_result.plan.steps if step.title == "生成产品方案"
    )
    assert approved_result.task.current_stage == AgentStage.COMPLETED
    assert approved_result.final_output is not None
    assert approved_plan_step.status == "completed"
    print("场景1 current_stage:", approved_result.task.current_stage)
    print("场景1 final_output:", approved_result.final_output)
    print("场景1 生成产品方案:", approved_plan_step.status)

    feedback_runtime, feedback_state = build_review_state("feedback-demo")
    feedback = "自动换刀不要进入 MVP，刀具库存也先不做。"
    feedback_result = feedback_runtime.handle_review(
        feedback_state,
        approved=False,
        feedback=feedback,
    )
    assert feedback_result.messages[-1].content == feedback
    assert feedback_result.decisions[-1].decision == feedback
    assert feedback_result.final_output is not None
    assert any(feedback in item for item in feedback_result.final_output.decisions)
    assert feedback_result.task.current_stage == AgentStage.COMPLETED
    print("场景2 current_stage:", feedback_result.task.current_stage)
    print("场景2 last_message:", feedback_result.messages[-1])
    print("场景2 decision:", feedback_result.decisions[-1])
    print("场景2 final decisions:", feedback_result.final_output.decisions)


if __name__ == "__main__":
    main()

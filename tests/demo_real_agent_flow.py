"""Demonstrate the complete PM Copilot flow with configured real LLM services."""

from agent.runtime import PMCopilotRuntime
from models.state import AgentStage, AgentState, Decision, Message, TaskContext


def main() -> None:
    """Run a CNC tool-management task from creation through finalization."""
    request = "帮我规划一个 CNC 刀具管理功能"
    state = AgentState(
        task=TaskContext(
            task_id="real-agent-flow-demo",
            title="CNC 刀具管理规划",
            original_request=request,
        ),
        messages=[Message(role="user", content=request)],
    )
    runtime = PMCopilotRuntime()

    runtime.start_task(state)
    print("start_task stage:", state.task.current_stage)
    print("clarification questions:")
    for message in state.messages:
        if message.role == "assistant":
            print("-", message.content)

    runtime.handle_clarification_response(
        state,
        "目前完全没有系统化刀具管理，主要想解决工艺和刀具关联以及寿命管理，"
        "主要使用者是工艺人员和设备操作员，自动换刀第一版暂不考虑。",
    )
    state.decisions.append(
        Decision(
            decision="自动换刀暂不进入 MVP",
            decided_by="user",
        )
    )

    runtime.create_plan(state)
    runtime.run_internal_research(state, "刀具 自动换刀 寿命 工艺")
    runtime.run_external_research(state, "CNC 刀具管理 tool life")
    runtime.run_product_analysis(state)

    print("plan:", state.plan)
    print("evidence count:", len(state.evidence))
    print("problems:", state.analysis.problems)
    print("mvp_scope:", state.analysis.mvp_scope)
    print("future_scope:", state.analysis.future_scope)

    runtime.handle_review(state, approved=True)
    assert state.task.current_stage == AgentStage.COMPLETED

    print("current_stage:", state.task.current_stage)
    print("final_output.title:", state.final_output.title)
    print("final_output.summary:", state.final_output.summary)
    print("final_output.mvp_scope:", state.final_output.mvp_scope)
    print("final_output.future_scope:", state.final_output.future_scope)


if __name__ == "__main__":
    main()

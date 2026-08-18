"""Demonstrate structured product analysis after research."""

from agent.runtime import PMCopilotRuntime
from models.state import AgentState, Message, TaskContext


def main() -> None:
    """Run the complete CNC task flow through product analysis."""
    state = AgentState(
        task=TaskContext(
            task_id="product-analysis-demo",
            title="CNC 刀具管理规划",
            original_request="帮我规划一个 CNC 刀具管理功能",
        ),
        messages=[
            Message(
                role="user",
                content="帮我规划一个 CNC 刀具管理功能",
            )
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
    result = runtime.run_product_analysis(state)

    print("current_stage:", result.task.current_stage)
    print("plan.steps:")
    for step in result.plan.steps:
        print(step)

    analysis = result.analysis
    print("analysis.problems:", analysis.problems)
    print("analysis.users:", analysis.users)
    print("analysis.scenarios:", analysis.scenarios)
    print("analysis.requirements:", analysis.requirements)
    print("analysis.solution:", analysis.solution)
    print("analysis.mvp_scope:", analysis.mvp_scope)
    print("analysis.future_scope:", analysis.future_scope)
    print("analysis.risks:", analysis.risks)


if __name__ == "__main__":
    main()

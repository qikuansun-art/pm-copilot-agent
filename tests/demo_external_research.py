"""Demonstrate external research becoming evidence in AgentState."""

from agent.runtime import PMCopilotRuntime
from models.state import AgentState, Message, TaskContext


def main() -> None:
    """Run the CNC task through internal and external research."""
    state = AgentState(
        task=TaskContext(
            task_id="external-research-demo",
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
    result = runtime.run_external_research(state, "CNC 刀具管理 tool life")

    print("current_stage:", result.task.current_stage)
    print("plan.steps:")
    for step in result.plan.steps:
        print(step)
    print("tool_calls:", result.tool_calls)
    print("evidence:", result.evidence)


if __name__ == "__main__":
    main()

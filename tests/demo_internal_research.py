"""Demonstrate converting internal knowledge search results into evidence."""

from agent.runtime import PMCopilotRuntime
from models.state import AgentState, Message, TaskContext


def main() -> None:
    """Run the CNC task through internal research and print its state."""
    state = AgentState(
        task=TaskContext(
            task_id="internal-research-demo",
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
    result = runtime.run_internal_research(state, "刀具 自动换刀 寿命")

    print("current_stage:", result.task.current_stage)
    print("plan.steps:")
    for step in result.plan.steps:
        print(step)
    print("tool_calls:", result.tool_calls)
    print("evidence:", result.evidence)


if __name__ == "__main__":
    main()

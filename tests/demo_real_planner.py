"""Demonstrate product planning with the configured real LLM."""

from agent.planner import PMPlanner
from models.state import AgentState, Decision, TaskContext


def main() -> None:
    """Generate and print a real LLM plan for the CNC task."""
    state = AgentState(
        task=TaskContext(
            task_id="real-planner-demo",
            title="CNC 刀具管理规划",
            original_request="帮我规划一个 CNC 刀具管理功能",
            known_facts=[
                "当前完全没有系统化刀具管理",
                "主要目标是建立工艺和刀具关联",
                "需要管理刀具寿命",
                "主要使用者是工艺人员和设备操作员",
            ],
            missing_information=[],
        ),
        decisions=[Decision(decision="自动换刀暂不进入 MVP")],
    )

    planner = PMPlanner()
    plan = planner.create_plan(state)

    print("goal:", plan.goal)
    print("steps:")
    for step in plan.steps:
        print("- id:", step.id)
        print("  title:", step.title)
        print("  status:", step.status)


if __name__ == "__main__":
    main()

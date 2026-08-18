"""LLM-powered product-task planner for PM Copilot."""

import json

from pydantic import ValidationError

from llm.client import LLMClient, create_llm_client
from llm.config import LLMConfig
from models.state import AgentPlan, AgentState


class PMPlanner:
    """Creates a structured product task plan with the configured LLM."""

    def __init__(self) -> None:
        """Initialize the configured LLM client."""
        config = LLMConfig.from_env()
        self.llm_client: LLMClient = create_llm_client(config)

    def create_plan(self, state: AgentState) -> AgentPlan:
        """Generate and validate a product plan for the current task."""
        system_prompt = """你是一名专业产品经理，负责为产品需求制定任务计划。
你必须只返回合法 JSON，不要输出 Markdown，也不要输出 JSON 之外的说明文字。
JSON 结构必须严格为：
{
  "goal": "...",
  "steps": [
    {
      "id": 1,
      "title": "...",
      "status": "..."
    }
  ]
}
规划规则：
1. 总步骤必须为 5～7 步，id 从 1 开始依次递增。
2. 必须保留“理解需求”和“需求澄清”，并将它们标记为 completed。
3. 后续步骤根据当前产品任务自主规划。
4. 计划必须包含资料调研、产品分析和最终方案。
5. 不要规划代码开发、数据库设计或其他与产品方案无关的任务。
6. status 只能是 completed 或 pending；未执行的后续步骤使用 pending。"""
        context = {
            "original_request": state.task.original_request,
            "known_facts": state.task.known_facts,
            "missing_information": state.task.missing_information,
            "decisions": [item.model_dump() for item in state.decisions],
        }
        user_prompt = "请根据以下任务上下文生成产品任务计划：\n" + json.dumps(
            context,
            ensure_ascii=False,
        )

        response = self.llm_client.generate(system_prompt, user_prompt)
        try:
            plan = AgentPlan.model_validate(json.loads(response))
            if not 5 <= len(plan.steps) <= 7:
                raise ValueError
            if any(step.status not in {"completed", "pending"} for step in plan.steps):
                raise ValueError
            if len(plan.steps) < 2 or (
                plan.steps[0].title != "理解需求"
                or plan.steps[0].status != "completed"
                or plan.steps[1].title != "需求澄清"
                or plan.steps[1].status != "completed"
            ):
                raise ValueError
            return plan
        except (json.JSONDecodeError, ValidationError, ValueError) as error:
            raise ValueError("Invalid LLM plan response") from error

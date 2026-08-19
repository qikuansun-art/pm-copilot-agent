"""LLM-powered research planner for PM Copilot."""

import json

from pydantic import ValidationError

from llm.client import LLMClient, create_llm_client
from llm.config import LLMConfig
from models.research import ResearchPlan
from models.state import AgentState


class ResearchPlanner:
    """Creates task-specific queries and research directions."""

    def __init__(self) -> None:
        """Initialize the configured LLM client."""
        config = LLMConfig.from_env()
        self.llm_client: LLMClient = create_llm_client(config)

    def create_research_plan(self, state: AgentState) -> ResearchPlan:
        """Generate and validate a research plan for the current task."""
        system_prompt = """你是一名产品研究规划专家，负责根据当前产品任务规划资料调研。
你必须只返回合法 JSON，不要输出 Markdown，也不要输出 JSON 之外的说明文字。
JSON 结构必须严格为：
{
  "internal_query": "...",
  "external_query": "...",
  "research_focus": ["...", "..."]
}
规则：
1. 搜索词必须根据当前任务动态生成。
2. 禁止默认使用 CNC、刀具、寿命等词，除非当前任务确实涉及这些内容。
3. internal_query 面向公司内部知识搜索，使用简洁中文关键词。
4. external_query 面向互联网行业调研，可以使用中文或英文关键词。
5. research_focus 只保留 2～4 个真正需要调研的方向。
6. 只规划需要研究的问题，不提前生成产品方案。
7. 不输出 Markdown。"""
        context = {
            "original_request": state.task.original_request,
            "known_facts": state.task.known_facts,
            "decisions": [item.model_dump() for item in state.decisions],
            "agent_plan": (
                {
                    "goal": state.plan.goal,
                    "steps": [step.model_dump() for step in state.plan.steps],
                }
                if state.plan
                else None
            ),
        }
        user_prompt = "请根据以下当前任务上下文生成资料调研计划：\n" + json.dumps(
            context,
            ensure_ascii=False,
        )

        response = self.llm_client.generate(system_prompt, user_prompt)
        try:
            research_plan = ResearchPlan.model_validate(json.loads(response))
            if not 2 <= len(research_plan.research_focus) <= 4:
                raise ValueError
            return research_plan
        except (json.JSONDecodeError, ValidationError, TypeError, ValueError) as error:
            raise ValueError("Invalid LLM research plan response") from error

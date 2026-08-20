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
3. internal_query 提供给按空格切分的简单关键词检索器，不是自然语言搜索语句。必须输出 3～6 个关键词，每个关键词之间使用一个空格分隔；不要为了数量强行补词。
4. internal_query 优先选择业务对象、核心流程、核心能力和用户明确提出的重要概念。关键词应是简短、可独立命中文档的原子业务概念，避免“管理”“系统”“功能”等宽泛词、无意义修饰词和完整自然语言句子。
5. internal_query 禁止把多个概念压缩成长复合词。例如错误：石材荒料加工流程 刀具管理 刀具寿命；推荐：石材荒料 荒料加工 大切 刀具管理 寿命。错误：设备维修工单管理流程 维修主管派单 超时提醒；推荐：设备维修 工单 派单 维修主管 超时。
6. 如果任务涉及多个业务主题，internal_query 必须用独立关键词覆盖每个主题的核心概念。例如同时涉及荒料加工和刀具管理时，必须分别包含荒料相关关键词和刀具相关关键词。
7. external_query 面向互联网行业调研，可以继续使用自然语言或中英文组合，不受 internal_query 的空格分词规则限制。
8. research_focus 只保留 2～4 个真正需要调研的方向。
9. 只规划需要研究的问题，不提前生成产品方案。
10. 不输出 Markdown。"""
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

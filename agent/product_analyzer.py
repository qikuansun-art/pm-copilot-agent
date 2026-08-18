"""LLM-powered structured product analysis for PM Copilot."""

import json

from pydantic import ValidationError

from llm.client import LLMClient, create_llm_client
from llm.config import LLMConfig
from models.state import AgentState, ProductAnalysis


class ProductAnalyzer:
    """Produces structured product analysis with the configured LLM."""

    def __init__(self) -> None:
        """Initialize the configured LLM client."""
        config = LLMConfig.from_env()
        self.llm_client: LLMClient = create_llm_client(config)

    def analyze(self, state: AgentState) -> ProductAnalysis:
        """Generate and validate product analysis for the current task."""
        system_prompt = """你是一名专业产品经理，负责基于任务事实、决策和证据进行产品分析。
你必须只返回合法 JSON，不要输出 Markdown，也不要输出 JSON 之外的说明文字。
JSON 结构必须严格为：
{
  "problems": [],
  "users": [],
  "scenarios": [],
  "requirements": [],
  "solution": [],
  "mvp_scope": [],
  "future_scope": [],
  "risks": []
}
分析原则：
1. problems 必须基于已知事实和 evidence，不得把推测写成事实。
2. users 只保留当前任务真正相关的核心角色。
3. scenarios 描述真实业务场景，不要写成页面功能。
4. requirements 应由 problem 和 scenario 推导。
5. solution 必须对应 requirements，不要无边界扩展。
6. mvp_scope 必须遵守已有 decisions。如果决策明确某功能不进入 MVP，则禁止将该功能放入 mvp_scope，但可以放入 future_scope。
7. risks 只保留真正会影响落地的风险。
8. 不要输出数据库表、接口设计、代码结构或其他开发细节。
9. 所有字段都必须存在，且值必须是字符串数组。"""
        context = {
            "original_request": state.task.original_request,
            "known_facts": state.task.known_facts,
            "assumptions": state.task.assumptions,
            "decisions": [item.model_dump() for item in state.decisions],
            "evidence": [item.model_dump() for item in state.evidence],
        }
        user_prompt = "请根据以下上下文完成产品分析：\n" + json.dumps(
            context,
            ensure_ascii=False,
        )

        response = self.llm_client.generate(system_prompt, user_prompt)
        try:
            parsed_response = json.loads(response)
            return ProductAnalysis.model_validate(parsed_response)
        except (json.JSONDecodeError, ValidationError) as error:
            raise ValueError("Invalid LLM product analysis response") from error

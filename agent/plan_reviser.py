"""LLM-powered targeted revision of an existing product plan."""

import json

from pydantic import ValidationError

from llm.client import LLMClient, create_llm_client
from llm.config import LLMConfig
from models.revision import PlanRevisionResult
from models.state import AgentState


class ProductPlanReviser:
    """Revises only the fields affected by human review feedback."""

    def __init__(self) -> None:
        config = LLMConfig.from_env()
        self.llm_client: LLMClient = create_llm_client(config)

    def revise(self, state: AgentState, feedback: str) -> PlanRevisionResult:
        """Produce the next plan version from the current final output."""
        if state.final_output is None:
            raise ValueError("Current final output is required for revision")

        system_prompt = """你是一名专业产品经理，负责根据 Human Review 定向修订已有产品方案。
你必须只返回合法 JSON，不要输出 Markdown 或 JSON 之外的文字。
JSON 结构必须严格为：
{
  "revised_plan": {
    "title": "...",
    "summary": "...",
    "problems": [],
    "target_users": [],
    "key_scenarios": [],
    "requirements": [],
    "solution": [],
    "mvp_scope": [],
    "future_scope": [],
    "risks": [],
    "decisions": []
  },
  "revision_summary": ["..."]
}
规则：
1. 这是一次方案 Revision，而不是重新进行产品规划。
2. current_final_output 是主要修改对象。保留没有被 Review Feedback 影响的字段和值，只调整相关部分。
3. 理解用户修改意图后修改对应字段，不要把用户原话机械复制到 revised_plan 或 decisions。
4. Review Feedback 是修订参考，不是已经确认的产品 Decision。不要直接把反馈原文加入 decisions。
5. 如某功能被要求移出 MVP，应在适当时移至 future_scope，并保持其他 MVP 内容不变。
6. revision_summary 用 1～5 条简洁文字说明实际改变了什么，不要只复述反馈。
7. 不重新进行需求理解、知识检索、行业调研或产品分析。"""
        context = {
            "original_request": state.task.original_request,
            "known_facts": state.task.known_facts,
            "evidence": [item.model_dump() for item in state.evidence],
            "analysis": state.analysis.model_dump() if state.analysis else None,
            "current_final_output": state.final_output.model_dump(),
            "existing_decisions": [item.model_dump() for item in state.decisions],
            "review_feedback": feedback,
        }
        response = self.llm_client.generate(
            system_prompt,
            "请定向修订以下当前方案：\n" + json.dumps(context, ensure_ascii=False),
        )
        try:
            result = PlanRevisionResult.model_validate(json.loads(response))
            if not result.revision_summary:
                raise ValueError
            return result
        except (json.JSONDecodeError, ValidationError, ValueError) as error:
            raise ValueError("Invalid LLM plan revision response") from error

"""LLM-powered structured business-flow generation."""

import json

from pydantic import BaseModel, ValidationError

from llm.client import LLMClient, create_llm_client
from llm.config import LLMConfig
from models.final_output import FinalProductPlan
from models.flow import ProductFlow


class ProductFlowResponse(BaseModel):
    """Envelope returned by the product-flow generation prompt."""

    has_flow: bool
    flow: ProductFlow | None = None


class ProductFlowGenerator:
    """Generates one primary business flow when a product plan has one."""

    def __init__(self) -> None:
        config = LLMConfig.from_env()
        self.llm_client: LLMClient = create_llm_client(config)

    def generate(
        self,
        original_request: str,
        final_output: FinalProductPlan,
    ) -> ProductFlow | None:
        """Return a structured business flow, or None when none is evident."""
        system_prompt = """你是一名产品经理，负责判断产品方案是否存在可表达的主要用户或业务流程，并在适合时生成结构化业务流程图。
你必须只返回合法 JSON，不要输出 Markdown、Mermaid 或 JSON 之外的文字。
不存在明确业务流转时返回：
{"has_flow": false}
存在明确业务流转时返回：
{
  "has_flow": true,
  "flow": {
    "title": "...",
    "description": "...",
    "nodes": [{"id": "n1", "label": "...", "node_type": "start"}],
    "edges": [{"source": "n1", "target": "n2", "label": ""}]
  }
}
生成原则：
1. 只表达业务流程，不表达技术架构、接口、数据库或系统组件。
2. 一个流程只表达一条最主要的用户或业务流程，不要堆砌全部功能模块。
3. 建议使用 4～10 个节点，节点文字简洁，尽量为 4～12 个中文字符。
4. node_type 只能是 start、step、decision、end；start 和 end 最多各一个。
5. 存在真实判断分支时可使用 decision，并使用 edge label 表达分支条件。
6. 每条 edge 的 source 和 target 必须引用 nodes 中真实存在且唯一的 id。
7. 不要为了生成流程图而虚构方案中没有的业务步骤。"""
        context = {
            "original_request": original_request,
            "final_output": {
                "problems": final_output.problems,
                "target_users": final_output.target_users,
                "key_scenarios": final_output.key_scenarios,
                "requirements": final_output.requirements,
                "solution": final_output.solution,
                "mvp_scope": final_output.mvp_scope,
            },
        }
        response = self.llm_client.generate(
            system_prompt,
            "请判断并生成以下产品方案的主要业务流程：\n"
            + json.dumps(context, ensure_ascii=False),
        )
        try:
            parsed = ProductFlowResponse.model_validate(json.loads(response))
            if not parsed.has_flow:
                return None
            if parsed.flow is None or not 4 <= len(parsed.flow.nodes) <= 10:
                raise ValueError
            return parsed.flow
        except (json.JSONDecodeError, ValidationError, ValueError) as error:
            raise ValueError("Invalid product flow response") from error

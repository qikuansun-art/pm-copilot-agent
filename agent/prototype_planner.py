"""LLM-powered structured interaction-prototype planning."""

import json

from pydantic import BaseModel, ValidationError

from llm.client import LLMClient, create_llm_client
from llm.config import LLMConfig
from models.final_output import FinalProductPlan
from models.flow import ProductFlow
from models.prototype import PrototypeSpec


class PrototypePlanResponse(BaseModel):
    """Envelope returned by the prototype planning prompt."""

    has_prototype: bool
    prototype: PrototypeSpec | None = None


class PrototypePlanner:
    """Plans MVP prototype pages and interactions from a final plan."""

    def __init__(self) -> None:
        config = LLMConfig.from_env()
        self.llm_client: LLMClient = create_llm_client(config)

    def generate(
        self,
        original_request: str,
        final_output: FinalProductPlan,
        product_flow: ProductFlow | None = None,
    ) -> PrototypeSpec | None:
        """Return an MVP PrototypeSpec, or None when pages cannot be inferred."""
        system_prompt = """你是一名产品原型规划专家，负责将已有产品方案规划成 Prototype V2 结构化交互原型规格。
你必须只返回合法 JSON，不要输出 Markdown 或 JSON 之外的文字。
信息不足以形成合理页面结构时返回：
{"has_prototype": false}
可以形成原型时返回：
{
  "has_prototype": true,
  "prototype": {
    "title": "...",
    "description": "...",
    "roles": [{"id": "operator", "name": "设备操作员", "description": "..."}],
    "default_role": "operator",
    "pages": [{
      "id": "page-list",
      "title": "...",
      "page_type": "list",
      "description": "...",
      "visible_to_roles": [],
      "fields": [{"id": "field-1", "label": "...", "field_type": "text", "required": false, "options": []}],
      "actions": [{"id": "action-1", "label": "...", "action_type": "navigate", "target": "page-detail", "visible_to_roles": []}],
      "table": {
        "columns": [{"id": "column-id", "label": "工单编号", "field": "order_id", "column_type": "text"}],
        "search_enabled": true,
        "filters": [{"id": "status-filter", "label": "状态", "filter_type": "status", "options": ["待派单", "维修中"]}],
        "row_actions": []
      },
      "tabs": [{"id": "pending", "label": "待派单"}],
      "cards": []
    }],
    "default_page": "page-list",
    "panels": [{
      "id": "assign-drawer",
      "title": "主管派单",
      "panel_type": "drawer",
      "fields": [{"id": "assignee", "label": "维修人员", "field_type": "select", "required": true, "options": []}],
      "actions": [{"id": "confirm-assign", "label": "确认派单", "action_type": "update_status", "target": null, "visible_to_roles": ["manager"]}]
    }],
    "statuses": ["待派单", "维修中", "待确认", "已完成"],
    "status_transitions": [{"from_status": "待派单", "action_id": "confirm-assign", "to_status": "维修中"}]
  }
}
规划原则：
1. 只覆盖 MVP Scope，禁止把 Future Scope 扩展进原型。
2. 建议规划 2～6 个页面；纯信息展示方案可以使用简单 dashboard 或 detail 页面。信息不足时返回无原型。
3. 从目标用户、关键场景、核心需求、解决方案、MVP 范围和可选业务流程推导页面与交互。
4. 页面和交互必须支撑一条主要业务流程，不要堆砌大量后台管理页。
5. 不生成 HTML、CSS、JavaScript、Figma、数据库、API 或技术架构。
6. page_type 只能是 dashboard、list、detail、form。
7. field_type 只能是 text、textarea、select、number、date。
8. action_type 只能是 navigate、open_modal、submit_form、update_status、close_modal、filter、search、open_drawer、switch_tab、switch_role。
9. 先判断角色是否有真实业务差异；无差异时 roles=[]。角色只表达原型视图差异，不设计真实权限系统。
10. 对列表型业务优先设计结构化 table；column_type 只能是 text、status、date、number，filter_type 只能是 select、search、status。
11. Tabs 用于表达同一列表的业务状态视图；dashboard 的关键统计使用 cards，不要把所有字段都做成卡片。
12. 聚焦填写、确认且不值得独立页面的操作可以使用 modal/drawer。open_modal/open_drawer target 必须引用对应类型的真实 panel id。
13. 若方案存在明确状态流转，生成 statuses 和 status_transitions；每个 transition 必须引用真实 action id，不要编造方案外状态。
14. 页面与 Action 的 visible_to_roles=[] 表示所有角色可见；非空值只能引用真实 role id，并只在确有角色差异时限制。
15. page、role、panel 和全部 action id 必须唯一；default_page/default_role 及 navigate/panel target 必须引用真实对象。
16. 交互应使用业务动作名称，例如新建、查看详情、派单、提交结果和确认完成。"""
        context = {
            "original_request": original_request,
            "final_output": {
                "target_users": final_output.target_users,
                "key_scenarios": final_output.key_scenarios,
                "requirements": final_output.requirements,
                "solution": final_output.solution,
                "mvp_scope": final_output.mvp_scope,
            },
            "product_flow": (
                product_flow.model_dump(mode="json")
                if product_flow is not None
                else None
            ),
        }
        response = self.llm_client.generate(
            system_prompt,
            "请根据以下已有方案规划交互原型：\n"
            + json.dumps(context, ensure_ascii=False),
        )
        try:
            parsed = PrototypePlanResponse.model_validate(json.loads(response))
            if not parsed.has_prototype:
                return None
            if parsed.prototype is None or not 1 <= len(parsed.prototype.pages) <= 6:
                raise ValueError
            return parsed.prototype
        except (json.JSONDecodeError, ValidationError, ValueError) as error:
            raise ValueError("Invalid prototype plan response") from error

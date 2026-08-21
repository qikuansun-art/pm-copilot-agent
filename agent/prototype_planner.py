"""LLM-powered structured interaction-prototype planning."""

import json

from pydantic import BaseModel, ValidationError

from llm.client import LLMClient, create_llm_client
from llm.config import LLMConfig
from models.final_output import FinalProductPlan
from models.flow import ProductFlow
from models.prototype import PrototypeSpec


def normalize_prototype_payload(payload: object) -> object:
    """Normalize only well-known, low-risk Prototype V2.5 formatting variants."""
    if not isinstance(payload, dict):
        return payload
    prototype = payload.get("prototype")
    if not isinstance(prototype, dict):
        return payload
    pages = prototype.get("pages")
    if not isinstance(pages, list):
        return payload
    for page in pages:
        if not isinstance(page, dict):
            continue
        components = page.get("components")
        actions = page.get("actions")
        if (
            isinstance(components, list)
            and components
            and isinstance(actions, list)
            and actions
            and not any(
                isinstance(component, dict) and component.get("component_type") == "actions"
                for component in components
            )
        ):
            page_id = str(page.get("id") or "page")
            component_ids = {
                component.get("id")
                for component in components
                if isinstance(component, dict)
            }
            component_id = f"{page_id}-actions"
            suffix = 2
            while component_id in component_ids:
                component_id = f"{page_id}-actions-{suffix}"
                suffix += 1
            orders = [
                component.get("order")
                for component in components
                if isinstance(component, dict)
                and isinstance(component.get("order"), int)
                and not isinstance(component.get("order"), bool)
            ]
            components.append({
                "id": component_id,
                "component_type": "actions",
                "title": "",
                "description": "",
                "order": max(orders, default=0) + 1,
                "region": "main",
                "visible_to_roles": [],
            })
        cards = page.get("cards")
        if isinstance(cards, list):
            for card in cards:
                if not isinstance(card, dict) or "label" in card:
                    continue
                if "title" in card:
                    card["label"] = card["title"]
                elif "name" in card:
                    card["label"] = card["name"]
        alerts = page.get("alerts")
        if isinstance(alerts, list):
            for alert in alerts:
                if not isinstance(alert, dict) or "message" in alert:
                    continue
                if "text" in alert:
                    alert["message"] = alert["text"]
                elif "content" in alert:
                    alert["message"] = alert["content"]
        layout = page.get("layout")
        if isinstance(layout, dict):
            for key in ("left_width", "right_width"):
                value = layout.get(key)
                if not isinstance(value, str):
                    continue
                stripped = value.strip()
                numeric = stripped[:-1].strip() if stripped.endswith("%") else stripped
                if numeric.isdigit():
                    layout[key] = int(numeric)
    return payload


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
        system_prompt = """你是一名产品原型规划专家，负责将已有产品方案规划成 Prototype V2.7 结构化交互原型规格。
你必须只返回合法 JSON，不要输出 Markdown 或 JSON 之外的文字。
信息不足以形成合理页面结构时返回：
{"has_prototype": false}
可以形成原型时返回：
{
  "has_prototype": true,
  "prototype": {
    "title": "...",
    "description": "...",
    "roles": [{"id": "operator", "name": "设备操作员", "description": "..."}, {"id": "manager", "name": "维修主管", "description": "..."}],
    "default_role": "operator",
    "pages": [{
      "id": "page-list",
      "title": "...",
      "page_type": "list",
      "description": "...",
      "visible_to_roles": [],
      "layout": {"layout_type": "dashboard_grid", "left_width": null, "right_width": null},
      "components": [
        {"id": "summary-cards", "component_type": "cards", "title": "概览", "description": "", "order": 1, "region": "top", "visible_to_roles": []},
        {"id": "status-tabs", "component_type": "tabs", "title": "状态视图", "description": "", "order": 2, "region": "main", "visible_to_roles": []},
        {"id": "records-table", "component_type": "table", "title": "记录列表", "description": "", "order": 3, "region": "main", "visible_to_roles": []}
      ],
      "fields": [{"id": "replace_part", "label": "是否更换备件", "field_type": "select", "required": false, "options": ["是", "否"], "visible_when": null, "required_when": null, "enabled_when": null}],
      "actions": [{"id": "action-1", "label": "主管派单", "action_type": "navigate", "target": "page-detail", "visible_to_roles": ["manager"], "visible_when": {"logic": "and", "conditions": [{"field": "status", "operator": "equals", "value": "待派单"}]}, "enabled_when": null}],
      "table": {
        "columns": [{"id": "column-id", "label": "工单编号", "field": "order_id", "column_type": "text"}],
        "search_enabled": true,
        "filters": [{"id": "status-filter", "label": "状态", "filter_type": "status", "options": ["待派单", "维修中"]}],
        "row_actions": []
      },
      "tabs": [{"id": "pending", "label": "待派单"}],
      "cards": [{"id": "pending-card", "label": "待处理", "value": "12", "description": "当前待处理数量"}],
      "detail_sections": [],
      "timeline_items": [],
      "alerts": [{"id": "timeout-alert", "message": "存在超时未处理工单", "alert_type": "warning"}]
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
2. 规划 2～8 个页面、0～5 个角色，每页最多 15 个主要 components；需求过大时只覆盖 MVP 核心流程，不生成大型 ERP 全量页面。
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
16. 交互应使用当前业务的动作名称，不要把维修工单、维修主管、维修人员等示例写死到其他业务。
17. 每个页面判断 layout：single_column 适合线性列表/表单；two_column 适合详情与辅助信息并列；sidebar_detail 适合主从浏览；dashboard_grid 适合指标、预警、列表组合。
18. components 是对 page.cards/table/tabs/fields/actions、detail_sections、timeline_items、alerts 的引用和编排，不复制业务数据。component_type 只能是 cards、table、form、detail、tabs、alert、timeline、text、actions；region 只能是 main、left、right、top、bottom，并按 order 排序。
19. 列表工作台通常依次使用 cards、tabs、table；详情页可把 detail/timeline 放 left，把 actions/alert 放 right。只创建页面确实需要的组件。
20. detail_sections 用 fields id 或任一 table column.field 将详情字段分组；每组具有 id、title、fields、order。不要把每个字段拆成独立 component。
21. timeline_items 仅表达当前业务中的展示型操作历史、审批、流转或跟进记录；字段为 id、title、description、status，不设计实时追加。
22. alerts 仅用于当前业务确实存在的预警或提示；alert_type 只能是 info、success、warning、error。
23. layout 和新增数组应按页面需要生成；没有必要时使用 null 或 []。

Prototype V2.5 schema rules：
- PrototypeCard 必须使用 id、label、value、description。必须使用 label，禁止用 title 或 name 代替。
- PrototypeAlert 必须使用 id、message、alert_type。必须使用 message，禁止用 title、text 或 content 代替。
- PrototypeLayout 必须使用 layout_type、left_width、right_width。两栏布局示例：{"layout_type":"two_column","left_width":60,"right_width":40}。宽度只能是整数或 null；允许 60、40，禁止 "60%"、"2fr"、"40px"、"auto"。
- PrototypeComponent 必须使用 id、component_type、order、region、visible_to_roles。
- PrototypeDetailSection 必须使用 id、title、fields、order。
- Card 完整示例：{"id":"pending-card","label":"待处理","value":"12","description":"当前待处理数量"}。
- Alert 完整示例：{"id":"timeout-alert","message":"存在超时未处理工单","alert_type":"warning"}。

Prototype V2.6 condition rules：
- 只能根据 target_users、key_scenarios、requirements、solution、mvp_scope 和 product_flow 中明确存在的业务约束生成条件。不要为了增加复杂度自行发明审批、权限或状态规则。
- Condition 必须是结构化 JSON，禁止输出 "status == '待派单' && role == 'manager'" 等表达式字符串。
- PrototypeCondition 格式：{"field":"status","operator":"equals","value":"待派单","value_field":null}。
- PrototypeConditionGroup 格式：{"logic":"and","conditions":[{"field":"role","operator":"equals","value":"maintenance_manager"},{"field":"status","operator":"equals","value":"待派单"}]}。只允许一层 Group，不要嵌套。
- operator 只能是 equals、not_equals、in、not_in、exists、not_exists、greater_than、less_than、greater_than_or_equal、less_than_or_equal。
- exists/not_exists 不需要 value；in/not_in 的 value 必须是数组；大小比较的固定 value 必须是数字。
- value 和 value_field 二选一。跨字段比较使用 value_field，例如：{"field":"requested_quantity","operator":"less_than_or_equal","value_field":"available_quantity"}，不要把字段名放进 value。
- field 只能使用 role、status、真实 PrototypeField.id 或真实 PrototypeTableColumn.field；value_field 只能引用真实业务字段。
- Action 可使用 visible_when、enabled_when；Field 可使用 visible_when、required_when、enabled_when；Page、Panel、Component 可使用 visible_when。无条件时使用 null。
- visible_to_roles 表达静态角色范围；visible_when 表达动态角色、状态或字段条件。两者不要互相替代。
- 示例：备件字段仅在是否更换备件为“是”时显示且必填：visible_when/required_when 均使用 {"logic":"and","conditions":[{"field":"replace_part","operator":"equals","value":"是"}]}。
- 示例：库存预警 Component 在 inventory_status equals low 时显示；出库 Action 在 requested_quantity less_than_or_equal value_field=available_quantity 时启用。"""
        system_prompt += """
Component Tree completeness rules：
- 如果 page.actions 非空且 page.components 非空，components 必须包含至少一个 component_type="actions"，用于渲染 page.actions。
- 列表/工作台页面的 actions 通常放在 top 或 main；详情页可放在 right、bottom 或 main。根据布局选择，不要写死具体业务。
- page.actions != [] → 非空 Component Tree 中必须有 actions component。table.row_actions 和 panel.actions 不需要 page actions component。
- 完整示例：
{"id":"page-list","title":"工单列表","page_type":"list","actions":[{"id":"create-order","label":"创建工单","action_type":"open_drawer","target":"panel-create"}],"components":[{"id":"comp-cards","component_type":"cards","region":"top","order":1},{"id":"comp-actions","component_type":"actions","region":"top","order":2},{"id":"comp-table","component_type":"table","region":"main","order":3}]}

Prototype V2.7 mock entity rules：
- 当 select、detail 或 table 需要维修人员、设备、备件、仓库、物料等参考数据时，使用 entity_types 和 entity_records；不要连接真实数据库、API、账号或组织架构。
- PrototypeEntityType 格式：{"id":"technician","name":"维修人员","fields":["id","name","status"]}。
- PrototypeEntityRecord 格式：{"id":"tech-001","entity_type":"technician","data":{"name":"张师傅","status":"空闲"}}。
- 每类只生成 3～5 条稳定、合理的 Mock Data；不要生成大量记录，不要为普通文本字段创建 Entity。
- 需要实体数据的 select 使用 data_source、option_label_field、option_value_field。例如：{"id":"technician_id","label":"选择维修人员","field_type":"select","data_source":"technician","option_label_field":"name","option_value_field":"id"}。
- data_source 必须引用真实 entity_types.id；entity_records.entity_type 必须引用真实 entity_types.id；label/value 字段必须存在于 entity type fields 中，记录自身 id 可用字段名 id 引用。
- 有 data_source 时 Renderer 优先使用 entity_records；没有 data_source 时继续使用静态 options。
- 维修工单可按需求生成 technician、device、spare_part；仓库业务应生成 warehouse、material 等自身实体，禁止照搬维修人员示例。
- Entity Record 的 status 第一版全部展示，不要新增 filter_condition 或扩展 Condition。
"""
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
            payload = json.loads(response)
        except json.JSONDecodeError as error:
            return self._repair_once(response, [f"Response is not valid JSON: {error.msg}"])

        try:
            return self._validate_payload(normalize_prototype_payload(payload))
        except ValidationError as error:
            return self._repair_once(
                json.dumps(payload, ensure_ascii=False),
                self._validation_errors(error),
            )
        except ValueError as error:
            raise ValueError("Invalid prototype plan response") from error

    @staticmethod
    def _validation_errors(error: ValidationError) -> list[str]:
        """Return concise schema paths suitable for one repair request."""
        result = []
        for item in error.errors(include_url=False, include_context=False)[:30]:
            path = ".".join(str(part) for part in item.get("loc", ())) or "prototype"
            result.append(f"{path}: {item.get('msg', 'Invalid value')}")
        return result

    @staticmethod
    def _validate_payload(payload: object) -> PrototypeSpec | None:
        """Validate one parsed and normalized response without repairing it."""
        parsed = PrototypePlanResponse.model_validate(payload)
        if not parsed.has_prototype:
            return None
        if (
            parsed.prototype is None
            or not 2 <= len(parsed.prototype.pages) <= 8
            or len(parsed.prototype.roles) > 5
        ):
            raise ValueError("Prototype complexity is outside supported limits")
        return parsed.prototype

    def _repair_once(
        self,
        original_response: str,
        validation_errors: list[str],
    ) -> PrototypeSpec | None:
        """Ask the LLM once to repair JSON/schema errors without replanning."""
        repair_prompt = """你之前生成了一份 PrototypeSpec JSON，结构基本正确，但未通过 Schema Validation。
不要重新规划产品。不要新增页面。不要删除原有业务能力。
只修复给出的 JSON 或 Schema 错误。
保留原业务含义，以及原有页面、角色、Action 和状态机。
返回完整 JSON，不要输出 Markdown、解释或 JSON 之外的文字。"""
        repair_prompt += """
Prototype V2.7 Entity 修复时必须保持引用一致：data_source 和 entity_records.entity_type 必须引用已有 entity_types.id；option_label_field/option_value_field 必须引用对应 fields 或记录 id。只修复引用错误，不扩展业务范围。
"""
        user_prompt = (
            "Validation Errors：\n- "
            + "\n- ".join(validation_errors)
            + "\n\nOriginal JSON：\n"
            + original_response
        )
        repaired_response = self.llm_client.generate(repair_prompt, user_prompt)
        try:
            repaired_payload = json.loads(repaired_response)
            return self._validate_payload(normalize_prototype_payload(repaired_payload))
        except (json.JSONDecodeError, ValidationError, ValueError) as error:
            raise ValueError("Invalid prototype plan response") from error

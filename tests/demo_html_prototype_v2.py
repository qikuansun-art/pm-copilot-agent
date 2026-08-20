"""Regression coverage for the deterministic Prototype V2 HTML renderer."""

from models.prototype import PrototypeSpec
from prototype.html_prototype import generate_interactive_prototype
from tests.demo_prototype_planner_v2 import v2_response


def main() -> None:
    spec = PrototypeSpec.model_validate(v2_response()["prototype"])
    html = generate_interactive_prototype(spec)

    # Case A: all V2 structures are represented by HTML or runtime data.
    for expected in (
        "role-switcher", "设备操作员", "维修主管", "维修人员",
        "工单编号", "设备", "故障", "状态", "更新时间",
        "data-table-search", "data-table-filter", "prototype-tabs",
        "待派单", "维修中", "待确认", "已完成",
        "prototype-panel drawer", "status-badge", "status_transitions",
        "selectedRecord", "switchRole", "openPanel", "dispatchAction",
    ):
        assert expected in html

    # Case B: role restrictions remain attached to their real actions.
    assert '"assign":{"type":"open_drawer","target":"assign-drawer","roles":["manager"]' in html
    assert '"repair":{"type":"navigate","target":"repair-detail","roles":["technician"]' in html
    assert '"confirm-complete":{"type":"update_status","target":null,"roles":["operator"]' in html
    assert "page.table.row_actions.filter(x=>allowed(x.visible_to_roles))" in html

    # Case C: transitions use validated actions and execute against selectedRecord.
    actions = {
        action.id
        for page in spec.pages
        for action in [*page.actions, *(page.table.row_actions if page.table else [])]
    } | {action.id for panel in spec.panels for action in panel.actions}
    assert all(item.action_id in actions for item in spec.status_transitions)
    assert [(item.from_status, item.to_status) for item in spec.status_transitions] == [
        ("待派单", "维修中"), ("维修中", "待确认"), ("待确认", "已完成")
    ]
    assert "selectedRecord?.__status===x.from_status" in html
    assert "状态已更新：" in html

    # Case D: a V1 payload still renders navigation, forms, and actions.
    legacy = PrototypeSpec.model_validate({
        "title": "V1 原型",
        "description": "旧格式",
        "default_page": "list",
        "pages": [
            {"id": "list", "title": "记录列表", "page_type": "list", "actions": [{"id": "new", "label": "新建", "action_type": "navigate", "target": "form"}]},
            {"id": "form", "title": "新建记录", "page_type": "form", "fields": [{"id": "name", "label": "名称", "field_type": "text", "required": True}], "actions": [{"id": "submit", "label": "提交", "action_type": "submit_form", "target": "list"}]},
        ],
    })
    legacy_html = generate_interactive_prototype(legacy)
    assert "记录列表" in legacy_html and '<form class="prototype-form"' in legacy_html
    assert "showPage" in legacy_html and "submit_form" in legacy_html
    assert 'id="prototype-role"' not in legacy_html

    # Case E: HTML content and inline JSON remain independently escaped.
    unsafe_payload = legacy.model_dump(mode="json")
    unsafe_payload["title"] = '<原型 & "测试">'
    unsafe_payload["description"] = "</script><script>alert('x')</script>"
    unsafe = generate_interactive_prototype(PrototypeSpec.model_validate(unsafe_payload))
    assert '&lt;原型 &amp; &quot;测试&quot;&gt;' in unsafe
    assert "</script><script>alert('x')</script>" not in unsafe
    assert "\\u003c/script\\u003e" in unsafe
    assert "eval(" not in html and "new Function" not in html

    print("Case A: V2 Role/Table/Search/Filter/Tabs/Drawer runtime generated")
    print("Case B: role-scoped actions preserved")
    print("Case C: selectedRecord status transitions validated")
    print("Case D: V1 HTML compatibility passed")
    print("Case E: HTML and inline JSON escaping passed")


if __name__ == "__main__":
    main()

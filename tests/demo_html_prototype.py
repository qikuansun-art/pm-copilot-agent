"""Regression coverage for deterministic interactive HTML prototypes."""

import json

from agent.runtime import PMCopilotRuntime
from models.final_output import FinalProductPlan
from models.prototype import PrototypeAction, PrototypeField, PrototypePage, PrototypeSpec
from models.state import AgentState, TaskContext
from prototype.html_prototype import generate_interactive_prototype


def maintenance_spec() -> PrototypeSpec:
    """Build a repair-work-order prototype with list, detail, and form pages."""
    return PrototypeSpec(
        title="设备维修工单管理",
        description="维修业务交互原型",
        default_page="orders",
        pages=[
            PrototypePage(
                id="orders",
                title="工单列表",
                page_type="list",
                actions=[
                    PrototypeAction(id="new", label="新建工单", action_type="navigate", target="create"),
                    PrototypeAction(id="view", label="查看详情", action_type="navigate", target="detail"),
                ],
            ),
            PrototypePage(
                id="create",
                title="新建工单",
                page_type="form",
                fields=[
                    PrototypeField(id="device", label="设备名称", field_type="text", required=True),
                    PrototypeField(id="fault", label="故障描述", field_type="textarea", required=True),
                    PrototypeField(id="priority", label="优先级", field_type="select", options=["普通", "紧急"]),
                ],
                actions=[PrototypeAction(id="submit", label="提交工单", action_type="submit_form", target="orders")],
            ),
            PrototypePage(
                id="detail",
                title="工单详情",
                page_type="detail",
                fields=[PrototypeField(id="status", label="状态", field_type="text")],
                actions=[
                    PrototypeAction(id="repair", label="维修处理", action_type="navigate", target="repair-form"),
                    PrototypeAction(id="confirm", label="确认完成", action_type="update_status"),
                    PrototypeAction(id="confirm-dialog", label="打开确认", action_type="open_modal"),
                ],
            ),
            PrototypePage(
                id="repair-form",
                title="维修处理",
                page_type="form",
                fields=[PrototypeField(id="result", label="维修结果", field_type="textarea", required=True)],
                actions=[PrototypeAction(id="submit-result", label="提交维修结果", action_type="submit_form", target="detail")],
            ),
        ],
    )


def information_spec() -> PrototypeSpec:
    """Build a simple dashboard/detail information prototype."""
    return PrototypeSpec(
        title="设备参数展示",
        description="只读参数原型",
        default_page="dashboard",
        pages=[
            PrototypePage(
                id="dashboard",
                title="设备概览",
                page_type="dashboard",
                actions=[PrototypeAction(id="parameters", label="查看参数", action_type="navigate", target="details")],
            ),
            PrototypePage(
                id="details",
                title="参数详情",
                page_type="detail",
                fields=[PrototypeField(id="temperature", label="温度", field_type="number")],
            ),
        ],
    )


class FailingPrototypePlanner:
    def generate(self, original_request, final_output, product_flow):
        raise ValueError("prototype failed")


def final_plan() -> FinalProductPlan:
    return FinalProductPlan(
        title="设备维修方案",
        summary="主方案保持可用",
        mvp_scope=["维修工单"],
    )


def main() -> None:
    """Cover workflow HTML, display HTML, escaping, and graceful failure."""
    # Case A: interactive repair prototype.
    html = generate_interactive_prototype(maintenance_spec())
    for expected in (
        "<!doctype html>", "设备维修工单管理", "工单列表", "新建工单",
        "工单详情", "维修处理", "设备名称", "故障描述", "showPage",
        "submit_form", "update_status", "状态已更新", "toast",
    ):
        assert expected in html
    assert 'type="text"' in html
    assert "<textarea" in html
    assert "<select" in html
    assert " required" in html

    # Case B: display-only prototype remains dashboard/detail without forms.
    display_html = generate_interactive_prototype(information_spec())
    assert "设备概览" in display_html and "参数详情" in display_html
    assert 'data-nav-page="dashboard"' in display_html
    assert 'data-page="details"' in display_html
    assert '<form class="prototype-form"' not in display_html

    # Case C: HTML and inline-script values are escaped independently.
    unsafe = PrototypeSpec(
        title='<设备 & "参数" \'展示\'>',
        description="</script><script>alert('x')</script>",
        default_page="page</script>",
        pages=[PrototypePage(
            id="page</script>",
            title="<参数详情>",
            page_type="form",
            fields=[PrototypeField(id="field", label='温度 < > & " \'', field_type="select", options=["<高>", "低 & 稳定"])],
            actions=[],
        )],
    )
    escaped = generate_interactive_prototype(unsafe)
    assert '<设备 & "参数"' not in escaped
    assert "&lt;设备 &amp; &quot;参数&quot; &#x27;展示&#x27;&gt;" in escaped
    assert "</script><script>alert('x')</script>" not in escaped
    assert "\\u003c/script\\u003e" in escaped
    assert "&lt;高&gt;" in escaped and "低 &amp; 稳定" in escaped

    # Case D: prototype planning failure cannot damage the existing final plan.
    state = AgentState(
        task=TaskContext(task_id="prototype-failure", title="维修", original_request="规划维修"),
        final_output=final_plan(),
        prototype_spec=maintenance_spec(),
    )
    runtime = PMCopilotRuntime.__new__(PMCopilotRuntime)
    runtime.prototype_planner = FailingPrototypePlanner()
    runtime._refresh_prototype_spec(state)
    assert state.final_output == final_plan()
    assert state.prototype_spec is None

    # AgentState persistence format and Legacy default remain compatible.
    restored = AgentState.model_validate_json(
        AgentState(task=state.task, final_output=final_plan(), prototype_spec=maintenance_spec()).model_dump_json()
    )
    assert restored.prototype_spec == maintenance_spec()
    legacy_payload = json.loads(restored.model_dump_json())
    legacy_payload.pop("prototype_spec")
    assert AgentState.model_validate(legacy_payload).prototype_spec is None

    # Case E: the modal is closed by default and has no initial open class.
    assert 'id="prototype-modal" class="panel-overlay modal-overlay" aria-hidden="true"' in html
    assert 'class="panel-overlay modal-overlay is-open"' not in html
    assert ".panel-overlay{" in html and "display:none" in html

    # Case F: all close paths use the same visible and accessibility state.
    assert "function closeModal()" in html
    assert "classList.remove('is-open')" in html
    assert "setAttribute('aria-hidden','true')" in html
    assert "if(e.target===x)closePanel()" in html
    assert "e.key==='Escape'" in html

    # Case G: only open_modal dispatch opens the modal.
    assert "if(action.type==='open_modal')" in html
    assert html.count("openModal(") == 2
    assert "document.addEventListener('DOMContentLoaded'" in html
    assert "closePanel();" in html

    # Case H: confirmation closes first and never redispatches open_modal.
    assert "function confirmModal()" in html
    assert "function confirmModal(){closePanel();showToast('操作已确认')}" in html
    assert "[data-modal-confirm]" in html

    print("Case A: list/detail/form interactions generated")
    print("Case B: dashboard/detail prototype generated")
    print("Case C: HTML and JSON values escaped")
    print("Case D: planner failure preserved FinalProductPlan")
    print("Case E: modal defaults to closed")
    print("Case F: cancel, overlay, and Escape close paths generated")
    print("Case G: open_modal is the only modal open dispatch")
    print("Case H: confirmation cannot redispatch open_modal")
    print("Persistence and Legacy compatibility: passed")


if __name__ == "__main__":
    main()

"""Regression coverage for bounded Prototype V2.5 normalization and repair."""

import copy
import json

from agent.prototype_planner import PrototypePlanner
from models.final_output import FinalProductPlan


class StubClient:
    def __init__(self, responses: list[str | dict]) -> None:
        self.responses = responses
        self.calls: list[tuple[str, str]] = []

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        self.calls.append((system_prompt, user_prompt))
        response = self.responses[len(self.calls) - 1]
        return response if isinstance(response, str) else json.dumps(response, ensure_ascii=False)


def final_plan() -> FinalProductPlan:
    return FinalProductPlan(
        title="库存管理",
        summary="库存 MVP",
        target_users=["仓库管理员"],
        key_scenarios=["查看库存", "处理预警"],
        requirements=["库存总览", "库存详情"],
        solution=["库存工作台"],
        mvp_scope=["库存总览", "库存详情"],
    )


def valid_payload() -> dict:
    return {"has_prototype": True, "prototype": {
        "title": "库存管理", "description": "库存 MVP", "default_page": "overview",
        "roles": [], "panels": [], "statuses": [], "status_transitions": [],
        "pages": [
            {"id": "overview", "title": "库存总览", "page_type": "dashboard",
             "layout": {"layout_type": "two_column", "left_width": 60, "right_width": 40},
             "cards": [{"id": "pending", "label": "待处理", "value": "12", "description": "待处理数量"}],
             "alerts": [{"id": "low-stock", "message": "库存不足", "alert_type": "warning"}]},
            {"id": "detail", "title": "库存详情", "page_type": "detail",
             "actions": [{"id": "confirm", "label": "确认", "action_type": "update_status"}]},
        ]}}


def planner(*responses: str | dict) -> tuple[PrototypePlanner, StubClient]:
    client = StubClient(list(responses))
    instance = PrototypePlanner.__new__(PrototypePlanner)
    instance.llm_client = client
    return instance, client


def generate(instance: PrototypePlanner):
    return instance.generate("规划库存管理", final_plan())


def main() -> None:
    # A: Card title is a safe label alias; no repair call is needed.
    payload = valid_payload()
    card = payload["prototype"]["pages"][0]["cards"][0]
    card["title"] = card.pop("label")
    instance, client = planner(payload)
    assert generate(instance).pages[0].cards[0].label == "待处理"
    assert len(client.calls) == 1

    # B: a pure numeric percentage safely normalizes to an integer.
    payload = valid_payload()
    payload["prototype"]["pages"][0]["layout"]["left_width"] = "60%"
    instance, client = planner(payload)
    assert generate(instance).pages[0].layout.left_width == 60
    assert len(client.calls) == 1

    # C: Alert text is a safe message alias; no repair call is needed.
    payload = valid_payload()
    alert = payload["prototype"]["pages"][0]["alerts"][0]
    alert["text"] = alert.pop("message")
    instance, client = planner(payload)
    assert generate(instance).pages[0].alerts[0].message == "库存不足"
    assert len(client.calls) == 1

    # D: units such as fr remain invalid and trigger exactly one repair.
    broken, repaired = valid_payload(), valid_payload()
    broken["prototype"]["pages"][0]["layout"]["left_width"] = "2fr"
    instance, client = planner(broken, repaired)
    assert generate(instance).pages[0].layout.left_width == 60
    assert len(client.calls) == 2
    assert "left_width" in client.calls[1][1] and "2fr" in client.calls[1][1]

    # E: business references are not normalized; the repair receives the error.
    broken, repaired = valid_payload(), valid_payload()
    for item in (broken, repaired):
        item["prototype"]["statuses"] = ["待确认", "已完成"]
    broken["prototype"]["status_transitions"] = [{"from_status": "待确认", "action_id": "missing", "to_status": "已完成"}]
    repaired["prototype"]["status_transitions"] = [{"from_status": "待确认", "action_id": "confirm", "to_status": "已完成"}]
    instance, client = planner(broken, repaired)
    assert generate(instance).status_transitions[0].action_id == "confirm"
    assert len(client.calls) == 2
    assert "Prototype transitions must reference an action" in client.calls[1][1]

    # F: a failed repair is terminal; no third LLM call occurs.
    broken = valid_payload()
    broken["prototype"]["pages"][0]["layout"]["left_width"] = "2fr"
    instance, client = planner(copy.deepcopy(broken), copy.deepcopy(broken))
    try:
        generate(instance)
    except ValueError as error:
        assert str(error) == "Invalid prototype plan response"
    else:
        raise AssertionError("A second invalid response must fail")
    assert len(client.calls) == 2

    # G: invalid initial JSON receives one JSON-only repair attempt.
    instance, client = planner("```json\n{broken\n```", valid_payload())
    assert generate(instance).title == "库存管理"
    assert len(client.calls) == 2
    assert "not valid JSON" in client.calls[1][1]

    print("Cases A-C: safe normalization passed without repair")
    print("Cases D-E: one schema-only repair passed")
    print("Case F: second failure stopped after two calls")
    print("Case G: invalid JSON repaired once")


if __name__ == "__main__":
    main()

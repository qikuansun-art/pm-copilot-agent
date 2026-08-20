"""Regression coverage for persisted optional-generation diagnostics."""

import json
from pathlib import Path

from pydantic import BaseModel, ValidationError

from agent.runtime import PMCopilotRuntime
from api.task_store import TaskStore
from models.final_output import FinalProductPlan
from models.prototype import PrototypePage, PrototypeSpec
from models.state import AgentState, GenerationOptions, TaskContext


class Planner:
    def __init__(self, outcome) -> None:
        self.outcome = outcome

    def generate(self, *args):
        if isinstance(self.outcome, Exception):
            raise self.outcome
        return self.outcome


class RequiredRole(BaseModel):
    id: str


class RoleEnvelope(BaseModel):
    roles: list[RequiredRole]


class ValidationFailurePlanner:
    def generate(self, *args):
        try:
            RoleEnvelope.model_validate({"roles": [{}]})
        except ValidationError as error:
            raise ValueError("Invalid prototype plan response") from error


def prototype() -> PrototypeSpec:
    return PrototypeSpec(
        title="诊断测试原型",
        description="用于状态测试",
        default_page="home",
        pages=[PrototypePage(id="home", title="首页", page_type="dashboard")],
    )


def state(enabled: bool = True) -> AgentState:
    return AgentState(
        task=TaskContext(
            task_id="generation-diagnostic",
            title="生成诊断",
            original_request="生成交互原型",
            generation_options=GenerationOptions(
                generate_flow=False,
                generate_prototype=enabled,
            ),
        ),
        final_output=FinalProductPlan(title="产品方案", summary="测试方案"),
    )


def runtime(outcome) -> PMCopilotRuntime:
    instance = PMCopilotRuntime.__new__(PMCopilotRuntime)
    instance.prototype_planner = Planner(outcome)
    instance.last_generation_status = {}
    return instance


def main() -> None:
    # Case A: successful generation clears all error fields.
    successful = state()
    runtime(prototype())._refresh_prototype_spec(successful)
    assert successful.prototype_spec == prototype()
    assert successful.generation_status.prototype.status == "completed"
    assert successful.generation_status.prototype.error_type is None
    assert successful.generation_status.prototype.details == []

    # Case B: a deliberate no-prototype response is empty, not failed.
    empty = state()
    runtime(None)._refresh_prototype_spec(empty)
    assert empty.prototype_spec is None
    assert empty.generation_status.prototype.status == "empty"

    # Case C: disabled generation never calls the planner and is skipped.
    skipped = state(enabled=False)
    skipped_runtime = runtime(AssertionError("planner must not run"))
    skipped_runtime._refresh_prototype_spec(skipped)
    assert skipped.generation_status.prototype.status == "skipped"

    # Case D: ordinary exceptions retain bounded type and message.
    failed = state()
    runtime(RuntimeError("ordinary failure " + "x" * 600))._refresh_prototype_spec(failed)
    diagnostic = failed.generation_status.prototype
    assert diagnostic.status == "failed"
    assert diagnostic.error_type == "RuntimeError"
    assert diagnostic.message.startswith("ordinary failure")
    assert len(diagnostic.message) == 500

    # Case E: wrapped Pydantic errors retain concise field paths.
    validation_failed = state()
    validation_runtime = PMCopilotRuntime.__new__(PMCopilotRuntime)
    validation_runtime.prototype_planner = ValidationFailurePlanner()
    validation_runtime._refresh_prototype_spec(validation_failed)
    validation = validation_failed.generation_status.prototype
    assert validation.status == "failed"
    assert validation.error_type == "ValidationError"
    assert validation.message == "Invalid prototype plan response"
    assert any(item.startswith("roles.0.id:") and "Field required" in item for item in validation.details)

    # Flow uses the same structured status and respects its disabled option.
    validation_runtime._refresh_product_flow(validation_failed)
    assert validation_failed.generation_status.flow.status == "skipped"

    # Case F: complete diagnostics survive SQLite store recreation.
    db_path = Path("data/test_generation_diagnostics.db")
    if db_path.exists():
        db_path.unlink()
    try:
        TaskStore(db_path).save(validation_failed)
        restored = TaskStore(db_path).get(validation_failed.task.task_id)
        assert restored is not None
        assert restored.generation_status == validation_failed.generation_status
    finally:
        if db_path.exists():
            db_path.unlink()

    # Case G: legacy JSON without diagnostics uses safe defaults.
    legacy_payload = json.loads(validation_failed.model_dump_json())
    legacy_payload.pop("generation_status")
    legacy = AgentState.model_validate(legacy_payload)
    assert legacy.generation_status.flow.status == "pending"
    assert legacy.generation_status.prototype.status == "pending"

    print("Case A: Prototype completed diagnostic passed")
    print("Case B: Prototype empty diagnostic passed")
    print("Case C: Prototype skipped diagnostic passed")
    print("Case D: ordinary exception diagnostic passed")
    print("Case E: ValidationError field details passed", validation.details)
    print("Case F: SQLite diagnostic restoration passed")
    print("Case G: Legacy diagnostic defaults passed")


if __name__ == "__main__":
    main()

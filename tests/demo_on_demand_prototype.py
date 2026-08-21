"""Regression coverage for the on-demand prototype lifecycle."""

import json
from types import SimpleNamespace

import api.main as api_main
from agent.runtime import PMCopilotRuntime
from models.final_output import FinalProductPlan
from models.prototype import PrototypePage, PrototypeSpec
from models.state import AgentStage, AgentState, GenerationOptions, ProductAnalysis, TaskContext


def prototype(title: str) -> PrototypeSpec:
    return PrototypeSpec(
        title=title,
        description="Prototype lifecycle test",
        default_page="home",
        pages=[PrototypePage(id="home", title="Home", page_type="dashboard")],
    )


def state(task_id: str = "on-demand-prototype") -> AgentState:
    return AgentState(
        task=TaskContext(
            task_id=task_id,
            title="On-demand prototype",
            original_request="Create a product plan",
            current_stage=AgentStage.ANALYZING,
            generation_options=GenerationOptions(generate_flow=False, generate_prototype=True),
        ),
        analysis=ProductAnalysis(),
    )


class CountingPlanner:
    def __init__(self, outcomes) -> None:
        self.outcomes = list(outcomes)
        self.calls = 0

    def generate(self, *args):
        outcome = self.outcomes[min(self.calls, len(self.outcomes) - 1)]
        self.calls += 1
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


class RuntimeFactory:
    planner = None

    def __init__(self) -> None:
        self.prototype_planner = self.planner

    _failed_diagnostic = staticmethod(PMCopilotRuntime._failed_diagnostic)


def main() -> None:
    # Main workflow ignores the legacy generate_prototype option.
    workflow = state("workflow")
    runtime = PMCopilotRuntime.__new__(PMCopilotRuntime)
    runtime.product_analyzer = type("Analyzer", (), {"analyze": lambda self, value: ProductAnalysis()})()
    runtime.finalizer = type("Finalizer", (), {"finalize": lambda self, value: FinalProductPlan(title="V1", summary="Plan")})()
    runtime.flow_generator = None
    runtime.last_generation_status = {}
    runtime.prototype_planner = CountingPlanner([AssertionError("must not run")])
    runtime.run_product_analysis(workflow)
    assert workflow.task.current_stage == AgentStage.WAITING_REVIEW
    assert runtime.prototype_planner.calls == 0
    assert workflow.prototype_spec is None

    # Review revisions and added conditions retain the older prototype.
    workflow.prototype_spec = prototype("V1 retained")
    workflow.prototype_plan_version = 1
    workflow.task.current_stage = AgentStage.WAITING_REVIEW
    runtime.plan_reviser = type(
        "Reviser",
        (),
        {"revise": lambda self, value, feedback: SimpleNamespace(revised_plan=FinalProductPlan(title="V2", summary=feedback), revision_summary=[feedback])},
    )()
    runtime.handle_review(workflow, approved=False, feedback="Review revision")
    assert workflow.task.plan_version == 2
    assert workflow.prototype_spec.title == "V1 retained"
    assert workflow.prototype_plan_version == 1
    assert runtime.prototype_planner.calls == 0

    workflow.task.current_stage = AgentStage.COMPLETED
    runtime.revise_completed_task(workflow, "Added condition")
    assert workflow.task.plan_version == 3
    assert workflow.prototype_spec.title == "V1 retained"
    assert workflow.prototype_plan_version == 1
    assert runtime.prototype_planner.calls == 0

    current = state("api-lifecycle")
    current.final_output = FinalProductPlan(title="V1", summary="Plan")
    current.task.current_stage = AgentStage.WAITING_REVIEW
    api_main.tasks[current.task.task_id] = current
    original_runtime = api_main.PMCopilotRuntime
    original_save = api_main.save_task_state
    saved_statuses = []
    planner = CountingPlanner([prototype("V1"), prototype("V1 forced"), RuntimeError("V2 failed")])
    RuntimeFactory.planner = planner
    api_main.PMCopilotRuntime = RuntimeFactory
    api_main.save_task_state = lambda value: saved_statuses.append(value.generation_status.prototype.status) or value
    try:
        generated = api_main.generate_task_prototype(current.task.task_id)
        assert planner.calls == 1
        assert generated["prototype_plan_version"] == 1
        assert generated["generation_status"]["prototype"]["status"] == "completed"
        assert "pending" in saved_statuses

        api_main.generate_task_prototype(current.task.task_id)
        assert planner.calls == 1
        api_main.generate_task_prototype(current.task.task_id, force=True)
        assert planner.calls == 2

        old_spec = current.prototype_spec
        current.task.plan_version = 2
        failed = api_main.generate_task_prototype(current.task.task_id)
        assert planner.calls == 3
        assert current.prototype_spec == old_spec
        assert failed["prototype_plan_version"] == 1
        assert failed["generation_status"]["prototype"]["status"] == "failed"

        legacy_payload = json.loads(current.model_dump_json())
        legacy_payload.pop("prototype_plan_version")
        assert AgentState.model_validate(legacy_payload).prototype_plan_version is None
    finally:
        api_main.PMCopilotRuntime = original_runtime
        api_main.save_task_state = original_save
        api_main.tasks.pop(current.task.task_id, None)

    print("On-demand prototype lifecycle: passed")


if __name__ == "__main__":
    main()

"""Regression coverage for optional artifact generation choices."""

import json

from agent.runtime import PMCopilotRuntime
from models.final_output import FinalProductPlan
from models.flow import FlowNode, ProductFlow
from models.prototype import PrototypePage, PrototypeSpec
from models.revision import PlanRevisionResult
from models.state import (
    AgentStage,
    AgentState,
    GenerationOptions,
    ProductAnalysis,
    TaskContext,
)


class CountingGenerator:
    def __init__(self, result):
        self.result = result
        self.calls = 0

    def generate(self, *args):
        self.calls += 1
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


class Analyzer:
    def analyze(self, state):
        return ProductAnalysis(problems=["问题"])


class Finalizer:
    def finalize(self, state):
        return plan(1)


class Reviser:
    def revise(self, state, feedback):
        return PlanRevisionResult(revised_plan=plan(2), revision_summary=[feedback])


def plan(version: int) -> FinalProductPlan:
    return FinalProductPlan(title=f"方案 V{version}", summary="核心方案")


def flow() -> ProductFlow:
    return ProductFlow(title="业务流程", nodes=[FlowNode(id="n1", label="开始", node_type="start")])


def prototype() -> PrototypeSpec:
    return PrototypeSpec(
        title="交互原型",
        description="MVP 交互",
        default_page="home",
        pages=[PrototypePage(id="home", title="首页", page_type="dashboard")],
    )


def runtime() -> tuple[PMCopilotRuntime, CountingGenerator, CountingGenerator]:
    instance = PMCopilotRuntime.__new__(PMCopilotRuntime)
    instance.product_analyzer = Analyzer()
    instance.finalizer = Finalizer()
    instance.plan_reviser = Reviser()
    flow_generator = CountingGenerator(flow())
    prototype_planner = CountingGenerator(prototype())
    instance.flow_generator = flow_generator
    instance.prototype_planner = prototype_planner
    instance.last_generation_status = {}
    return instance, flow_generator, prototype_planner


def state(options: GenerationOptions, stage: AgentStage = AgentStage.ANALYZING) -> AgentState:
    return AgentState(
        task=TaskContext(
            task_id="generation-options",
            title="生成选项",
            original_request="生成产品方案",
            current_stage=stage,
            generation_options=options,
        ),
        final_output=plan(1) if stage == AgentStage.WAITING_REVIEW else None,
    )


def main() -> None:
    # Case A: the legacy Flow option is ignored; AI still decides the outcome.
    instance, flow_generator, prototype_planner = runtime()
    core_only = instance.run_product_analysis(state(GenerationOptions(generate_flow=False)))
    assert core_only.final_output is not None
    assert core_only.product_flow is not None
    assert flow_generator.calls == 1 and prototype_planner.calls == 0

    # Case B: core plan plus flow.
    instance, flow_generator, prototype_planner = runtime()
    with_flow = instance.run_product_analysis(state(GenerationOptions(generate_flow=True)))
    assert with_flow.product_flow is not None
    assert flow_generator.calls == 1 and prototype_planner.calls == 0

    # Case C: the legacy prototype option no longer affects the main workflow.
    instance, flow_generator, prototype_planner = runtime()
    with_prototype = instance.run_product_analysis(state(GenerationOptions(generate_flow=False, generate_prototype=True)))
    assert with_prototype.prototype_spec is None
    assert flow_generator.calls == 1 and prototype_planner.calls == 0

    # Case D: all optional capabilities are available; report remains on demand.
    instance, flow_generator, prototype_planner = runtime()
    all_enabled = instance.run_product_analysis(state(GenerationOptions(generate_flow=True, generate_prototype=True, generate_report=True)))
    assert all_enabled.product_flow is not None and all_enabled.prototype_spec is None
    assert all_enabled.task.generation_options.generate_report is True
    assert flow_generator.calls == 1 and prototype_planner.calls == 0

    # Case E: revision regenerates only enabled artifacts.
    instance, flow_generator, prototype_planner = runtime()
    revision = state(GenerationOptions(generate_flow=True, generate_prototype=False), AgentStage.WAITING_REVIEW)
    instance.handle_review(revision, approved=False, feedback="增加条件")
    assert revision.final_output == plan(2)
    assert flow_generator.calls == 1 and prototype_planner.calls == 0

    # Case F: legacy JSON uses defaults.
    payload = json.loads(revision.model_dump_json())
    payload["task"].pop("generation_options")
    legacy = AgentState.model_validate(payload)
    assert legacy.task.generation_options == GenerationOptions()

    # Optional artifact failure is recorded but cannot block the core plan.
    instance, flow_generator, prototype_planner = runtime()
    flow_generator.result = ValueError("flow failed")
    degraded = instance.run_product_analysis(state(GenerationOptions(generate_flow=True)))
    assert degraded.task.current_stage == AgentStage.WAITING_REVIEW
    assert degraded.final_output is not None and degraded.product_flow is None
    assert instance.last_generation_status["flow"] == "failed"

    print("Case A: legacy Flow option did not disable automatic Flow judgment")
    print("Case B: Flow generated without Prototype")
    print("Case C: legacy Prototype option did not run the planner")
    print("Case D: Flow generated while Prototype remained on demand")
    print("Case E: Review Revision regenerated enabled artifacts only")
    print("Case F: Legacy Task restored default GenerationOptions")
    print("Optional artifact failure: degraded without blocking Final Plan")


if __name__ == "__main__":
    main()

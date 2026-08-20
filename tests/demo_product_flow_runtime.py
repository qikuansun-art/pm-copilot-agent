"""Regression coverage for ProductFlow lifecycle and persistence."""

import json
from pathlib import Path

from agent.runtime import PMCopilotRuntime
from api.task_store import TaskStore
from models.final_output import FinalProductPlan
from models.flow import FlowEdge, FlowNode, ProductFlow
from models.prototype import PrototypePage, PrototypeSpec
from models.revision import PlanRevisionResult
from models.state import AgentStage, AgentState, GenerationOptions, ProductAnalysis, TaskContext


def final_plan(version: int) -> FinalProductPlan:
    """Build a small versioned maintenance plan."""
    return FinalProductPlan(
        title=f"维修工单方案 V{version}",
        summary="建立维修工单闭环。",
        problems=["维修过程不可追踪"],
        target_users=["操作员", "维修主管", "维修人员"],
        key_scenarios=["设备故障报修"],
        requirements=["创建工单", "主管派单", f"V{version} 维修处理"],
        solution=["使用工单串联维修流程"],
        mvp_scope=["报修", "派单", "维修确认"],
    )


def flow(version: int) -> ProductFlow:
    """Build a valid versioned flow."""
    return ProductFlow(
        title=f"维修流程 V{version}",
        nodes=[
            FlowNode(id="n1", label="发现故障", node_type="start"),
            FlowNode(id="n2", label="创建工单"),
            FlowNode(id="n3", label=f"V{version}维修处理"),
            FlowNode(id="n4", label="确认完成", node_type="end"),
        ],
        edges=[
            FlowEdge(source="n1", target="n2"),
            FlowEdge(source="n2", target="n3"),
            FlowEdge(source="n3", target="n4"),
        ],
    )


def prototype(version: int) -> PrototypeSpec:
    """Build a valid versioned prototype spec."""
    return PrototypeSpec(
        title=f"维修原型 V{version}",
        description="维修工单交互原型",
        default_page="dashboard",
        pages=[PrototypePage(id="dashboard", title=f"V{version}工单概览", page_type="dashboard")],
    )


class StubAnalyzer:
    """Return stable product analysis."""

    def analyze(self, state):
        return ProductAnalysis(problems=["维修过程不可追踪"])


class StubFinalizer:
    """Return one prepared final plan."""

    def __init__(self, output: FinalProductPlan) -> None:
        self.output = output

    def finalize(self, state):
        return self.output


class SequenceFlowGenerator:
    """Return or raise prepared outcomes while counting calls."""

    def __init__(self, outcomes: list[object]) -> None:
        self.outcomes = outcomes
        self.calls = 0

    def generate(self, original_request, final_output):
        outcome = self.outcomes[self.calls]
        self.calls += 1
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


class SequencePrototypePlanner:
    """Return prepared prototype versions while counting calls."""

    def __init__(self, outcomes: list[object]) -> None:
        self.outcomes = outcomes
        self.calls = 0

    def generate(self, original_request, final_output, product_flow):
        outcome = self.outcomes[self.calls]
        self.calls += 1
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


class SequenceReviser:
    """Return prepared final-plan versions."""

    def __init__(self, outputs: list[FinalProductPlan]) -> None:
        self.outputs = outputs
        self.calls = 0

    def revise(self, state, feedback):
        output = self.outputs[self.calls]
        self.calls += 1
        return PlanRevisionResult(
            revised_plan=output,
            revision_summary=[f"已应用：{feedback}"],
        )


def analysis_runtime(flow_outcome: object) -> PMCopilotRuntime:
    """Build a Runtime limited to analysis/finalization dependencies."""
    runtime = PMCopilotRuntime.__new__(PMCopilotRuntime)
    runtime.product_analyzer = StubAnalyzer()
    runtime.finalizer = StubFinalizer(final_plan(1))
    runtime.flow_generator = SequenceFlowGenerator([flow_outcome])
    runtime.prototype_planner = SequencePrototypePlanner([prototype(1)])
    return runtime


def analyzing_state(task_id: str) -> AgentState:
    return AgentState(
        task=TaskContext(
            task_id=task_id,
            title="维修工单",
            original_request="规划设备维修工单流程",
            current_stage=AgentStage.ANALYZING,
            generation_options=GenerationOptions(generate_prototype=True),
        )
    )


def main() -> None:
    """Cover initial generation, revisions, approval, SQLite, and legacy JSON."""
    # Cases A-C: flow success, no flow, and generation failure are non-blocking.
    generated = analysis_runtime(flow(1)).run_product_analysis(
        analyzing_state("flow-generated")
    )
    assert generated.task.current_stage == AgentStage.WAITING_REVIEW
    assert generated.final_output is not None
    assert generated.product_flow == flow(1)
    assert generated.prototype_spec == prototype(1)

    no_flow = analysis_runtime(None).run_product_analysis(
        analyzing_state("flow-none")
    )
    assert no_flow.task.current_stage == AgentStage.WAITING_REVIEW
    assert no_flow.final_output is not None
    assert no_flow.product_flow is None

    failed_flow = analysis_runtime(ValueError("invalid flow")).run_product_analysis(
        analyzing_state("flow-failed")
    )
    assert failed_flow.task.current_stage == AgentStage.WAITING_REVIEW
    assert failed_flow.final_output is not None
    assert failed_flow.product_flow is None

    # Cases D-E: both review revisions and added conditions regenerate flow.
    runtime = PMCopilotRuntime.__new__(PMCopilotRuntime)
    runtime.plan_reviser = SequenceReviser([final_plan(2), final_plan(3)])
    runtime.flow_generator = SequenceFlowGenerator([flow(2), flow(3)])
    runtime.prototype_planner = SequencePrototypePlanner([prototype(2), prototype(3)])
    revision_state = AgentState(
        task=TaskContext(
            task_id="flow-revisions",
            title="维修工单",
            original_request="规划设备维修工单流程",
            current_stage=AgentStage.WAITING_REVIEW,
            generation_options=GenerationOptions(generate_prototype=True),
        ),
        final_output=final_plan(1),
        product_flow=flow(1),
        prototype_spec=prototype(1),
    )
    runtime.handle_review(revision_state, approved=False, feedback="增加维修结果")
    assert revision_state.task.plan_version == 2
    assert revision_state.product_flow == flow(2)
    assert revision_state.product_flow != flow(1)
    assert revision_state.prototype_spec == prototype(2)

    runtime.handle_review(revision_state, approved=True)
    assert revision_state.task.current_stage == AgentStage.COMPLETED
    runtime.revise_completed_task(revision_state, "增加操作员确认")
    assert revision_state.task.plan_version == 3
    assert revision_state.product_flow == flow(3)
    assert revision_state.prototype_spec == prototype(3)
    assert runtime.flow_generator.calls == 2

    # Case F: approval preserves flow and does not call the generator.
    approved_flow = revision_state.product_flow
    approved_prototype = revision_state.prototype_spec
    calls_before_approve = runtime.flow_generator.calls
    prototype_calls_before_approve = runtime.prototype_planner.calls
    runtime.handle_review(revision_state, approved=True)
    assert revision_state.task.current_stage == AgentStage.COMPLETED
    assert revision_state.product_flow == approved_flow
    assert revision_state.prototype_spec == approved_prototype
    assert runtime.flow_generator.calls == calls_before_approve
    assert runtime.prototype_planner.calls == prototype_calls_before_approve

    # Case G: complete ProductFlow survives TaskStore recreation.
    db_path = Path("data/test_product_flow_tasks.db")
    if db_path.exists():
        db_path.unlink()
    try:
        TaskStore(db_path).save(revision_state)
        restored = TaskStore(db_path).get(revision_state.task.task_id)
        assert restored is not None
        assert restored.product_flow == flow(3)
        assert restored.prototype_spec == prototype(3)
    finally:
        if db_path.exists():
            db_path.unlink()

    # Case H: old JSON without product_flow keeps the Pydantic default None.
    legacy_payload = json.loads(revision_state.model_dump_json())
    legacy_payload.pop("product_flow")
    legacy_payload.pop("prototype_spec")
    legacy = AgentState.model_validate(legacy_payload)
    assert legacy.product_flow is None
    assert legacy.prototype_spec is None

    print("Cases A-C: initial flow outcomes remain WAITING_REVIEW")
    print("Case D: Review Revision regenerated V2 flow")
    print("Case E: Added Condition regenerated V3 flow")
    print("Case F: Approve preserved flow without a generator call")
    print("Case G: SQLite restored", restored.product_flow.title, restored.prototype_spec.title)
    print("Case H: legacy product_flow and prototype_spec are None")


if __name__ == "__main__":
    main()

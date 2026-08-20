"""Runtime orchestration for the initial PM Copilot state transition."""

from agent.requirement_understanding import RequirementUnderstandingService
from agent.planner import PMPlanner
from agent.product_analyzer import ProductAnalyzer
from agent.research_planner import ResearchPlanner
from agent.finalizer import ProductPlanFinalizer
from agent.plan_reviser import ProductPlanReviser
from models.research import ResearchPlan
from models.state import AgentStage, AgentState, Message, ReviewFeedback
from models.state import Evidence, ToolCall
from tools.knowledge_search import KnowledgeSearchTool
from tools.web_search import WebSearchTool


class PMCopilotRuntime:
    """Coordinates requirement understanding and updates the agent state."""

    def __init__(self) -> None:
        """Initialize the runtime's requirement-understanding service."""
        self.requirement_understanding = RequirementUnderstandingService()
        self.planner = PMPlanner()
        self.research_planner = ResearchPlanner()
        self.knowledge_search = KnowledgeSearchTool()
        self.web_search = WebSearchTool()
        self.product_analyzer = ProductAnalyzer()
        self.finalizer = ProductPlanFinalizer()
        self.plan_reviser = ProductPlanReviser()

    def start_task(self, state: AgentState) -> AgentState:
        """Run requirement understanding and advance the supplied task state."""
        state.task.current_stage = AgentStage.UNDERSTANDING

        result = self.requirement_understanding.understand(
            state.task.original_request
        )

        state.task.known_facts = result.known_facts
        state.task.missing_information = result.missing_information

        if result.need_clarification and result.questions:
            state.task.current_stage = AgentStage.WAITING_CLARIFICATION
            for item in result.questions:
                state.messages.append(
                    Message(
                        role="assistant",
                        content=f"{item.question}\n原因：{item.reason}",
                    )
                )
        else:
            state.task.current_stage = AgentStage.PLANNING

        return state

    def create_research_plan(self, state: AgentState) -> ResearchPlan:
        """Create and return research queries for a researching task."""
        if state.task.current_stage != AgentStage.RESEARCHING:
            raise ValueError("Task is not in the researching stage")

        return self.research_planner.create_research_plan(state)

    def run_internal_research(
        self,
        state: AgentState,
        query: str,
    ) -> AgentState:
        """Search internal knowledge and record its tool call and evidence."""
        if state.task.current_stage != AgentStage.RESEARCHING:
            raise ValueError("Task is not in the researching stage")

        results = self.knowledge_search.search(
            query,
            knowledge_group_ids=state.task.knowledge_group_ids,
        )
        formatted_results = "\n\n".join(
            f"[{item.source_type}] {item.source}\n"
            f"{item.content}\n"
            f"score: {item.score:.2f}"
            for item in results
        )
        readable_results = f"query: {query}"
        if formatted_results:
            readable_results = f"{readable_results}\n\n{formatted_results}"
        state.tool_calls.append(
            ToolCall(
                tool_name="knowledge_search",
                input={"query": query},
                result=readable_results,
                status="completed",
            )
        )

        for item in results:
            state.evidence.append(
                Evidence(
                    content=item.content,
                    source_type=item.source_type,
                    source=item.source,
                    confidence=(
                        "high"
                        if item.score >= 0.8
                        else "medium"
                        if item.score >= 0.5
                        else "low"
                    ),
                )
            )

        if state.plan is not None:
            for step in state.plan.steps:
                if step.title == "内部资料检索":
                    step.status = "completed"
                elif step.title == "外部行业调研":
                    step.status = "running"

        state.task.current_stage = AgentStage.RESEARCHING
        return state

    def handle_clarification_response(
        self,
        state: AgentState,
        user_response: str,
    ) -> AgentState:
        """Record a clarification response and advance the task to planning."""
        if state.task.current_stage != AgentStage.WAITING_CLARIFICATION:
            raise ValueError("Task is not waiting for clarification")

        state.messages.append(Message(role="user", content=user_response))
        state.task.known_facts.append(f"用户补充：{user_response}")
        state.task.missing_information = []
        state.task.current_stage = AgentStage.PLANNING

        return state

    def run_external_research(
        self,
        state: AgentState,
        query: str,
    ) -> AgentState:
        """Search mock web sources and record external research evidence."""
        if state.task.current_stage != AgentStage.RESEARCHING:
            raise ValueError("Task is not in the researching stage")

        results = self.web_search.search(query)
        readable_results = "\n\n".join(
            f"title: {item.title}\n"
            f"snippet: {item.snippet}\n"
            f"source: {item.source}"
            for item in results
        )
        state.tool_calls.append(
            ToolCall(
                tool_name="web_search",
                input={"query": query},
                result=readable_results,
                status="completed",
            )
        )

        for item in results:
            state.evidence.append(
                Evidence(
                    content=f"{item.title}: {item.snippet}",
                    source_type="web",
                    source=item.source,
                    confidence="medium",
                )
            )

        if state.plan is not None:
            for step in state.plan.steps:
                if step.title == "外部行业调研":
                    step.status = "completed"
                elif step.title == "问题与场景分析":
                    step.status = "running"

        state.task.current_stage = AgentStage.ANALYZING
        return state

    def create_plan(self, state: AgentState) -> AgentState:
        """Create the initial plan and advance the task to research."""
        if state.task.current_stage != AgentStage.PLANNING:
            raise ValueError("Task is not ready for planning")

        state.plan = self.planner.create_plan(state)
        state.task.current_stage = AgentStage.RESEARCHING

        for step in state.plan.steps:
            if step.status == "pending":
                step.status = "running"
                break

        return state

    def run_product_analysis(self, state: AgentState) -> AgentState:
        """Produce product analysis and advance the task to human review."""
        if state.task.current_stage != AgentStage.ANALYZING:
            raise ValueError("Task is not in the analyzing stage")

        state.analysis = self.product_analyzer.analyze(state)
        state.final_output = self.finalizer.finalize(state)

        if state.plan is not None:
            for step in state.plan.steps:
                if step.title in {"问题与场景分析", "MVP 范围设计"}:
                    step.status = "completed"
                elif step.title == "生成产品方案":
                    step.status = "running"

        state.task.current_stage = AgentStage.WAITING_REVIEW
        return state

    def handle_review(
        self,
        state: AgentState,
        approved: bool,
        feedback: str | None = None,
    ) -> AgentState:
        """Record human review feedback and finalize the product plan."""
        if state.task.current_stage != AgentStage.WAITING_REVIEW:
            raise ValueError("Task is not waiting for review")
        if not approved and not feedback:
            raise ValueError("Feedback is required when review is not approved")

        if not approved:
            return self._revise_plan(state, feedback or "", "review_feedback")

        state.task.current_stage = AgentStage.FINALIZING
        if state.final_output is None:
            state.final_output = self.finalizer.finalize(state)

        if state.plan is not None:
            # COMPLETED is a terminal state: no plan step may remain active.
            # Do not depend on LLM-generated titles when enforcing this invariant.
            for step in state.plan.steps:
                step.status = "completed"

        state.task.current_stage = AgentStage.COMPLETED
        return state

    def revise_completed_task(
        self,
        state: AgentState,
        feedback: str,
    ) -> AgentState:
        """Apply a new condition to a completed task as its next plan version."""
        if state.task.current_stage != AgentStage.COMPLETED:
            raise ValueError("Task is not completed")
        if not feedback.strip():
            raise ValueError("Revision feedback is required")
        return self._revise_plan(state, feedback, "added_condition")

    def _revise_plan(
        self,
        state: AgentState,
        feedback: str,
        revision_type: str,
    ) -> AgentState:
        """Run one focused revision and retain its versioned history."""
        version_from = state.task.plan_version
        revision = self.plan_reviser.revise(state, feedback)
        state.review_feedback.append(
            ReviewFeedback(
                version=version_from + 1,
                version_from=version_from,
                version_to=version_from + 1,
                feedback=feedback,
                revision_summary=revision.revision_summary,
                revision_type=revision_type,
            )
        )
        state.task.plan_version = version_from + 1
        state.final_output = revision.revised_plan
        state.task.current_stage = AgentStage.WAITING_REVIEW
        if state.plan is not None and state.plan.steps:
            # A revision reopens only the final step. Normalize stale statuses
            # from earlier versions before marking that step as active.
            for step in state.plan.steps:
                step.status = "completed"
            state.plan.steps[-1].status = "running"
        return state

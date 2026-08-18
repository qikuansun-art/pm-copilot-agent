"""Runtime orchestration for the initial PM Copilot state transition."""

from agent.requirement_understanding import RequirementUnderstandingService
from agent.planner import PMPlanner
from agent.product_analyzer import ProductAnalyzer
from agent.finalizer import ProductPlanFinalizer
from models.state import AgentStage, AgentState, Message
from models.state import Decision, Evidence, ToolCall
from tools.knowledge_search import KnowledgeSearchTool
from tools.web_search import WebSearchTool


class PMCopilotRuntime:
    """Coordinates requirement understanding and updates the agent state."""

    def __init__(self) -> None:
        """Initialize the runtime's requirement-understanding service."""
        self.requirement_understanding = RequirementUnderstandingService()
        self.planner = PMPlanner()
        self.knowledge_search = KnowledgeSearchTool()
        self.web_search = WebSearchTool()
        self.product_analyzer = ProductAnalyzer()
        self.finalizer = ProductPlanFinalizer()

    def start_task(self, state: AgentState) -> AgentState:
        """Run requirement understanding and advance the supplied task state."""
        state.task.current_stage = AgentStage.UNDERSTANDING

        result = self.requirement_understanding.understand(
            state.task.original_request
        )

        state.task.known_facts = result.known_facts
        state.task.missing_information = result.missing_information

        if result.need_clarification:
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

    def run_internal_research(
        self,
        state: AgentState,
        query: str,
    ) -> AgentState:
        """Search internal knowledge and record its tool call and evidence."""
        if state.task.current_stage != AgentStage.RESEARCHING:
            raise ValueError("Task is not in the researching stage")

        results = self.knowledge_search.search(query)
        state.tool_calls.append(
            ToolCall(
                tool_name="knowledge_search",
                input={"query": query},
                result="\n".join(results),
                status="completed",
            )
        )

        for item in results:
            state.evidence.append(
                Evidence(
                    content=item,
                    source_type="knowledge",
                    source="knowledge/cnc_context.md",
                    confidence="high",
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

        if feedback:
            state.messages.append(Message(role="user", content=feedback))
            state.decisions.append(
                Decision(
                    decision=feedback,
                    reason="用户在方案 Review 阶段提出修改意见",
                    decided_by="user",
                )
            )

        state.task.current_stage = AgentStage.FINALIZING
        state.final_output = self.finalizer.finalize(state)

        if state.plan is not None:
            for step in state.plan.steps:
                if step.title == "生成产品方案":
                    step.status = "completed"

        state.task.current_stage = AgentStage.COMPLETED
        return state

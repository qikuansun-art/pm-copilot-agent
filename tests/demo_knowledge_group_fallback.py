"""Demonstrate scoped retrieval fallback for explicitly selected groups."""

from pathlib import Path
from unittest.mock import patch

from agent.runtime import PMCopilotRuntime
from knowledge.document_store import DocumentStore
from models.state import AgentStage, AgentState, TaskContext
from tools.knowledge_search import KnowledgeSearchTool


def main() -> None:
    """Verify weak group matches become low-confidence fallback evidence."""
    test_db_path = Path("data/test_knowledge_group_fallback.db")
    if test_db_path.exists():
        test_db_path.unlink()

    try:
        store = DocumentStore(test_db_path)
        tooling_group = store.create_group("刀具管理")
        store.add_document(
            "tool_management.md",
            [
                "刀具管理需要建立工艺与刀具关联，并根据累计加工时长进行寿命统计。"
                "人工换刀后需要更新刀具状态。"
            ],
            group_id=tooling_group.group_id,
        )
        tool = KnowledgeSearchTool()
        runtime = PMCopilotRuntime.__new__(PMCopilotRuntime)
        runtime.knowledge_search = tool

        with patch("tools.knowledge_search.document_store", store):
            query = "CNC 刀具管理 内部工艺关联 寿命管理 设备换刀流程"
            results = tool.search(
                query,
                knowledge_group_ids=[tooling_group.group_id],
            )
            print("fallback results:", results)
            assert len(results) == 1
            assert results[0].source == "tool_management.md"
            assert results[0].source_type == "uploaded_document"
            assert 0 < results[0].score < 0.5

            state = AgentState(
                task=TaskContext(
                    task_id="knowledge-group-fallback-demo",
                    title="刀具管理规划",
                    original_request="帮我规划 CNC 刀具管理",
                    current_stage=AgentStage.RESEARCHING,
                    knowledge_group_ids=[tooling_group.group_id],
                )
            )
            runtime.run_internal_research(state, query)
            assert len(state.evidence) == 1
            assert state.evidence[0].source == "tool_management.md"
            assert state.evidence[0].confidence == "low"
            tool_result = state.tool_calls[-1].result
            assert f"query: {query}" in tool_result
            assert "tool_management.md" in tool_result
            assert results[0].content in tool_result
            assert "score: 0.20" in tool_result

            unrelated_results = tool.search(
                "完全无关的仓库盘点",
                knowledge_group_ids=[tooling_group.group_id],
            )
            print("unrelated results:", unrelated_results)
            assert unrelated_results == []
    finally:
        if test_db_path.exists():
            test_db_path.unlink()


if __name__ == "__main__":
    main()

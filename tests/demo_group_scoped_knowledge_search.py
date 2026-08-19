"""Demonstrate uploaded-knowledge retrieval scoped by task groups."""

from pathlib import Path
from unittest.mock import patch

from agent.runtime import PMCopilotRuntime
from knowledge.document_store import DocumentStore
from models.state import AgentStage, AgentState, TaskContext
from tools.knowledge_search import KnowledgeSearchTool


def main() -> None:
    """Verify group filtering, unrestricted search, and Runtime propagation."""
    test_db_path = Path("data/test_group_scoped_search.db")
    if test_db_path.exists():
        test_db_path.unlink()

    try:
        store = DocumentStore(test_db_path)
        stone_group = store.create_group("荒料加工")
        tooling_group = store.create_group("刀具管理")
        store.add_document(
            "stone_group.md",
            ["荒料加工包括量尺、领料、大切和扫描。"],
            group_id=stone_group.group_id,
        )
        store.add_document(
            "tooling_group.md",
            ["刀具管理包括刀具寿命、换刀和刀具状态。"],
            group_id=tooling_group.group_id,
        )

        tool = KnowledgeSearchTool()
        with patch("tools.knowledge_search.document_store", store):
            stone_results = tool.search(
                "荒料 加工",
                knowledge_group_ids=[stone_group.group_id],
            )
            print("stone group results:", stone_results)
            assert any(item.source == "stone_group.md" for item in stone_results)
            assert not any(item.source == "tooling_group.md" for item in stone_results)

            tooling_results = tool.search(
                "刀具 寿命",
                knowledge_group_ids=[tooling_group.group_id],
            )
            print("tooling group results:", tooling_results)
            assert any(item.source == "tooling_group.md" for item in tooling_results)
            assert not any(item.source == "stone_group.md" for item in tooling_results)

            unrestricted_results = tool.search(
                "加工 刀具",
                knowledge_group_ids=[],
            )
            print("unrestricted results:", unrestricted_results)
            unrestricted_sources = {item.source for item in unrestricted_results}
            assert "stone_group.md" in unrestricted_sources
            assert "tooling_group.md" in unrestricted_sources

            runtime = PMCopilotRuntime.__new__(PMCopilotRuntime)
            runtime.knowledge_search = tool
            state = AgentState(
                task=TaskContext(
                    task_id="group-scoped-runtime-demo",
                    title="荒料加工规划",
                    original_request="帮我规划荒料加工管理",
                    current_stage=AgentStage.RESEARCHING,
                    knowledge_group_ids=[stone_group.group_id],
                )
            )
            runtime.run_internal_research(state, "刀具 寿命")
            print("runtime evidence:", state.evidence)
            assert state.evidence
            assert not any(item.source == "tooling_group.md" for item in state.evidence)
    finally:
        if test_db_path.exists():
            test_db_path.unlink()


if __name__ == "__main__":
    main()

"""Regression coverage for uploaded-document retrieval fallback."""

from pathlib import Path
from unittest.mock import patch

from knowledge.document_store import DocumentStore
from tools.knowledge_search import KnowledgeSearchTool


def uploaded_sources(results) -> set[str]:
    """Return uploaded-document filenames from search results."""
    return {
        item.source
        for item in results
        if item.source_type == "uploaded_document"
    }


def main() -> None:
    """Verify unrestricted, scoped, weak, and normal-match behavior."""
    test_db_path = Path("data/test_knowledge_group_fallback.db")
    if test_db_path.exists():
        test_db_path.unlink()

    try:
        store = DocumentStore(test_db_path)
        stone_group = store.create_group("荒料加工")
        tooling_group = store.create_group("刀具管理")
        store.add_document(
            "stone_block_processing.md",
            ["石材荒料入库后进入大切加工流程。"],
            group_id=stone_group.group_id,
        )
        store.add_document(
            "tool_management.md",
            ["刀具管理需要覆盖工艺关联和刀具寿命。"],
            group_id=tooling_group.group_id,
        )
        store.add_document(
            "single_keyword.md",
            ["这里只介绍一般加工过程。"],
            group_id=stone_group.group_id,
        )
        store.add_document(
            "normal_match.md",
            ["正常 一二 三四"],
            group_id=stone_group.group_id,
        )
        store.add_document(
            "weak_two_matches.md",
            ["低分 资料"],
            group_id=stone_group.group_id,
        )

        tool = KnowledgeSearchTool()
        cross_domain_query = "石材荒料 大切 刀具管理 排版 寿命"

        with patch("tools.knowledge_search.document_store", store):
            # Case A: unrestricted fallback searches all uploaded documents.
            unrestricted = tool.search(cross_domain_query, knowledge_group_ids=[])
            assert uploaded_sources(unrestricted) == {
                "stone_block_processing.md",
                "tool_management.md",
            }
            assert all(item.score == 0.4 for item in unrestricted)

            # Case B: fallback remains inside the selected group boundary.
            stone_only = tool.search(
                cross_domain_query,
                knowledge_group_ids=[stone_group.group_id],
            )
            assert uploaded_sources(stone_only) == {"stone_block_processing.md"}

            # Case C: one-token matches cannot enter fallback.
            one_token_query = "石材荒料 大切 刀具管理 排版 加工"
            one_token_results = tool.search(one_token_query, knowledge_group_ids=[])
            assert "single_keyword.md" not in uploaded_sources(one_token_results)

            # Case D: a normal uploaded match suppresses all weak fallbacks.
            normal_query = "正常 一二 三四 低分 资料"
            normal_results = tool.search(normal_query, knowledge_group_ids=[])
            assert uploaded_sources(normal_results) == {"normal_match.md"}
            assert next(
                item for item in normal_results if item.source == "normal_match.md"
            ).score == 0.6

        print("Case A:", sorted(uploaded_sources(unrestricted)))
        print("Case B:", sorted(uploaded_sources(stone_only)))
        print("Case C: single_keyword.md excluded")
        print("Case D:", sorted(uploaded_sources(normal_results)))
    finally:
        if test_db_path.exists():
            test_db_path.unlink()


if __name__ == "__main__":
    main()

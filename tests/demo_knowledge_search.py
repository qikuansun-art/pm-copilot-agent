"""Demonstrate retrieval across uploaded and built-in knowledge."""

from math import isclose

from knowledge.document_store import document_store
from tools.knowledge_search import KnowledgeSearchTool


def main() -> None:
    """Verify ranking and matching for uploaded and built-in knowledge."""
    document = document_store.add_document(
        filename="stone_block_processing.md",
        chunks=[
            "荒料入库后需要记录荒料编号、材质和尺寸。",
            "荒料加工流程包括量尺、领料、大切、背网、粗磨、刷胶和表面处理。",
            "加工完成后扫描图片，用于库存管理和销售展示。",
        ],
    )
    tool = KnowledgeSearchTool()

    try:
        stone_results = tool.search("荒料 加工 扫描")
        print("query: 荒料 加工 扫描")
        for item in stone_results:
            print("content:", item.content)
            print("source:", item.source)
            print("source_type:", item.source_type)
            print("score:", item.score)
        assert [item.content for item in stone_results] == [
            "荒料加工流程包括量尺、领料、大切、背网、粗磨、刷胶和表面处理。",
            "加工完成后扫描图片，用于库存管理和销售展示。",
        ]
        assert all(item.source == "stone_block_processing.md" for item in stone_results)
        assert all(item.source_type == "uploaded_document" for item in stone_results)
        assert all(isclose(item.score, 2 / 3) for item in stone_results)
        assert not any("刀具寿命第一阶段" in item.content for item in stone_results)

        tool_results = tool.search("刀具 寿命")
        print("\nquery: 刀具 寿命")
        for item in tool_results:
            print("content:", item.content)
            print("source:", item.source)
            print("source_type:", item.source_type)
            print("score:", item.score)
        assert tool_results
        tool_life_result = next(
            item for item in tool_results if "刀具寿命" in item.content
        )
        assert tool_life_result.source == "knowledge/cnc_context.md"
        assert tool_life_result.source_type == "builtin"
        assert tool_life_result.score == 1.0

        missing_results = tool.search("完全不存在")
        print("\nquery: 完全不存在")
        print("results:", missing_results)
        assert missing_results == []
    finally:
        document_store.delete_document(document.document_id)


if __name__ == "__main__":
    main()

"""Demonstrate keyword searches over the local CNC knowledge base."""

from tools.knowledge_search import KnowledgeSearchTool


def main() -> None:
    """Run and print the four requested knowledge-search queries."""
    tool = KnowledgeSearchTool()

    for query in ["刀具", "自动换刀", "寿命", "不存在的内容"]:
        print(f"query: {query}")
        print("results:", tool.search(query))


if __name__ == "__main__":
    main()

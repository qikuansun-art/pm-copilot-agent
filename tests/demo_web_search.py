"""Demonstrate the empty V1 web-search adapter behavior."""

from tools.web_search import WebSearchTool


def main() -> None:
    """Verify that all queries return no results without a real provider."""
    tool = WebSearchTool()

    queries = [
        "CNC 刀具管理 tool life",
        "石材荒料加工流程",
        "库存管理系统",
    ]
    for query in queries:
        results = tool.search(query)
        assert results == [], f"Expected no web results for query: {query}"
        print(f"query: {query}")
        print("results: []")


if __name__ == "__main__":
    main()

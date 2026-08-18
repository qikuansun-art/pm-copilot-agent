"""Demonstrate relevant and unrelated mock web searches."""

from tools.web_search import WebSearchTool


def main() -> None:
    """Run and print the two requested mock web-search scenarios."""
    tool = WebSearchTool()

    for query in ["CNC 刀具管理 tool life", "完全无关内容"]:
        print(f"query: {query}")
        results = tool.search(query)
        if not results:
            print("results: []")
            continue

        for result in results:
            print("title:", result.title)
            print("snippet:", result.snippet)
            print("source:", result.source)


if __name__ == "__main__":
    main()

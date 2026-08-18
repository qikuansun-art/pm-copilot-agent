"""Simple keyword-based search over local Markdown knowledge files."""

from pathlib import Path


class KnowledgeSearchTool:
    """Searches PM Copilot's internal Markdown knowledge by keywords."""

    def __init__(self, knowledge_dir: str = "knowledge") -> None:
        """Initialize the tool with the directory containing knowledge files."""
        self.knowledge_dir = Path(knowledge_dir)

    def search(self, query: str) -> list[str]:
        """Return up to ten non-empty lines matching any query keyword."""
        keywords = query.split()
        if not keywords or not self.knowledge_dir.is_dir():
            return []

        results: list[str] = []
        for file_path in sorted(self.knowledge_dir.glob("*.md")):
            with file_path.open(encoding="utf-8") as knowledge_file:
                for raw_line in knowledge_file:
                    line = raw_line.strip()
                    if line and any(keyword in line for keyword in keywords):
                        results.append(line)
                        if len(results) == 10:
                            return results

        return results

"""Structured keyword retrieval over built-in and uploaded knowledge."""

from pathlib import Path

from knowledge.document_store import document_store
from models.knowledge import KnowledgeSearchResult

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_KNOWLEDGE_DIR = PROJECT_ROOT / "knowledge"


class KnowledgeSearchTool:
    """Searches built-in Markdown and uploaded document chunks."""

    def __init__(self, knowledge_dir: str | Path = DEFAULT_KNOWLEDGE_DIR) -> None:
        """Initialize the tool with the directory containing knowledge files."""
        self.knowledge_dir = Path(knowledge_dir)

    def search(
        self,
        query: str,
        knowledge_group_ids: list[str] | None = None,
    ) -> list[KnowledgeSearchResult]:
        """Return up to ten structured matches with keyword relevance scores."""
        keywords = list(dict.fromkeys(query.split()))
        if not keywords:
            return []

        candidates: list[KnowledgeSearchResult] = []
        uploaded_fallback_candidates: list[KnowledgeSearchResult] = []
        allowed_group_ids = set(knowledge_group_ids or [])
        restrict_uploaded_documents = bool(allowed_group_ids)

        for document in document_store.list_documents():
            if (
                restrict_uploaded_documents
                and document.group_id not in allowed_group_ids
            ):
                continue
            for chunk in document_store.get_chunks(document.document_id):
                content = chunk.content.strip()
                if not content:
                    continue
                match_count = sum(1 for keyword in keywords if keyword in content)
                score = match_count / len(keywords)
                result = KnowledgeSearchResult(
                    content=content,
                    source=chunk.filename,
                    source_type="uploaded_document",
                    score=score,
                )
                if score >= 0.5:
                    candidates.append(result)
                if score > 0 and match_count >= 2:
                    uploaded_fallback_candidates.append(result)

        if self.knowledge_dir.is_dir():
            for file_path in sorted(self.knowledge_dir.glob("*.md")):
                with file_path.open(encoding="utf-8") as knowledge_file:
                    for raw_line in knowledge_file:
                        content = raw_line.strip()
                        if not content or content.startswith("#"):
                            continue
                        match_count = sum(
                            1 for keyword in keywords if keyword in content
                        )
                        score = match_count / len(keywords)
                        if score >= 0.5:
                            candidates.append(
                                KnowledgeSearchResult(
                                    content=content,
                                    source=file_path.as_posix(),
                                    source_type="builtin",
                                    score=score,
                                )
                            )

        candidates.sort(
            key=lambda item: (
                -item.score,
                0 if item.source_type == "uploaded_document" else 1,
            )
        )

        results: list[KnowledgeSearchResult] = []
        seen: set[str] = set()
        for candidate in candidates:
            if candidate.content in seen:
                continue
            seen.add(candidate.content)
            results.append(candidate)
            if len(results) == 10:
                break

        if any(item.source_type == "uploaded_document" for item in results):
            return results

        uploaded_fallback_candidates.sort(key=lambda item: -item.score)
        fallback_count = 0
        for candidate in uploaded_fallback_candidates:
            if candidate.content in seen:
                continue
            seen.add(candidate.content)
            results.append(candidate)
            fallback_count += 1
            if fallback_count == 3 or len(results) == 10:
                break

        return results

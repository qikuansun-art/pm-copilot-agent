"""Models for uploaded-document knowledge storage."""

from pydantic import BaseModel


class DocumentRecord(BaseModel):
    """Describes one document registered in the knowledge store."""

    document_id: str
    filename: str
    source_type: str = "uploaded"
    status: str = "ready"
    chunk_count: int = 0
    group_id: str | None = None


class KnowledgeGroup(BaseModel):
    """Describes a named group of uploaded knowledge documents."""

    group_id: str
    name: str
    document_count: int = 0


class KnowledgeChunk(BaseModel):
    """Represents one text chunk belonging to an uploaded document."""

    chunk_id: str
    document_id: str
    filename: str
    content: str
    chunk_index: int
    source_type: str = "uploaded_document"


class KnowledgeSearchResult(BaseModel):
    """Represents one ranked result from internal knowledge retrieval."""

    content: str
    source: str
    source_type: str
    score: float

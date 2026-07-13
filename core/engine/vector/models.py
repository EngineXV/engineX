"""Shared dataclasses for the vector store layer."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class VectorDocument:
    """A document with its vector embedding and metadata."""

    id: str
    content: str
    embedding: list[float] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SearchResult:
    """Result of a vector similarity search."""

    id: str
    content: str
    score: float
    metadata: dict[str, Any] = field(default_factory=dict)
    # Optional fields for future chunk-level resolution
    collection: str | None = None
    document_id: str | None = None
    chunk_id: str | None = None

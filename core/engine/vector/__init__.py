"""EngineX vector store abstraction — pluggable backends for retrieval-augmented workflows."""

from .models import SearchResult, VectorDocument
from .provider import VectorStore

__all__ = ["VectorStore", "VectorDocument", "SearchResult"]

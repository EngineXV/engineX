"""Abstract VectorStore provider — plug in any vector backend."""

from abc import ABC, abstractmethod
from collections.abc import Sequence

from .models import SearchResult, VectorDocument


class VectorStore(ABC):
    """Abstract interface for vector storage and retrieval."""

    @abstractmethod
    def add(self, documents: Sequence[VectorDocument]) -> list[str]:
        """Add documents to the store, returning their IDs."""
        ...

    async def aadd(self, documents: Sequence[VectorDocument]) -> list[str]:
        """Async version of add()."""
        import asyncio

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.add, documents)

    @abstractmethod
    def search(
        self,
        query: str,
        top_k: int = 5,
        where: dict[str, object] | None = None,
    ) -> list[SearchResult]:
        """Search for documents similar to the query string."""
        ...

    async def asearch(
        self,
        query: str,
        top_k: int = 5,
        where: dict[str, object] | None = None,
    ) -> list[SearchResult]:
        """Async version of search()."""
        import asyncio

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.search(query, top_k, where),
        )

    @abstractmethod
    def delete(self, ids: list[str]) -> None:
        """Delete documents by their IDs."""
        ...

    def health(self) -> bool:
        """Check if the backend is healthy. Override in subclasses."""
        return True

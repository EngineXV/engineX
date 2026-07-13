"""ChromaDB backend for the vector store."""

import logging
from collections.abc import Sequence
from typing import Any

from engine.vector.config import get_vector_store_config
from engine.vector.models import SearchResult, VectorDocument
from engine.vector.provider import VectorStore

logger = logging.getLogger(__name__)

try:
    import chromadb  # noqa: F401
except ImportError:  # pragma: no cover
    chromadb = None  # type: ignore


class ChromaVectorStore(VectorStore):
    """Vector store backed by a local ChromaDB instance."""

    def __init__(
        self,
        collection_name: str | None = None,
        persist_directory: str | None = None,
        embedding_function: Any = None,
    ):
        if chromadb is None:
            raise ImportError(
                "chromadb is required for ChromaVectorStore. "
                "Install it with `uv add chromadb`."
            )
        cfg = get_vector_store_config()
        self.collection_name = collection_name or cfg.get("collection_name", "enginex")
        self.persist_directory = persist_directory or cfg.get(
            "persist_directory", "./.chroma_db"
        )

        if embedding_function is not None:
            self._embedding_function = embedding_function
        else:
            model_name = cfg.get("embedding_model")
            if model_name:
                self._embedding_function = (
                    chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction(
                        model_name=model_name
                    )
                )
            else:
                self._embedding_function = None

        self._client = chromadb.PersistentClient(path=self.persist_directory)
        self._collection = self._client.get_or_create_collection(
            name=self.collection_name,
            embedding_function=self._embedding_function,
        )

    def add(self, documents: Sequence[VectorDocument]) -> list[str]:
        ids = [doc.id for doc in documents]
        contents = [doc.content for doc in documents]

        # Chroma rejects empty metadata dicts; convert {} to None
        metadatas = [doc.metadata if doc.metadata else None for doc in documents]

        embeddings = None
        if all(d.embedding is not None for d in documents):
            embeddings = [d.embedding for d in documents]  # type: ignore

        self._collection.add(
            ids=ids,
            documents=contents,
            metadatas=metadatas,
            embeddings=embeddings,
        )
        return ids

    def search(
        self,
        query: str,
        top_k: int = 5,
        where: dict[str, object] | None = None,
    ) -> list[SearchResult]:
        results = self._collection.query(
            query_texts=[query],
            n_results=top_k,
            where=where,
        )
        ids = results.get("ids", [[]])[0]
        documents = results.get("documents", [[]])[0]
        distances = results.get("distances", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]

        out: list[SearchResult] = []
        for doc_id, content, dist, meta in zip(ids, documents, distances, metadatas):
            score = 1.0 - float(dist) if dist is not None else 0.0
            out.append(
                SearchResult(
                    id=doc_id,
                    content=content,
                    score=score,
                    metadata=meta if isinstance(meta, dict) else {},
                )
            )
        return out

    def delete(self, ids: list[str]) -> None:
        self._collection.delete(ids=ids)

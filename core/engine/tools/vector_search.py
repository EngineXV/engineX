"""Tool: vector_search — query the vector store."""

import json
import logging

from engine.runner.tool_registry import tool
from engine.vector.chroma import ChromaVectorStore

logger = logging.getLogger(__name__)

# Lazy initialisation
_store = None


def _get_store():
    global _store
    if _store is None:
        _store = ChromaVectorStore()
    return _store


@tool(description="Search the vector knowledge base for relevant documents.")
def vector_search(
    query: str,
    top_k: int = 5,
    where: str = "{}",
) -> str:
    """Search the vector store.

    Returns a JSON array of results.
    """
    try:
        metadata_filter = json.loads(where) if where else None
    except json.JSONDecodeError:
        return json.dumps({"error": "Invalid JSON in 'where' parameter."})

    # Chroma rejects empty dicts; treat {} as no filter
    if metadata_filter == {}:
        metadata_filter = None

    store = _get_store()
    try:
        results = store.search(query=query, top_k=top_k, where=metadata_filter)
    except Exception as exc:
        logger.exception("Vector search failed")
        return json.dumps({"error": str(exc)})

    return json.dumps(
        [
            {
                "id": r.id,
                "content": r.content,
                "score": round(r.score, 4),
                "metadata": r.metadata,
                "collection": r.collection,
                "document_id": r.document_id,
                "chunk_id": r.chunk_id,
            }
            for r in results
        ],
        indent=2,
    )

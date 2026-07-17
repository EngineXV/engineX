"""Tool: embed_and_insert — embed text and store in the vector DB."""

import logging
from typing import Any

from engine.runner.tool_registry import tool
from engine.vector.chroma import ChromaVectorStore
from engine.vector.embedding import embed
from engine.vector.models import VectorDocument

logger = logging.getLogger(__name__)

# Lazy initialisation for the store
_store = None


def _get_store() -> ChromaVectorStore:
    global _store
    if _store is None:
        _store = ChromaVectorStore()
    return _store


@tool(description="Embed text and insert it into the vector knowledge base.")
def embed_and_insert(
    text: str,
    metadata: str = "{}",
    doc_id: str = "",
) -> str:
    """Embed the given text and store it in the vector database.

    Returns the ID of the inserted document.
    """
    import json

    try:
        meta: dict[str, Any] = json.loads(metadata) if metadata else {}
    except json.JSONDecodeError:
        return json.dumps({"error": "Invalid JSON in metadata parameter."})

    # Generate a unique ID if none provided
    import uuid

    doc_id = doc_id or str(uuid.uuid4())

    try:
        vectors = embed([text])
    except Exception as exc:
        logger.exception("Embedding failed")
        return json.dumps({"error": f"Embedding failed: {exc}"})

    store = _get_store()
    doc = VectorDocument(id=doc_id, content=text, embedding=vectors[0], metadata=meta)
    try:
        store.add([doc])
    except Exception as exc:
        logger.exception("Vector store insertion failed")
        return json.dumps({"error": f"Insertion failed: {exc}"})

    return json.dumps({"id": doc_id, "status": "inserted"})

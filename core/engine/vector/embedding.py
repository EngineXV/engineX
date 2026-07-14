"""Lightweight hash-based embedding utility (no external dependencies)."""

import hashlib

from engine.config import get_engine_config


def embed(texts: list[str], dim: int = 384) -> list[list[float]]:
    """Return deterministic hash-based embeddings for a list of texts.

    This is a lightweight alternative to ML-based embeddings.  Useful for
    testing, exact-match retrieval, or quick deduplication when semantic
    search is not required.

    The embedding dimension defaults to 384 but can be overridden via
    vector_store.embedding_dimension in the Engine config.
    """
    cfg = get_engine_config().get("vector_store", {})
    dim = cfg.get("embedding_dimension", dim)

    vectors = []
    for text in texts:
        # Derive a deterministic vector from the text hash
        seed = int(hashlib.sha256(text.encode()).hexdigest(), 16) % (10**9)
        vec = []
        for i in range(dim):
            # Simple pseudo-random float between -1 and 1 based on seed + index
            val = (hash(f"{seed}:{i}") % 2000) / 1000 - 1.0
            vec.append(val)
        vectors.append(vec)
    return vectors

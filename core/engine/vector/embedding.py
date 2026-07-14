"""Lightweight embedding utility using configured SentenceTransformer model."""

from engine.config import get_engine_config


def embed(texts: list[str]) -> list[list[float]]:
    """Return embeddings for a list of texts.

    Uses the model specified in ~/.engine/configuration.json under
    vector_store.embedding_model, or a sensible default.
    """
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as err:
        raise ImportError(
            "sentence-transformers is required for embedding. "
            "Install it with `uv add sentence-transformers`."
        ) from err

    cfg = get_engine_config().get("vector_store", {})
    model_name = cfg.get("embedding_model", "all-MiniLM-L6-v2")
    model = SentenceTransformer(model_name)
    return model.encode(texts, convert_to_tensor=False).tolist()

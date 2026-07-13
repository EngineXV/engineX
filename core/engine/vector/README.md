# Vector Store

Pluggable vector database abstraction for EngineX retrieval workflows.

## Quick start

```python
from engine.vector.chroma import ChromaVectorStore
from engine.vector.models import VectorDocument

store = ChromaVectorStore()
store.add([VectorDocument(id="1", content="EngineX is a goal‑driven agent runtime.")])
results = store.search("agent runtime")
print(results[0].content)

---

### 3. Update `core/tests/test_vector_store.py` (includes the empty‑collection test)

```bash
cat > core/tests/test_vector_store.py << 'EOF'
"""Tests for the vector store abstraction and tool."""

import json
from collections.abc import Sequence
from pathlib import Path

import pytest
from chromadb.api.types import EmbeddingFunction

pytest.importorskip("chromadb")

from engine.tools.vector_search import vector_search
from engine.vector.chroma import ChromaVectorStore
from engine.vector.models import VectorDocument


class DummyEmbeddingFunction(EmbeddingFunction):
    """Returns a fixed embedding for any input — no network, instant."""

    def __init__(self) -> None:
        pass

    def name(self) -> str:
        return "dummy"

    def get_config(self) -> dict:
        return {}

    def __call__(self, input: Sequence[str]) -> list[list[float]]:
        return [[0.0] * 384 for _ in input]


@pytest.fixture
def temp_store(tmp_path: Path):
    """Create a ChromaVectorStore with a temporary directory and no real embeddings."""
    store = ChromaVectorStore(
        collection_name="test",
        persist_directory=str(tmp_path / "chroma"),
        embedding_function=DummyEmbeddingFunction(),
    )
    yield store


class TestChromaVectorStore:
    def test_add_and_search(self, temp_store):
        docs = [
            VectorDocument(id="1", content="Hello world"),
            VectorDocument(id="2", content="Goodbye"),
        ]
        temp_store.add(docs)
        results = temp_store.search("hello", top_k=1)
        assert len(results) == 1
        assert results[0].id in {"1", "2"}
        assert isinstance(results[0].content, str)
        assert 0.0 <= results[0].score <= 1.0

    def test_search_empty_collection(self, temp_store):
        """Searching an empty collection should return no results."""
        results = temp_store.search("anything")
        assert results == []

    def test_search_with_metadata_filter(self, temp_store):
        docs = [
            VectorDocument(id="a", content="legal doc", metadata={"type": "legal"}),
            VectorDocument(id="b", content="marketing pdf", metadata={"type": "marketing"}),
        ]
        temp_store.add(docs)
        results = temp_store.search("doc", top_k=2, where={"type": "legal"})
        assert len(results) == 1
        assert results[0].id == "a"

    def test_delete(self, temp_store):
        docs = [VectorDocument(id="x", content="to delete")]
        temp_store.add(docs)
        temp_store.delete(["x"])
        results = temp_store.search("delete")
        assert results == []

    def test_health(self, temp_store):
        assert temp_store.health() is True


class TestVectorSearchTool:
    def test_tool_returns_json(self, temp_store, monkeypatch):
        monkeypatch.setattr(
            "engine.tools.vector_search._store", temp_store
        )
        docs = [VectorDocument(id="99", content="specific data")]
        temp_store.add(docs)

        result_json = vector_search("data", top_k=1)
        result = json.loads(result_json)
        assert isinstance(result, list)
        assert result[0]["id"] == "99"

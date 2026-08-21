# Vector Store

Pluggable vector database abstraction for EngineX retrieval workflows.

## Quick start

```python
from engine.vector.chroma import ChromaVectorStore
from engine.vector.models import VectorDocument

store = ChromaVectorStore()
store.add([VectorDocument(id="1", content="EngineX is a goal–driven agent runtime.")])
results = store.search("agent runtime")
print(results[0].content)
```

## Backends

- **ChromaDB** – implemented (local, config’driven)
- **pgvector / Pinecone / Qdrant** – future

## Architecture

```
Workflow Node
      │
      ▼
 vector_search Tool
      │
      ▼
 VectorStore Interface
      │
 ┌──┼─────────────━
 │                    │
ChromaStore      Future backends
```

This follows Issue #47.

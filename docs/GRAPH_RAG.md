# GraphRAG in EngineX
Pluggable retrieval‑augmented generation using vector stores.

## Components
- **VectorStore ABC** – pluggable interface
- **ChromaDB backend** – default local backend
- **Embedding utility** – hash‑based or ML embeddings
- **embed_and_insert tool** – ingestion
- **vector_search tool** – retrieval
- **Chunking** – split text before embedding

## Quick start
```python
from engine.vector.chroma import ChromaVectorStore
from engine.vector.embedding import embed
store = ChromaVectorStore()
store.add([VectorDocument(id="1", content="example", embedding=embed(["example"])[0])])
results = store.search("query")
```

See `examples/templates/graphrag_ingest` for a full workflow.

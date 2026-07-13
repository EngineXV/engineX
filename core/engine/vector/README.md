# Vector Store

This package contains the vector database abstraction used by GraphRAG workflows.

## Objective

Provide a common interface for semantic retrieval while keeping the runtime independent of any specific vector database.

Initial backend:

- ChromaDB

Future backends:

- pgvector
- Qdrant
- Pinecone

The retrieval layer will be exposed through EngineX tools so workflow nodes remain backend-agnostic.

## Planned Responsibilities

- Collection management
- Document insertion
- Similarity search
- Metadata storage
- Deletion
- Health checks

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
 ┌────┴───────────────┐
 │                    │
ChromaStore      PGVectorStore
```

This follows Issue #47.

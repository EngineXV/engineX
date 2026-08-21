"""Lightweight text chunking for document ingestion."""

from __future__ import annotations


def chunk_text(
    text: str,
    chunk_size: int = 500,
    overlap: int = 50,
    separator: str = " ",
) -> list[str]:
    """Split text into overlapping chunks of roughly `chunk_size` words.

    Only full chunks are returned; any remaining words that would form a
    chunk smaller than `chunk_size` are discarded.
    """
    if not text.strip():
        return []

    words = text.split(separator)
    if len(words) <= chunk_size:
        return [text]

    chunks: list[str] = []
    step = max(1, chunk_size - overlap)
    start = 0

    while start + chunk_size <= len(words):
        end = start + chunk_size
        chunks.append(separator.join(words[start:end]))
        start += step

    return chunks

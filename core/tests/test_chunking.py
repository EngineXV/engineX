"""Tests for the text chunking utility."""

from engine.vector.chunking import chunk_text


class TestChunkText:
    def test_empty_text(self):
        assert chunk_text("") == []
        assert chunk_text("   ") == []

    def test_single_chunk(self):
        assert chunk_text("hello world", chunk_size=10) == ["hello world"]

    def test_multiple_no_overlap(self):
        text = "a b c d e f g h"
        assert chunk_text(text, chunk_size=2, overlap=0) == [
            "a b",
            "c d",
            "e f",
            "g h",
        ]

    def test_with_overlap(self):
        text = "a b c d e f g h"
        assert chunk_text(text, chunk_size=4, overlap=2) == [
            "a b c d",
            "c d e f",
            "e f g h",
        ]

    def test_leftover(self):
        text = "a b c d e"
        # 5 words, chunk_size=3, overlap=1 → step=2
        # Chunks: "a b c", "c d e", "e" (last < overlap=1 → merge)
        assert chunk_text(text, chunk_size=3, overlap=1) == [
            "a b c",
            "c d e",
        ]

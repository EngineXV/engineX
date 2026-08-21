"""Tests for the hash-based embedding utility."""

from engine.vector.embedding import embed


class TestEmbed:
    def test_embed_returns_list_of_lists(self):
        result = embed(["hello", "world"])
        assert isinstance(result, list)
        assert len(result) == 2
        assert all(isinstance(v, list) for v in result)

    def test_embed_output_dimension(self):
        result = embed(["test"], dim=128)
        assert len(result[0]) == 128

    def test_embed_deterministic(self):
        a = embed(["hello"])
        b = embed(["hello"])
        assert a == b

    def test_embed_different_texts_different_vectors(self):
        a = embed(["hello"])[0]
        b = embed(["world"])[0]
        assert a != b

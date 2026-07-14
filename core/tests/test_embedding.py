"""Tests for the embedding utility."""

from unittest.mock import patch

import pytest

from engine.vector.embedding import embed


@pytest.fixture
def mock_sentence_transformer():
    with patch("sentence_transformers.SentenceTransformer") as mock_cls:
        instance = mock_cls.return_value
        instance.encode.return_value.tolist.return_value = [
            [0.1, 0.2, 0.3],
            [0.4, 0.5, 0.6],
        ]
        yield mock_cls


class TestEmbed:
    def test_embed_returns_list_of_lists(self, mock_sentence_transformer):
        result = embed(["hello", "world"])
        assert isinstance(result, list)
        assert len(result) == 2
        assert all(isinstance(v, list) for v in result)

    def test_embed_calls_model_with_texts(self, mock_sentence_transformer):
        texts = ["hello", "world"]
        embed(texts)
        instance = mock_sentence_transformer.return_value
        instance.encode.assert_called_once_with(texts, convert_to_tensor=False)

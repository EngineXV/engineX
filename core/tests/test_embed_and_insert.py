"""Tests for the embed_and_insert tool."""

import json
from unittest.mock import patch

import pytest

from engine.tools.embed_and_insert import embed_and_insert


@pytest.fixture
def mock_store_and_embed():
    with (
        patch("engine.tools.embed_and_insert.ChromaVectorStore") as mock_store_cls,
        patch("engine.tools.embed_and_insert.embed") as mock_embed,
    ):
        mock_store = mock_store_cls.return_value
        mock_embed.return_value = [[0.1, 0.2, 0.3]]
        yield mock_store, mock_embed


class TestEmbedAndInsert:
    def test_inserts_document_and_returns_id(self, mock_store_and_embed):
        mock_store, mock_embed = mock_store_and_embed
        result = embed_and_insert("hello world", "{}", "doc-1")
        data = json.loads(result)
        assert data["id"] == "doc-1"
        assert data["status"] == "inserted"
        mock_store.add.assert_called_once()

    def test_insert_generates_id_if_empty(self, mock_store_and_embed):
        mock_store, mock_embed = mock_store_and_embed
        result = embed_and_insert("hello")
        data = json.loads(result)
        assert "id" in data
        assert data["status"] == "inserted"
        # Check that a UUID-like string was generated
        assert len(data["id"]) == 36

    def test_returns_error_on_bad_metadata(self, mock_store_and_embed):
        result = embed_and_insert("text", "not valid json")
        data = json.loads(result)
        assert "error" in data

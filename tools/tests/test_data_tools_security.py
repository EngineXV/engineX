"""Security tests for MCP data tools path handling."""

from __future__ import annotations

from engine_tools.tools.data_tools import _resolve_data_dir


class TestResolveDataDir:
    def test_rejects_empty(self):
        path, err = _resolve_data_dir("")
        assert path is None
        assert err == "data_dir is required"

    def test_rejects_dotdot(self):
        path, err = _resolve_data_dir("/tmp/../etc")
        assert path is None
        assert ".." in err

    def test_resolves_relative_path(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        sub = tmp_path / "data"
        sub.mkdir()
        path, err = _resolve_data_dir("data")
        assert err is None
        assert path == sub.resolve()

    def test_enforces_engine_data_root(self, tmp_path, monkeypatch):
        root = tmp_path / "sandbox"
        allowed = root / "ok"
        allowed.mkdir(parents=True)
        outside = tmp_path / "outside"
        outside.mkdir()
        monkeypatch.setenv("ENGINE_DATA_ROOT", str(root))

        path, err = _resolve_data_dir(str(allowed))
        assert err is None
        assert path == allowed.resolve()

        path, err = _resolve_data_dir(str(outside))
        assert path is None
        assert "ENGINE_DATA_ROOT" in err

    def test_blocks_escape_via_relative_dotdot(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ENGINE_DATA_ROOT", str(tmp_path))
        path, err = _resolve_data_dir(str(tmp_path / "nested" / ".." / ".." / "etc"))
        assert path is None
        assert ".." in err

"""Data Tools - Load, save, and list data files for agent pipelines"""

from __future__ import annotations

import os
from pathlib import Path

from mcp.server.fastmcp import FastMCP


def _resolve_data_dir(data_dir: str) -> tuple[Path | None, str | None]:
    """Resolve and validate a data directory path.

    Rejects empty paths, ``..`` segments, and paths outside ENGINE_DATA_ROOT
    when that environment variable is set.
    """
    if not data_dir or not str(data_dir).strip():
        return None, "data_dir is required"
    if ".." in Path(data_dir).parts:
        return None, "data_dir must not contain '..'"

    path = Path(data_dir).expanduser()
    if not path.is_absolute():
        path = (Path.cwd() / path).resolve()
    else:
        path = path.resolve()

    root = os.environ.get("ENGINE_DATA_ROOT")
    if root:
        root_path = Path(root).expanduser().resolve()
        try:
            path.relative_to(root_path)
        except ValueError:
            return None, f"data_dir must be under ENGINE_DATA_ROOT ({root_path})"

    return path, None


def _open_file_uri(file_uri: str) -> tuple[bool, str]:
    """Best-effort open a file:// URI in the default browser."""
    import subprocess
    import sys

    devnull = subprocess.DEVNULL
    try:
        if sys.platform == "darwin":
            subprocess.Popen(["open", file_uri], stdout=devnull, stderr=devnull)
        elif sys.platform == "linux":
            subprocess.Popen(["xdg-open", file_uri], stdout=devnull, stderr=devnull)
        else:
            return False, "Browser open not supported on this platform"
        return True, "Opened in browser"
    except Exception as exc:
        return False, str(exc)


def register_tools(mcp: FastMCP) -> None:
    """Register data management tools with the MCP server"""

    @mcp.tool()
    def save_data(filename: str, data: str, data_dir: str) -> dict:
        """Purpose"""
        if not filename or ".." in filename or "/" in filename or "\\" in filename:
            return {"error": "Invalid filename. Use simple names like 'users.json'"}
        if not data_dir:
            return {"error": "data_dir is required"}

        dir_path, err = _resolve_data_dir(data_dir)
        if err:
            return {"error": err}

        try:
            dir_path.mkdir(parents=True, exist_ok=True)
            path = dir_path / filename
            path.write_text(data, encoding="utf-8")
            lines = data.count("\n") + 1
            return {
                "success": True,
                "filename": filename,
                "size_bytes": len(data.encode("utf-8")),
                "lines": lines,
                "preview": data[:200] + ("..." if len(data) > 200 else ""),
            }
        except Exception as e:
            return {"error": f"Failed to save data: {str(e)}"}

    @mcp.tool()
    def load_data(
        filename: str,
        data_dir: str,
        offset_bytes: int = 0,
        limit_bytes: int = 10000,
    ) -> dict:
        """Purpose"""
        if not filename or ".." in filename or "/" in filename or "\\" in filename:
            return {"error": "Invalid filename"}
        if not data_dir:
            return {"error": "data_dir is required"}

        dir_path, err = _resolve_data_dir(data_dir)
        if err:
            return {"error": err}

        try:
            offset_bytes = int(offset_bytes)
            limit_bytes = int(limit_bytes)
            path = dir_path / filename
            if not path.exists():
                return {"error": f"File not found: {filename}"}

            file_size = path.stat().st_size

            # Handle edge case: offset beyond file size
            if offset_bytes >= file_size:
                return {
                    "success": True,
                    "filename": filename,
                    "content": "",
                    "offset_bytes": offset_bytes,
                    "bytes_read": 0,
                    "next_offset_bytes": file_size,
                    "file_size_bytes": file_size,
                    "has_more": False,
                }

            with open(path, "rb") as f:
                # O(1) seek to byte offset
                f.seek(offset_bytes)

                # Read exactly limit_bytes
                raw_bytes = f.read(limit_bytes)

                # Trim to valid UTF-8 boundary
                # Scan backwards max 4 bytes to find valid UTF-8 start
                chunk = raw_bytes
                text = None
                for i in range(min(4, len(raw_bytes)) + 1):
                    try:
                        slice_end = len(raw_bytes) - i if i > 0 else len(raw_bytes)
                        text = raw_bytes[:slice_end].decode("utf-8")
                        chunk = raw_bytes[:slice_end]
                        break
                    except UnicodeDecodeError:
                        continue

                # If we couldn't decode at all, return error
                if text is None:
                    return {"error": "Could not decode file as UTF-8"}

                # UTF-8 boundary is already handled above
                next_offset = offset_bytes + len(chunk)

                return {
                    "success": True,
                    "filename": filename,
                    "content": text,
                    "offset_bytes": offset_bytes,
                    "bytes_read": len(chunk),
                    "next_offset_bytes": next_offset,
                    "file_size_bytes": file_size,
                    "has_more": next_offset < file_size,
                }
        except Exception as e:
            return {"error": f"Failed to load data: {str(e)}"}

    @mcp.tool()
    def serve_file_to_user(
        filename: str, data_dir: str, label: str = "", open_in_browser: bool = False
    ) -> dict:
        """Purpose"""
        if not filename or ".." in filename or "/" in filename or "\\" in filename:
            return {"error": "Invalid filename. Use simple names like 'report.html'"}
        if not data_dir:
            return {"error": "data_dir is required"}

        dir_path, err = _resolve_data_dir(data_dir)
        if err:
            return {"error": err}

        try:
            path = dir_path / filename
            if not path.exists():
                return {"error": f"File not found: {filename}"}

            full_path = str(path)
            file_uri = f"file://{full_path}"
            result = {
                "success": True,
                "file_uri": file_uri,
                "file_path": full_path,
                "label": label or filename,
            }

            if open_in_browser:
                opened, msg = _open_file_uri(file_uri)
                result["browser_opened"] = opened
                result["browser_message"] = msg

            return result
        except Exception as e:
            return {"error": f"Failed to serve file: {str(e)}"}

    @mcp.tool()
    def list_data_files(data_dir: str) -> dict:
        """Purpose"""
        if not data_dir:
            return {"error": "data_dir is required"}

        dir_path, err = _resolve_data_dir(data_dir)
        if err:
            return {"error": err}

        try:
            if not dir_path.exists():
                return {"files": []}

            files = []
            for f in sorted(dir_path.iterdir()):
                if f.is_file():
                    files.append(
                        {
                            "filename": f.name,
                            "size_bytes": f.stat().st_size,
                        }
                    )
            return {"files": files}
        except Exception as e:
            return {"error": f"Failed to list data files: {str(e)}"}

    @mcp.tool()
    def append_data(filename: str, data: str, data_dir: str) -> dict:
        """Purpose"""
        if not filename or ".." in filename or "/" in filename or "\\" in filename:
            return {"error": "Invalid filename. Use simple names like 'report.html'"}
        if not data_dir:
            return {"error": "data_dir is required"}

        dir_path, err = _resolve_data_dir(data_dir)
        if err:
            return {"error": err}

        try:
            dir_path.mkdir(parents=True, exist_ok=True)
            path = dir_path / filename
            with open(path, "a", encoding="utf-8") as f:
                f.write(data)
            appended_bytes = len(data.encode("utf-8"))
            total_bytes = path.stat().st_size
            return {
                "success": True,
                "filename": filename,
                "size_bytes": total_bytes,
                "appended_bytes": appended_bytes,
            }
        except Exception as e:
            return {"error": f"Failed to append data: {str(e)}"}

    @mcp.tool()
    def edit_data(filename: str, old_text: str, new_text: str, data_dir: str) -> dict:
        """Purpose"""
        if not filename or ".." in filename or "/" in filename or "\\" in filename:
            return {"error": "Invalid filename. Use simple names like 'report.html'"}
        if not data_dir:
            return {"error": "data_dir is required"}

        dir_path, err = _resolve_data_dir(data_dir)
        if err:
            return {"error": err}

        try:
            path = dir_path / filename
            if not path.exists():
                return {"error": f"File not found: {filename}"}

            content = path.read_text(encoding="utf-8")
            count = content.count(old_text)

            if count == 0:
                return {
                    "error": (
                        "old_text not found in the file. "
                        "Make sure you're matching the exact text, "
                        "including whitespace and newlines."
                    )
                }
            if count > 1:
                return {
                    "error": (
                        f"old_text found {count} times — it must be unique. "
                        "Include more surrounding context to match exactly once."
                    )
                }

            updated = content.replace(old_text, new_text, 1)
            path.write_text(updated, encoding="utf-8")

            return {
                "success": True,
                "filename": filename,
                "size_bytes": len(updated.encode("utf-8")),
                "replacements": 1,
            }
        except Exception as e:
            return {"error": f"Failed to edit data: {str(e)}"}

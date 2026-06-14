"""ENGINE_LLM_DEBUG"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import IO, Any

logger = logging.getLogger(__name__)

_LLM_DEBUG_RAW = os.environ.get("ENGINE_LLM_DEBUG", "").strip()
_LLM_DEBUG_ENABLED = _LLM_DEBUG_RAW.lower() in ("1", "true") or (
    bool(_LLM_DEBUG_RAW) and _LLM_DEBUG_RAW.lower() not in ("0", "false", "")
)

_log_file: IO[str] | None = None
_log_ready = False  # lazy init guard


def _open_log() -> IO[str] | None:
    """Open a JSONL log file. Returns None if disabled"""
    if not _LLM_DEBUG_ENABLED:
        return None
    raw = _LLM_DEBUG_RAW
    if raw.lower() in ("1", "true"):
        log_dir = Path.home() / ".engine" / "llm_logs"
    else:
        log_dir = Path(raw)
    log_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = log_dir / f"{ts}.jsonl"
    logger.info("LLM debug log → %s", path)
    return open(path, "a", encoding="utf-8")  # noqa: SIM115


def log_llm_turn(
    *,
    node_id: str,
    stream_id: str,
    execution_id: str,
    iteration: int,
    assistant_text: str,
    tool_calls: list[dict[str, Any]],
    tool_results: list[dict[str, Any]],
    token_counts: dict[str, Any],
) -> None:
    """Write one JSONL line capturing a complete LLM turn"""
    if not _LLM_DEBUG_ENABLED:
        return
    try:
        global _log_file, _log_ready  # noqa: PLW0603
        if not _log_ready:
            _log_file = _open_log()
            _log_ready = True
        if _log_file is None:
            return
        record = {
            "timestamp": datetime.now().isoformat(),
            "node_id": node_id,
            "stream_id": stream_id,
            "execution_id": execution_id,
            "iteration": iteration,
            "assistant_text": assistant_text,
            "tool_calls": tool_calls,
            "tool_results": tool_results,
            "token_counts": token_counts,
        }
        _log_file.write(json.dumps(record, default=str) + "\n")
        _log_file.flush()
    except Exception:
        pass  # never break the agent

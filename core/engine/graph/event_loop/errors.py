"""Context-window error detection for event-loop nodes"""

from __future__ import annotations

import re

# Pattern for detecting context-window-exceeded errors across LLM providers.
_CONTEXT_TOO_LARGE_RE = re.compile(
    r"context.{0,20}(length|window|limit|size)|"
    r"too.{0,10}(long|large|many.{0,10}tokens)|"
    r"(exceed|exceeds|exceeded).{0,30}(limit|window|context|tokens)|"
    r"maximum.{0,20}token|prompt.{0,20}too.{0,10}long",
    re.IGNORECASE,
)


def _is_context_too_large_error(exc: BaseException) -> bool:
    """Detect whether an exception indicates the LLM input was too large"""
    cls = type(exc).__name__
    if "ContextWindow" in cls:
        return True
    return bool(_CONTEXT_TOO_LARGE_RE.search(str(exc)))

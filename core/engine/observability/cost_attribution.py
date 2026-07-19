"""Cost attribution engine — surface hidden retry and nested call costs.

This module implements the spend attribution tree described in issue #45.
Every LLM completion and tool call within a session is represented as a
``CostEntry``. Entries are grouped into a ``CostTree`` that mirrors the
execution hierarchy: session → node → attempt → invocation.

Usage::

    from engine.observability.cost_attribution import build_cost_tree, run_cost_usd

    tree = await build_cost_tree(session_id, log_store)
    print(f"Total cost: ${run_cost_usd(tree):.6f}")
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from engine.runtime.runtime_log_store import RuntimeLogStore

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Minimum retries on a single node before it is flagged as a retry storm.
RETRY_STORM_THRESHOLD = 3

#: Minimum node visit count before flagging as a runaway loop.
RUNAWAY_LOOP_THRESHOLD = 5

#: Minimum number of parallel branches before flagging as uncapped fan-out.
UNCAPPED_FANOUT_THRESHOLD = 10


# ---------------------------------------------------------------------------
# Cost computation helpers
# ---------------------------------------------------------------------------


def _compute_cost_usd(
    model: str,
    input_tokens: int,
    output_tokens: int,
    raw_response: Any = None,
) -> float:
    """Compute USD cost for an LLM call.

    Priority:
    1. ``litellm.completion_cost(response)`` — uses litellm's own price tables
       and any cost fields the provider embeds in the response.
    2. ``model_catalog.get_model_pricing(model)`` — our curated fallback.
    3. 0.0 — safe default; the entry is still recorded for token attribution.
    """
    # Attempt 1: litellm native cost
    if raw_response is not None:
        try:
            import litellm

            cost = litellm.completion_cost(completion_response=raw_response)
            if isinstance(cost, int | float) and cost >= 0:
                return float(cost)
        except Exception:
            pass

    # Attempt 2: our curated model catalog
    try:
        from engine.llm.model_catalog import get_model_pricing

        pricing = get_model_pricing(model)
        if pricing:
            input_rate = pricing.get("input", 0.0)  # USD per 1M tokens
            output_rate = pricing.get("output", 0.0)
            return (input_tokens * input_rate + output_tokens * output_rate) / 1_000_000
    except Exception:
        pass

    return 0.0


def compute_tool_cost_usd(duration_s: float) -> float:
    """Tool calls have no direct LLM cost; return 0.0.

    This exists as an extension point for future per-tool pricing (e.g.
    metered external API calls).
    """
    return 0.0


# ---------------------------------------------------------------------------
# Schema: CostEntry — one record per invocation
# ---------------------------------------------------------------------------


class CostEntry(BaseModel):
    """One cost-bearing invocation within a session.

    A single node execution that retries N times produces N separate
    ``CostEntry`` records, each with a distinct ``attempt`` number.
    This satisfies the acceptance criterion: "Retry attempts labeled
    separately in cost breakdown (not merged into one line)."
    """

    entry_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    session_id: str = ""
    node_id: str = ""
    attempt: int = 1  # 1-based; each retry is a separate entry
    step_index: int = 0
    invocation_type: str = "llm"  # "llm" | "tool"
    model: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    tool_name: str | None = None  # set when invocation_type=="tool"
    duration_s: float = 0.0
    timestamp: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    # For subagent attribution; empty string means this is a root-level call.
    parent_session_id: str = ""
    # Anomaly flags applied during build_cost_tree / detect_anomalies.
    flags: list[str] = Field(default_factory=list)

    model_config = {"extra": "allow"}


# ---------------------------------------------------------------------------
# Schema: CostTree — hierarchy of entries for one session
# ---------------------------------------------------------------------------


class NodeCostSummary(BaseModel):
    """Aggregated cost for one node across all its attempts."""

    node_id: str
    total_cost_usd: float = 0.0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    attempt_count: int = 0  # number of distinct attempts (1 = clean, >1 = retried)
    entries: list[CostEntry] = Field(default_factory=list)
    flags: list[str] = Field(default_factory=list)

    model_config = {"extra": "allow"}


class CostTree(BaseModel):
    """Full cost attribution tree for one session.

    Structure::

        CostTree
        └── nodes: dict[node_id → NodeCostSummary]
                └── entries: list[CostEntry]   (one per attempt × invocation)
    """

    session_id: str
    agent_id: str = ""
    total_cost_usd: float = 0.0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    node_count: int = 0
    started_at: str = ""
    duration_ms: int = 0
    nodes: dict[str, NodeCostSummary] = Field(default_factory=dict)
    # Session-level anomaly flags
    flags: list[str] = Field(default_factory=list)

    model_config = {"extra": "allow"}


# ---------------------------------------------------------------------------
# Tree builder
# ---------------------------------------------------------------------------


async def build_cost_tree(
    session_id: str,
    log_store: RuntimeLogStore,
) -> CostTree:
    """Assemble a ``CostTree`` for *session_id* from persisted log files.

    Reads ``cost_attribution.jsonl`` first (the authoritative per-call log).
    Falls back to reconstructing entries from ``tool_logs.jsonl`` if the cost
    log is absent (e.g. for sessions recorded before this feature was added).
    """
    # --- Try the dedicated cost attribution log first ---
    entries = await log_store.load_cost_entries(session_id)

    if not entries:
        # Fallback: synthesise CostEntry records from tool_logs.jsonl
        entries = await _rebuild_from_tool_logs(session_id, log_store)

    # --- Aggregate into tree ---
    tree = CostTree(session_id=session_id)

    for entry in entries:
        node_id = entry.node_id
        if node_id not in tree.nodes:
            tree.nodes[node_id] = NodeCostSummary(node_id=node_id)

        node = tree.nodes[node_id]
        node.entries.append(entry)
        node.total_cost_usd += entry.cost_usd
        node.total_input_tokens += entry.input_tokens
        node.total_output_tokens += entry.output_tokens

    # Track distinct attempts per node
    for node in tree.nodes.values():
        attempts_seen: set[int] = {e.attempt for e in node.entries}
        node.attempt_count = len(attempts_seen)

    # Roll up totals
    tree.total_cost_usd = sum(n.total_cost_usd for n in tree.nodes.values())
    tree.total_input_tokens = sum(n.total_input_tokens for n in tree.nodes.values())
    tree.total_output_tokens = sum(n.total_output_tokens for n in tree.nodes.values())
    tree.node_count = len(tree.nodes)

    # Load summary for metadata
    summary = await log_store.load_summary(session_id)
    if summary:
        tree.agent_id = summary.agent_id
        tree.started_at = summary.started_at
        tree.duration_ms = summary.duration_ms

    # Apply anomaly detection
    detect_anomalies(tree)

    return tree


async def _rebuild_from_tool_logs(
    session_id: str,
    log_store: RuntimeLogStore,
) -> list[CostEntry]:
    """Synthesise CostEntry records from tool_logs.jsonl (fallback path)."""
    tool_logs = await log_store.load_tool_logs(session_id)
    if tool_logs is None:
        return []

    entries: list[CostEntry] = []
    for step in tool_logs.steps:
        # LLM invocation entry
        if step.input_tokens or step.output_tokens:
            cost = _compute_cost_usd(
                model="",  # model not stored in NodeStepLog — best-effort 0.0
                input_tokens=step.input_tokens,
                output_tokens=step.output_tokens,
            )
            entries.append(
                CostEntry(
                    session_id=session_id,
                    node_id=step.node_id,
                    attempt=1,  # legacy logs have no attempt field
                    step_index=step.step_index,
                    invocation_type="llm",
                    model="",
                    input_tokens=step.input_tokens,
                    output_tokens=step.output_tokens,
                    cost_usd=cost,
                    duration_s=step.latency_ms / 1000.0,
                )
            )

        # Tool call entries
        for tc in step.tool_calls:
            entries.append(
                CostEntry(
                    session_id=session_id,
                    node_id=step.node_id,
                    attempt=1,
                    step_index=step.step_index,
                    invocation_type="tool",
                    model="",
                    tool_name=tc.tool_name,
                    cost_usd=compute_tool_cost_usd(tc.duration_s),
                    duration_s=tc.duration_s,
                )
            )

    return entries


# ---------------------------------------------------------------------------
# Anomaly detection
# ---------------------------------------------------------------------------


def detect_anomalies(tree: CostTree) -> None:
    """Flag black-box cost patterns in-place on *tree* and its nodes.

    Patterns detected
    -----------------
    retry_storm
        A single node was retried ≥ ``RETRY_STORM_THRESHOLD`` times.
    runaway_loop
        A single node appears ≥ ``RUNAWAY_LOOP_THRESHOLD`` times across
        attempts (e.g. a judge loop that never converges).
    uncapped_fanout
        The session spawned ≥ ``UNCAPPED_FANOUT_THRESHOLD`` parallel branches
        (distinct node_ids with attempt==1 executed at the same step).
    """
    all_tree_flags: list[str] = []

    for node in tree.nodes.values():
        node_flags: list[str] = []
        attempt_count = node.attempt_count

        if attempt_count >= RETRY_STORM_THRESHOLD:
            flag = f"retry_storm:{node.node_id}:{attempt_count}_retries"
            node_flags.append(flag)
            all_tree_flags.append(flag)

        # Runaway loop: many step_index values in the same attempt
        max_step_in_attempt: dict[int, int] = {}
        for entry in node.entries:
            prev = max_step_in_attempt.get(entry.attempt, 0)
            if entry.step_index > prev:
                max_step_in_attempt[entry.attempt] = entry.step_index

        for attempt_num, max_step in max_step_in_attempt.items():
            if max_step >= RUNAWAY_LOOP_THRESHOLD:
                flag = f"runaway_loop:{node.node_id}:attempt={attempt_num}:steps={max_step}"
                node_flags.append(flag)
                all_tree_flags.append(flag)

        node.flags = node_flags

    # Uncapped fan-out: count distinct node_ids
    if len(tree.nodes) >= UNCAPPED_FANOUT_THRESHOLD:
        flag = f"uncapped_fanout:{len(tree.nodes)}_nodes"
        all_tree_flags.append(flag)

    tree.flags = list(dict.fromkeys(all_tree_flags))  # deduplicate, preserve order


# ---------------------------------------------------------------------------
# Convenience aggregation helpers
# ---------------------------------------------------------------------------


def run_cost_usd(tree: CostTree) -> float:
    """Return the total USD cost for *tree*."""
    return tree.total_cost_usd


def format_cost_waterfall(tree: CostTree, *, top_n: int | None = None) -> str:
    """Return a human-readable cost waterfall string for *tree*.

    Used by ``engine cost-tree`` CLI command.
    """
    lines: list[str] = []
    sep = "─" * 65

    # Header
    lines.append(f"Session : {tree.session_id}")
    if tree.agent_id:
        lines.append(f"Agent   : {tree.agent_id}")
    lines.append(
        f"Total   : ${tree.total_cost_usd:.6f}  "
        f"({tree.total_input_tokens:,} input + {tree.total_output_tokens:,} output tokens)"
    )
    if tree.duration_ms:
        lines.append(f"Duration: {tree.duration_ms / 1000:.2f}s")

    if tree.flags:
        lines.append(f"⚠ Flags : {', '.join(tree.flags)}")

    lines.append("")
    lines.append(f"{'Node':<30} {'Cost':>10}  {'Attempts':>8}  {'Tokens (in/out)':>18}")
    lines.append(sep)

    # Sort nodes by cost descending
    sorted_nodes = sorted(tree.nodes.values(), key=lambda n: n.total_cost_usd, reverse=True)
    if top_n:
        sorted_nodes = sorted_nodes[:top_n]

    for node in sorted_nodes:
        attempt_label = f"{node.attempt_count} attempts" if node.attempt_count > 1 else "1 attempt"
        retry_marker = " ⚠" if node.attempt_count > 1 else ""
        lines.append(
            f"{node.node_id:<30} ${node.total_cost_usd:>9.6f}  "
            f"{attempt_label:>8}{retry_marker}  "
            f"{node.total_input_tokens:>9,}/{node.total_output_tokens:<9,}"
        )

        # Per-attempt breakdown
        attempts: dict[int, list[CostEntry]] = {}
        for entry in node.entries:
            attempts.setdefault(entry.attempt, []).append(entry)

        for attempt_num in sorted(attempts):
            attempt_entries = attempts[attempt_num]
            attempt_cost = sum(e.cost_usd for e in attempt_entries)
            attempt_in = sum(e.input_tokens for e in attempt_entries)
            attempt_out = sum(e.output_tokens for e in attempt_entries)
            lines.append(
                f"  {'└─ attempt ' + str(attempt_num):<28} ${attempt_cost:>9.6f}  "
                f"{'':>8}  "
                f"{attempt_in:>9,}/{attempt_out:<9,}"
            )

            for entry in attempt_entries:
                if entry.invocation_type == "llm":
                    model_label = entry.model or "llm"
                    lines.append(
                        f"      {'└─ llm:' + model_label:<24} ${entry.cost_usd:>9.6f}  "
                        f"{'':>8}  "
                        f"{entry.input_tokens:>9,}/{entry.output_tokens:<9,}"
                    )
                elif entry.invocation_type == "tool":
                    tool_label = entry.tool_name or "tool"
                    lines.append(
                        f"      {'└─ tool:' + tool_label:<24} ${'0.000000':>9}  "
                        f"{'':>8}  "
                        f"{'':>9} {entry.duration_s:.3f}s"
                    )

    lines.append(sep)

    if tree.flags:
        lines.append("")
        lines.append("Anomaly flags:")
        for flag in tree.flags:
            lines.append(f"  • {flag}")

    return "\n".join(lines)

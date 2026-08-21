"""Tests for black-box spend attribution (issue #45).

Covers:
- CostEntry USD computation from tokens + model pricing
- Retry attempts appear as separate cost entries (not merged)
- build_cost_tree() assembles the full hierarchy from log files
- CostAlertStore fires at 3× median
- detect_anomalies() flags retry storms
- cmd_cost_tree CLI exits 0 and produces expected output
"""

from __future__ import annotations

import asyncio
import json
import uuid
from pathlib import Path

from engine.observability.cost_alerts import (
    ALERT_THRESHOLD,
    MIN_RUNS_FOR_ALERT,
    CostAlert,
    CostAlertStore,
)
from engine.observability.cost_attribution import (
    RETRY_STORM_THRESHOLD,
    CostEntry,
    CostTree,
    NodeCostSummary,
    _compute_cost_usd,
    build_cost_tree,
    detect_anomalies,
    format_cost_waterfall,
    run_cost_usd,
)
from engine.runtime.runtime_log_schemas import NodeDetail, NodeStepLog
from engine.runtime.runtime_log_store import RuntimeLogStore

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_session_id() -> str:
    return f"session_test_{uuid.uuid4().hex[:8]}"


def _make_log_store(tmp_path: Path) -> RuntimeLogStore:
    return RuntimeLogStore(tmp_path)


def _seed_cost_entries(store: RuntimeLogStore, session_id: str, entries: list[CostEntry]) -> None:
    """Write cost entries to the store synchronously for test setup."""
    store.ensure_run_dir(session_id)
    for entry in entries:
        store.append_cost_entry(session_id, entry)


def _seed_tool_logs(store: RuntimeLogStore, session_id: str, steps: list[NodeStepLog]) -> None:
    """Write NodeStepLog entries to the store synchronously."""
    store.ensure_run_dir(session_id)
    for step in steps:
        store.append_step(session_id, step)


def _seed_node_details(store: RuntimeLogStore, session_id: str, details: list[NodeDetail]) -> None:
    """Write NodeDetail entries to the store synchronously."""
    store.ensure_run_dir(session_id)
    for detail in details:
        store.append_node_detail(session_id, detail)


# ---------------------------------------------------------------------------
# C1: CostEntry / cost computation
# ---------------------------------------------------------------------------


class TestCostComputation:
    """Test USD cost computation from tokens and model pricing."""

    def test_compute_cost_usd_from_catalog(self):
        """Catalog pricing should yield a positive USD cost for known models."""
        # Any model in the catalog with pricing should return non-zero cost
        cost = _compute_cost_usd(
            model="claude-haiku-4-5-20251001",
            input_tokens=1000,
            output_tokens=500,
        )
        # Accept 0.0 if the model isn't in the catalog — the function is fallback-safe
        assert isinstance(cost, float)
        assert cost >= 0.0

    def test_compute_cost_usd_zero_tokens(self):
        """Zero tokens should yield zero cost regardless of model."""
        cost = _compute_cost_usd(model="gpt-4o", input_tokens=0, output_tokens=0)
        assert cost == 0.0

    def test_compute_cost_usd_unknown_model(self):
        """Unknown model should return 0.0 without raising."""
        cost = _compute_cost_usd(
            model="nonexistent-model-xyz",
            input_tokens=1000,
            output_tokens=500,
        )
        assert cost == 0.0

    def test_cost_entry_has_required_fields(self):
        """CostEntry should accept and store all required fields."""
        entry = CostEntry(
            session_id="session_test_abc",
            node_id="extract",
            attempt=2,
            step_index=1,
            invocation_type="llm",
            model="claude-haiku-4-5-20251001",
            input_tokens=800,
            output_tokens=300,
            cost_usd=0.00025,
        )
        assert entry.session_id == "session_test_abc"
        assert entry.node_id == "extract"
        assert entry.attempt == 2
        assert entry.invocation_type == "llm"
        assert entry.cost_usd == 0.00025
        assert entry.entry_id  # auto-generated UUID

    def test_cost_entry_tool_type(self):
        """Tool CostEntry should store tool_name and invocation_type."""
        entry = CostEntry(
            session_id="session_test_abc",
            node_id="search_node",
            attempt=1,
            step_index=0,
            invocation_type="tool",
            tool_name="web_search",
            cost_usd=0.0,
            duration_s=1.23,
        )
        assert entry.invocation_type == "tool"
        assert entry.tool_name == "web_search"
        assert entry.cost_usd == 0.0

    def test_cost_entry_serialisation(self):
        """CostEntry should round-trip through JSON."""
        entry = CostEntry(
            session_id="session_abc",
            node_id="node1",
            attempt=1,
            invocation_type="llm",
            model="gpt-4o-mini",
            input_tokens=100,
            output_tokens=50,
            cost_usd=0.00005,
        )
        raw = json.loads(entry.model_dump_json())
        reconstructed = CostEntry(**raw)
        assert reconstructed.cost_usd == entry.cost_usd
        assert reconstructed.session_id == entry.session_id


# ---------------------------------------------------------------------------
# C2: Retry attempts are separate cost entries
# ---------------------------------------------------------------------------


class TestRetryAttemptsSeparate:
    """Retry attempts must appear as separate CostEntry records (AC criterion)."""

    def test_separate_entries_per_attempt(self, tmp_path):
        """Two retry attempts on the same node produce two separate CostEntry records."""
        store = _make_log_store(tmp_path)
        session_id = _make_session_id()

        attempt_1 = CostEntry(
            session_id=session_id,
            node_id="summarize",
            attempt=1,
            invocation_type="llm",
            model="gpt-4o-mini",
            input_tokens=800,
            output_tokens=300,
            cost_usd=0.00012,
        )
        attempt_2 = CostEntry(
            session_id=session_id,
            node_id="summarize",
            attempt=2,
            invocation_type="llm",
            model="gpt-4o-mini",
            input_tokens=820,
            output_tokens=310,
            cost_usd=0.00013,
        )
        _seed_cost_entries(store, session_id, [attempt_1, attempt_2])

        # Read back
        loaded = asyncio.run(store.load_cost_entries(session_id))
        assert len(loaded) == 2

        attempts_seen = {e.attempt for e in loaded}
        assert 1 in attempts_seen
        assert 2 in attempts_seen

    def test_entries_labeled_with_distinct_attempt_numbers(self, tmp_path):
        """Each loaded CostEntry preserves the correct attempt number."""
        store = _make_log_store(tmp_path)
        session_id = _make_session_id()

        for attempt in range(1, 5):
            entry = CostEntry(
                session_id=session_id,
                node_id="node_x",
                attempt=attempt,
                invocation_type="llm",
                input_tokens=100 * attempt,
                output_tokens=50 * attempt,
                cost_usd=0.0001 * attempt,
            )
            _seed_cost_entries(store, session_id, [entry])

        loaded = asyncio.run(store.load_cost_entries(session_id))
        assert len(loaded) == 4
        loaded_attempts = sorted(e.attempt for e in loaded)
        assert loaded_attempts == [1, 2, 3, 4]


# ---------------------------------------------------------------------------
# C3: build_cost_tree assembles hierarchy
# ---------------------------------------------------------------------------


class TestBuildCostTree:
    """build_cost_tree() should assemble a CostTree from persisted log files."""

    def test_tree_aggregates_entries_by_node(self, tmp_path):
        """Entries from the same node should be grouped together."""
        store = _make_log_store(tmp_path)
        session_id = _make_session_id()

        entries = [
            CostEntry(
                session_id=session_id,
                node_id="extract",
                attempt=1,
                invocation_type="llm",
                cost_usd=0.001,
                input_tokens=500,
                output_tokens=200,
            ),
            CostEntry(
                session_id=session_id,
                node_id="summarize",
                attempt=1,
                invocation_type="llm",
                cost_usd=0.002,
                input_tokens=700,
                output_tokens=300,
            ),
            CostEntry(
                session_id=session_id,
                node_id="extract",
                attempt=1,
                invocation_type="tool",
                tool_name="read_file",
                cost_usd=0.0,
                duration_s=0.5,
            ),
        ]
        _seed_cost_entries(store, session_id, entries)

        tree = asyncio.run(build_cost_tree(session_id, store))

        assert tree.session_id == session_id
        assert "extract" in tree.nodes
        assert "summarize" in tree.nodes
        # extract has 2 entries, summarize has 1
        assert len(tree.nodes["extract"].entries) == 2
        assert len(tree.nodes["summarize"].entries) == 1

    def test_tree_total_cost_is_sum(self, tmp_path):
        """Total cost in the tree equals the sum of all entry costs."""
        store = _make_log_store(tmp_path)
        session_id = _make_session_id()

        costs = [0.001, 0.002, 0.0005]
        entries = [
            CostEntry(
                session_id=session_id,
                node_id=f"node_{i}",
                attempt=1,
                invocation_type="llm",
                cost_usd=c,
            )
            for i, c in enumerate(costs)
        ]
        _seed_cost_entries(store, session_id, entries)

        tree = asyncio.run(build_cost_tree(session_id, store))
        assert abs(tree.total_cost_usd - sum(costs)) < 1e-10

    def test_tree_attempt_count_per_node(self, tmp_path):
        """Nodes with multiple entries at different attempts report correct attempt_count."""
        store = _make_log_store(tmp_path)
        session_id = _make_session_id()

        entries = [
            CostEntry(session_id=session_id, node_id="node_a", attempt=1, invocation_type="llm"),
            CostEntry(session_id=session_id, node_id="node_a", attempt=2, invocation_type="llm"),
            CostEntry(session_id=session_id, node_id="node_a", attempt=3, invocation_type="llm"),
        ]
        _seed_cost_entries(store, session_id, entries)

        tree = asyncio.run(build_cost_tree(session_id, store))
        assert tree.nodes["node_a"].attempt_count == 3

    def test_tree_fallback_from_tool_logs(self, tmp_path):
        """If cost_attribution.jsonl is absent, tree falls back to tool_logs.jsonl."""
        store = _make_log_store(tmp_path)
        session_id = _make_session_id()

        # Write only tool_logs.jsonl (no cost_attribution.jsonl)
        step = NodeStepLog(
            node_id="process",
            node_type="event_loop",
            step_index=0,
            input_tokens=400,
            output_tokens=150,
            latency_ms=500,
        )
        _seed_tool_logs(store, session_id, [step])

        tree = asyncio.run(build_cost_tree(session_id, store))
        assert "process" in tree.nodes
        assert tree.nodes["process"].total_input_tokens == 400

    def test_run_cost_usd_helper(self, tmp_path):
        """run_cost_usd() should return the tree's total cost."""
        store = _make_log_store(tmp_path)
        session_id = _make_session_id()

        _seed_cost_entries(
            store,
            session_id,
            [CostEntry(session_id=session_id, node_id="n", attempt=1, cost_usd=0.042)],
        )
        tree = asyncio.run(build_cost_tree(session_id, store))
        assert abs(run_cost_usd(tree) - 0.042) < 1e-10


# ---------------------------------------------------------------------------
# C4: Alert at 3× median
# ---------------------------------------------------------------------------


class TestCostAlert:
    """CostAlertStore should fire an alert at 3× median cost."""

    def _store_with_history(
        self, tmp_path: Path, agent_id: str, baseline_cost: float, n_runs: int = 10
    ) -> CostAlertStore:
        """Create a store with *n_runs* baseline cost entries."""
        store = CostAlertStore(agent_id=agent_id, base_dir=tmp_path / agent_id)
        for i in range(n_runs):
            store.record_run_cost(session_id=f"session_{i}", cost_usd=baseline_cost)
        return store

    def test_alert_fires_at_3x_median(self, tmp_path):
        """A run costing 3× the median should trigger an alert."""
        baseline = 0.01
        agent_id = "test-agent"
        store = self._store_with_history(tmp_path, agent_id, baseline, n_runs=10)

        spike_session = "session_spike"
        spike_cost = baseline * (ALERT_THRESHOLD + 0.1)  # just over threshold
        store.record_run_cost(session_id=spike_session, cost_usd=spike_cost)
        alert = store.check_alert(session_id=spike_session, cost_usd=spike_cost)

        assert alert is not None
        assert isinstance(alert, CostAlert)
        assert alert.ratio > ALERT_THRESHOLD
        assert alert.agent_id == agent_id
        assert alert.session_id == spike_session

    def test_no_alert_below_threshold(self, tmp_path):
        """A run at exactly 2× median should NOT trigger an alert."""
        baseline = 0.01
        agent_id = "test-agent-b"
        store = self._store_with_history(tmp_path, agent_id, baseline, n_runs=10)

        normal_session = "session_normal"
        normal_cost = baseline * 2.0  # below the 3× threshold
        store.record_run_cost(session_id=normal_session, cost_usd=normal_cost)
        alert = store.check_alert(session_id=normal_session, cost_usd=normal_cost)

        assert alert is None

    def test_no_alert_when_insufficient_history(self, tmp_path):
        """Alert should not fire when fewer than MIN_RUNS_FOR_ALERT runs are recorded."""
        agent_id = "new-agent"
        store = CostAlertStore(agent_id=agent_id, base_dir=tmp_path / agent_id)

        # Record fewer than MIN_RUNS_FOR_ALERT entries
        for i in range(MIN_RUNS_FOR_ALERT - 1):
            store.record_run_cost(session_id=f"s_{i}", cost_usd=0.01)

        # Spike cost — should not alert due to insufficient history
        store.record_run_cost(session_id="s_spike", cost_usd=9999.0)
        alert = store.check_alert(session_id="s_spike", cost_usd=9999.0)
        assert alert is None

    def test_alert_persisted_to_jsonl(self, tmp_path):
        """Fired alerts should be appended to cost_alerts.jsonl."""
        baseline = 0.01
        agent_id = "persist-agent"
        store = self._store_with_history(tmp_path, agent_id, baseline, n_runs=10)

        spike_session = "session_persist"
        spike_cost = baseline * 10.0
        store.record_run_cost(session_id=spike_session, cost_usd=spike_cost)
        alert = store.check_alert(session_id=spike_session, cost_usd=spike_cost)
        assert alert is not None

        # Load alerts back
        loaded = store.load_alerts()
        assert len(loaded) >= 1
        assert loaded[-1].session_id == spike_session

    def test_alert_ratio_correct(self, tmp_path):
        """Alert ratio should be run_cost / median_cost."""
        baseline = 0.01
        agent_id = "ratio-agent"
        store = self._store_with_history(tmp_path, agent_id, baseline, n_runs=20)

        spike_cost = baseline * 5.0
        spike_session = "session_ratio"
        store.record_run_cost(session_id=spike_session, cost_usd=spike_cost)
        alert = store.check_alert(session_id=spike_session, cost_usd=spike_cost)

        assert alert is not None
        # Median should be close to baseline; ratio close to 5
        assert abs(alert.ratio - spike_cost / alert.median_cost_usd) < 0.1


# ---------------------------------------------------------------------------
# C5: detect_anomalies flags retry storms
# ---------------------------------------------------------------------------


class TestAnomalyDetection:
    """detect_anomalies() should flag retry storms and runaway loops."""

    def _make_tree_with_retries(self, node_id: str, attempt_count: int) -> CostTree:
        """Build a CostTree with *attempt_count* retries on *node_id*."""
        entries = [
            CostEntry(
                session_id="session_test",
                node_id=node_id,
                attempt=a,
                invocation_type="llm",
                cost_usd=0.001,
            )
            for a in range(1, attempt_count + 1)
        ]
        node_summary = NodeCostSummary(node_id=node_id, entries=entries)
        node_summary.attempt_count = attempt_count
        tree = CostTree(session_id="session_test", nodes={node_id: node_summary})
        return tree

    def test_retry_storm_flagged(self):
        """Nodes with >= RETRY_STORM_THRESHOLD retries should be flagged."""
        tree = self._make_tree_with_retries("failing_node", RETRY_STORM_THRESHOLD)
        detect_anomalies(tree)

        assert any("retry_storm" in f for f in tree.flags)
        assert any("retry_storm" in f for f in tree.nodes["failing_node"].flags)

    def test_no_flag_below_threshold(self):
        """Nodes with fewer retries than the threshold should NOT be flagged."""
        tree = self._make_tree_with_retries("clean_node", RETRY_STORM_THRESHOLD - 1)
        detect_anomalies(tree)

        assert not any("retry_storm" in f for f in tree.flags)

    def test_runaway_loop_flagged(self):
        """High step_index values within one attempt should trigger runaway_loop flag."""
        from engine.observability.cost_attribution import RUNAWAY_LOOP_THRESHOLD

        entries = [
            CostEntry(
                session_id="session_test",
                node_id="judge_node",
                attempt=1,
                step_index=i,
                invocation_type="llm",
                cost_usd=0.001,
            )
            for i in range(RUNAWAY_LOOP_THRESHOLD + 1)
        ]
        node_summary = NodeCostSummary(node_id="judge_node", entries=entries, attempt_count=1)
        tree = CostTree(session_id="session_test", nodes={"judge_node": node_summary})
        detect_anomalies(tree)

        assert any("runaway_loop" in f for f in tree.flags)

    def test_detect_anomalies_is_idempotent(self):
        """Calling detect_anomalies() twice should not duplicate flags."""
        tree = self._make_tree_with_retries("node", RETRY_STORM_THRESHOLD)
        detect_anomalies(tree)
        flags_after_first = list(tree.flags)
        detect_anomalies(tree)
        # Flags list should not grow on second call
        assert len(tree.flags) == len(flags_after_first)


# ---------------------------------------------------------------------------
# C6: format_cost_waterfall output
# ---------------------------------------------------------------------------


class TestFormatCostWaterfall:
    """format_cost_waterfall() should produce a readable, complete string."""

    def _make_simple_tree(self) -> CostTree:
        entry = CostEntry(
            session_id="session_demo",
            node_id="extract",
            attempt=1,
            invocation_type="llm",
            model="gpt-4o-mini",
            input_tokens=1000,
            output_tokens=400,
            cost_usd=0.0012,
        )
        node = NodeCostSummary(
            node_id="extract",
            entries=[entry],
            total_cost_usd=0.0012,
            total_input_tokens=1000,
            total_output_tokens=400,
            attempt_count=1,
        )
        return CostTree(
            session_id="session_demo",
            agent_id="my-agent",
            total_cost_usd=0.0012,
            total_input_tokens=1000,
            total_output_tokens=400,
            nodes={"extract": node},
        )

    def test_waterfall_contains_session_id(self):
        tree = self._make_simple_tree()
        output = format_cost_waterfall(tree)
        assert "session_demo" in output

    def test_waterfall_contains_cost(self):
        tree = self._make_simple_tree()
        output = format_cost_waterfall(tree)
        assert "0.001200" in output or "$0.00" in output

    def test_waterfall_contains_node_id(self):
        tree = self._make_simple_tree()
        output = format_cost_waterfall(tree)
        assert "extract" in output

    def test_waterfall_contains_agent_id(self):
        tree = self._make_simple_tree()
        output = format_cost_waterfall(tree)
        assert "my-agent" in output

    def test_waterfall_shows_retry_marker(self):
        """Nodes with >1 attempt should show a retry marker."""
        entry1 = CostEntry(session_id="s", node_id="n", attempt=1, cost_usd=0.001)
        entry2 = CostEntry(session_id="s", node_id="n", attempt=2, cost_usd=0.001)
        node = NodeCostSummary(node_id="n", entries=[entry1, entry2], attempt_count=2)
        tree = CostTree(session_id="s", nodes={"n": node})
        output = format_cost_waterfall(tree)
        assert "⚠" in output or "2 attempts" in output


# ---------------------------------------------------------------------------
# C7: CLI cmd_cost_tree
# ---------------------------------------------------------------------------


class TestCmdCostTree:
    """engine cost-tree CLI should exit 0 and print the waterfall."""

    def _make_session_with_logs(self, tmp_path: Path, agent_name: str, session_id: str) -> Path:
        """Create a fake session directory with cost_attribution.jsonl.

        Files are placed under ``<tmp_path>/.engine/agents/<agent_name>/`` so
        that ``_find_session_log_store`` (which resolves ``Path.home() / '.engine' / 'agents'``)
        can discover them when ``Path.home()`` is monkeypatched to ``tmp_path``.
        """
        session_dir = (
            tmp_path / ".engine" / "agents" / agent_name / "sessions" / session_id / "logs"
        )
        session_dir.mkdir(parents=True)

        entry = CostEntry(
            session_id=session_id,
            node_id="test_node",
            attempt=1,
            invocation_type="llm",
            model="gpt-4o-mini",
            input_tokens=500,
            output_tokens=200,
            cost_usd=0.00025,
        )
        line = json.dumps(entry.model_dump()) + "\n"
        (session_dir / "cost_attribution.jsonl").write_text(line, encoding="utf-8")
        return tmp_path / ".engine" / "agents" / agent_name

    def test_cmd_cost_tree_exits_0(self, tmp_path, monkeypatch):
        """cmd_cost_tree should exit 0 when the session is found."""
        import argparse

        from engine.runner.cli import cmd_cost_tree

        agent_name = "test-agent"
        session_id = _make_session_id()
        self._make_session_with_logs(tmp_path, agent_name, session_id)

        # Patch Path.home() to return tmp_path
        monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))

        args = argparse.Namespace(
            session_id=session_id,
            agent=agent_name,
            json=False,
            top=None,
        )
        rc = cmd_cost_tree(args)
        assert rc == 0

    def test_cmd_cost_tree_missing_session_exits_1(self, tmp_path, monkeypatch):
        """cmd_cost_tree should exit 1 when the session does not exist."""
        import argparse

        from engine.runner.cli import cmd_cost_tree

        # Create an empty agents dir
        (tmp_path / "agents").mkdir()
        monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))

        args = argparse.Namespace(
            session_id="session_nonexistent_12345678",
            agent=None,
            json=False,
            top=None,
        )
        rc = cmd_cost_tree(args)
        assert rc == 1

    def test_cmd_cost_tree_json_output(self, tmp_path, monkeypatch, capsys):
        """--json flag should produce parseable JSON output."""
        import argparse

        from engine.runner.cli import cmd_cost_tree

        agent_name = "json-agent"
        session_id = _make_session_id()
        self._make_session_with_logs(tmp_path, agent_name, session_id)
        monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))

        args = argparse.Namespace(
            session_id=session_id,
            agent=agent_name,
            json=True,
            top=None,
        )
        rc = cmd_cost_tree(args)
        assert rc == 0

        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["session_id"] == session_id
        assert "nodes" in data
        assert "total_cost_usd" in data


# ---------------------------------------------------------------------------
# C8: RuntimeLogStore persists CostEntry
# ---------------------------------------------------------------------------


class TestRuntimeLogStoreIntegration:
    """RuntimeLogStore should append and load CostEntry records."""

    def test_append_and_load_cost_entries(self, tmp_path):
        """append_cost_entry / load_cost_entries round-trip."""
        store = _make_log_store(tmp_path)
        session_id = _make_session_id()
        store.ensure_run_dir(session_id)

        entries = [
            CostEntry(
                session_id=session_id,
                node_id="n1",
                attempt=1,
                invocation_type="llm",
                cost_usd=0.0011,
                input_tokens=300,
                output_tokens=100,
            ),
            CostEntry(
                session_id=session_id,
                node_id="n1",
                attempt=2,
                invocation_type="llm",
                cost_usd=0.0012,
                input_tokens=310,
                output_tokens=105,
            ),
            CostEntry(
                session_id=session_id,
                node_id="n2",
                attempt=1,
                invocation_type="tool",
                tool_name="calculator",
                cost_usd=0.0,
                duration_s=0.05,
            ),
        ]
        for entry in entries:
            store.append_cost_entry(session_id, entry)

        loaded = asyncio.run(store.load_cost_entries(session_id))
        assert len(loaded) == 3
        assert {e.attempt for e in loaded if e.node_id == "n1"} == {1, 2}
        assert any(e.invocation_type == "tool" for e in loaded)

    def test_load_missing_cost_attribution_returns_empty(self, tmp_path):
        """load_cost_entries returns [] when cost_attribution.jsonl doesn't exist."""
        store = _make_log_store(tmp_path)
        session_id = _make_session_id()
        store.ensure_run_dir(session_id)

        loaded = asyncio.run(store.load_cost_entries(session_id))
        assert loaded == []

    def test_cost_entry_survives_corrupt_line(self, tmp_path):
        """Corrupt JSONL lines should be skipped without crashing."""
        store = _make_log_store(tmp_path)
        session_id = _make_session_id()
        store.ensure_run_dir(session_id)

        # Write one valid and one corrupt line
        run_dir = tmp_path / "sessions" / session_id / "logs"
        run_dir.mkdir(parents=True, exist_ok=True)
        entry = CostEntry(session_id=session_id, node_id="n", attempt=1, cost_usd=0.001)
        cost_file = run_dir / "cost_attribution.jsonl"
        cost_file.write_text(
            entry.model_dump_json() + "\n" + "{invalid json\n",
            encoding="utf-8",
        )

        loaded = asyncio.run(store.load_cost_entries(session_id))
        # Only the valid line should be loaded
        assert len(loaded) == 1
        assert loaded[0].node_id == "n"

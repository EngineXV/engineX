from hourly_tracking import graph


def test_graph_loads():
    assert graph.id == "hourly-tracking-graph"


def test_node_count():
    assert len(graph.nodes) == 5


def test_feedback_loop_exists():
    edge_ids = [edge.id for edge in graph.edges]
    assert "correct-to-validate" in edge_ids


def test_hourly_schedule():
    trigger = graph.async_entry_points[0]
    assert trigger.trigger_config["interval_minutes"] == 60

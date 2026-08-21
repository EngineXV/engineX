from hourly_tracking import graph


def test_graph_loads():
    assert graph.id == "hourly-tracking-graph"


def test_node_count():
    assert len(graph.nodes) == 6
    assert "human_review" in [node.id for node in graph.nodes]
    assert graph.pause_nodes == ["human_review"]


def test_feedback_loop_exists():
    edge_ids = [edge.id for edge in graph.edges]
    assert "correct-to-validate" in edge_ids


def test_human_review_has_reject_edge():
    edges = {edge.id: edge for edge in graph.edges}
    assert "human-to-correct" in edges

    reject_edge = edges["human-to-correct"]
    assert reject_edge.source == "human_review"
    assert reject_edge.target == "correct_transactions"
    assert reject_edge.condition_expr == "human_approved == False"


def test_human_review_covers_both_outcomes():
    outgoing = [edge for edge in graph.edges if edge.source == "human_review"]
    exprs = {edge.condition_expr for edge in outgoing}
    assert "human_approved == True" in exprs
    assert "human_approved == False" in exprs


def test_hourly_schedule():
    trigger = graph.async_entry_points[0]
    assert trigger.trigger_config["interval_minutes"] == 60

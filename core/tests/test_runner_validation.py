"""Tests for AgentRunner validation logic."""

from engine.graph import EdgeSpec, Goal, GraphSpec, NodeSpec
from engine.runner.runner import AgentRunner
from engine.runner.tool_registry import ToolRegistry


def test_validate_ignores_builtin_tools():
    """Runner.validate() should not warn about missing built-in tools (set_output, ask_user)."""
    
    # Create a node that requires built-in tools and one missing custom tool
    node = NodeSpec(
        id="test_node",
        name="Test Node",
        description="A test node",
        node_type="event_loop",
        input_keys=[],
        output_keys=[],
        tools=["set_output", "ask_user", "missing_custom_tool"]
    )
    
    goal = Goal(id="test-goal", name="Test Goal", description="test", success_criteria=[])
    
    graph = GraphSpec(
        id="test-graph",
        goal_id=goal.id,
        version="1.0",
        entry_node="test_node",
        entry_points={"start": "test_node"},
        terminal_nodes=["test_node"],
        pause_nodes=[],
        nodes=[node],
        edges=[]
    )
    
    from pathlib import Path
    runner = AgentRunner(
        agent_path=Path("dummy_path"),
        graph=graph,
        goal=goal,
    )
    
    result = runner.validate()
    
    # Check that there are warnings (Graph errors might exist due to success criteria etc, but we just check the list)
    missing_warnings = [w for w in result.warnings if "Missing tool implementations" in w]
    assert len(missing_warnings) == 1
    
    warning_text = missing_warnings[0]
    assert "missing_custom_tool" in warning_text
    
    # We should NOT see warnings for set_output or ask_user
    assert "set_output" not in warning_text
    assert "ask_user" not in warning_text

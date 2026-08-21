"""Agent export loading and metadata types"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from engine.config import get_max_retries_per_node
from engine.graph import Goal
from engine.graph.edge import AsyncEntryPointSpec, EdgeCondition, EdgeSpec, GraphSpec
from engine.graph.goal import Constraint, SuccessCriterion
from engine.graph.node import NodeSpec


@dataclass
class AgentInfo:
    """Information about an exported agent"""

    name: str
    description: str
    goal_name: str
    goal_description: str
    node_count: int
    edge_count: int
    nodes: list[dict]
    edges: list[dict]
    entry_node: str
    terminal_nodes: list[str]
    success_criteria: list[dict]
    constraints: list[dict]
    required_tools: list[str]
    has_tools_module: bool
    # Multi-entry-point support
    async_entry_points: list[dict] = field(default_factory=list)
    is_multi_entry_point: bool = False
    # Supervisor metadata (optional)
    supervisor: bool = False
    supervisor_name: str = ""
    department: str = ""
    role_title: str = ""


@dataclass
class ValidationResult:
    """Result of agent validation"""

    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    missing_tools: list[str] = field(default_factory=list)
    missing_credentials: list[str] = field(default_factory=list)


def load_agent_export(data: str | dict) -> tuple[GraphSpec, Goal]:
    """Load GraphSpec and Goal from export_graph() output"""
    if isinstance(data, str):
        data = json.loads(data)

    # Extract graph and goal
    graph_data = data.get("graph", {})
    goal_data = data.get("goal", {})

    # Build NodeSpec objects
    nodes = []
    for node_data in graph_data.get("nodes", []):
        nodes.append(NodeSpec(**node_data))

    # Build EdgeSpec objects
    edges = []
    for edge_data in graph_data.get("edges", []):
        condition_str = edge_data.get("condition", "on_success")
        condition_map = {
            "always": EdgeCondition.ALWAYS,
            "on_success": EdgeCondition.ON_SUCCESS,
            "on_failure": EdgeCondition.ON_FAILURE,
            "conditional": EdgeCondition.CONDITIONAL,
            "llm_decide": EdgeCondition.LLM_DECIDE,
        }
        edge = EdgeSpec(
            id=edge_data["id"],
            source=edge_data["source"],
            target=edge_data["target"],
            condition=condition_map.get(condition_str, EdgeCondition.ON_SUCCESS),
            condition_expr=edge_data.get("condition_expr"),
            priority=edge_data.get("priority", 0),
            input_mapping=edge_data.get("input_mapping", {}),
        )
        edges.append(edge)

    # Build AsyncEntryPointSpec objects for multi-entry-point support
    async_entry_points = []
    for aep_data in graph_data.get("async_entry_points", []):
        async_entry_points.append(
            AsyncEntryPointSpec(
                id=aep_data["id"],
                name=aep_data.get("name", aep_data["id"]),
                entry_node=aep_data["entry_node"],
                trigger_type=aep_data.get("trigger_type", "manual"),
                trigger_config=aep_data.get("trigger_config", {}),
                isolation_level=aep_data.get("isolation_level", "shared"),
                priority=aep_data.get("priority", 0),
                max_concurrent=aep_data.get("max_concurrent", 10),
            )
        )

    # Build GraphSpec
    graph = GraphSpec(
        id=graph_data.get("id", "agent-graph"),
        goal_id=graph_data.get("goal_id", ""),
        version=graph_data.get("version", "1.0.0"),
        entry_node=graph_data.get("entry_node", ""),
        entry_points=graph_data.get("entry_points", {}),
        async_entry_points=async_entry_points,
        terminal_nodes=graph_data.get("terminal_nodes", []),
        pause_nodes=graph_data.get("pause_nodes", []),
        nodes=nodes,
        edges=edges,
        max_steps=graph_data.get("max_steps", 100),
        max_retries_per_node=graph_data.get("max_retries_per_node", get_max_retries_per_node()),
        description=graph_data.get("description", ""),
    )

    success_criteria = []
    for sc_data in goal_data.get("success_criteria", []):
        success_criteria.append(
            SuccessCriterion(
                id=sc_data["id"],
                description=sc_data["description"],
                metric=sc_data.get("metric", ""),
                target=sc_data.get("target", ""),
                weight=sc_data.get("weight", 1.0),
            )
        )

    constraints = []
    for c_data in goal_data.get("constraints", []):
        constraints.append(
            Constraint(
                id=c_data["id"],
                description=c_data["description"],
                constraint_type=c_data.get("constraint_type", "hard"),
                category=c_data.get("category", "safety"),
                check=c_data.get("check", ""),
            )
        )

    goal = Goal(
        id=goal_data.get("id", ""),
        name=goal_data.get("name", ""),
        description=goal_data.get("description", ""),
        success_criteria=success_criteria,
        constraints=constraints,
    )

    return graph, goal

"""Supervised Agreement Analysis — Supervisor + worker."""

from .agent import (
    edges,
    entry_node,
    entry_points,
    goal,
    graph,
    nodes,
    pause_nodes,
    supervisor_goal,
    supervised_worker_path,
    terminal_nodes,
)
from .config import default_config, metadata

__version__ = metadata.version

__all__ = [
    "goal",
    "supervisor_goal",
    "nodes",
    "edges",
    "graph",
    "entry_node",
    "entry_points",
    "pause_nodes",
    "terminal_nodes",
    "default_config",
    "metadata",
    "supervised_worker_path",
]

"""Deep Research template — interactive multi-source research with HITL review."""

from .agent import (
    edges,
    entry_node,
    entry_points,
    goal,
    graph,
    nodes,
    pause_nodes,
    terminal_nodes,
)
from .config import default_config, metadata

__version__ = metadata.version

__all__ = [
    "goal",
    "nodes",
    "edges",
    "graph",
    "entry_node",
    "entry_points",
    "pause_nodes",
    "terminal_nodes",
    "default_config",
    "metadata",
]

"""Meeting Scheduler template — calendar booking with Google Meet and Sheets logging."""

from .agent import (
    conversation_mode,
    edges,
    entry_node,
    entry_points,
    goal,
    graph,
    identity_prompt,
    loop_config,
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
    "conversation_mode",
    "identity_prompt",
    "loop_config",
    "default_config",
    "metadata",
]

"""Contract Review — extract contract fields with human approval"""

from .agent import (
    ContractReviewAgent,
    default_agent,
    edges,
    goal,
    nodes,
)
from .config import AgentMetadata, default_config, metadata

__version__ = "1.0.0"

__all__ = [
    "ContractReviewAgent",
    "default_agent",
    "goal",
    "nodes",
    "edges",
    "AgentMetadata",
    "default_config",
    "metadata",
]

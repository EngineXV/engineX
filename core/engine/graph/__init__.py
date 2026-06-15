"""Graph structures: Goals, Nodes, Edges, and Execution"""

from engine.graph.client_io import (
    ActiveNodeClientIO,
    ClientIOGateway,
    InertNodeClientIO,
    NodeClientIO,
)
from engine.graph.conversation import ConversationStore, Message, NodeConversation
from engine.graph.edge import DEFAULT_MAX_TOKENS, EdgeCondition, EdgeSpec, GraphSpec
from engine.graph.event_loop_node import (
    EventLoopNode,
    JudgeProtocol,
    JudgeVerdict,
    LoopConfig,
    OutputAccumulator,
)
from engine.graph.executor import GraphExecutor
from engine.graph.goal import Constraint, Goal, GoalStatus, SuccessCriterion
from engine.graph.hitl import ApprovalDecision, ApprovalResult  # noqa: F401
from engine.graph.node import NodeContext, NodeProtocol, NodeResult, NodeSpec

__all__ = [
    # Goal
    "Goal",
    "SuccessCriterion",
    "Constraint",
    "GoalStatus",
    # Node
    "NodeSpec",
    "NodeContext",
    "NodeResult",
    "NodeProtocol",
    # Edge
    "EdgeSpec",
    "EdgeCondition",
    "GraphSpec",
    "DEFAULT_MAX_TOKENS",
    # Executor
    "GraphExecutor",
    # Conversation
    "NodeConversation",
    "ConversationStore",
    "Message",
    # Event Loop
    "EventLoopNode",
    "LoopConfig",
    "OutputAccumulator",
    "JudgeProtocol",
    "JudgeVerdict",
    # HITL
    "ApprovalDecision",
    "ApprovalResult",
    # Client I/O
    "NodeClientIO",
    "ActiveNodeClientIO",
    "InertNodeClientIO",
    "ClientIOGateway",
]

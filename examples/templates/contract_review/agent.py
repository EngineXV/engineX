"""Agent graph for Contract Review"""

from framework.graph import Constraint, EdgeCondition, EdgeSpec, Goal, SuccessCriterion
from framework.graph.edge import GraphSpec
from framework.graph.executor import ExecutionResult, GraphExecutor
from framework.runtime.event_bus import EventBus
from framework.runtime.core import Runtime
from framework.llm import LiteLLMProvider
from framework.runner.tool_registry import ToolRegistry

from .config import default_config, metadata
from .nodes import audit_node, extract_node, human_review_node, intake_node

goal = Goal(
    id="contract-review",
    name="Contract Review",
    description="Extract contract fields with human approval and audit trail.",
    success_criteria=[
        SuccessCriterion(
            id="sc-fields",
            description="Key contract fields extracted",
            metric="fields_extracted",
            target="true",
            weight=0.35,
        ),
        SuccessCriterion(
            id="sc-review",
            description="Human reviewer approved or edited output",
            metric="human_review_complete",
            target="true",
            weight=0.35,
        ),
        SuccessCriterion(
            id="sc-audit",
            description="Audit record produced",
            metric="audit_record_present",
            target="true",
            weight=0.3,
        ),
    ],
    constraints=[
        Constraint(
            id="c-no-fabrication",
            description="Do not add contract terms not present in source text",
            constraint_type="hard",
            category="quality",
        ),
    ],
)

nodes = [intake_node, extract_node, human_review_node, audit_node]

edges = [
    EdgeSpec(
        id="intake-to-extract",
        source="intake",
        target="extract",
        condition=EdgeCondition.ON_SUCCESS,
        priority=1,
    ),
    EdgeSpec(
        id="extract-to-review",
        source="extract",
        target="human_review",
        condition=EdgeCondition.ON_SUCCESS,
        priority=1,
    ),
    EdgeSpec(
        id="review-to-audit",
        source="human_review",
        target="audit",
        condition=EdgeCondition.ON_SUCCESS,
        priority=1,
    ),
]

entry_node = "intake"
entry_points = {"start": "intake"}
pause_nodes = ["human_review"]
terminal_nodes = ["audit"]
loop_config = {
    "max_iterations": 50,
    "max_tool_calls_per_turn": 10,
    "max_history_tokens": 64000,
}


class ContractReviewAgent:
    """Contract Review — intake → extract → human review → audit"""

    def __init__(self, config=None):
        self.config = config or default_config
        self.goal = goal
        self.nodes = nodes
        self.edges = edges
        self.entry_node = entry_node
        self.entry_points = entry_points
        self.pause_nodes = pause_nodes
        self.terminal_nodes = terminal_nodes
        self._executor: GraphExecutor | None = None
        self._graph: GraphSpec | None = None
        self._event_bus: EventBus | None = None
        self._tool_registry: ToolRegistry | None = None

    def _build_graph(self) -> GraphSpec:
        return GraphSpec(
            id="contract-review-graph",
            goal_id=goal.id,
            version="1.0.0",
            entry_node=entry_node,
            entry_points=entry_points,
            terminal_nodes=terminal_nodes,
            pause_nodes=pause_nodes,
            nodes=nodes,
            edges=edges,
            default_model=self.config.model,
            max_tokens=self.config.max_tokens,
            loop_config=loop_config,
        )

    def _setup(self) -> GraphExecutor:
        from pathlib import Path

        storage_path = Path.home() / ".engine" / "agents" / "contract_review"
        storage_path.mkdir(parents=True, exist_ok=True)

        self._event_bus = EventBus()
        self._tool_registry = ToolRegistry()

        mcp_config_path = Path(__file__).parent / "mcp_servers.json"
        if mcp_config_path.exists():
            self._tool_registry.load_mcp_config(mcp_config_path)

        llm = LiteLLMProvider(
            model=self.config.model,
            api_key=self.config.api_key,
            api_base=self.config.api_base,
        )

        self._graph = self._build_graph()
        runtime = Runtime(storage_path)

        self._executor = GraphExecutor(
            runtime=runtime,
            llm=llm,
            tools=list(self._tool_registry.get_tools().values()),
            tool_executor=self._tool_registry.get_executor(),
            event_bus=self._event_bus,
            storage_path=storage_path,
            loop_config=self._graph.loop_config,
        )
        return self._executor

    async def start(self) -> None:
        if self._executor is None:
            self._setup()

    async def stop(self) -> None:
        self._executor = None
        self._event_bus = None

    async def trigger_and_wait(
        self,
        entry_point: str,
        input_data: dict,
        timeout: float | None = None,
        session_state: dict | None = None,
    ) -> ExecutionResult | None:
        if self._executor is None or self._graph is None:
            raise RuntimeError("Agent not started")
        return await self._executor.execute(
            graph=self._graph,
            goal=goal,
            input_data=input_data,
            session_state=session_state,
        )

    async def run(self, context: dict, session_state=None) -> ExecutionResult:
        await self.start()
        try:
            result = await self.trigger_and_wait("start", context, session_state=session_state)
            return result or ExecutionResult(success=False, error="Execution timeout")
        finally:
            await self.stop()

    def info(self):
        return {
            "name": metadata.name,
            "version": metadata.version,
            "description": metadata.description,
            "goal": {"name": self.goal.name, "description": self.goal.description},
            "nodes": [n.id for n in self.nodes],
            "edges": [e.id for e in self.edges],
            "entry_node": self.entry_node,
            "entry_points": self.entry_points,
            "pause_nodes": self.pause_nodes,
            "terminal_nodes": self.terminal_nodes,
            "client_facing_nodes": [n.id for n in self.nodes if n.client_facing],
        }

    def validate(self):
        errors = []
        warnings = []
        node_ids = {node.id for node in self.nodes}
        for edge in self.edges:
            if edge.source not in node_ids:
                errors.append(f"Edge {edge.id}: source '{edge.source}' not found")
            if edge.target not in node_ids:
                errors.append(f"Edge {edge.id}: target '{edge.target}' not found")
        if self.entry_node not in node_ids:
            errors.append(f"Entry node '{self.entry_node}' not found")
        for terminal in self.terminal_nodes:
            if terminal not in node_ids:
                errors.append(f"Terminal node '{terminal}' not found")
        return {"valid": len(errors) == 0, "errors": errors, "warnings": warnings}


default_agent = ContractReviewAgent()

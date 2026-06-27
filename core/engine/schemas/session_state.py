"""Session State Schema - Unified state for session execution"""

from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field, computed_field

if TYPE_CHECKING:
    from engine.graph.executor import ExecutionResult


class SessionStatus(StrEnum):
    """Status of a session execution"""

    ACTIVE = "active"  # Currently executing
    PAUSED = "paused"  # Waiting for resume (client input, pause node)
    PENDING_HUMAN_APPROVAL = "pending_human_approval"  # Waiting for explicit HITL approval
    COMPLETED = "completed"  # Finished successfully
    FAILED = "failed"  # Finished with error
    CANCELLED = "cancelled"  # User/system cancelled


class SessionTimestamps(BaseModel):
    """Timestamps tracking session lifecycle"""

    started_at: str  # ISO 8601 format
    updated_at: str  # ISO 8601 format (updated on every state write)
    completed_at: str | None = None
    paused_at_time: str | None = None  # When it was paused

    model_config = {"extra": "allow"}


class SessionProgress(BaseModel):
    """Execution progress tracking"""

    current_node: str | None = None
    paused_at: str | None = None  # Node ID where paused
    resume_from: str | None = None  # Entry point or node ID to resume from
    steps_executed: int = 0
    total_tokens: int = 0
    total_latency_ms: int = 0
    path: list[str] = Field(default_factory=list)  # Node IDs traversed

    # Quality metrics (from ExecutionResult)
    total_retries: int = 0
    nodes_with_failures: list[str] = Field(default_factory=list)
    retry_details: dict[str, int] = Field(default_factory=dict)
    had_partial_failures: bool = False
    execution_quality: str = "clean"  # "clean", "degraded", or "failed"
    node_visit_counts: dict[str, int] = Field(default_factory=dict)

    model_config = {"extra": "allow"}


class SessionResult(BaseModel):
    """Final result of session execution"""

    success: bool | None = None  # None if still running
    error: str | None = None
    output: dict[str, Any] = Field(default_factory=dict)

    model_config = {"extra": "allow"}


class SessionMetrics(BaseModel):
    """Execution metrics (from Run.metrics)"""

    decision_count: int = 0
    problem_count: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    nodes_executed: list[str] = Field(default_factory=list)
    edges_traversed: list[str] = Field(default_factory=list)

    model_config = {"extra": "allow"}


class SessionState(BaseModel):
    """Complete state for a session execution"""

    # Schema version for forward/backward compatibility
    schema_version: str = "1.1"

    # Identity
    session_id: str  # Format: session_YYYYMMDD_HHMMSS_{uuid_8char}
    stream_id: str = ""  # Which ExecutionStream created this
    correlation_id: str = ""  # For correlating related executions

    # Status
    status: SessionStatus = SessionStatus.ACTIVE

    # Goal/Agent context
    goal_id: str
    agent_id: str = ""
    entry_point: str = "start"

    # Timestamps
    timestamps: SessionTimestamps

    # Progress
    progress: SessionProgress = Field(default_factory=SessionProgress)

    # Result
    result: SessionResult = Field(default_factory=SessionResult)

    # Memory (for resumability)
    memory: dict[str, Any] = Field(default_factory=dict)

    # Metrics
    metrics: SessionMetrics = Field(default_factory=SessionMetrics)

    # Problems (from Run.problems)
    problems: list[dict[str, Any]] = Field(default_factory=list)

    # Decisions (from Run.decisions - can be large, so store references)
    decisions: list[dict[str, Any]] = Field(default_factory=list)

    # Input data (for debugging/replay)
    input_data: dict[str, Any] = Field(default_factory=dict)

    # Isolation level (from ExecutionContext)
    isolation_level: str = "shared"

    # Checkpointing (for crash recovery and resume-from-failure)
    checkpoint_enabled: bool = False
    latest_checkpoint_id: str | None = None

    model_config = {"extra": "allow"}

    @computed_field
    @property
    def duration_ms(self) -> int:
        """Duration of the session in milliseconds"""
        if not self.timestamps.completed_at:
            return 0
        started = datetime.fromisoformat(self.timestamps.started_at)
        completed = datetime.fromisoformat(self.timestamps.completed_at)
        return int((completed - started).total_seconds() * 1000)

    @computed_field
    @property
    def is_resumable(self) -> bool:
        """Can this session be resumed?"""
        return self.status != SessionStatus.COMPLETED

    @computed_field
    @property
    def is_resumable_from_checkpoint(self) -> bool:
        """Can this session be resumed from a checkpoint?"""
        # ANY session with checkpoints can be resumed (not just failed ones)
        # This enables: pause/resume, iterative execution, continuation after completion
        return self.checkpoint_enabled and self.latest_checkpoint_id is not None

    @classmethod
    def from_execution_result(
        cls,
        session_id: str,
        goal_id: str,
        result: "ExecutionResult",
        stream_id: str = "",
        correlation_id: str = "",
        started_at: str = "",
        input_data: dict[str, Any] | None = None,
        agent_id: str = "",
        entry_point: str = "start",
    ) -> "SessionState":
        """Create SessionState from ExecutionResult"""

        now = datetime.now().isoformat()

        # Determine status based on execution result
        if result.session_state.get("status") == SessionStatus.PENDING_HUMAN_APPROVAL:
            status = SessionStatus.PENDING_HUMAN_APPROVAL
        elif result.paused_at:
            status = SessionStatus.PAUSED
        elif result.success:
            status = SessionStatus.COMPLETED
        else:
            status = SessionStatus.FAILED

        return cls(
            session_id=session_id,
            stream_id=stream_id,
            correlation_id=correlation_id,
            goal_id=goal_id,
            agent_id=agent_id,
            entry_point=entry_point,
            status=status,
            timestamps=SessionTimestamps(
                started_at=started_at or now,
                updated_at=now,
                completed_at=now if not result.paused_at else None,
                paused_at_time=now if result.paused_at else None,
            ),
            progress=SessionProgress(
                current_node=result.paused_at or (result.path[-1] if result.path else None),
                paused_at=result.paused_at,
                resume_from=result.session_state.get("resume_from")
                if result.session_state
                else None,
                steps_executed=result.steps_executed,
                total_tokens=result.total_tokens,
                total_latency_ms=result.total_latency_ms,
                path=result.path,
                total_retries=result.total_retries,
                nodes_with_failures=result.nodes_with_failures,
                retry_details=result.retry_details,
                had_partial_failures=result.had_partial_failures,
                execution_quality=result.execution_quality,
                node_visit_counts=result.node_visit_counts,
            ),
            result=SessionResult(
                success=result.success,
                error=result.error,
                output=result.output,
            ),
            memory=result.session_state.get("memory", {}) if result.session_state else {},
            input_data=input_data or {},
        )

    def to_session_state_dict(self) -> dict[str, Any]:
        """Convert to session_state format for GraphExecutor.execute()"""
        # Derive resume target: explicit > last node in path > entry point
        resume_from = (
            self.progress.resume_from
            or self.progress.paused_at
            or (self.progress.path[-1] if self.progress.path else None)
        )
        return {
            "status": self.status,
            "paused_at": resume_from,
            "resume_from": resume_from,
            "memory": self.memory,
            "execution_path": self.progress.path,
            "node_visit_counts": self.progress.node_visit_counts,
        }


class BillingCodeMapping(BaseModel):
    """Proposed medical billing code mapped from clinical documentation."""

    code: str
    code_system: str  # ICD-11, CPT, HCPCS, etc.
    description: str = ""
    procedure: str = ""
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    financial_risk: float = Field(default=0.0, ge=0.0, le=1.0)
    modifiers: list[str] = Field(default_factory=list)
    diagnosis_pointers: list[str] = Field(default_factory=list)
    source_spans: list[dict[str, Any]] = Field(default_factory=list)
    validation_flags: list[str] = Field(default_factory=list)
    carrier_rules_checked: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = {"extra": "allow"}


class BillingConfidenceVector(BaseModel):
    """Confidence dimensions used for audit and routing decisions."""

    extraction: float = Field(default=1.0, ge=0.0, le=1.0)
    code_match: float = Field(default=1.0, ge=0.0, le=1.0)
    modifier_match: float = Field(default=1.0, ge=0.0, le=1.0)
    carrier_compliance: float = Field(default=1.0, ge=0.0, le=1.0)

    model_config = {"extra": "allow"}

    @computed_field
    @property
    def minimum(self) -> float:
        """Lowest confidence dimension."""
        return min(
            self.extraction,
            self.code_match,
            self.modifier_match,
            self.carrier_compliance,
        )


class BillingHumanOverrideLog(BaseModel):
    """Auditable record of a human billing auditor decision."""

    auditor_id: str
    action: str  # approve, reject, modify
    reason: str = ""
    original_code: BillingCodeMapping | None = None
    approved_code: BillingCodeMapping | None = None
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = {"extra": "allow"}


class MedicalBillingState(SessionState):
    """Session state for HITL medical billing and insurance coding audits."""

    clinical_text: str = ""
    extracted_procedures: list[dict[str, Any]] = Field(default_factory=list)
    proposed_codes: list[BillingCodeMapping] = Field(default_factory=list)
    confidence_vectors: dict[str, BillingConfidenceVector] = Field(default_factory=dict)
    validation_flags: list[dict[str, Any]] = Field(default_factory=list)
    human_override_logs: list[BillingHumanOverrideLog] = Field(default_factory=list)
    approval_payload: dict[str, Any] = Field(default_factory=dict)

    model_config = {"extra": "allow"}

"""Human-in-the-loop approval helpers."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from engine.schemas.checkpoint import Checkpoint
from engine.schemas.session_state import (
    BillingCodeMapping,
    BillingHumanOverrideLog,
    MedicalBillingState,
    SessionStatus,
)
from engine.storage.checkpoint_store import CheckpointStore


class ApprovalDecision(StrEnum):
    """Shell approval choices for HITL steps."""

    APPROVE = "approve"
    MODIFY = "modify"
    REJECT = "reject"
    ABORT = "abort"


@dataclass
class ApprovalResult:
    """Result of an interactive approval prompt."""

    decision: ApprovalDecision
    reason: str = ""
    feedback: str = ""


class MedicalBillingReviewReason(StrEnum):
    """Reasons a proposed claim item requires human billing review."""

    LOW_CONFIDENCE = "low_confidence"
    HIGH_FINANCIAL_RISK = "high_financial_risk"
    CRITICAL_RULE_VIOLATION = "critical_rule_violation"


class MedicalBillingReviewThresholds(BaseModel):
    """Thresholds for medical billing HITL escalation."""

    minimum_confidence: float = Field(default=0.75, ge=0.0, le=1.0)
    maximum_financial_risk: float = Field(default=0.80, ge=0.0, le=1.0)
    critical_flag_prefixes: tuple[str, ...] = ("critical", "fatal", "deny")


class MedicalBillingReviewItem(BaseModel):
    """Claim item and rationale sent to the human billing auditor."""

    index: int
    code: BillingCodeMapping
    reasons: list[MedicalBillingReviewReason]
    confidence_floor: float
    financial_risk: float
    validation_flags: list[str] = Field(default_factory=list)


class MedicalBillingApprovalPayload(BaseModel):
    """Comparative review payload surfaced at the HITL boundary."""

    status: SessionStatus = SessionStatus.PENDING_HUMAN_APPROVAL
    clinical_text: str = ""
    proposed_codes: list[BillingCodeMapping] = Field(default_factory=list)
    review_items: list[MedicalBillingReviewItem] = Field(default_factory=list)
    generated_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class MedicalBillingResolutionPayload(BaseModel):
    """UI/API payload resolving a medical billing human approval pause."""

    auditor_id: str
    action: ApprovalDecision
    approved_codes: list[BillingCodeMapping] | None = None
    reason: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


def build_medical_billing_review_items(
    state: MedicalBillingState,
    thresholds: MedicalBillingReviewThresholds | None = None,
) -> list[MedicalBillingReviewItem]:
    """Return claim items that must be escalated for human billing review."""
    thresholds = thresholds or MedicalBillingReviewThresholds()
    review_items: list[MedicalBillingReviewItem] = []

    for index, code in enumerate(state.proposed_codes):
        confidence_vector = state.confidence_vectors.get(code.code)
        confidence_floor = confidence_vector.minimum if confidence_vector else code.confidence
        validation_flags = list(code.validation_flags)
        reasons: list[MedicalBillingReviewReason] = []

        if confidence_floor < thresholds.minimum_confidence:
            reasons.append(MedicalBillingReviewReason.LOW_CONFIDENCE)

        if code.financial_risk >= thresholds.maximum_financial_risk:
            reasons.append(MedicalBillingReviewReason.HIGH_FINANCIAL_RISK)

        if _has_critical_rule_violation(validation_flags, thresholds.critical_flag_prefixes):
            reasons.append(MedicalBillingReviewReason.CRITICAL_RULE_VIOLATION)

        if reasons:
            review_items.append(
                MedicalBillingReviewItem(
                    index=index,
                    code=code,
                    reasons=reasons,
                    confidence_floor=confidence_floor,
                    financial_risk=code.financial_risk,
                    validation_flags=validation_flags,
                )
            )

    return review_items


def build_medical_billing_approval_payload(
    state: MedicalBillingState,
    review_items: list[MedicalBillingReviewItem],
) -> MedicalBillingApprovalPayload:
    """Build the comparative payload displayed to a billing auditor."""
    return MedicalBillingApprovalPayload(
        clinical_text=state.clinical_text,
        proposed_codes=state.proposed_codes,
        review_items=review_items,
    )


async def intercept_medical_billing_review(
    state: MedicalBillingState,
    current_node: str,
    storage_path: str | Path | None = None,
    thresholds: MedicalBillingReviewThresholds | None = None,
) -> MedicalBillingState:
    """Pause a medical billing session when proposed codes need human approval."""
    review_items = build_medical_billing_review_items(state, thresholds)
    if not review_items:
        return state

    now = datetime.now().isoformat()
    approval_payload = build_medical_billing_approval_payload(state, review_items)

    state.status = SessionStatus.PENDING_HUMAN_APPROVAL
    state.timestamps.updated_at = now
    state.timestamps.paused_at_time = now
    state.progress.current_node = current_node
    state.progress.paused_at = current_node
    state.progress.resume_from = current_node
    state.approval_payload = approval_payload.model_dump(mode="json")
    state.memory["medical_billing_approval_payload"] = state.approval_payload

    if storage_path:
        checkpoint_store = CheckpointStore(Path(storage_path))
        checkpoint = Checkpoint.create(
            checkpoint_type="human_approval",
            session_id=state.session_id,
            current_node=current_node,
            next_node=current_node,
            execution_path=state.progress.path,
            shared_memory=state.memory,
            is_clean=True,
            description="Medical billing claim items pending human approval",
        )
        await checkpoint_store.save_checkpoint(checkpoint)
        state.checkpoint_enabled = True
        state.latest_checkpoint_id = checkpoint.checkpoint_id
        state.memory["latest_checkpoint_id"] = checkpoint.checkpoint_id

    return state


def resolve_medical_billing_review(
    state: MedicalBillingState,
    resolution: MedicalBillingResolutionPayload,
) -> MedicalBillingState:
    """Apply the human auditor response and prepare state for resumed execution."""
    approved_codes = resolution.approved_codes
    if resolution.action == ApprovalDecision.APPROVE:
        approved_codes = approved_codes or state.proposed_codes
    elif resolution.action == ApprovalDecision.MODIFY:
        approved_codes = approved_codes or state.proposed_codes
    elif resolution.action == ApprovalDecision.REJECT:
        approved_codes = []
    elif resolution.action == ApprovalDecision.ABORT:
        state.status = SessionStatus.CANCELLED

    if approved_codes is not None:
        original_by_code = {code.code: code for code in state.proposed_codes}
        original_codes = list(state.proposed_codes)
        state.proposed_codes = approved_codes
        for index, approved_code in enumerate(approved_codes):
            original_code = (
                original_by_code.get(approved_code.code)
                or (original_codes[index] if index < len(original_codes) else None)
            )
            state.human_override_logs.append(
                BillingHumanOverrideLog(
                    auditor_id=resolution.auditor_id,
                    action=resolution.action.value,
                    reason=resolution.reason,
                    original_code=original_code,
                    approved_code=approved_code,
                    metadata=resolution.metadata,
                )
            )

    if resolution.action != ApprovalDecision.ABORT:
        state.status = SessionStatus.ACTIVE

    now = datetime.now().isoformat()
    state.timestamps.updated_at = now
    state.progress.paused_at = None
    state.progress.resume_from = state.progress.current_node
    state.approval_payload = {}
    state.memory["medical_billing_approved_codes"] = [
        code.model_dump(mode="json") for code in state.proposed_codes
    ]
    state.memory["medical_billing_human_override_logs"] = [
        log.model_dump(mode="json") for log in state.human_override_logs
    ]

    return state


def _has_critical_rule_violation(flags: list[str], prefixes: tuple[str, ...]) -> bool:
    for flag in flags:
        normalized = flag.strip().lower()
        if any(normalized.startswith(prefix) for prefix in prefixes):
            return True
    return False

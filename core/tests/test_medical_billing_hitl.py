"""Tests for medical billing HITL review helpers."""

from __future__ import annotations

import pytest

from engine.graph.hitl import (
    ApprovalDecision,
    MedicalBillingResolutionPayload,
    MedicalBillingReviewReason,
    intercept_medical_billing_review,
    resolve_medical_billing_review,
)
from engine.schemas.session_state import (
    BillingCodeMapping,
    BillingConfidenceVector,
    MedicalBillingState,
    SessionStatus,
    SessionTimestamps,
)
from engine.storage.checkpoint_store import CheckpointStore


def _billing_state(*codes: BillingCodeMapping) -> MedicalBillingState:
    return MedicalBillingState(
        session_id="session_billing_1",
        goal_id="goal_billing",
        agent_id="medical-billing-auditor",
        timestamps=SessionTimestamps(
            started_at="2026-06-23T10:00:00",
            updated_at="2026-06-23T10:00:00",
        ),
        clinical_text="Patient received arthrocentesis after documented knee effusion.",
        proposed_codes=list(codes),
        progress={"path": ["extract_ehr", "validate_codes"]},
        memory={"claim_id": "claim-123"},
    )


@pytest.mark.asyncio
async def test_low_certainty_billing_code_triggers_human_review_checkpoint(tmp_path):
    code = BillingCodeMapping(
        code="20610",
        code_system="CPT",
        description="Arthrocentesis, major joint",
        confidence=0.61,
        financial_risk=0.42,
    )
    state = _billing_state(code)
    state.confidence_vectors[code.code] = BillingConfidenceVector(
        extraction=0.92,
        code_match=0.61,
        modifier_match=0.88,
        carrier_compliance=0.90,
    )

    reviewed = await intercept_medical_billing_review(
        state=state,
        current_node="validate_codes",
        storage_path=tmp_path,
    )

    assert reviewed.status == SessionStatus.PENDING_HUMAN_APPROVAL
    assert reviewed.progress.paused_at == "validate_codes"
    assert reviewed.latest_checkpoint_id is not None
    assert reviewed.approval_payload["review_items"][0]["code"]["code"] == "20610"
    assert reviewed.approval_payload["review_items"][0]["reasons"] == [
        MedicalBillingReviewReason.LOW_CONFIDENCE.value
    ]

    checkpoint = await CheckpointStore(tmp_path).load_checkpoint(reviewed.latest_checkpoint_id)
    assert checkpoint is not None
    assert checkpoint.checkpoint_type == "human_approval"
    assert checkpoint.shared_memory["medical_billing_approval_payload"]["status"] == (
        SessionStatus.PENDING_HUMAN_APPROVAL.value
    )


@pytest.mark.asyncio
async def test_low_risk_confident_billing_code_continues_without_review(tmp_path):
    code = BillingCodeMapping(
        code="99213",
        code_system="CPT",
        description="Established patient office visit",
        confidence=0.93,
        financial_risk=0.10,
    )
    state = _billing_state(code)

    reviewed = await intercept_medical_billing_review(
        state=state,
        current_node="validate_codes",
        storage_path=tmp_path,
    )

    assert reviewed.status == SessionStatus.ACTIVE
    assert reviewed.latest_checkpoint_id is None
    assert reviewed.approval_payload == {}


def test_resolution_payload_records_auditor_modification_and_resumes_state():
    original = BillingCodeMapping(
        code="99214",
        code_system="CPT",
        description="Office visit, moderate complexity",
        confidence=0.68,
        financial_risk=0.70,
    )
    corrected = BillingCodeMapping(
        code="99213",
        code_system="CPT",
        description="Office visit, low complexity",
        confidence=0.99,
        financial_risk=0.20,
    )
    state = _billing_state(original)
    state.status = SessionStatus.PENDING_HUMAN_APPROVAL
    state.progress.current_node = "human_review"
    state.progress.paused_at = "human_review"

    resolved = resolve_medical_billing_review(
        state,
        MedicalBillingResolutionPayload(
            auditor_id="auditor-7",
            action=ApprovalDecision.MODIFY,
            approved_codes=[corrected],
            reason="Documentation supports lower-complexity E/M coding.",
        ),
    )

    assert resolved.status == SessionStatus.ACTIVE
    assert resolved.progress.paused_at is None
    assert resolved.proposed_codes == [corrected]
    assert resolved.human_override_logs[0].auditor_id == "auditor-7"
    assert resolved.human_override_logs[0].action == ApprovalDecision.MODIFY.value
    assert resolved.human_override_logs[0].original_code == original
    assert resolved.human_override_logs[0].approved_code == corrected
    assert resolved.memory["medical_billing_approved_codes"][0]["code"] == "99213"

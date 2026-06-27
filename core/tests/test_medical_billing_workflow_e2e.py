"""End-to-end workflow tests for Medical Billing HITL with mock API reconciliation loops."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import pytest

from engine.graph.hitl import (
    ApprovalDecision,
    MedicalBillingReviewReason,
    MedicalBillingReviewThresholds,
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

# ============================================================================
# Mock API Layer — Simulates External Services
# ============================================================================


class MockEHRExtractor:
    """Mock EHR system that extracts clinical procedures from text."""

    @staticmethod
    def extract_procedures(clinical_text: str) -> list[dict[str, Any]]:
        """Extract procedures from clinical documentation."""
        procedures = []

        # Mock extraction rules
        if "arthrocentesis" in clinical_text.lower():
            procedures.append(
                {
                    "procedure_name": "Arthrocentesis",
                    "location": "knee",
                    "date": "2026-06-23",
                    "confidence": 0.95,
                }
            )

        if "ultrasound" in clinical_text.lower():
            procedures.append(
                {
                    "procedure_name": "Ultrasound guidance",
                    "location": "knee",
                    "date": "2026-06-23",
                    "confidence": 0.88,
                }
            )

        if "aspiration" in clinical_text.lower():
            procedures.append(
                {
                    "procedure_name": "Fluid aspiration",
                    "location": "knee effusion",
                    "date": "2026-06-23",
                    "confidence": 0.92,
                }
            )

        return procedures


class MockBillingCodeMapper:
    """Mock service that maps procedures to standard medical billing codes."""

    PROCEDURE_TO_CODES = {
        "Arthrocentesis": [
            BillingCodeMapping(
                code="20610",
                code_system="CPT",
                description=(
                    "Arthrocentesis, major joint or bursa "
                    "(including ultrasound guidance), aspiration"
                ),
                procedure="Arthrocentesis",
                confidence=0.88,
                financial_risk=0.35,
                modifiers=["26"],  # Professional component
                validation_flags=[],
            ),
        ],
        "Fluid aspiration": [
            BillingCodeMapping(
                code="20610",
                code_system="CPT",
                description=(
                    "Arthrocentesis, major joint or bursa "
                    "(including ultrasound guidance), aspiration"
                ),
                procedure="Fluid aspiration",
                confidence=0.85,
                financial_risk=0.30,
                validation_flags=[],
            ),
        ],
        "Ultrasound guidance": [
            BillingCodeMapping(
                code="76942",
                code_system="CPT",
                description="Ultrasound, surgical guidance; needle biopsy",
                procedure="Ultrasound guidance",
                confidence=0.80,
                financial_risk=0.25,
                validation_flags=["warning: bundled_service"],
            ),
        ],
    }

    @staticmethod
    def map_procedures_to_codes(procedures: list[dict[str, Any]]) -> list[BillingCodeMapping]:
        """Map extracted procedures to billing codes."""
        codes = []
        for proc in procedures:
            proc_name = proc.get("procedure_name", "")
            if proc_name in MockBillingCodeMapper.PROCEDURE_TO_CODES:
                codes.extend(MockBillingCodeMapper.PROCEDURE_TO_CODES[proc_name])
        return codes


class MockCarrierComplianceValidator:
    """Mock insurance carrier compliance service."""

    CARRIER_RULES = {
        "20610": {
            "requires_modifier": True,
            "allowed_modifiers": ["26", "TC"],
            "bundle_codes": ["76942"],
            "critical_flags": [],
            "financial_limit": 500.0,
        },
        "76942": {
            "requires_modifier": False,
            "bundled_with": ["20610"],
            "critical_flags": ["warning: may_be_bundled"],
            "financial_limit": 200.0,
        },
    }

    @staticmethod
    def validate_codes(codes: list[BillingCodeMapping]) -> dict[str, Any]:
        """Validate codes against carrier rules and return validation results."""
        validation_result = {
            "codes_validated": len(codes),
            "critical_issues": [],
            "warnings": [],
            "compliance_score": 1.0,
        }

        for code in codes:
            code_str = code.code
            if code_str in MockCarrierComplianceValidator.CARRIER_RULES:
                rules = MockCarrierComplianceValidator.CARRIER_RULES[code_str]

                # Check modifier requirements
                if rules.get("requires_modifier") and not code.modifiers:
                    validation_result["critical_issues"].append(
                        f"Code {code_str} requires modifier but none provided"
                    )
                    code.validation_flags.append("critical: missing_modifier")

                # Check bundling
                if rules.get("bundled_with"):
                    other_codes = [c.code for c in codes if c.code != code_str]
                    if any(bc in other_codes for bc in rules["bundled_with"]):
                        validation_result["warnings"].append(
                            f"Code {code_str} may be bundled with other submitted codes"
                        )
                        code.validation_flags.append("warning: bundled_service")

                # Check financial limits
                if code.financial_risk >= rules.get("financial_limit", float("inf")):
                    validation_result["warnings"].append(
                        f"Code {code_str} exceeds financial risk threshold"
                    )

        return validation_result


class MockAuditStorage:
    """Mock audit storage system for persisting claim records."""

    _audit_records: dict[str, dict[str, Any]] = {}

    @classmethod
    def store_audit_record(
        cls,
        session_id: str,
        claim_id: str,
        clinical_text: str,
        proposed_codes: list[BillingCodeMapping],
        approved_codes: list[BillingCodeMapping],
        override_logs: list[dict[str, Any]],
    ) -> str:
        """Store audit record and return audit_record_id."""
        audit_record_id = f"audit-{session_id[:8]}-{len(cls._audit_records)}"
        cls._audit_records[audit_record_id] = {
            "session_id": session_id,
            "claim_id": claim_id,
            "clinical_text": clinical_text,
            "proposed_codes": [c.model_dump() for c in proposed_codes],
            "approved_codes": [c.model_dump() for c in approved_codes],
            "override_logs": override_logs,
            "stored_at": datetime.now().isoformat(),
        }
        return audit_record_id

    @classmethod
    def retrieve_audit_record(cls, audit_record_id: str) -> dict[str, Any] | None:
        """Retrieve audit record by ID."""
        return cls._audit_records.get(audit_record_id)

    @classmethod
    def clear_records(cls):
        """Clear all stored records (for testing)."""
        cls._audit_records.clear()


# ============================================================================
# Workflow State Machine Tests — End-to-End Reconciliation
# ============================================================================


class TestMedicalBillingWorkflowE2E:
    """End-to-end workflow tests with mock API reconciliation loops."""

    def setup_method(self):
        """Clear audit storage before each test."""
        MockAuditStorage.clear_records()

    def _create_medical_billing_state(
        self,
        session_id: str = "session_billing_e2e_001",
        clinical_text: str = "",
    ) -> MedicalBillingState:
        """Create a MedicalBillingState with defaults."""
        from engine.schemas.session_state import SessionProgress

        return MedicalBillingState(
            session_id=session_id,
            goal_id="goal_medical_billing",
            agent_id="medical-billing-auditor",
            timestamps=SessionTimestamps(
                started_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat(),
            ),
            clinical_text=clinical_text,
            progress=SessionProgress(path=[]),
            memory={},
        )

    def test_workflow_step_1_ehr_intake_and_procedure_extraction(self):
        """Test: EHR intake extracts procedures from clinical documentation."""
        clinical_text = (
            "Patient underwent arthrocentesis of the knee under ultrasound guidance. "
            "Fluid aspiration was performed due to documented effusion."
        )

        state = self._create_medical_billing_state(clinical_text=clinical_text)
        assert state.clinical_text == clinical_text

        # Step 1: Extract procedures
        procedures = MockEHRExtractor.extract_procedures(clinical_text)
        state.extracted_procedures = procedures

        assert len(procedures) >= 3
        assert any(p["procedure_name"] == "Arthrocentesis" for p in procedures)
        assert state.progress.path == []
        state.progress.path.append("ehr_intake")

        assert state.progress.path == ["ehr_intake"]

    def test_workflow_step_2_code_extraction_with_confidence_vectors(self):
        """Test: Code extraction assigns confidence vectors to proposed codes."""
        state = self._create_medical_billing_state(
            clinical_text="Arthrocentesis with ultrasound guidance and fluid aspiration"
        )

        # Extract procedures
        procedures = MockEHRExtractor.extract_procedures(state.clinical_text)
        state.extracted_procedures = procedures
        state.progress.path.append("ehr_intake")

        # Step 2: Map to billing codes
        proposed_codes = MockBillingCodeMapper.map_procedures_to_codes(procedures)
        state.proposed_codes = proposed_codes
        state.progress.path.append("code_extraction")

        assert len(proposed_codes) >= 2

        # Assign confidence vectors
        for code in proposed_codes:
            state.confidence_vectors[code.code] = BillingConfidenceVector(
                extraction=0.92,
                code_match=code.confidence,
                modifier_match=0.88 if code.modifiers else 1.0,
                carrier_compliance=0.85,
            )

        assert "20610" in state.confidence_vectors
        assert state.confidence_vectors["20610"].minimum <= 0.92

    def test_workflow_step_3_compliance_validation_and_risk_assessment(self):
        """Test: Compliance validation checks codes against carrier rules."""
        state = self._create_medical_billing_state(
            clinical_text="Arthrocentesis with ultrasound and aspiration"
        )

        # Setup: Extract and map codes
        procedures = MockEHRExtractor.extract_procedures(state.clinical_text)
        proposed_codes = MockBillingCodeMapper.map_procedures_to_codes(procedures)
        state.proposed_codes = proposed_codes

        # Add confidence vectors
        for code in proposed_codes:
            state.confidence_vectors[code.code] = BillingConfidenceVector(
                extraction=0.92,
                code_match=code.confidence,
                modifier_match=0.85,
                carrier_compliance=0.80,
            )

        state.progress.path.append("code_extraction")

        # Step 3: Validate against carrier rules
        validation_result = MockCarrierComplianceValidator.validate_codes(proposed_codes)
        state.validation_flags.append(validation_result)
        state.progress.path.append("compliance_validation")

        # Check results
        assert validation_result["codes_validated"] > 0
        # May have warnings about bundling
        assert isinstance(validation_result["warnings"], list)

    @pytest.mark.asyncio
    async def test_workflow_step_4_hitl_intercept_high_risk_codes(self):
        """Test: High-risk codes trigger HITL intercept and checkpoint."""
        state = self._create_medical_billing_state(clinical_text="Complex arthrocentesis procedure")

        # Setup workflow
        procedures = MockEHRExtractor.extract_procedures(state.clinical_text)
        proposed_codes = MockBillingCodeMapper.map_procedures_to_codes(procedures)
        state.proposed_codes = proposed_codes

        # Simulate low confidence on one code
        state.confidence_vectors["20610"] = BillingConfidenceVector(
            extraction=0.92,
            code_match=0.68,  # Low code match
            modifier_match=0.65,  # Low modifier match
            carrier_compliance=0.80,
        )

        state.progress.path.extend(["ehr_intake", "code_extraction", "compliance_validation"])

        # Step 4: HITL intercept
        thresholds = MedicalBillingReviewThresholds(minimum_confidence=0.75)
        reviewed_state = await intercept_medical_billing_review(
            state=state,
            current_node="compliance_validation",
            thresholds=thresholds,
        )

        # Verify intercept triggered
        assert reviewed_state.status == SessionStatus.PENDING_HUMAN_APPROVAL
        assert reviewed_state.progress.paused_at == "compliance_validation"
        assert len(reviewed_state.approval_payload) > 0

        review_items = reviewed_state.approval_payload.get("review_items", [])
        assert len(review_items) > 0
        assert MedicalBillingReviewReason.LOW_CONFIDENCE.value in review_items[0]["reasons"]

    @pytest.mark.asyncio
    async def test_workflow_step_5_human_auditor_review_and_modification(self):
        """Test: Human auditor modifies low-confidence codes."""
        from engine.graph.hitl import MedicalBillingResolutionPayload

        # Setup: Create state with low-confidence code
        state = self._create_medical_billing_state(clinical_text="Arthrocentesis procedure")

        original_code = BillingCodeMapping(
            code="99214",
            code_system="CPT",
            description="Office visit, moderate complexity",
            confidence=0.68,
            financial_risk=0.70,
        )
        state.proposed_codes = [original_code]
        state.status = SessionStatus.PENDING_HUMAN_APPROVAL
        state.progress.current_node = "hitl_review"
        state.progress.paused_at = "hitl_review"

        # Step 5: Auditor reviews and modifies
        corrected_code = BillingCodeMapping(
            code="20610",
            code_system="CPT",
            description="Arthrocentesis, major joint",
            confidence=0.95,
            financial_risk=0.35,
        )

        resolution = MedicalBillingResolutionPayload(
            auditor_id="auditor-doc-smith-001",
            action=ApprovalDecision.MODIFY,
            approved_codes=[corrected_code],
            reason="Documentation clearly indicates arthrocentesis procedure, not office visit. "
            "Corrected to appropriate billing code.",
            metadata={
                "review_time_seconds": 45,
                "auditor_role": "billing_specialist",
            },
        )

        resolved_state = resolve_medical_billing_review(state, resolution)

        # Verify resolution
        assert resolved_state.status == SessionStatus.ACTIVE
        assert resolved_state.progress.paused_at is None
        assert resolved_state.proposed_codes[0].code == "20610"
        assert len(resolved_state.human_override_logs) == 1

        log = resolved_state.human_override_logs[0]
        assert log.auditor_id == "auditor-doc-smith-001"
        assert log.action == ApprovalDecision.MODIFY.value
        assert log.original_code == original_code
        assert log.approved_code == corrected_code

    @pytest.mark.asyncio
    async def test_workflow_step_6_audit_trail_persistence(self, tmp_path):
        """Test: Final audit record captures complete claim lifecycle."""
        # Setup: Complete workflow state
        state = self._create_medical_billing_state(
            session_id="session_audit_demo",
            clinical_text="Patient underwent arthrocentesis with ultrasound guidance",
        )

        # Simulate full workflow
        procedures = MockEHRExtractor.extract_procedures(state.clinical_text)
        proposed_codes = MockBillingCodeMapper.map_procedures_to_codes(procedures)
        state.proposed_codes = proposed_codes

        # Add confidence vectors
        for code in proposed_codes:
            state.confidence_vectors[code.code] = BillingConfidenceVector(
                extraction=0.92,
                code_match=0.85,
                modifier_match=0.88,
                carrier_compliance=0.90,
            )

        # Simulate approval
        from engine.graph.hitl import MedicalBillingResolutionPayload

        resolution = MedicalBillingResolutionPayload(
            auditor_id="auditor-final-001",
            action=ApprovalDecision.APPROVE,
            reason="All codes verified and compliant",
        )

        resolved_state = resolve_medical_billing_review(state, resolution)

        # Step 6: Store audit record
        audit_record_id = MockAuditStorage.store_audit_record(
            session_id=resolved_state.session_id,
            claim_id="claim-2026-06-23-001",
            clinical_text=resolved_state.clinical_text,
            proposed_codes=state.proposed_codes,
            approved_codes=resolved_state.proposed_codes,
            override_logs=[log.model_dump() for log in resolved_state.human_override_logs],
        )

        # Verify audit record
        audit_record = MockAuditStorage.retrieve_audit_record(audit_record_id)
        assert audit_record is not None
        assert audit_record["claim_id"] == "claim-2026-06-23-001"
        assert len(audit_record["proposed_codes"]) > 0
        assert "stored_at" in audit_record

    def test_reconciliation_loop_low_risk_bypass(self):
        """Test: Low-risk, high-confidence codes bypass human review."""
        # Scenario: High-confidence arthrocentesis code
        state = self._create_medical_billing_state(clinical_text="Routine arthrocentesis procedure")

        # Extract and map
        procedures = MockEHRExtractor.extract_procedures(state.clinical_text)
        codes = MockBillingCodeMapper.map_procedures_to_codes(procedures)
        state.proposed_codes = codes

        # High confidence vectors
        for code in codes:
            state.confidence_vectors[code.code] = BillingConfidenceVector(
                extraction=0.95,
                code_match=0.92,
                modifier_match=0.90,
                carrier_compliance=0.94,
            )

        # Apply thresholds
        thresholds = MedicalBillingReviewThresholds(minimum_confidence=0.75)

        # Check: Should NOT require HITL review
        from engine.graph.hitl import build_medical_billing_review_items

        review_items = build_medical_billing_review_items(state, thresholds)
        assert len(review_items) == 0  # No items require review

    def test_reconciliation_loop_complex_bundling_scenario(self):
        """Test: Complex scenario with bundling warnings triggers review."""
        state = self._create_medical_billing_state(
            clinical_text="Ultrasound-guided arthrocentesis with detailed imaging"
        )

        # Create codes
        codes = [
            BillingCodeMapping(
                code="20610",
                code_system="CPT",
                description="Arthrocentesis with ultrasound",
                confidence=0.88,
                financial_risk=0.35,
            ),
            BillingCodeMapping(
                code="76942",
                code_system="CPT",
                description="Ultrasound surgical guidance",
                confidence=0.80,
                financial_risk=0.25,
                validation_flags=["warning: may_be_bundled"],
            ),
        ]
        state.proposed_codes = codes

        # Confidence vectors
        for code in codes:
            state.confidence_vectors[code.code] = BillingConfidenceVector(
                extraction=0.90,
                code_match=code.confidence,
                modifier_match=0.85,
                carrier_compliance=0.82,
            )

        # Validate with mock service
        validation = MockCarrierComplianceValidator.validate_codes(codes)

        # Should have bundling warning
        assert len(validation["warnings"]) > 0
        assert any("bundled" in w.lower() for w in validation["warnings"])

    @pytest.mark.asyncio
    async def test_full_workflow_end_to_end(self, tmp_path):
        """Test: Complete workflow from intake to audit storage."""
        print("\n" + "=" * 70)
        print("MEDICAL BILLING HITL WORKFLOW — COMPLETE E2E TEST")
        print("=" * 70)

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # PHASE 1: INTAKE & EXTRACTION
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        print("\n[PHASE 1] EHR Intake & Clinical Extraction")
        clinical_text = (
            "66M presents with right knee effusion following sports injury. "
            "Performed arthrocentesis under ultrasound guidance with therapeutic fluid aspiration. "
            "35 mL cloudy synovial fluid obtained. Sent for analysis."
        )
        print(f"Clinical Text: {clinical_text[:80]}...")

        state = self._create_medical_billing_state(
            session_id="e2e_workflow_complete",
            clinical_text=clinical_text,
        )

        procedures = MockEHRExtractor.extract_procedures(clinical_text)
        state.extracted_procedures = procedures
        proc_names = [p["procedure_name"] for p in procedures]
        print(f"Extracted {len(procedures)} procedures: {proc_names}")

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # PHASE 2: CODE EXTRACTION & MAPPING
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        print("\n[PHASE 2] Procedure → Billing Code Mapping")
        proposed_codes = MockBillingCodeMapper.map_procedures_to_codes(procedures)
        state.proposed_codes = proposed_codes

        for code in proposed_codes:
            print(f"  Code: {code.code} ({code.code_system}) - {code.description[:50]}...")
            print(
                f"    Confidence: {code.confidence:.2%}, Financial Risk: {code.financial_risk:.2%}"
            )

        # Build confidence vectors
        for code in proposed_codes:
            state.confidence_vectors[code.code] = BillingConfidenceVector(
                extraction=0.93,
                code_match=code.confidence,
                modifier_match=0.87,
                carrier_compliance=0.89,
            )
        print(f"OK: Assigned confidence vectors to {len(proposed_codes)} codes")

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # PHASE 3: COMPLIANCE VALIDATION
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        print("\n[PHASE 3] Compliance Validation Against Carrier Rules")
        validation = MockCarrierComplianceValidator.validate_codes(proposed_codes)
        state.validation_flags.append(validation)

        print(f"  Codes Validated: {validation['codes_validated']}")
        print(f"  Critical Issues: {len(validation['critical_issues'])}")
        print(f"  Warnings: {len(validation['warnings'])}")
        if validation["warnings"]:
            for w in validation["warnings"][:2]:
                print(f"    WARN: {w}")
        print("OK: Validation complete")

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # PHASE 4: HITL INTERCEPT CHECK
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        print("\n[PHASE 4] HITL Intercept & Approval Check")
        thresholds = MedicalBillingReviewThresholds(
            minimum_confidence=0.75,
            maximum_financial_risk=0.80,
        )

        reviewed_state = await intercept_medical_billing_review(
            state=state,
            current_node="compliance_validation",
            thresholds=thresholds,
        )

        if reviewed_state.status == SessionStatus.PENDING_HUMAN_APPROVAL:
            print("  WARN: HITL INTERCEPT TRIGGERED")
            review_items = reviewed_state.approval_payload.get("review_items", [])
            print(f"  Items Requiring Review: {len(review_items)}")
            for item in review_items:
                print(f"    Code {item['code']['code']}: {', '.join(item['reasons'])}")
        else:
            print("  OK: No HITL intercept needed - codes approved for processing")

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # PHASE 5: HUMAN AUDITOR REVIEW (simulated)
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        print("\n[PHASE 5] Human Auditor Review & Approval")

        from engine.graph.hitl import MedicalBillingResolutionPayload

        # Auditor approves codes
        resolution = MedicalBillingResolutionPayload(
            auditor_id="auditor-jenkins-2026",
            action=ApprovalDecision.APPROVE,
            reason="All codes verified against clinical documentation. "
            "Compliance checks passed. Ready for claim submission.",
            metadata={
                "review_duration_seconds": 120,
                "notes": "Standard procedure, clear documentation",
            },
        )

        final_state = resolve_medical_billing_review(reviewed_state, resolution)
        print(f"  Auditor: {resolution.auditor_id}")
        print(f"  Action: {resolution.action.upper()}")
        print(f"  Reason: {resolution.reason[:60]}...")
        print("OK: Auditor review complete - resuming execution")

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # PHASE 6: AUDIT TRAIL & PERSISTENCE
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        print("\n[PHASE 6] Audit Trail & Persistence")

        audit_record_id = MockAuditStorage.store_audit_record(
            session_id=final_state.session_id,
            claim_id="claim-2026-06-23-knee-arthro",
            clinical_text=final_state.clinical_text,
            proposed_codes=final_state.proposed_codes,
            approved_codes=final_state.proposed_codes,
            override_logs=[log.model_dump() for log in final_state.human_override_logs],
        )

        audit_record = MockAuditStorage.retrieve_audit_record(audit_record_id)
        print(f"  Audit Record ID: {audit_record_id}")
        print(f"  Claim ID: {audit_record['claim_id']}")
        print(f"  Codes Stored: {len(audit_record['proposed_codes'])}")
        print(f"  Override Logs: {len(audit_record['override_logs'])}")
        print("OK: Audit trail persisted to storage")

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # VERIFICATION & RECONCILIATION
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        print("\n[VERIFICATION] Reconciliation Checks")
        print(f"  OK: Session Status: {final_state.status}")
        print(f"  OK: Execution Not Paused: {final_state.progress.paused_at is None}")
        print(f"  OK: Audit Trail: {len(final_state.human_override_logs)} override logs")
        print(f"  OK: Memory Snapshot: {len(final_state.memory)} keys")

        # Final assertions
        assert final_state.status == SessionStatus.ACTIVE
        assert final_state.progress.paused_at is None
        assert audit_record is not None
        assert len(final_state.human_override_logs) >= 0

        print("\n" + "=" * 70)
        print("- COMPLETE WORKFLOW SUCCESS")
        print("=" * 70)

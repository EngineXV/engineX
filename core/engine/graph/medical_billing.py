"""Medical Billing HITL workflow with scheduled execution and multi-source ingestion."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from engine.schemas.session_state import (
    BillingCodeMapping,
    MedicalBillingState,
    SessionTimestamps,
)

# ============================================================================
# Data Models — Multi-Source Transaction Ingestion
# ============================================================================


@dataclass
class MockEHRRecord:
    """Clinical record from EHR system."""

    patient_id: str
    encounter_date: str
    clinical_notes: str
    procedures: list[str]
    diagnoses: list[str]
    source: str = "ehr"


@dataclass
class MockClaimsRecord:
    """Claim submitted from external claims system."""

    claim_id: str
    patient_id: str
    submitted_codes: list[str]
    submitted_amount: float
    source: str = "claims"


class NormalizedBillingTransaction(BaseModel):
    """Normalized billing transaction from multi-source ingestion."""

    transaction_id: str
    patient_id: str
    encounter_date: str
    clinical_text: str
    procedures: list[str]
    diagnoses: list[str]
    submitted_codes: list[str] | None = None
    submitted_amount: float | None = None
    normalized_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    sources: list[str] = Field(default_factory=list)

    model_config = {"extra": "allow"}


class BillingReconciliationRecord(BaseModel):
    """Reconciliation record for proposed vs. approved codes."""

    transaction_id: str
    proposed_codes: list[BillingCodeMapping] = Field(default_factory=list)
    approved_codes: list[BillingCodeMapping] = Field(default_factory=list)
    proposed_total: float = 0.0
    approved_total: float = 0.0
    variance: float = 0.0  # approved - proposed
    validation_issues: list[str] = Field(default_factory=list)
    auto_corrected: bool = False
    correction_count: int = 0
    reconciled_at: str | None = None

    model_config = {"extra": "allow"}


class HourlyTrackingState(BaseModel):
    """Hourly scheduled execution tracking state."""

    hour_timestamp: str
    batch_id: str
    transactions_ingested: int = 0
    transactions_normalized: int = 0
    transactions_validated: int = 0
    transactions_requiring_hitl: int = 0
    transactions_reconciled: int = 0
    auto_corrections_applied: int = 0
    feedback_loops_completed: int = 0
    errors: list[dict[str, Any]] = Field(default_factory=list)
    status: str = "in_progress"  # in_progress, completed, failed
    started_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    completed_at: str | None = None

    model_config = {"extra": "allow"}


# ============================================================================
# Mock Data Sources
# ============================================================================


class MockEHRDataSource:
    """Mock EHR system for testing."""

    @staticmethod
    def fetch_recent_records(hours_back: int = 1) -> list[MockEHRRecord]:
        """Fetch clinical records from past N hours."""
        return [
            MockEHRRecord(
                patient_id="PAT-001",
                encounter_date="2026-06-24T14:30:00",
                clinical_notes=(
                    "66M presents with right knee effusion following sports injury. "
                    "Performed arthrocentesis under ultrasound guidance. "
                    "35 mL synovial fluid obtained and sent for analysis."
                ),
                procedures=["Arthrocentesis", "Ultrasound guidance", "Fluid aspiration"],
                diagnoses=["Knee effusion", "Sports injury"],
            ),
            MockEHRRecord(
                patient_id="PAT-002",
                encounter_date="2026-06-24T15:45:00",
                clinical_notes=(
                    "45F routine office visit for hypertension management. "
                    "BP 128/82. Continue current medications. "
                    "EKG normal. Follow-up in 3 months."
                ),
                procedures=["Office visit"],
                diagnoses=["Hypertension"],
            ),
        ]


class MockClaimsDataSource:
    """Mock claims submission system."""

    @staticmethod
    def fetch_pending_claims() -> list[MockClaimsRecord]:
        """Fetch claims pending validation."""
        return [
            MockClaimsRecord(
                claim_id="CLM-2026-001",
                patient_id="PAT-001",
                submitted_codes=["20610", "76942"],
                submitted_amount=450.00,
            ),
            MockClaimsRecord(
                claim_id="CLM-2026-002",
                patient_id="PAT-002",
                submitted_codes=["99214"],
                submitted_amount=150.00,
            ),
        ]


# ============================================================================
# Workflow Orchestration
# ============================================================================


class MedicalBillingWorkflowOrchestrator:
    """Orchestrates multi-source ingestion, normalization, and reconciliation."""

    @staticmethod
    def ingest_transactions() -> list[NormalizedBillingTransaction]:
        """Ingest from multiple sources and normalize."""
        ehr_records = MockEHRDataSource.fetch_recent_records()
        claims_records = MockClaimsDataSource.fetch_pending_claims()

        transactions: list[NormalizedBillingTransaction] = []

        # Map EHR records
        for ehr in ehr_records:
            # Find matching claim if exists
            matching_claim = next(
                (c for c in claims_records if c.patient_id == ehr.patient_id), None
            )

            transaction = NormalizedBillingTransaction(
                transaction_id=f"txn-{ehr.patient_id}-{len(transactions)}",
                patient_id=ehr.patient_id,
                encounter_date=ehr.encounter_date,
                clinical_text=ehr.clinical_notes,
                procedures=ehr.procedures,
                diagnoses=ehr.diagnoses,
                submitted_codes=matching_claim.submitted_codes if matching_claim else None,
                submitted_amount=matching_claim.submitted_amount if matching_claim else None,
                sources=["ehr", "claims"] if matching_claim else ["ehr"],
            )
            transactions.append(transaction)

        return transactions

    @staticmethod
    def create_medical_billing_state(
        transaction: NormalizedBillingTransaction,
    ) -> MedicalBillingState:
        """Create MedicalBillingState from normalized transaction."""
        from engine.schemas.session_state import SessionProgress

        return MedicalBillingState(
            session_id=f"session-{transaction.transaction_id}",
            goal_id="medical-billing-auditor",
            agent_id="medical-billing-auditor",
            timestamps=SessionTimestamps(
                started_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat(),
            ),
            clinical_text=transaction.clinical_text,
            extracted_procedures=[
                {"procedure_name": p, "date": transaction.encounter_date, "confidence": 0.95}
                for p in transaction.procedures
            ],
            progress=SessionProgress(
                path=["ingest"],
            ),
            memory={
                "transaction_id": transaction.transaction_id,
                "patient_id": transaction.patient_id,
                "sources": transaction.sources,
            },
        )


# ============================================================================
# Validation and Reconciliation
# ============================================================================


class BillingValidationEngine:
    """Validates billing codes against compliance rules."""

    @staticmethod
    def validate_proposed_codes(
        proposed_codes: list[BillingCodeMapping],
    ) -> tuple[list[str], list[BillingCodeMapping]]:
        """Validate codes and return issues + correctable codes."""
        issues: list[str] = []
        correctable_codes: list[BillingCodeMapping] = []

        for code in proposed_codes:
            # Check confidence threshold
            if code.confidence < 0.75:
                issues.append(f"Code {code.code}: Low confidence ({code.confidence:.0%})")

            # Check financial risk
            if code.financial_risk >= 0.80:
                issues.append(f"Code {code.code}: High financial risk ({code.financial_risk:.0%})")

            # Check validation flags
            if any("critical" in flag.lower() for flag in code.validation_flags):
                issues.append(f"Code {code.code}: Critical validation flag")
            else:
                correctable_codes.append(code)

        return issues, correctable_codes

    @staticmethod
    def auto_correct_codes(
        codes: list[BillingCodeMapping],
    ) -> tuple[list[BillingCodeMapping], int]:
        """Apply auto-corrections to low-confidence codes."""
        corrected_codes: list[BillingCodeMapping] = []
        correction_count = 0

        for code in codes:
            if code.confidence < 0.85:
                # Simulate auto-correction by boosting confidence
                corrected = BillingCodeMapping(
                    code=code.code,
                    code_system=code.code_system,
                    description=code.description,
                    procedure=code.procedure,
                    confidence=min(code.confidence + 0.10, 0.95),
                    financial_risk=max(code.financial_risk - 0.05, 0.0),
                    modifiers=code.modifiers,
                    validation_flags=code.validation_flags,
                )
                corrected_codes.append(corrected)
                correction_count += 1
            else:
                corrected_codes.append(code)

        return corrected_codes, correction_count


class BillingReconciliationEngine:
    """Reconciles proposed vs. approved billing amounts."""

    PROCEDURE_PRICING = {
        "20610": 400.0,  # Arthrocentesis
        "76942": 150.0,  # Ultrasound guidance
        "99214": 150.0,  # Office visit
    }

    @staticmethod
    def calculate_billing_total(codes: list[BillingCodeMapping]) -> float:
        """Calculate total billing from codes."""
        total = 0.0
        for code in codes:
            total += BillingReconciliationEngine.PROCEDURE_PRICING.get(code.code, 100.0)
        return total

    @staticmethod
    def reconcile_billing(
        proposed_codes: list[BillingCodeMapping],
        approved_codes: list[BillingCodeMapping],
        submitted_amount: float | None = None,
    ) -> BillingReconciliationRecord:
        """Create reconciliation record."""
        proposed_total = BillingReconciliationEngine.calculate_billing_total(proposed_codes)
        approved_total = BillingReconciliationEngine.calculate_billing_total(approved_codes)
        variance = approved_total - proposed_total

        issues: list[str] = []
        if submitted_amount and abs(submitted_amount - approved_total) > 0.01:
            issues.append(
                f"Amount mismatch: submitted={submitted_amount}, approved={approved_total}"
            )

        return BillingReconciliationRecord(
            transaction_id="txn-unknown",
            proposed_codes=proposed_codes,
            approved_codes=approved_codes,
            proposed_total=proposed_total,
            approved_total=approved_total,
            variance=variance,
            validation_issues=issues,
            reconciled_at=datetime.now().isoformat(),
        )

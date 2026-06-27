# Medical Billing & Insurance Coding Auditor

An open-source, HITL (Human-in-the-Loop) agent for healthcare organizations to eliminate billing code compliance errors and reduce insurance claim denials.

## Problem Statement

Healthcare organizations lose billions annually due to:
- Insurance claim denials from incorrect ICD-11, CPT, or HCPCS code assignments
- Manual data entry workload for billing teams
- Complex regulatory compliance requirements that cannot be fully automated
- High liability from coding errors

## Solution

This agent implements a **self-correcting, human-approved medical compliance lifecycle**:

1. **EHR Intake**: Securely ingest raw clinical documentation and EHR notes
2. **Code Extraction**: Auto-extract clinical procedures and map to standard billing codes
3. **Compliance Validation**: Route codes through validation checks against regional insurance carrier rules
4. **HITL Intercept**: Pause execution and surface high-risk codes for human billing auditor review
5. **Resolution Handshake**: Process human approval/modification and update execution state
6. **Audit Storage**: Persist final claim state and human override logs to secure storage

## Workflow

```
Clinical Documentation
        ↓
   EHR Intake
        ↓
  Code Extraction
   (ICD-11, CPT, HCPCS)
        ↓
Compliance Validation
   (vs. Carrier Rules)
        ↓
   High Risk? → HITL Review ← Human Auditor
        │              ↓
        │      Resolution Handshake
        │       (approval/modification)
        │              ↓
        └──────────────┘
             ↓
      Audit Storage
    (Compliance Trail)
```

## Key Features

✅ **Self-Correcting Loop** — Auto-correction for minor matching issues  
✅ **Confidence Scoring** — Multi-dimensional confidence vectors (extraction, code_match, modifier_match, carrier_compliance)  
✅ **Risk Assessment** — Financial risk scoring for claim items  
✅ **HITL Safety Net** — Explicit human authorization for high-uncertainty or high-risk codes  
✅ **Audit Trail** — Complete record of all human approvals and code modifications  
✅ **Checkpoint Recovery** — Pause/resume capability with state persistence  

## State Definition: `MedicalBillingState`

Extends `SessionState` with:

- `clinical_text: str` — Raw clinical documentation
- `extracted_procedures: list[dict]` — Extracted clinical procedures from EHR
- `proposed_codes: list[BillingCodeMapping]` — Auto-generated billing code proposals
- `confidence_vectors: dict[str, BillingConfidenceVector]` — Multi-dimensional confidence metrics per code
- `validation_flags: list[dict]` — Compliance validation results
- `human_override_logs: list[BillingHumanOverrideLog]` — Auditable records of human decisions
- `approval_payload: dict` — Comparative payload sent to auditor for review

## Escalation Criteria

A proposed claim item is escalated for human review (`PENDING_HUMAN_APPROVAL`) if **any** of:

1. **Low Confidence** — `confidence_floor < 0.75` (minimum across all confidence dimensions)
2. **High Financial Risk** — `financial_risk >= 0.80` (adjustable per organization)
3. **Critical Rule Violation** — Validation flags contain critical/deny prefixes

## Definition of Done (Acceptance Criteria)

✅ Framework cleanly intercepts high-risk proposed claim items without crashing  
✅ State details accurately serialized to checkpoint storage while awaiting human approval  
✅ API boundary updates session state from user interaction input, allowing resumed graph runs  
✅ Unit tests confirm low-certainty proposed codes trigger appropriate human review pathway  

## Running the Agent

```bash
# Validate agent template
./engine validate examples/templates/medical_billing_auditor

# Run with TUI
./engine run examples/templates/medical_billing_auditor --tui

# Run with specific clinical input
./engine run examples/templates/medical_billing_auditor \
  --clinical-text "Patient underwent arthrocentesis after documented knee effusion" \
  --tui
```

## Integration Points

### Secure MCP Tools
- EHR data extraction (via secure MCP tools)
- Carrier rule validation APIs
- Audit logging to compliance storage

### State Persistence
- `CheckpointStore` for pause/resume state management
- Session state serialization to database
- Human approval payload marshaling to API boundary

### API Endpoint
- `POST /api/sessions/{session_id}/approve` — Submit human auditor decision
- Payload: `MedicalBillingResolutionPayload` with auditor ID, action, approved codes, reason
- Response: Updated `MedicalBillingState` with status → `ACTIVE` and path ready for resumed execution

## Testing

```bash
make test core/tests/test_medical_billing_hitl.py
```

Tests verify:
- Low-confidence codes trigger human review and checkpoint creation
- Low-risk, confident codes bypass review and continue execution
- Human approval payload correctly updates session state and resumes execution
- Override logs maintain complete audit trail

## Contributing

See [CONTRIBUTING.md](../../CONTRIBUTING.md) for guidelines.

## License

See [LICENSE](../../LICENSE) for details.

---

**Built with EngineX** — Open-source goal-driven agent runtime for healthcare, legal, and enterprise workflows.

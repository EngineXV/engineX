"""Nodes for the Medical Billing Auditor agent."""

from engine.graph import NodeSpec

# EHR Intake Node
ehr_intake = NodeSpec(
    id="ehr_intake",
    name="EHR Intake",
    description="Securely parse unstructured clinical summaries from EHR and extract procedures",
    node_type="event_loop",
    client_facing=True,
    input_keys=["clinical_text"],
    output_keys=["clinical_text", "extracted_procedures"],
    system_prompt="""\
You are the intake step for a Medical Billing Auditor agent.

**Task:** Obtain the raw clinical documentation and EHR notes.

**Rules:**
1. Read the user's messages — do NOT assume prefilled memory fields.
2. If the user sends a greeting or unclear message, reply and ask them to provide clinical documentation.
3. When the user provides clinical text, call set_output for the clinical_text field:
   set_output(key="clinical_text", value="<verbatim clinical documentation>")
4. Store documentation verbatim; do not summarize or paraphrase.
5. Extract any mentioned procedures and return as structured data.
""",
    tools=[],
)

# Code Extraction Node
code_extraction = NodeSpec(
    id="code_extraction",
    name="Code Extraction",
    description="Auto-extract clinical procedures and map to standard medical billing codes (ICD-11, CPT, HCPCS)",
    node_type="event_loop",
    client_facing=False,
    input_keys=["clinical_text"],
    output_keys=[
        "proposed_codes",
        "confidence_vectors",
        "extraction_confidence",
    ],
    system_prompt="""\
You are a medical billing code extraction specialist.

**Task:** Extract clinical procedures from documentation and map to standard billing codes.

**Steps:**
1. Read the clinical_text from input.
2. Identify all clinical procedures, diagnoses, and interventions mentioned.
3. For each procedure, propose appropriate ICD-11, CPT, or HCPCS codes.
4. Assign confidence scores (0.0-1.0) for:
   - extraction: How confident the procedure was accurately extracted from text
   - code_match: How confident the assigned code accurately represents the procedure
   - modifier_match: Confidence in any required modifiers
   - carrier_compliance: Confidence the code meets regional carrier rules
5. Assign financial_risk (0.0-1.0) based on code complexity and claim value.
6. Call set_output for proposed_codes and confidence_vectors.

**Output Format:**
Proposed codes should include: code, code_system (CPT/ICD-11/HCPCS), description, confidence, financial_risk
""",
    tools=[],
)

# Compliance Validation Node
compliance_validation = NodeSpec(
    id="compliance_validation",
    name="Compliance Validation",
    description="Validate codes against regional insurance carrier rules and compliance requirements",
    node_type="event_loop",
    client_facing=False,
    input_keys=["proposed_codes", "confidence_vectors"],
    output_keys=[
        "validation_flags",
        "high_risk_codes",
        "ready_for_review",
    ],
    system_prompt="""\
You are a medical billing compliance validator.

**Task:** Check proposed billing codes against regional carrier rules and compliance requirements.

**Steps:**
1. For each proposed code:
   - Verify it matches expected code format (CPT: 5 digits, ICD-11: alphanumeric, etc.)
   - Check for common misuses or bundling violations
   - Validate modifiers against carrier rules
   - Flag any critical compliance issues
2. Categorize codes by risk level:
   - Low: confidence >= 0.75, financial_risk < 0.30, no flags
   - Medium: low confidence or elevated risk, but no critical flags
   - High: critical compliance flags or financial_risk >= 0.80
3. Call set_output with validation results.

**Flag Prefixes (escalate to HITL if present):**
- "critical" / "fatal" / "deny" — Prevents claim submission
- "warning" — May cause delay or reduction
""",
    tools=[],
)

# HITL Review Node
hitl_review = NodeSpec(
    id="hitl_review",
    name="HITL Review",
    description="Pause execution and surface high-risk codes to billing auditor for human authorization",
    node_type="event_loop",
    client_facing=True,
    input_keys=["proposed_codes", "validation_flags", "high_risk_codes"],
    output_keys=["approval_payload"],
    system_prompt="""\
You are facilitating a human-in-the-loop (HITL) review step.

**Task:** Present high-risk or low-confidence billing codes to a human auditor for review.

**Steps:**
1. Display the proposed codes and their confidence/risk scores.
2. Highlight codes marked for review due to:
   - Low confidence (< 0.75)
   - High financial risk (>= 0.80)
   - Critical compliance flags
3. Show the auditor the clinical context and reasoning.
4. Wait for auditor input via set_output:
   - action: "approve" / "modify" / "reject"
   - approved_codes: (if modified, the corrected codes)
   - reason: (explanation for the decision)
""",
    tools=[],
)

# Resolution Handshake Node
resolution_handshake = NodeSpec(
    id="resolution_handshake",
    name="Resolution Handshake",
    description="Process human auditor decision and update execution state with approved adjustments",
    node_type="event_loop",
    client_facing=False,
    input_keys=["approval_payload", "proposed_codes"],
    output_keys=["final_codes", "human_override_logs", "ready_for_audit"],
    system_prompt="""\
You are processing the human auditor's approval decision.

**Task:** Update the execution state with human-approved code adjustments.

**Steps:**
1. Read the auditor's decision (approve/modify/reject).
2. If "approve": finalize the proposed codes as-is.
3. If "modify": apply the auditor's corrections and log the changes.
4. If "reject": mark codes as rejected and note the reason.
5. Create an audit log entry with:
   - Auditor ID
   - Original vs. Approved codes
   - Decision reason
   - Timestamp
6. Update state to resume execution.
""",
    tools=[],
)

# Audit Storage Node
audit_storage = NodeSpec(
    id="audit_storage",
    name="Audit Storage",
    description="Persist final claim state and human override logs to secure audit storage",
    node_type="event_loop",
    client_facing=False,
    input_keys=["final_codes", "human_override_logs", "clinical_text"],
    output_keys=["audit_record_id", "audit_complete"],
    system_prompt="""\
You are finalizing the audit trail and storing the claim.

**Task:** Save the final claim state and all human decisions to audit storage.

**Steps:**
1. Compile the final audit record:
   - Original clinical documentation
   - Extracted procedures
   - Proposed codes (before human review)
   - Final approved codes
   - All human override logs
   - Timestamps and auditor IDs
2. Generate a unique audit_record_id.
3. Persist to secure storage.
4. Return confirmation.
""",
    tools=[],
)

__all__ = [
    "ehr_intake",
    "code_extraction",
    "compliance_validation",
    "hitl_review",
    "resolution_handshake",
    "audit_storage",
]

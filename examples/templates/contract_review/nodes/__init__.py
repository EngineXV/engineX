"""Node definitions for Contract Review"""

from engine.graph import NodeSpec

intake_node = NodeSpec(
    id="intake",
    name="Intake",
    description="Collect contract text from the user.",
    node_type="event_loop",
    client_facing=True,
    input_keys=["contract_text", "document_name"],
    output_keys=["contract_text", "document_name"],
    system_prompt="""\
You are the intake step for a Contract Review agent.

**Task:** Obtain the full contract text and an optional document name.

If `contract_text` is already in context, call set_output immediately:
- set_output("contract_text", "<value>")
- set_output("document_name", "<name or Unknown>")

Otherwise greet briefly, ask the user to paste the contract or provide a path, then stop.
When they reply, store their text verbatim with set_output. Do not summarize yet.
""",
    tools=[],
)

extract_node = NodeSpec(
    id="extract",
    name="Extract Fields",
    description="Extract structured fields from the contract.",
    node_type="event_loop",
    client_facing=False,
    input_keys=["contract_text", "document_name"],
    output_keys=[
        "parties",
        "effective_date",
        "term",
        "termination_clause",
        "liability_cap",
        "payment_terms",
        "confidence",
        "extraction_notes",
    ],
    system_prompt="""\
You are a contract extraction specialist.

Read contract_text and extract:
- parties (who signed / counter-parties)
- effective_date
- term (duration or end date)
- termination_clause (short summary)
- liability_cap (amount or "none stated")
- payment_terms (short summary)
- confidence (high/medium/low)
- extraction_notes (gaps, ambiguities)

Rules:
- Do not invent data not present in the contract.
- Use "Not found" when a field is missing.
- Call set_output for each field above.
""",
    tools=[],
)

human_review_node = NodeSpec(
    id="human_review",
    name="Human Review",
    description="Human approves or edits extracted fields before finalization.",
    node_type="event_loop",
    client_facing=True,
    input_keys=[
        "parties",
        "effective_date",
        "term",
        "termination_clause",
        "liability_cap",
        "payment_terms",
        "confidence",
        "extraction_notes",
        "document_name",
    ],
    output_keys=[
        "review_decision",
        "reviewer_edits",
        "approved_parties",
        "approved_effective_date",
        "approved_term",
        "approved_termination_clause",
        "approved_liability_cap",
        "approved_payment_terms",
    ],
    system_prompt="""\
You are the human review gate for contract extraction.

Present the extracted fields clearly. Ask the reviewer to:
1. Approve as-is, OR
2. Provide corrections.

When the user responds:
- set_output("review_decision", "approved" or "edited")
- set_output("reviewer_edits", summary of what changed, or "none")
- set_output approved_* fields with final values (after edits if any)

Do not finalize until explicit approval.
""",
    tools=[],
)

audit_node = NodeSpec(
    id="audit",
    name="Audit Log",
    description="Produce audit record of AI extraction and human decision.",
    node_type="event_loop",
    client_facing=False,
    input_keys=[
        "document_name",
        "parties",
        "effective_date",
        "term",
        "termination_clause",
        "liability_cap",
        "payment_terms",
        "confidence",
        "extraction_notes",
        "review_decision",
        "reviewer_edits",
        "approved_parties",
        "approved_effective_date",
        "approved_term",
        "approved_termination_clause",
        "approved_liability_cap",
        "approved_payment_terms",
    ],
    output_keys=["audit_record", "final_summary"],
    system_prompt="""\
Create an audit record JSON string and a short final summary.

set_output("audit_record", JSON with keys:
  document_name, ai_extraction, human_review_decision, reviewer_edits, approved_fields, timestamp_note)

set_output("final_summary", 2-3 sentences for the reviewer confirming what was approved)

Use only information from context. No new facts.
""",
    tools=[],
)

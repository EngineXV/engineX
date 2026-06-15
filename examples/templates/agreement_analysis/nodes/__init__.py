"""Node definitions for Agreement Analysis"""

from engine.graph import NodeSpec

intake_node = NodeSpec(
    id="intake",
    name="Intake",
    description="Collect agreement text from the user.",
    node_type="event_loop",
    client_facing=True,
    input_keys=["contract_text", "document_name"],
    output_keys=["contract_text", "document_name"],
    system_prompt="""\
You are the intake step for an Agreement Analysis agent.

**Task:** Obtain the full agreement text and an optional document name.

**Rules:**
1. Read the user's messages in the conversation — do NOT assume prefilled memory fields.
2. If the user sends a greeting or short message that is clearly not agreement text, \
reply briefly and ask them to paste the agreement or provide a file path. Do NOT call set_output yet.
3. When the user provides agreement text, call set_output once per field using this format:
   set_output(key="contract_text", value="<verbatim text>")
   set_output(key="document_name", value="<name or Unknown>")
4. Do not summarize or paraphrase — store the agreement verbatim.
5. Never repeat the same set_output call if it already succeeded.
""",
    tools=[],
)

extract_node = NodeSpec(
    id="extract",
    name="Extract Fields",
    description="Extract structured fields from the agreement.",
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
You are an agreement extraction specialist.

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
- Do not invent data not present in the agreement.
- Use "Not found" when a field is missing.
- Call set_output for each field above.
""",
    tools=[],
)

human_review_node = NodeSpec(
    id="human_review",
    name="Approval Gate",
    description="Reviewer approves or edits extracted fields before finalization.",
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
You are the approval gate for agreement extraction.

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

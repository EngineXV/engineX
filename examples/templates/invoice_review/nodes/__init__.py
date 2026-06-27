"""Invoice review nodes."""

from engine.graph import NodeSpec

intake_node = NodeSpec(
    id="intake",
    name="Intake",
    description="Collect invoice content.",
    node_type="event_loop",
    client_facing=True,
    input_keys=["invoice_text"],
    output_keys=["invoice_text"],
    system_prompt="Collect invoice text and set_output('invoice_text', content).",
    tools=["set_output"],
)

extract_node = NodeSpec(
    id="extract",
    name="Extract",
    description="Extract structured invoice fields.",
    node_type="event_loop",
    client_facing=False,
    input_keys=["invoice_text"],
    output_keys=["invoice_json"],
    system_prompt=(
        "Extract vendor, invoice_number, date, total, line_items as JSON. "
        "set_output('invoice_json', json_string)."
    ),
    tools=["set_output"],
)

approval_node = NodeSpec(
    id="approval",
    name="Finance Approval",
    description="Human approval for exceptions.",
    node_type="event_loop",
    client_facing=True,
    input_keys=["invoice_json"],
    output_keys=["approval_status", "approval_notes"],
    system_prompt=(
        "Present extracted invoice_json and ask finance to approve or reject. "
        "set_output approval_status and approval_notes."
    ),
    tools=["set_output"],
)

audit_node = NodeSpec(
    id="audit",
    name="Audit",
    description="Write audit record.",
    node_type="event_loop",
    client_facing=False,
    input_keys=["invoice_json", "approval_status", "approval_notes"],
    output_keys=["audit_record"],
    system_prompt="set_output('audit_record', JSON audit bundle). Finish.",
    tools=["set_output"],
)

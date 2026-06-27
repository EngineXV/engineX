"""Support triage nodes."""

from engine.graph import NodeSpec

intake_node = NodeSpec(
    id="intake",
    name="Intake",
    description="Collect the customer message.",
    node_type="event_loop",
    client_facing=True,
    input_keys=["customer_message"],
    output_keys=["customer_message"],
    system_prompt="Ask for the customer message if missing, then set_output('customer_message', text).",
    tools=["set_output"],
)

classify_node = NodeSpec(
    id="classify",
    name="Classify",
    description="Classify urgency and topic.",
    node_type="event_loop",
    client_facing=False,
    input_keys=["customer_message"],
    output_keys=["triage_summary"],
    system_prompt=(
        "Summarize the issue, urgency (low/medium/high), and recommended queue. "
        "set_output('triage_summary', JSON string)."
    ),
    tools=["set_output"],
)

review_node = NodeSpec(
    id="review",
    name="Review Draft",
    description="Human approves the draft reply.",
    node_type="event_loop",
    client_facing=True,
    input_keys=["customer_message", "triage_summary", "draft_reply"],
    output_keys=["draft_reply", "approved"],
    system_prompt=(
        "Draft a concise support reply from triage_summary. "
        "set_output('draft_reply', reply). Ask the human to approve or edit."
    ),
    tools=["set_output"],
)

finalize_node = NodeSpec(
    id="finalize",
    name="Finalize",
    description="Record approved response.",
    node_type="event_loop",
    client_facing=False,
    input_keys=["draft_reply", "approved"],
    output_keys=["final_record"],
    system_prompt="set_output('final_record', JSON with draft_reply and approved flag). Finish.",
    tools=["set_output"],
)

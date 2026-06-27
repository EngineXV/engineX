"""Node definitions for Hourly Tracking Agent."""

from engine.graph import NodeSpec

fetch_transactions_node = NodeSpec(
    id="fetch_transactions",
    name="Fetch Transactions",
    description="Fetch broker and investor transactions.",
    node_type="event_loop",
    client_facing=False,
    input_keys=[],
    output_keys=[
        "raw_transactions_json",
    ],
    system_prompt="""\
Call fetch_broker_transactions().

Call fetch_investor_logs().

Combine both transaction sources into a single JSON structure.

set_output(
    "raw_transactions_json",
    combined_json
)

Finish.
""",
    tools=[
        "fetch_broker_transactions",
        "fetch_investor_logs",
    ],
)

process_transactions_node = NodeSpec(
    id="process_transactions",
    name="Process Transactions",
    description="Normalize transactions.",
    node_type="event_loop",
    client_facing=False,
    input_keys=[
        "raw_transactions_json",
    ],
    output_keys=[
        "structured_transactions_json",
    ],
    system_prompt="""\
Call normalize_transactions().

Convert raw transaction inputs into a standardized schema:

transaction_id
broker_id
investor_id
input_amount
output_amount
fees

set_output(
    "structured_transactions_json",
    structured_transactions
)

Finish.
""",
    tools=[
        "normalize_transactions",
    ],
)

validate_transactions_node = NodeSpec(
    id="validate_transactions",
    name="Validate Transactions",
    description="Validate transaction math.",
    node_type="event_loop",
    client_facing=False,
    input_keys=[
        "structured_transactions_json",
    ],
    output_keys=[
        "validation_passed",
        "discrepancies_json",
        "requires_human_review",
    ],
    system_prompt="""\
Call validate_transactions().

Copy outputs:

validation_passed
discrepancies
requires_human_review

set_output(
    "validation_passed",
    validation_passed
)

set_output(
    "discrepancies_json",
    discrepancies
)

set_output(
    "requires_human_review",
    requires_human_review
)

Finish.
""",
    tools=[
        "validate_transactions",
    ],
)

correct_transactions_node = NodeSpec(
    id="correct_transactions",
    name="Correct Transactions",
    description="Fix invalid transaction records.",
    node_type="event_loop",
    client_facing=False,
    input_keys=[
        "structured_transactions_json",
        "discrepancies_json",
    ],
    output_keys=[
        "structured_transactions_json",
    ],
    system_prompt="""\
Call correct_transactions().

Replace structured_transactions_json
with corrected output.

set_output(
    "structured_transactions_json",
    corrected_transactions
)

Finish.
""",
    tools=[
        "correct_transactions",
    ],
)

human_review_node = NodeSpec(
    id="human_review",
    name="Human Review",
    description="Operator approves unresolved reconciliation exceptions.",
    node_type="event_loop",
    client_facing=True,
    input_keys=[
        "structured_transactions_json",
        "discrepancies_json",
    ],
    output_keys=[
        "human_approved",
        "reviewer_notes",
        "structured_transactions_json",
    ],
    system_prompt="""\
Present discrepancies_json and structured_transactions_json to the operator.

Explain what auto-correction attempted and why human approval is required.

Ask the operator to approve with adjusted values or reject for rework.

When approved:
- set_output("human_approved", True)
- set_output("reviewer_notes", "<operator rationale>")
- set_output("structured_transactions_json", "<approved transactions JSON>")

When rejected:
- set_output("human_approved", False)
- set_output("reviewer_notes", "<what to fix>")
""",
    tools=[
        "set_output",
    ],
)

store_results_node = NodeSpec(
    id="store_results",
    name="Store Results",
    description="Store verified transactions.",
    node_type="event_loop",
    client_facing=False,
    input_keys=[
        "structured_transactions_json",
    ],
    output_keys=[
        "tracking_summary",
    ],
    system_prompt="""\
Call store_verified_results().

Store verified transactions.

set_output(
    "tracking_summary",
    result
)

Finish.
""",
    tools=[
        "store_verified_results",
    ],
)

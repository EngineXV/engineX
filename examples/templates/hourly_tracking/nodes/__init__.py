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
Call normalize_transactions().

Convert raw transaction inputs into a
standardized schema.

set_output(
    "structured_transactions_json",
    structured_transactions
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
Normalize transactions into:

transaction_id
broker_id
investor_id
input_amount
output_amount
fees

set_output(
    "structured_transactions_json",
    normalized_json
)

Finish.
""",
    tools=["normalize_transactions"],
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
    ],
    system_prompt="""\
Call validate_transactions().

Copy outputs:

validation_passed
discrepancies

set_output("validation_passed", validation_passed)
set_output("discrepancies_json", discrepancies)

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

Finish.
""",
    tools=[
        "correct_transactions",
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

set_output("tracking_summary", result)

Finish.
""",
    tools=[
        "store_verified_results",
    ],
)

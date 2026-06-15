"""Node definitions for Log Monitor agent."""

from engine.graph import NodeSpec

fetch_enrich_node = NodeSpec(
    id="fetch_enrich",
    name="Fetch & Enrich",
    description="Poll Grafana, deduplicate fingerprints, and rule-score incidents.",
    node_type="event_loop",
    client_facing=False,
    input_keys=[],
    output_keys=[
        "preflight_ok",
        "tick_summary",
        "incidents_json",
        "clear_incidents_json",
        "ambiguous_incidents_json",
        "needs_llm_triage",
        "new_incident_count",
        "skipped_muted_count",
        "mock_mode",
    ],
    system_prompt="""\
You are the fetch & enrich step for a log monitoring agent.

1. Call preflight_check(require_live=false) once. set_output("preflight_ok", ok field).
2. Call run_log_monitor_pipeline() once.
3. Copy ALL returned fields into set_output:
   - tick_summary
   - incidents_json
   - clear_incidents_json
   - ambiguous_incidents_json
   - needs_llm_triage (true/false)
   - new_incident_count
   - skipped_muted_count
   - mock_mode (true/false from pipeline)

Do not invent incidents. If the tool returns zero incidents, still set outputs with empty JSON arrays.
Finish after set_output calls succeed.
""",
    tools=["preflight_check", "run_log_monitor_pipeline"],
)

llm_triage_node = NodeSpec(
    id="llm_triage",
    name="LLM Triage",
    description="Resolve ambiguous incident severities with LLM judgment.",
    node_type="event_loop",
    client_facing=False,
    input_keys=["ambiguous_incidents_json", "incidents_json", "clear_incidents_json"],
    output_keys=["incidents_json", "triage_notes"],
    system_prompt="""\
You triage ambiguous log incidents.

Read ambiguous_incidents_json and clear_incidents_json from context.

For each ambiguous incident, choose final severity: SEVERE, HIGH, MEDIUM, or LOW.
Use message content, service name, count, deploy_note, and metric_note.

Rules:
- payments/auth/checkout issues skew higher
- single cron/report parse errors skew lower
- repeated infrastructure timeouts skew HIGH or SEVERE

Merge triaged incidents back with clear_incidents_json into one list.
set_output("incidents_json", JSON array string of ALL incidents with updated severities)
set_output("triage_notes", short bullet summary of changes)

Do not drop incidents.
""",
    tools=[],
)

dispatch_node = NodeSpec(
    id="dispatch",
    name="Dispatch Alerts",
    description="Route SEVERE/HIGH to Slack/PagerDuty, MEDIUM to human review queue.",
    node_type="event_loop",
    client_facing=False,
    input_keys=["incidents_json"],
    output_keys=[
        "dispatch_summary",
        "needs_human_review",
        "medium_incidents_json",
        "alerts_sent_json",
    ],
    system_prompt="""\
You dispatch alerts for scored incidents.

1. Call build_dispatch_plan(incidents_json=<incidents_json from context>).
2. For each incident in severe_high_json:
   - notify_slack(severity, title, body, fingerprint)
   - if severity is SEVERE: notify_pagerduty(severity, title, body, fingerprint)
   - create_incident_ticket(title, body, severity)
   Title format: "{service}: {first 80 chars of message}"
   Body includes: severity, count, owner, deploy_note, metric_note, fingerprint.

3. If daemon_mode is true from the plan, for each incident in daemon_medium_json:
   - notify_slack with severity MEDIUM (digest — no PagerDuty)

4. set_output("dispatch_summary", counts of alerts/tickets sent)
5. set_output("needs_human_review", needs_human_review from plan — false in daemon mode)
6. set_output("medium_incidents_json", medium_json from plan)
7. set_output("alerts_sent_json", JSON list of tool results)

Skip Slack/PagerDuty gracefully if tools return skipped=true.
""",
    tools=[
        "build_dispatch_plan",
        "notify_slack",
        "notify_pagerduty",
        "create_incident_ticket",
    ],
)

human_review_node = NodeSpec(
    id="human_review",
    name="Human Review",
    description="Operator approves, downgrades, or snoozes MEDIUM incidents.",
    node_type="event_loop",
    client_facing=True,
    input_keys=["medium_incidents_json", "dispatch_summary"],
    output_keys=["review_decision", "review_notes", "approved_medium_json"],
    system_prompt="""\
You are the human review gate for MEDIUM severity incidents.

Present medium_incidents_json clearly with service, message, severity, owner.

Ask the operator to:
1. Approve alerts for all MEDIUM items, OR
2. Downgrade to LOW (no Slack), OR
3. Snooze fingerprint(s) for later

When they respond:
- set_output("review_decision", "approved" | "downgraded" | "snoozed")
- set_output("review_notes", summary)
- set_output("approved_medium_json", JSON array — empty if downgraded/snoozed)

If medium_incidents_json is empty array, set review_decision=skipped and finish.
""",
    tools=[],
)

learn_node = NodeSpec(
    id="learn",
    name="Learn & Tune",
    description="Persist outcomes for dedup tuning and audit.",
    node_type="event_loop",
    client_facing=False,
    input_keys=[
        "incidents_json",
        "review_decision",
        "review_notes",
        "approved_medium_json",
        "alerts_sent_json",
    ],
    output_keys=["learning_summary", "final_summary"],
    system_prompt="""\
Record learning outcomes for this tick.

For each incident in incidents_json, call record_learning_outcome with:
- fingerprint
- severity
- action ("alerted", "human_approved", "downgraded", "snoozed", "logged")

Use review_decision when handling MEDIUM items from approved_medium_json.

set_output("learning_summary", count of outcomes recorded)
set_output("final_summary", 2-3 sentence operator-facing summary of the tick)
""",
    tools=["record_learning_outcome"],
)

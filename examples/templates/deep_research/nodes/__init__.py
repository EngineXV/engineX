"""Node definitions for Deep Research agent."""

from engine.graph import NodeSpec

intake_node = NodeSpec(
    id="intake",
    name="Research Intake",
    description="Clarify the research topic and scope with the user.",
    node_type="event_loop",
    client_facing=True,
    input_keys=["user_request"],
    output_keys=["research_brief"],
    success_criteria=(
        "The research brief states the topic, key questions, scope, and desired depth."
    ),
    system_prompt="""\
You are a research intake specialist. Clarify what the user wants researched.

Rules:
- Do NOT search the web or fetch sources — research happens in the next step.
- If the request is vague, ask at most 2 clarifying questions (scope, angle, depth).
- When scope is clear, confirm your understanding and ask the user to confirm.
- After confirmation, call set_output("research_brief", "<actionable paragraph>").
""",
    tools=["set_output"],
)

research_node = NodeSpec(
    id="research",
    name="Research",
    description="Search the web, fetch sources, and compile findings.",
    node_type="event_loop",
    client_facing=False,
    input_keys=["research_brief", "feedback"],
    output_keys=["findings", "sources", "gaps"],
    nullable_output_keys=["feedback"],
    success_criteria=(
        "Findings reference at least 3 distinct sources with URLs. "
        "Claims are grounded in fetched content."
    ),
    system_prompt="""\
You are a research agent. Given research_brief (and optional feedback), investigate the topic.

Work in phases:
1. web_search — 3-5 diverse queries covering different angles.
2. web_scrape — fetch 5-8 promising URLs; skip failures.
3. Analyze themes, contradictions, and confidence levels.

Use append_data("research_notes.md", ...) to log findings as you go.
Call set_output for each key in separate turns:
- set_output("findings", "<structured summary with source URLs>")
- set_output("sources", "<JSON list of {url, title, summary}>")
- set_output("gaps", "<what is still under-covered>")
""",
    tools=[
        "web_search",
        "web_scrape",
        "load_data",
        "save_data",
        "append_data",
        "list_data_files",
        "set_output",
    ],
)

review_node = NodeSpec(
    id="review",
    name="Review Findings",
    description="Present findings and get human direction before writing the report.",
    node_type="event_loop",
    client_facing=True,
    input_keys=["findings", "sources", "gaps", "research_brief"],
    output_keys=["needs_more_research", "feedback"],
    success_criteria=(
        "The user has reviewed findings and chosen more research or report generation."
    ),
    system_prompt="""\
Present findings to the user:
1. Summary (2-3 sentences)
2. Key findings (bulleted, with confidence)
3. Sources used (count and quality)
4. Gaps (under-covered areas)

Ask whether to dig deeper or proceed to the final report.

After the user responds, call:
- set_output("needs_more_research", "true" or "false")
- set_output("feedback", "<what to explore further, or empty string>")
""",
    tools=["set_output"],
)

report_node = NodeSpec(
    id="report",
    name="Write & Deliver Report",
    description="Write a cited HTML report and deliver it to the user.",
    node_type="event_loop",
    client_facing=True,
    input_keys=["findings", "sources", "research_brief"],
    output_keys=["delivery_status", "next_action"],
    success_criteria=(
        "HTML report saved, link presented, and user indicated next action."
    ),
    system_prompt="""\
Write a research report as HTML using save_data + append_data (never one giant save_data call).

Steps:
1. save_data("report.html", "<!DOCTYPE html>... head, CSS, executive summary ...")
2. append_data chunks for Key Findings, Analysis, References, footer, </html>
3. serve_file_to_user("report.html", label="Research Report", open_in_browser=true)
4. Present file_path from the tool result and summarize the report.
5. Ask: new topic or deeper research on this topic?
6. set_output("delivery_status", "completed")
7. set_output("next_action", "new_topic" or "more_research")

Every factual claim must use [n] citation notation linked to references.
Use load_data / list_data_files if you need full research_notes.md content.
""",
    tools=[
        "save_data",
        "append_data",
        "serve_file_to_user",
        "load_data",
        "list_data_files",
        "set_output",
    ],
)

__all__ = ["intake_node", "research_node", "review_node", "report_node"]

"""Node definitions for Customer Feedback Analyzer agent."""

from engine.graph import NodeSpec

intake_node = NodeSpec(
    id="intake",
    name="Feedback Intake",
    description="Receive the customer feedback and prepare it for analysis.",
    node_type="event_loop",
    client_facing=True,
    input_keys=["user_request"],
    output_keys=["raw_feedback"],
    success_criteria=(
        "The raw customer feedback is captured and stored."
    ),
    system_prompt="""\
You are a feedback intake specialist. Your goal is to capture customer feedback.

Rules:
- Ask the user to provide the customer feedback if they haven't already.
- Once provided, confirm you have received it.
- Call set_output("raw_feedback", "<the exact feedback provided>").
""",
    tools=["set_output"],
)

analysis_node = NodeSpec(
    id="analysis",
    name="Analyze Feedback",
    description="Analyze the feedback for sentiment and categorize the issue.",
    node_type="event_loop",
    client_facing=False,
    input_keys=["raw_feedback"],
    output_keys=["sentiment", "category", "analysis_summary"],
    success_criteria=(
        "Feedback is categorized and sentiment is analyzed."
    ),
    system_prompt="""\
You are a customer feedback analyst. 

1. Use the categorize_issue tool to determine the category of the feedback.
2. Determine the sentiment (positive, neutral, negative).
3. Write a brief 1-2 sentence summary of the core issue.

Call set_output for each key:
- set_output("sentiment", "<positive|neutral|negative>")
- set_output("category", "<result from categorize_issue>")
- set_output("analysis_summary", "<your summary>")
""",
    tools=["categorize_issue", "set_output"],
)

drafting_node = NodeSpec(
    id="drafting",
    name="Draft Response",
    description="Draft a professional response based on the analysis.",
    node_type="event_loop",
    client_facing=False,
    input_keys=["raw_feedback", "sentiment", "category", "analysis_summary"],
    output_keys=["draft_response"],
    success_criteria=(
        "A professional, empathetic response is drafted addressing the specific issue."
    ),
    system_prompt="""\
You are a customer support specialist. Write a reply to the customer based on the feedback analysis.

Rules:
- Be empathetic and professional.
- Acknowledge their specific issue (use the category and summary).
- If it's a bug, apologize and say the team is looking into it.
- If it's a feature request, thank them and say it will be passed to the product team.
- Keep it concise (under 4 paragraphs).

Call set_output:
- set_output("draft_response", "<your drafted email/message>")
""",
    tools=["set_output"],
)

review_node = NodeSpec(
    id="review",
    name="Review and Send",
    description="Present the drafted response to a human for review before sending.",
    node_type="event_loop",
    client_facing=True,
    input_keys=["raw_feedback", "sentiment", "category", "draft_response"],
    output_keys=["final_action"],
    success_criteria=(
        "The human reviewer approves the message or requests changes."
    ),
    system_prompt="""\
Present the analysis and drafted response to the human reviewer:

1. Original Feedback: <raw_feedback>
2. Analysis: Sentiment (<sentiment>), Category (<category>)
3. Proposed Reply: <draft_response>

Ask the user if they approve this reply, or if they would like any changes made.

After the user responds:
- If approved, call set_output("final_action", "approved") and say you are sending it (simulated).
- If changes requested, politely say you understand and call set_output("final_action", "needs_revision").
""",
    tools=["set_output"],
)

__all__ = ["intake_node", "analysis_node", "drafting_node", "review_node"]

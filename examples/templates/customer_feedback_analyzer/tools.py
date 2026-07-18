"""Tools for Customer Feedback Analyzer agent."""

from engine.tools import Tool, ToolResult


def categorize_issue_tool(feedback: str) -> ToolResult:
    """Categorize the customer feedback into predefined buckets."""
    # Dummy implementation for demonstration
    lower_feedback = feedback.lower()
    if "bug" in lower_feedback or "error" in lower_feedback or "broken" in lower_feedback:
        category = "Technical Support"
    elif "price" in lower_feedback or "cost" in lower_feedback or "expensive" in lower_feedback:
        category = "Billing/Pricing"
    elif "feature" in lower_feedback or "add" in lower_feedback or "wish" in lower_feedback:
        category = "Feature Request"
    else:
        category = "General Feedback"
        
    return ToolResult(
        output=f"Categorized as: {category}",
        metadata={"category": category}
    )

tools = [
    Tool(
        name="categorize_issue",
        description="Categorize the customer feedback into predefined buckets.",
        func=categorize_issue_tool,
        input_schema={
            "type": "object",
            "properties": {
                "feedback": {
                    "type": "string",
                    "description": "The customer feedback text to categorize."
                }
            },
            "required": ["feedback"]
        }
    )
]

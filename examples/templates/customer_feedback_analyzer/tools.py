"""Tools for Customer Feedback Analyzer agent."""

from __future__ import annotations

from typing import Any

from engine.runner.tool_registry import tool


@tool(description="Categorize the customer feedback into predefined buckets.")
def categorize_issue(feedback: str) -> dict[str, Any]:
    """Categorize the customer feedback into predefined buckets."""
    lower_feedback = feedback.lower()
    if "bug" in lower_feedback or "error" in lower_feedback or "broken" in lower_feedback:
        category = "Technical Support"
    elif "price" in lower_feedback or "cost" in lower_feedback or "expensive" in lower_feedback:
        category = "Billing/Pricing"
    elif "feature" in lower_feedback or "add" in lower_feedback or "wish" in lower_feedback:
        category = "Feature Request"
    else:
        category = "General Feedback"

    return {
        "output": f"Categorized as: {category}",
        "category": category,
    }

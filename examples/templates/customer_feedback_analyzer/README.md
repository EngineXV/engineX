# Customer Feedback Analyzer

An EngineX agent that takes raw customer feedback, analyzes the sentiment, categorizes the issue, and drafts a professional response for human review.

This demonstrates the use of a multi-node pipeline and a Human-In-The-Loop (HITL) pause node for review.

## Usage

```bash
# Validate the agent graph
./engine validate examples/templates/customer_feedback_analyzer

# Run the agent in the terminal UI
./engine run examples/templates/customer_feedback_analyzer --tui
```

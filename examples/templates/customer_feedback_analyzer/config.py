"""Runtime configuration for Customer Feedback Analyzer agent."""

from dataclasses import dataclass, field

from engine.config import RuntimeConfig

default_config = RuntimeConfig()

skip_credential_validation = True


@dataclass
class AgentMetadata:
    name: str = "Customer Feedback Analyzer"
    version: str = "1.0.0"
    description: str = "Analyzes customer feedback, extracts sentiment, and drafts a response for human review."
    intro_message: str = (
        "Hi! I'm the Customer Feedback Analyzer. Give me a piece of customer feedback "
        "and I will analyze its sentiment, categorize the issue, and draft a professional reply."
    )
    skills: list[str] = field(default_factory=lambda: ["analysis", "drafting"])


metadata = AgentMetadata()

"""Support Triage template — classify and draft responses with HITL."""

from dataclasses import dataclass, field

from engine.config import RuntimeConfig

default_config = RuntimeConfig()


@dataclass
class AgentMetadata:
    name: str = "Support Triage"
    version: str = "1.0.0"
    description: str = (
        "Triage inbound support messages, classify urgency, and draft a reply "
        "with human approval before sending."
    )
    intro_message: str = "Paste a customer message and I'll classify it and draft a response."
    skills: list[str] = field(default_factory=list)


metadata = AgentMetadata()

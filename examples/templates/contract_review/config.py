"""Runtime configuration for Contract Review agent"""

from dataclasses import dataclass

from framework.config import RuntimeConfig

default_config = RuntimeConfig()


@dataclass
class AgentMetadata:
    name: str = "Contract Review"
    version: str = "1.0.0"
    description: str = (
        "Extract key fields from contracts (parties, dates, terms) with "
        "human-in-the-loop approval and an audit trail."
    )
    intro_message: str = (
        "Paste contract text or provide a file path. I'll extract key fields "
        "for your review before finalizing."
    )


metadata = AgentMetadata()

"""Runtime configuration for Agreement Analysis agent"""

from dataclasses import dataclass, field

from engine.config import RuntimeConfig

default_config = RuntimeConfig()


@dataclass
class AgentMetadata:
    name: str = "Agreement Analysis"
    version: str = "1.0.0"
    description: str = (
        "Structured extraction of agreement terms — parties, dates, obligations — "
        "with human-in-the-loop approval and a full audit trail."
    )
    intro_message: str = (
        "Paste agreement text or provide a file path. I'll extract key terms "
        "for your approval before finalizing."
    )
    skills: list[str] = field(
        default_factory=lambda: ["agreement-review"],
    )


metadata = AgentMetadata()

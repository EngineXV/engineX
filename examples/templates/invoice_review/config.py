"""Invoice Review template."""

from dataclasses import dataclass, field

from engine.config import RuntimeConfig

default_config = RuntimeConfig()


@dataclass
class AgentMetadata:
    name: str = "Invoice Review"
    version: str = "1.0.0"
    description: str = (
        "Extract invoice fields and route exceptions for finance approval."
    )
    intro_message: str = (
        "Paste invoice text or a file path to extract line items for review."
    )
    skills: list[str] = field(default_factory=list)


metadata = AgentMetadata()

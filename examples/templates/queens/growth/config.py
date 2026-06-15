"""Runtime configuration for Victoria — Growth Queen."""

from dataclasses import dataclass

from engine.config import RuntimeConfig

default_config = RuntimeConfig()


@dataclass
class AgentMetadata:
    name: str = "Victoria"
    version: str = "1.0.0"
    description: str = "Growth Queen Bee — supervises agreement analysis for partnerships and channel deals."
    intro_message: str = (
        "Hi, I'm Victoria, Head of Growth. Share a partnership or channel agreement and I'll coordinate the review."
    )
    queen_bee: bool = True
    queen_name: str = "Victoria"
    department: str = "Growth"
    role_title: str = "Head of Growth"
    domain_focus: str = "partnership agreements, channel deals, and growth contracts"


metadata = AgentMetadata()

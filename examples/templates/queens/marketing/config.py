"""Runtime configuration for Catherine — Marketing Queen."""

from dataclasses import dataclass

from engine.config import RuntimeConfig

default_config = RuntimeConfig()


@dataclass
class AgentMetadata:
    name: str = "Catherine"
    version: str = "1.0.0"
    description: str = "Marketing Queen Bee — supervises agreement analysis for marketing and sponsorship deals."
    intro_message: str = (
        "Hi, I'm Catherine, Head of Marketing. Send a partnership or sponsorship agreement and I'll handle the analysis."
    )
    queen_bee: bool = True
    queen_name: str = "Catherine"
    department: str = "Marketing"
    role_title: str = "Head of Marketing"
    domain_focus: str = "marketing partnerships, sponsorship deals, and brand collaborations"


metadata = AgentMetadata()

"""Runtime configuration for Alexandra — Technology Queen."""

from dataclasses import dataclass

from engine.config import RuntimeConfig

default_config = RuntimeConfig()


@dataclass
class AgentMetadata:
    name: str = "Alexandra"
    version: str = "1.0.0"
    description: str = "Technology Queen Bee — supervises agreement analysis for vendor, SaaS, and tech partnerships."
    intro_message: str = (
        "Hi, I'm Alexandra, Head of Technology. Share a vendor agreement, SaaS contract, or tech "
        "partnership doc and I'll delegate analysis to my worker and keep you updated."
    )
    queen_bee: bool = True
    queen_name: str = "Alexandra"
    department: str = "Technology"
    role_title: str = "Head of Technology"
    domain_focus: str = "vendor agreements, SaaS contracts, and technology partnerships"


metadata = AgentMetadata()

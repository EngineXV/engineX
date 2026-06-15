"""Runtime configuration for Rachel — Operations Queen."""

from dataclasses import dataclass

from engine.config import RuntimeConfig

default_config = RuntimeConfig()


@dataclass
class AgentMetadata:
    name: str = "Rachel"
    version: str = "1.0.0"
    description: str = "Operations Queen Bee — supervises agreement analysis for ops and SLA contracts."
    intro_message: str = (
        "Hi, I'm Rachel, Head of Operations. Paste an SLA, ops contract, or process agreement and I'll run it through my worker."
    )
    queen_bee: bool = True
    queen_name: str = "Rachel"
    department: str = "Operations"
    role_title: str = "Head of Operations"
    domain_focus: str = "operational agreements, SLAs, and process contracts"


metadata = AgentMetadata()

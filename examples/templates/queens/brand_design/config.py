"""Runtime configuration for Sophia — Brand & Design Queen."""

from dataclasses import dataclass

from engine.config import RuntimeConfig

default_config = RuntimeConfig()


@dataclass
class AgentMetadata:
    name: str = "Sophia"
    version: str = "1.0.0"
    description: str = "Brand & Design Queen Bee — supervises agreement analysis for creative and licensing contracts."
    intro_message: str = (
        "Hi, I'm Sophia, Head of Brand & Design. Share a creative or licensing agreement and I'll run it through my worker."
    )
    queen_bee: bool = True
    queen_name: str = "Sophia"
    department: str = "Brand & Design"
    role_title: str = "Head of Brand & Design"
    domain_focus: str = "creative agreements, licensing, and design contracts"


metadata = AgentMetadata()

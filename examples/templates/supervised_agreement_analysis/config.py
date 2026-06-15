"""Runtime configuration for Queen Supervisor agent"""

from dataclasses import dataclass

from engine.config import RuntimeConfig

default_config = RuntimeConfig()


@dataclass
class AgentMetadata:
    name: str = "Supervised Agreement Analysis"
    version: str = "1.0.0"
    description: str = (
        "Queen Bee supervises the Agreement Analysis worker — you chat with the Queen, "
        "she starts and monitors the pipeline."
    )
    intro_message: str = (
        "I'm your Queen supervisor. Tell me what agreement to analyze and I'll delegate "
        "to the worker, monitor progress, and keep you updated. You can paste text directly "
        "or ask me to start a review."
    )


metadata = AgentMetadata()

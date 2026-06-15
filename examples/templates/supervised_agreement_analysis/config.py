"""Runtime configuration for Agreement Supervisor agent"""

from dataclasses import dataclass

from engine.config import RuntimeConfig

default_config = RuntimeConfig()


@dataclass
class AgentMetadata:
    name: str = "Supervised Agreement Analysis"
    version: str = "1.0.0"
    description: str = (
        "Supervisor agent for the Agreement Analysis worker — chat here to delegate "
        "and monitor the pipeline."
    )
    intro_message: str = (
        "I'm your Agreement supervisor. Tell me what agreement to analyze and I'll delegate "
        "to the worker, monitor progress, and keep you updated. You can paste text directly "
        "or ask me to start a review."
    )


metadata = AgentMetadata()

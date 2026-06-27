"""Runtime configuration for Deep Research agent."""

from dataclasses import dataclass, field

from engine.config import RuntimeConfig

default_config = RuntimeConfig()

skip_credential_validation = True


@dataclass
class AgentMetadata:
    name: str = "Deep Research"
    version: str = "1.0.0"
    description: str = "Interactive research: intake → web research → human review → cited HTML report."
    intro_message: str = (
        "Hi! I'm your deep research assistant. Tell me a topic and I'll investigate it "
        "— searching sources, summarizing findings for your review, then writing a cited report."
    )
    skills: list[str] = field(default_factory=lambda: ["research"])


metadata = AgentMetadata()

"""Runtime configuration for Victoria — Growth Supervisor."""

from dataclasses import dataclass

from engine.config import RuntimeConfig

default_config = RuntimeConfig()


@dataclass
class AgentMetadata:
    name: str = "Victoria"
    version: str = "1.0.0"
    description: str = "Growth department supervisor — supervises agreement analysis for partnerships and channel deals."
    intro_message: str = (
        "Hi, I'm Victoria, Head of Growth. Share a partnership or channel agreement and I'll coordinate the review."
    )
    supervisor: bool = True
    supervisor_name: str = "Victoria"
    department: str = "Growth"
    role_title: str = "Head of Growth"
    domain_focus: str = "partnership agreements, channel deals, and growth contracts"
    worker_template: str = "meeting_scheduler"


metadata = AgentMetadata()

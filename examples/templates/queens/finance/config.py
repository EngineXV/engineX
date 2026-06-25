"""Runtime configuration for Charlotte — Finance Supervisor."""

from dataclasses import dataclass

from engine.config import RuntimeConfig

default_config = RuntimeConfig()


@dataclass
class AgentMetadata:
    name: str = "Charlotte"
    version: str = "1.0.0"
    description: str = "Finance department supervisor — supervises agreement analysis for financial and payment agreements."
    intro_message: str = "Hi, I'm Charlotte, Head of Finance. Paste a financial agreement or payment terms doc and I'll delegate analysis."
    supervisor: bool = True
    supervisor_name: str = "Charlotte"
    department: str = "Finance"
    role_title: str = "Head of Finance"
    domain_focus: str = "financial agreements, payment terms, and investment documents"


metadata = AgentMetadata()

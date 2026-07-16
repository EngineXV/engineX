"""Runtime configuration for Eleanor — Legal Supervisor."""

from dataclasses import dataclass

from engine.config import RuntimeConfig

default_config = RuntimeConfig()


@dataclass
class AgentMetadata:
    name: str = "Eleanor"
    version: str = "1.0.0"
    description: str = "Legal department supervisor — supervises agreement analysis for NDAs and legal contracts."
    intro_message: str = "Hi, I'm Eleanor, Head of Legal. Share an NDA or contract and I'll delegate review to my worker."
    supervisor: bool = True
    supervisor_name: str = "Eleanor"
    department: str = "Legal"
    role_title: str = "Head of Legal"
    domain_focus: str = "NDAs, legal contracts, and compliance agreements"
    worker_template: str = "agreement_analysis"


metadata = AgentMetadata()

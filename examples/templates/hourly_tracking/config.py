"""Runtime configuration for Hourly Tracking agent."""

from dataclasses import dataclass

from engine.config import RuntimeConfig

default_config = RuntimeConfig()

skip_credential_validation = True


@dataclass
class AgentMetadata:
    name: str = "Hourly Tracking Agent"
    version: str = "1.0.0"
    description: str = (
        "Hourly reconciliation workflow that ingests broker and investor "
        "transactions, validates financial consistency, performs "
        "auto-correction, and stores verified outputs."
    )
    intro_message: str = (
        "Hourly Tracking Agent running. Every hour it fetches transaction "
        "data, validates reconciliation rules, corrects discrepancies, "
        "and stores verified results."
    )


metadata = AgentMetadata()

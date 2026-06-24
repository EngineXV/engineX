"""Configuration metadata for Medical Billing Auditor agent."""

from dataclasses import dataclass


@dataclass
class Metadata:
    """Agent metadata."""

    version: str = "1.0.0"
    author: str = "EngineX Contributors"
    description: str = "HITL Medical Billing & Insurance Coding Auditor"
    tags: list[str] = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = ["medical", "billing", "hitl", "healthcare", "coding", "audit"]


metadata = Metadata()

"""Runtime configuration for Log Monitor agent."""

from dataclasses import dataclass

from engine.config import RuntimeConfig

default_config = RuntimeConfig()

# Optional env-based credentials; validated at tool runtime, not preload.
skip_credential_validation = True


@dataclass
class AgentMetadata:
    name: str = "Log Monitor"
    version: str = "1.0.0"
    description: str = (
        "Poll Grafana for error logs, deduplicate, score severity, "
        "LLM-triage ambiguous cases, and alert Slack/PagerDuty/Jira."
    )
    intro_message: str = (
        "Log monitor is running. Timer polls Grafana every minute for filtered errors. "
        "SEVERE/HIGH alerts go to Slack/PagerDuty; MEDIUM waits for human approval."
    )


metadata = AgentMetadata()

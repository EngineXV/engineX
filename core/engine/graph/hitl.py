"""Human-in-the-loop approval types for interactive CLI prompts."""

from dataclasses import dataclass
from enum import StrEnum


class ApprovalDecision(StrEnum):
    """Shell approval choices for HITL steps."""

    APPROVE = "approve"
    REJECT = "reject"
    ABORT = "abort"


@dataclass
class ApprovalResult:
    """Result of an interactive approval prompt."""

    decision: ApprovalDecision
    reason: str = ""
    feedback: str = ""

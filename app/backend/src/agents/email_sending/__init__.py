"""
Email Sending Agent - Phase 5, Agent 5.2.

Uploads leads with personalized emails to Instantly.ai campaigns,
manages sending queues, monitors delivery, and handles bounces.
"""

from src.agents.email_sending.agent import (
    EmailSendingAgent,
    EmailSendingConfig,
)
from src.agents.email_sending.schemas import (
    BatchResult,
    EmailSendingResult,
    SendingProgress,
)

__all__ = [
    "EmailSendingAgent",
    "EmailSendingConfig",
    "EmailSendingResult",
    "SendingProgress",
    "BatchResult",
]

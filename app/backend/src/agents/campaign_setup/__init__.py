"""
Campaign Setup Agent (Phase 5.1).

Creates campaigns in Instantly.ai with email sequences,
configures sending schedules, and sets up warmup settings.
"""

from src.agents.campaign_setup.agent import (
    CampaignSetupAgent,
    CampaignSetupConfig,
    run_campaign_setup,
)
from src.agents.campaign_setup.schemas import (
    CampaignSetupResult,
    EmailSequenceStep,
    SendingSchedule,
)

__all__ = [
    "CampaignSetupAgent",
    "CampaignSetupConfig",
    "CampaignSetupResult",
    "EmailSequenceStep",
    "SendingSchedule",
    "run_campaign_setup",
]

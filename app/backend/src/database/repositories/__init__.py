"""
Database repositories for agent data access.

Provides data access layer for:
- Phase 1: Niches, personas, and research data
- Phase 2: Campaigns, leads, and dedup logs
- Workflow: Checkpoints for all phases
"""

from src.database.repositories.campaign_repository import CampaignRepository
from src.database.repositories.lead_repository import LeadRepository
from src.database.repositories.niche_repository import NicheRepository
from src.database.repositories.persona_repository import PersonaRepository
from src.database.repositories.workflow_checkpoint_repository import (
    WorkflowCheckpointRepository,
)

__all__ = [
    # Phase 1
    "NicheRepository",
    "PersonaRepository",
    # Phase 2
    "CampaignRepository",
    "LeadRepository",
    # Workflow
    "WorkflowCheckpointRepository",
]

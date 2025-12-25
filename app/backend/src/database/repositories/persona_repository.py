"""
Persona Repository - Data access layer for persona research.

Provides CRUD operations for personas and persona_research_data tables.
Used by Persona Research Agent (1.2) and downstream agents.
"""

import logging
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import (
    PersonaModel,
    PersonaResearchDataModel,
)

logger = logging.getLogger(__name__)


class PersonaRepository:
    """
    Repository for persona-related database operations.

    Provides methods to create, read, update personas and their
    associated research data.
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize repository with database session.

        Args:
            session: SQLAlchemy async session
        """
        self.session = session

    # =========================================================================
    # Persona CRUD
    # =========================================================================

    async def create_persona(
        self,
        name: str,
        niche_id: str | UUID | None = None,
        job_titles: list[str] | None = None,
        seniority_levels: list[str] | None = None,
        departments: list[str] | None = None,
        industries: list[str] | None = None,
        goals: list[str] | None = None,
        challenges: list[str] | None = None,
        objections: list[str] | None = None,
        messaging_tone: str | None = None,
        description: str | None = None,
        custom_fields: dict[str, Any] | None = None,
    ) -> PersonaModel:
        """
        Create a new persona record.

        Args:
            name: Memorable persona name (e.g., "The Scaling VP")
            niche_id: Parent niche UUID
            job_titles: Target job titles
            seniority_levels: Seniority levels
            departments: Target departments
            industries: Target industries
            goals: Persona goals
            challenges: Pain points/challenges
            objections: Common objections
            messaging_tone: Recommended messaging tone
            description: Optional description
            custom_fields: Additional custom data

        Returns:
            Created PersonaModel instance
        """
        # Convert niche_id to UUID if string
        niche_uuid = None
        if niche_id:
            niche_uuid = UUID(niche_id) if isinstance(niche_id, str) else niche_id

        persona = PersonaModel(
            name=name,
            niche_id=niche_uuid,
            description=description,
            job_titles=job_titles or [],
            seniority_levels=seniority_levels or [],
            departments=departments or [],
            industries=industries or [],
            goals=goals or [],
            challenges=challenges or [],
            objections=objections or [],
            messaging_tone=messaging_tone,
            custom_fields=custom_fields or {},
        )
        self.session.add(persona)
        await self.session.flush()
        await self.session.refresh(persona)

        logger.info(f"Created persona: {persona.id} - {name}")
        return persona

    async def create_personas_bulk(
        self,
        personas_data: list[dict[str, Any]],
    ) -> list[PersonaModel]:
        """
        Create multiple personas in bulk.

        Args:
            personas_data: List of persona data dictionaries

        Returns:
            List of created PersonaModel instances
        """
        personas = []
        for data in personas_data:
            persona = await self.create_persona(**data)
            personas.append(persona)

        logger.info(f"Created {len(personas)} personas in bulk")
        return personas

    async def get_persona(self, persona_id: str | UUID) -> PersonaModel | None:
        """
        Get persona by ID.

        Args:
            persona_id: Persona UUID

        Returns:
            PersonaModel or None if not found
        """
        if isinstance(persona_id, str):
            persona_id = UUID(persona_id)

        result = await self.session.execute(
            select(PersonaModel).where(PersonaModel.id == persona_id)
        )
        return result.scalar_one_or_none()  # type: ignore[return-value]

    async def get_personas_by_niche(self, niche_id: str | UUID) -> list[PersonaModel]:
        """
        Get all personas for a niche.

        Args:
            niche_id: Niche UUID

        Returns:
            List of PersonaModel
        """
        if isinstance(niche_id, str):
            niche_id = UUID(niche_id)

        result = await self.session.execute(
            select(PersonaModel).where(PersonaModel.niche_id == niche_id)
        )
        return list(result.scalars().all())

    async def update_persona(
        self,
        persona_id: str | UUID,
        **updates: Any,
    ) -> PersonaModel | None:
        """
        Update persona fields.

        Args:
            persona_id: Persona UUID
            **updates: Fields to update

        Returns:
            Updated PersonaModel or None if not found
        """
        persona = await self.get_persona(persona_id)
        if not persona:
            return None

        for key, value in updates.items():
            if hasattr(persona, key):
                setattr(persona, key, value)

        await self.session.flush()
        await self.session.refresh(persona)

        logger.info(f"Updated persona: {persona_id}")
        return persona

    # =========================================================================
    # Persona Research Data
    # =========================================================================

    async def create_persona_research_data(
        self,
        persona_id: str | UUID,
        research_type: str,
        key_phrases: list[str] | None = None,
        pain_point_triggers: list[str] | None = None,
        common_objections: list[str] | None = None,
        successful_angles: list[str] | None = None,
        data_sources: list[str] | None = None,
        source_urls: list[str] | None = None,
        confidence_score: float | None = None,
    ) -> PersonaResearchDataModel:
        """
        Create persona research data record.

        Args:
            persona_id: Parent persona UUID
            research_type: Type of research (reddit, linkedin, web)
            key_phrases: Extracted key phrases
            pain_point_triggers: Pain point triggers
            common_objections: Common objections found
            successful_angles: Successful messaging angles
            data_sources: Data sources used
            source_urls: URLs of sources
            confidence_score: Confidence in research (0-1)

        Returns:
            Created PersonaResearchDataModel
        """
        if isinstance(persona_id, str):
            persona_id = UUID(persona_id)

        research = PersonaResearchDataModel(
            persona_id=persona_id,
            research_type=research_type,
            key_phrases=key_phrases or [],
            pain_point_triggers=pain_point_triggers or [],
            common_objections=common_objections or [],
            successful_angles=successful_angles or [],
            data_sources=data_sources or [],
            source_urls=source_urls or [],
            confidence_score=confidence_score,
        )
        self.session.add(research)
        await self.session.flush()
        await self.session.refresh(research)

        logger.info(f"Created research data for persona: {persona_id}")
        return research

    async def create_persona_research_data_bulk(
        self,
        research_data_list: list[dict[str, Any]],
    ) -> list[PersonaResearchDataModel]:
        """
        Create multiple research data records in bulk.

        Args:
            research_data_list: List of research data dictionaries

        Returns:
            List of created PersonaResearchDataModel instances
        """
        results = []
        for data in research_data_list:
            research = await self.create_persona_research_data(**data)
            results.append(research)

        logger.info(f"Created {len(results)} research records in bulk")
        return results

    async def get_persona_research_data(
        self, persona_id: str | UUID
    ) -> list[PersonaResearchDataModel]:
        """
        Get all research data for a persona.

        Args:
            persona_id: Persona UUID

        Returns:
            List of PersonaResearchDataModel
        """
        if isinstance(persona_id, str):
            persona_id = UUID(persona_id)

        result = await self.session.execute(
            select(PersonaResearchDataModel).where(
                PersonaResearchDataModel.persona_id == persona_id
            )
        )
        return list(result.scalars().all())

    async def get_research_data_by_persona_ids(
        self, persona_ids: list[str | UUID]
    ) -> list[PersonaResearchDataModel]:
        """
        Get research data for multiple personas.

        Args:
            persona_ids: List of persona UUIDs

        Returns:
            List of PersonaResearchDataModel
        """
        uuids = [UUID(pid) if isinstance(pid, str) else pid for pid in persona_ids]

        result = await self.session.execute(
            select(PersonaResearchDataModel).where(PersonaResearchDataModel.persona_id.in_(uuids))
        )
        return list(result.scalars().all())

    # =========================================================================
    # Convenience Methods
    # =========================================================================

    async def get_persona_full(self, persona_id: str | UUID) -> dict[str, Any] | None:
        """
        Get complete persona data including research.

        Args:
            persona_id: Persona UUID

        Returns:
            Dictionary with persona and research data
        """
        persona = await self.get_persona(persona_id)
        if not persona:
            return None

        research_data = await self.get_persona_research_data(persona_id)

        return {
            "persona": persona.to_dict(),
            "research_data": [r.to_dict() for r in research_data],
        }

    async def get_personas_full_by_niche(self, niche_id: str | UUID) -> list[dict[str, Any]]:
        """
        Get all personas with research data for a niche.

        Args:
            niche_id: Niche UUID

        Returns:
            List of dictionaries with persona and research data
        """
        personas = await self.get_personas_by_niche(niche_id)
        results = []

        for persona in personas:
            research_data = await self.get_persona_research_data(persona.id)
            results.append(
                {
                    "persona": persona.to_dict(),
                    "research_data": [r.to_dict() for r in research_data],
                }
            )

        return results

    async def commit(self) -> None:
        """Commit the current transaction."""
        await self.session.commit()

    async def rollback(self) -> None:
        """Rollback the current transaction."""
        await self.session.rollback()

"""
Niche Repository - Data access layer for niche research.

Provides CRUD operations for niches, niche_scores, and niche_research_data tables.
Used by Niche Research Agent (1.1) and downstream agents.
"""

import logging
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import (
    IndustryFitScoreModel,
    NicheModel,
    NicheResearchDataModel,
    NicheScoreModel,
)

logger = logging.getLogger(__name__)


class NicheRepository:
    """
    Repository for niche-related database operations.

    Provides methods to create, read, update niches and their associated
    scores and research data.
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize repository with database session.

        Args:
            session: SQLAlchemy async session
        """
        self.session = session

    # =========================================================================
    # Niche CRUD
    # =========================================================================

    async def create_niche(
        self,
        name: str,
        industry: list[str] | None = None,
        job_titles: list[str] | None = None,
        company_size: list[str] | None = None,
        description: str | None = None,
        pain_points: list[str] | None = None,
        value_propositions: list[str] | None = None,
        custom_fields: dict[str, Any] | None = None,
    ) -> NicheModel:
        """
        Create a new niche record.

        Args:
            name: Niche name (e.g., "SaaS Marketing Directors")
            industry: Target industries
            job_titles: Target job titles
            company_size: Target company sizes
            description: Optional description
            pain_points: Identified pain points
            value_propositions: Value propositions
            custom_fields: Additional custom data

        Returns:
            Created NicheModel instance
        """
        niche = NicheModel(
            name=name,
            description=description,
            industry=industry or [],
            job_titles=job_titles or [],
            company_size=company_size or [],
            pain_points=pain_points or [],
            value_propositions=value_propositions or [],
            custom_fields=custom_fields or {},
        )
        self.session.add(niche)
        await self.session.flush()
        await self.session.refresh(niche)

        logger.info(f"Created niche: {niche.id} - {name}")
        return niche

    async def get_niche(self, niche_id: str | UUID) -> NicheModel | None:
        """
        Get niche by ID.

        Args:
            niche_id: Niche UUID

        Returns:
            NicheModel or None if not found
        """
        if isinstance(niche_id, str):
            niche_id = UUID(niche_id)

        result = await self.session.execute(select(NicheModel).where(NicheModel.id == niche_id))
        return result.scalar_one_or_none()  # type: ignore[return-value]

    async def get_niche_by_name(self, name: str) -> NicheModel | None:
        """
        Get niche by name.

        Args:
            name: Niche name

        Returns:
            NicheModel or None if not found
        """
        result = await self.session.execute(select(NicheModel).where(NicheModel.name == name))
        return result.scalar_one_or_none()  # type: ignore[return-value]

    async def update_niche(
        self,
        niche_id: str | UUID,
        **updates: Any,
    ) -> NicheModel | None:
        """
        Update niche fields.

        Args:
            niche_id: Niche UUID
            **updates: Fields to update

        Returns:
            Updated NicheModel or None if not found
        """
        niche = await self.get_niche(niche_id)
        if not niche:
            return None

        for key, value in updates.items():
            if hasattr(niche, key):
                setattr(niche, key, value)

        await self.session.flush()
        await self.session.refresh(niche)

        logger.info(f"Updated niche: {niche_id}")
        return niche

    # =========================================================================
    # Niche Scores
    # =========================================================================

    async def create_niche_scores(
        self,
        niche_id: str | UUID,
        market_size_score: int,
        competition_score: int,
        reachability_score: int,
        value_score: int,
        overall_score: float,
        recommendation: str,
        data_sources: list[str] | None = None,
        confidence_level: float | None = None,
    ) -> NicheScoreModel:
        """
        Create niche scoring record.

        Args:
            niche_id: Parent niche UUID
            market_size_score: Market size score (0-100)
            competition_score: Competition score (0-100)
            reachability_score: Reachability score (0-100)
            value_score: Value score (0-100)
            overall_score: Overall weighted score
            recommendation: 'proceed', 'review', or 'reject'
            data_sources: List of data sources used
            confidence_level: Confidence in scores (0-1)

        Returns:
            Created NicheScoreModel instance
        """
        if isinstance(niche_id, str):
            niche_id = UUID(niche_id)

        scores = NicheScoreModel(
            niche_id=niche_id,
            market_size_score=market_size_score,
            competition_score=competition_score,
            reachability_score=reachability_score,
            value_score=value_score,
            overall_score=overall_score,
            recommendation=recommendation,
            data_sources=data_sources or [],
            confidence_level=confidence_level,
        )
        self.session.add(scores)
        await self.session.flush()
        await self.session.refresh(scores)

        logger.info(f"Created niche scores for niche: {niche_id}")
        return scores

    async def get_niche_scores(self, niche_id: str | UUID) -> NicheScoreModel | None:
        """
        Get scores for a niche.

        Args:
            niche_id: Niche UUID

        Returns:
            NicheScoreModel or None
        """
        if isinstance(niche_id, str):
            niche_id = UUID(niche_id)

        result = await self.session.execute(
            select(NicheScoreModel).where(NicheScoreModel.niche_id == niche_id)
        )
        return result.scalar_one_or_none()  # type: ignore[return-value]

    # =========================================================================
    # Niche Research Data
    # =========================================================================

    async def create_niche_research_data(
        self,
        niche_id: str | UUID,
        research_data: dict[str, Any],
    ) -> NicheResearchDataModel:
        """
        Create niche research data record.

        Args:
            niche_id: Parent niche UUID
            research_data: Dictionary of research findings

        Returns:
            Created NicheResearchDataModel instance
        """
        if isinstance(niche_id, str):
            niche_id = UUID(niche_id)

        research = NicheResearchDataModel(
            niche_id=niche_id,
            market_size_estimate=research_data.get("market_size_estimate"),
            company_count_estimate=research_data.get("company_count_estimate"),
            persona_count_estimate=research_data.get("persona_count_estimate"),
            growth_rate=research_data.get("growth_rate"),
            market_data_sources=research_data.get("market_data_sources", {}),
            competitors_found=research_data.get("competitors_found", {}),
            saturation_level=research_data.get("saturation_level"),
            differentiation_opportunities=research_data.get("differentiation_opportunities", []),
            inbox_fatigue_indicators=research_data.get("inbox_fatigue_indicators", []),
            linkedin_presence=research_data.get("linkedin_presence"),
            data_availability=research_data.get("data_availability"),
            email_findability=research_data.get("email_findability"),
            public_presence_level=research_data.get("public_presence_level"),
            data_sources_found=research_data.get("data_sources_found", {}),
            pain_points_detailed=research_data.get("pain_points_detailed", []),
            pain_intensity=research_data.get("pain_intensity"),
            pain_urgency=research_data.get("pain_urgency"),
            pain_point_quotes=research_data.get("pain_point_quotes", []),
            evidence_sources=research_data.get("evidence_sources", {}),
            has_budget_authority=research_data.get("has_budget_authority"),
            typical_budget_range=research_data.get("typical_budget_range"),
            decision_process=research_data.get("decision_process"),
            buying_triggers=research_data.get("buying_triggers", []),
            research_duration_ms=research_data.get("research_duration_ms"),
            tools_used=research_data.get("tools_used", []),
            queries_executed=research_data.get("queries_executed", []),
        )
        self.session.add(research)
        await self.session.flush()
        await self.session.refresh(research)

        logger.info(f"Created research data for niche: {niche_id}")
        return research

    async def get_niche_research_data(self, niche_id: str | UUID) -> NicheResearchDataModel | None:
        """
        Get research data for a niche.

        Args:
            niche_id: Niche UUID

        Returns:
            NicheResearchDataModel or None
        """
        if isinstance(niche_id, str):
            niche_id = UUID(niche_id)

        result = await self.session.execute(
            select(NicheResearchDataModel).where(NicheResearchDataModel.niche_id == niche_id)
        )
        return result.scalar_one_or_none()  # type: ignore[return-value]

    # =========================================================================
    # Industry Fit Scores
    # =========================================================================

    async def create_industry_fit_score(
        self,
        niche_id: str | UUID,
        industry: str,
        fit_score: int,
        reasoning: str | None = None,
        pain_point_alignment: list[str] | None = None,
    ) -> IndustryFitScoreModel:
        """
        Create industry fit score.

        Args:
            niche_id: Parent niche UUID
            industry: Industry name
            fit_score: Fit score (0-100)
            reasoning: Why this score
            pain_point_alignment: Aligned pain points

        Returns:
            Created IndustryFitScoreModel
        """
        if isinstance(niche_id, str):
            niche_id = UUID(niche_id)

        score = IndustryFitScoreModel(
            niche_id=niche_id,
            industry=industry,
            fit_score=fit_score,
            reasoning=reasoning,
            pain_point_alignment=pain_point_alignment or [],
        )
        self.session.add(score)
        await self.session.flush()
        await self.session.refresh(score)

        logger.info(f"Created industry fit score: {industry} = {fit_score}")
        return score

    async def get_industry_fit_scores(self, niche_id: str | UUID) -> list[IndustryFitScoreModel]:
        """
        Get all industry fit scores for a niche.

        Args:
            niche_id: Niche UUID

        Returns:
            List of IndustryFitScoreModel
        """
        if isinstance(niche_id, str):
            niche_id = UUID(niche_id)

        result = await self.session.execute(
            select(IndustryFitScoreModel).where(IndustryFitScoreModel.niche_id == niche_id)
        )
        return list(result.scalars().all())

    # =========================================================================
    # Convenience Methods
    # =========================================================================

    async def get_niche_full(self, niche_id: str | UUID) -> dict[str, Any] | None:
        """
        Get complete niche data including scores and research.

        Args:
            niche_id: Niche UUID

        Returns:
            Dictionary with niche, scores, and research data
        """
        niche = await self.get_niche(niche_id)
        if not niche:
            return None

        scores = await self.get_niche_scores(niche_id)
        research = await self.get_niche_research_data(niche_id)
        industry_scores = await self.get_industry_fit_scores(niche_id)

        return {
            "niche": niche.to_dict(),
            "scores": scores.to_dict() if scores else None,
            "research_data": research.to_dict() if research else None,
            "industry_fit_scores": [s.to_dict() for s in industry_scores],
        }

    async def commit(self) -> None:
        """Commit the current transaction."""
        await self.session.commit()

    async def rollback(self) -> None:
        """Rollback the current transaction."""
        await self.session.rollback()

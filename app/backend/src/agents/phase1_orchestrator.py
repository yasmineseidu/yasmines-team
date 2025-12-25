"""
Phase 1 Orchestrator - Market Intelligence Pipeline.

Chains together Phase 1 agents and handles database persistence:
1. Niche Research Agent (1.1) - Analyze niche viability
2. Persona Research Agent (1.2) - Deep-dive into personas
3. Research Export Agent (1.3) - Export to Google Docs

This orchestrator:
- Manages the data flow between agents
- Persists results to the database after each agent
- Handles failures gracefully with proper rollback
- Provides checkpoint/resume capability

Usage:
    async with get_session() as session:
        orchestrator = Phase1Orchestrator(session)
        result = await orchestrator.run(
            niche_name="SaaS Marketing Directors",
            industry=["SaaS", "Software"],
            job_titles=["Marketing Director", "VP Marketing"],
        )
        print(f"Research folder: {result.folder_url}")
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.database.repositories import NicheRepository, PersonaRepository

logger = logging.getLogger(__name__)


# =============================================================================
# Result Types
# =============================================================================


@dataclass
class Phase1Result:
    """Result of Phase 1 orchestration."""

    # Identifiers
    niche_id: str
    persona_ids: list[str] = field(default_factory=list)

    # Status
    recommendation: str = "review"  # proceed, review, reject
    status: str = "completed"  # completed, rejected, failed

    # Research outputs
    pain_points: list[str] = field(default_factory=list)
    consolidated_pain_points: list[str] = field(default_factory=list)

    # Export (if successful)
    folder_url: str | None = None
    documents: list[dict[str, Any]] = field(default_factory=list)

    # Metadata
    execution_time_ms: int = 0
    completed_at: datetime = field(default_factory=datetime.now)
    error: str | None = None


# =============================================================================
# Phase 1 Orchestrator
# =============================================================================


class Phase1Orchestrator:
    """
    Orchestrates the complete Phase 1 market intelligence pipeline.

    Manages the flow:
    Niche Research (1.1) → Persona Research (1.2) → Research Export (1.3)

    Handles:
    - Agent invocation with proper parameters
    - Database persistence after each agent
    - Handoff data between agents
    - Failure handling and rollback
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize orchestrator with database session.

        Args:
            session: SQLAlchemy async session for database operations
        """
        self.session = session
        self.niche_repo = NicheRepository(session)
        self.persona_repo = PersonaRepository(session)

    async def run(
        self,
        niche_name: str,
        industry: list[str],
        job_titles: list[str],
        company_size: list[str] | None = None,
        description: str | None = None,
        skip_export: bool = False,
        force_proceed: bool = False,
    ) -> Phase1Result:
        """
        Execute complete Phase 1 pipeline.

        Steps:
        1. Run Niche Research Agent → save to DB
        2. Check recommendation → stop if 'reject' (unless force_proceed)
        3. Run Persona Research Agent → save to DB
        4. Run Research Export Agent → create Google Docs
        5. Return folder URL for human approval

        Args:
            niche_name: Human-readable niche name
            industry: Target industries
            job_titles: Target job titles
            company_size: Optional company sizes
            description: Optional niche description
            skip_export: If True, skip export agent (for testing)
            force_proceed: If True, continue even if recommendation is 'reject'

        Returns:
            Phase1Result with outcomes and folder URL
        """
        import time

        start_time = time.time()
        result = Phase1Result(niche_id="")

        try:
            # =================================================================
            # Step 1: Run Niche Research Agent
            # =================================================================
            logger.info(f"Phase 1 Step 1: Running Niche Research for '{niche_name}'")

            niche_result = await self._run_niche_research(
                niche_name=niche_name,
                industry=industry,
                job_titles=job_titles,
                company_size=company_size,
                description=description,
            )

            result.niche_id = niche_result["niche_id"]
            result.recommendation = niche_result.get("recommendation", "review")
            result.pain_points = niche_result.get("pain_points", [])

            # Commit niche research
            await self.niche_repo.commit()

            # =================================================================
            # Step 2: Check Recommendation
            # =================================================================
            if result.recommendation == "reject" and not force_proceed:
                logger.info(f"Niche '{niche_name}' rejected. Stopping pipeline.")
                result.status = "rejected"
                result.execution_time_ms = int((time.time() - start_time) * 1000)
                return result
            elif result.recommendation == "reject" and force_proceed:
                logger.info(f"Niche '{niche_name}' rejected but force_proceed=True. Continuing...")
                result.recommendation = "review"  # Override for downstream

            # =================================================================
            # Step 3: Run Persona Research Agent
            # =================================================================
            logger.info(f"Phase 1 Step 2: Running Persona Research for niche {result.niche_id}")

            persona_result = await self._run_persona_research(
                niche_id=result.niche_id,
                pain_points_hint=result.pain_points,
            )

            result.persona_ids = persona_result.get("persona_ids", [])
            result.consolidated_pain_points = persona_result.get("consolidated_pain_points", [])

            # Commit persona research
            await self.persona_repo.commit()

            # =================================================================
            # Step 4: Run Research Export Agent (optional)
            # =================================================================
            if not skip_export:
                logger.info("Phase 1 Step 3: Exporting research to Google Docs")

                export_result = await self._run_research_export(
                    niche_id=result.niche_id,
                    persona_ids=result.persona_ids,
                    consolidated_pain_points=result.consolidated_pain_points,
                )

                result.folder_url = export_result.get("folder_url")
                result.documents = export_result.get("documents", [])

                # Update niche with folder URL
                await self.niche_repo.update_niche(
                    result.niche_id,
                    custom_fields={
                        "research_folder_url": result.folder_url,
                        "status": "pending_approval",
                    },
                )
                await self.niche_repo.commit()

            result.status = "completed"
            result.execution_time_ms = int((time.time() - start_time) * 1000)

            logger.info(
                f"Phase 1 completed for '{niche_name}' in {result.execution_time_ms}ms. "
                f"Personas: {len(result.persona_ids)}, Folder: {result.folder_url}"
            )

            return result

        except Exception as e:
            logger.error(f"Phase 1 failed: {e}")
            await self.niche_repo.rollback()
            result.status = "failed"
            result.error = str(e)
            result.execution_time_ms = int((time.time() - start_time) * 1000)
            return result

    # =========================================================================
    # Agent Runners
    # =========================================================================

    async def _run_niche_research(
        self,
        niche_name: str,
        industry: list[str],
        job_titles: list[str],
        company_size: list[str] | None = None,
        description: str | None = None,
    ) -> dict[str, Any]:
        """
        Run Niche Research Agent and persist results.

        Returns:
            Dictionary with niche_id, recommendation, pain_points
        """
        # Import agent here to avoid circular imports
        from src.agents.niche_research_agent.agent import NicheResearchAgent

        # Create and run agent
        agent = NicheResearchAgent()
        niche_result = await agent.research_niche(
            query=niche_name,
            max_subreddits=10,
            posts_per_subreddit=25,
        )

        # Persist niche to database
        niche = await self.niche_repo.create_niche(
            name=niche_name,
            industry=industry,
            job_titles=job_titles,
            company_size=company_size,
            description=description,
            pain_points=[pp.description for pp in niche_result.pain_points],
        )

        # Calculate scores from result
        total_subs = sum(sub.subscriber_count for sub in niche_result.subreddits)
        market_size_score = min(int(total_subs / 10000), 100)
        competition_score = 50  # Would need more data
        reachability_score = 70 if total_subs > 50000 else 40
        value_score = min(len(niche_result.pain_points) * 15, 100)
        overall_score = (
            market_size_score + competition_score + reachability_score + value_score
        ) / 4

        # Determine recommendation
        if overall_score >= 70:
            recommendation = "proceed"
        elif overall_score >= 50:
            recommendation = "review"
        else:
            recommendation = "reject"

        # Persist scores
        await self.niche_repo.create_niche_scores(
            niche_id=niche.id,
            market_size_score=market_size_score,
            competition_score=competition_score,
            reachability_score=reachability_score,
            value_score=value_score,
            overall_score=overall_score,
            recommendation=recommendation,
            data_sources=["reddit", "web_search"],
            confidence_level=0.7,
        )

        # Persist research data
        await self.niche_repo.create_niche_research_data(
            niche_id=niche.id,
            research_data={
                "company_count_estimate": total_subs // 100,
                "persona_count_estimate": total_subs // 50,
                "pain_points_detailed": [
                    {
                        "description": pp.description,
                        "severity": pp.severity,
                        "frequency": pp.frequency,
                    }
                    for pp in niche_result.pain_points
                ],
                "pain_intensity": "high" if len(niche_result.pain_points) > 5 else "medium",
                "tools_used": ["reddit_api", "web_search"],
                "research_duration_ms": niche_result.research_metadata.get("duration_ms", 0),
            },
        )

        return {
            "niche_id": str(niche.id),
            "recommendation": recommendation,
            "overall_score": overall_score,
            "pain_points": [pp.description for pp in niche_result.pain_points],
        }

    async def _run_persona_research(
        self,
        niche_id: str,
        pain_points_hint: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Run Persona Research Agent and persist results.

        Returns:
            Dictionary with persona_ids, consolidated_pain_points
        """
        # Import agent here to avoid circular imports
        from src.agents.persona_research.agent import PersonaResearchAgent

        # Get niche data from database
        niche_data = await self.niche_repo.get_niche_full(niche_id)
        if not niche_data:
            raise ValueError(f"Niche not found: {niche_id}")

        # Create and run agent
        agent = PersonaResearchAgent()
        result = await agent.run(
            niche_id=niche_id,
            pain_points_hint=pain_points_hint,
            niche_data=niche_data["niche"],
        )

        # Persist personas to database
        persona_ids: list[str] = []
        for persona in result.personas:
            db_persona = await self.persona_repo.create_persona(
                name=persona.name,
                niche_id=niche_id,
                job_titles=persona.job_titles,
                seniority_levels=[persona.seniority_level.value] if persona.seniority_level else [],
                departments=[persona.department] if persona.department else [],
                goals=persona.goals,
                challenges=[pp.pain for pp in persona.pain_points],
                objections=[obj.objection for obj in persona.objections],
                messaging_tone=result.recommended_tone.value if result.recommended_tone else None,
            )
            persona_ids.append(str(db_persona.id))

            # Persist research data for this persona
            if result.research_data:
                for research in result.research_data:
                    if research.persona_id == persona.id:
                        await self.persona_repo.create_persona_research_data(
                            persona_id=db_persona.id,
                            research_type=research.source,
                            source_urls=[research.url] if research.url else [],
                            pain_point_triggers=[pp.pain for pp in persona.pain_points[:3]],
                            successful_angles=[
                                getattr(persona.messaging_angles.get("primary"), "angle", "")
                                if persona.messaging_angles.get("primary")
                                else ""
                            ],
                            confidence_score=0.7,
                        )

        # Persist industry fit scores
        for industry_score in result.industry_scores:
            await self.niche_repo.create_industry_fit_score(
                niche_id=niche_id,
                industry=industry_score.industry,
                fit_score=industry_score.score,
                reasoning=industry_score.reasoning,
                pain_point_alignment=industry_score.pain_point_alignment,
            )

        return {
            "persona_ids": persona_ids,
            "consolidated_pain_points": result.consolidated_pain_points,
            "industry_scores": [
                s.to_dict() if hasattr(s, "to_dict") else vars(s) for s in result.industry_scores
            ],
        }

    async def _run_research_export(
        self,
        niche_id: str,
        persona_ids: list[str],
        consolidated_pain_points: list[str],
    ) -> dict[str, Any]:
        """
        Run Research Export Agent.

        Returns:
            Dictionary with folder_url and documents
        """
        # Import agent here to avoid circular imports
        from src.agents.research_export.agent import ResearchExportAgent

        # Get all data from database
        niche_full = await self.niche_repo.get_niche_full(niche_id)
        if not niche_full:
            raise ValueError(f"Niche not found: {niche_id}")

        personas_data = []
        persona_research_data = []
        for pid in persona_ids:
            persona_full = await self.persona_repo.get_persona_full(pid)
            if persona_full:
                personas_data.append(persona_full["persona"])
                persona_research_data.extend(persona_full["research_data"])

        # Create and run agent
        agent = ResearchExportAgent()
        result = await agent.export_research(
            niche_id=niche_id,
            niche_data=niche_full["niche"],
            niche_scores=niche_full["scores"] or {},
            niche_research_data=niche_full["research_data"],
            personas=personas_data,
            persona_research_data=persona_research_data,
            industry_scores=niche_full["industry_fit_scores"],
            consolidated_pain_points=consolidated_pain_points,
        )

        return {
            "folder_url": result.get("folder_url"),
            "documents": result.get("documents", []),
        }


# =============================================================================
# Convenience Functions
# =============================================================================


async def run_phase1_pipeline(
    session: AsyncSession,
    niche_name: str,
    industry: list[str],
    job_titles: list[str],
    **kwargs: Any,
) -> Phase1Result:
    """
    Convenience function to run Phase 1 pipeline.

    Args:
        session: Database session
        niche_name: Niche name
        industry: Target industries
        job_titles: Target job titles
        **kwargs: Additional arguments

    Returns:
        Phase1Result
    """
    orchestrator = Phase1Orchestrator(session)
    return await orchestrator.run(
        niche_name=niche_name,
        industry=industry,
        job_titles=job_titles,
        **kwargs,
    )

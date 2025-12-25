"""
Summary builder for Import Finalizer Agent.

Compiles comprehensive import statistics from campaign data.
"""

import logging
from typing import Any

from src.agents.import_finalizer.schemas import (
    CampaignData,
    DeduplicationSummary,
    ImportSummary,
    NicheData,
    ScoringSummary,
    ScrapingSummary,
    TierBreakdown,
    ValidationSummary,
)

logger = logging.getLogger(__name__)


def build_scraping_summary(campaign: CampaignData) -> ScrapingSummary:
    """
    Build scraping summary section.

    Args:
        campaign: Campaign data from database.

    Returns:
        ScrapingSummary with lead scraping statistics.
    """
    total_scraped = campaign.total_leads_scraped
    cost_per_lead = campaign.scraping_cost / total_scraped if total_scraped > 0 else 0.0

    return ScrapingSummary(
        target_leads=campaign.target_leads,
        total_scraped=total_scraped,
        scraping_cost=campaign.scraping_cost,
        cost_per_lead=cost_per_lead,
    )


def build_validation_summary(campaign: CampaignData) -> ValidationSummary:
    """
    Build validation summary section.

    Args:
        campaign: Campaign data from database.

    Returns:
        ValidationSummary with validation statistics.
    """
    total_checked = campaign.total_leads_valid + campaign.total_leads_invalid
    validity_rate = campaign.total_leads_valid / total_checked if total_checked > 0 else 0.0

    return ValidationSummary(
        total_valid=campaign.total_leads_valid,
        total_invalid=campaign.total_leads_invalid,
        validity_rate=validity_rate,
    )


def build_dedup_summary(campaign: CampaignData) -> DeduplicationSummary:
    """
    Build deduplication summary section.

    Args:
        campaign: Campaign data from database.

    Returns:
        DeduplicationSummary with deduplication statistics.
    """
    return DeduplicationSummary(
        within_campaign_dupes=campaign.total_duplicates_found,
        cross_campaign_dupes=campaign.total_cross_duplicates,
        available_after_dedup=campaign.total_leads_available,
    )


def build_scoring_summary(campaign: CampaignData) -> ScoringSummary:
    """
    Build scoring summary section.

    Args:
        campaign: Campaign data from database.

    Returns:
        ScoringSummary with scoring statistics.
    """
    tier_breakdown = TierBreakdown(
        tier_a=campaign.leads_tier_a,
        tier_b=campaign.leads_tier_b,
        tier_c=campaign.leads_tier_c,
        tier_d=0,
    )

    return ScoringSummary(
        total_scored=campaign.leads_scored,
        avg_score=campaign.avg_lead_score,
        tier_breakdown=tier_breakdown,
    )


def build_full_summary(
    campaign: CampaignData,
    niche: NicheData | None = None,
) -> ImportSummary:
    """
    Build complete import summary from campaign data.

    Args:
        campaign: Campaign data from database.
        niche: Optional niche data for context.

    Returns:
        ImportSummary with all sections.
    """
    logger.info(f"Building import summary for campaign {campaign.id}")

    scraping = build_scraping_summary(campaign)
    validation = build_validation_summary(campaign)
    deduplication = build_dedup_summary(campaign)
    scoring = build_scoring_summary(campaign)

    niche_name = niche.name if niche else "Unknown"

    summary = ImportSummary(
        campaign_id=campaign.id,
        campaign_name=campaign.name,
        niche_name=niche_name,
        scraping=scraping,
        validation=validation,
        deduplication=deduplication,
        scoring=scoring,
    )

    logger.info(
        f"Summary built: {summary.total_available} leads available, "
        f"Tier A: {scoring.tier_breakdown.tier_a}, "
        f"Tier B: {scoring.tier_breakdown.tier_b}"
    )

    return summary


def build_summary_from_dict(
    campaign_data: dict[str, Any],
    niche_data: dict[str, Any] | None = None,
) -> ImportSummary:
    """
    Build import summary from raw dictionary data.

    Convenience function for building summary from database query results.

    Args:
        campaign_data: Raw campaign data dictionary.
        niche_data: Optional raw niche data dictionary.

    Returns:
        ImportSummary with all sections.
    """
    campaign = CampaignData.from_dict(campaign_data)
    niche = NicheData.from_dict(niche_data) if niche_data else None
    return build_full_summary(campaign, niche)


def format_summary_for_display(summary: ImportSummary) -> str:
    """
    Format summary for text display (logs, notifications).

    Args:
        summary: The import summary to format.

    Returns:
        Formatted text representation.
    """
    lines = [
        f"=== Import Summary for {summary.campaign_name} ===",
        f"Niche: {summary.niche_name}",
        "",
        "SCRAPING:",
        f"  Target: {summary.scraping.target_leads:,}",
        f"  Scraped: {summary.scraping.total_scraped:,}",
        f"  Cost: ${summary.scraping.scraping_cost:.2f}",
        f"  Cost/Lead: ${summary.scraping.cost_per_lead:.4f}",
        "",
        "VALIDATION:",
        f"  Valid: {summary.validation.total_valid:,}",
        f"  Invalid: {summary.validation.total_invalid:,}",
        f"  Rate: {summary.validation.validity_rate:.1%}",
        "",
        "DEDUPLICATION:",
        f"  Within-Campaign: {summary.deduplication.within_campaign_dupes:,}",
        f"  Cross-Campaign: {summary.deduplication.cross_campaign_dupes:,}",
        f"  Available: {summary.deduplication.available_after_dedup:,}",
        "",
        "SCORING:",
        f"  Scored: {summary.scoring.total_scored:,}",
        f"  Avg Score: {summary.scoring.avg_score:.1f}",
        f"  Tier A: {summary.scoring.tier_breakdown.tier_a:,}",
        f"  Tier B: {summary.scoring.tier_breakdown.tier_b:,}",
        f"  Tier C: {summary.scoring.tier_breakdown.tier_c:,}",
        "",
        f"TOTAL AVAILABLE: {summary.total_available:,} leads",
    ]
    return "\n".join(lines)

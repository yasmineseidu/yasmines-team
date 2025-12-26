"""
SQLAlchemy models for database tables.

Defines ORM models for approval workflow and other database entities.
"""

from typing import Any

from sqlalchemy import (
    ARRAY,
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):  # type: ignore[misc]
    """Base class for all SQLAlchemy models."""

    pass


# Enum values for database
APPROVAL_STATUS_VALUES = ("pending", "approved", "disapproved", "editing", "expired", "cancelled")
APPROVAL_CONTENT_TYPE_VALUES = ("budget", "document", "content", "custom")
APPROVAL_ACTION_VALUES = ("approve", "disapprove", "edit", "cancel", "expire", "resubmit", "notify")


class ApprovalRequestModel(Base):
    """
    SQLAlchemy model for approval_requests table.

    Stores approval request data including Telegram message references.
    """

    __tablename__ = "approval_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    content_type = Column(
        Enum(*APPROVAL_CONTENT_TYPE_VALUES, name="approval_content_type"),
        nullable=False,
        default="custom",
    )
    status = Column(
        Enum(*APPROVAL_STATUS_VALUES, name="approval_status"),
        nullable=False,
        default="pending",
        index=True,
    )
    requester_id = Column(BigInteger, nullable=False)
    approver_id = Column(BigInteger, nullable=False, index=True)
    telegram_chat_id = Column(BigInteger, nullable=False)
    telegram_message_id = Column(BigInteger, nullable=True, index=True)
    data = Column(JSONB, nullable=False, default=dict)
    edit_token = Column(String(64), nullable=True, unique=True)
    edit_token_expires_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationship to history entries
    history = relationship(
        "ApprovalHistoryModel",
        back_populates="request",
        cascade="all, delete-orphan",
        order_by="ApprovalHistoryModel.created_at.desc()",
    )

    # Indexes
    __table_args__ = (
        Index("ix_approval_requests_approver_created", "approver_id", "created_at"),
        Index("ix_approval_requests_status_created", "status", "created_at"),
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "title": self.title,
            "content": self.content,
            "content_type": self.content_type,
            "status": self.status,
            "requester_id": self.requester_id,
            "approver_id": self.approver_id,
            "telegram_chat_id": self.telegram_chat_id,
            "telegram_message_id": self.telegram_message_id,
            "data": self.data or {},
            "edit_token": self.edit_token,
            "edit_token_expires_at": self.edit_token_expires_at,
            "expires_at": self.expires_at,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class ApprovalHistoryModel(Base):
    """
    SQLAlchemy model for approval_history table.

    Tracks all actions taken on approval requests for audit trail.
    """

    __tablename__ = "approval_history"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    request_id = Column(
        UUID(as_uuid=True),
        ForeignKey("approval_requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    action = Column(
        Enum(*APPROVAL_ACTION_VALUES, name="approval_action"),
        nullable=False,
    )
    actor_id = Column(BigInteger, nullable=False)
    actor_username = Column(String(255), nullable=True)
    comment = Column(Text, nullable=True)
    edited_data = Column(JSONB, nullable=True)
    previous_status = Column(
        Enum(*APPROVAL_STATUS_VALUES, name="approval_status", create_type=False),
        nullable=True,
    )
    new_status = Column(
        Enum(*APPROVAL_STATUS_VALUES, name="approval_status", create_type=False),
        nullable=True,
    )
    telegram_callback_query_id = Column(String(255), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Relationship to request
    request = relationship("ApprovalRequestModel", back_populates="history")

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "request_id": str(self.request_id),
            "action": self.action,
            "actor_id": self.actor_id,
            "actor_username": self.actor_username,
            "comment": self.comment,
            "edited_data": self.edited_data,
            "previous_status": self.previous_status,
            "new_status": self.new_status,
            "telegram_callback_query_id": self.telegram_callback_query_id,
            "created_at": self.created_at,
        }


# =============================================================================
# Phase 1: Market Intelligence Models
# =============================================================================


class NicheModel(Base):
    """
    SQLAlchemy model for niches table.

    Stores niche definitions including target industry, job titles,
    and identified pain points.
    """

    __tablename__ = "niches"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    industry = Column(ARRAY(Text), nullable=True)
    company_size = Column(ARRAY(Text), nullable=True)
    job_titles = Column(ARRAY(Text), nullable=True)
    pain_points = Column(ARRAY(Text), nullable=True)
    value_propositions = Column(ARRAY(Text), nullable=True)
    market_size = Column(String(100), nullable=True)
    competition_level = Column(String(50), nullable=True)
    avg_deal_size = Column(Numeric, nullable=True)
    tags = Column(ARRAY(Text), nullable=True, server_default="{}")
    custom_fields = Column(JSONB, nullable=True, server_default="{}")
    created_at = Column(DateTime(timezone=True), nullable=True, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=True, server_default=func.now())

    # Relationships
    scores = relationship("NicheScoreModel", back_populates="niche", uselist=False)
    research_data = relationship("NicheResearchDataModel", back_populates="niche", uselist=False)
    industry_fit_scores = relationship("IndustryFitScoreModel", back_populates="niche")

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for agent consumption."""
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "industry": self.industry or [],
            "company_size": self.company_size or [],
            "job_titles": self.job_titles or [],
            "pain_points": self.pain_points or [],
            "value_propositions": self.value_propositions or [],
            "market_size": self.market_size,
            "competition_level": self.competition_level,
            "avg_deal_size": float(self.avg_deal_size) if self.avg_deal_size else None,
            "tags": self.tags or [],
            "custom_fields": self.custom_fields or {},
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class NicheScoreModel(Base):
    """
    SQLAlchemy model for niche_scores table.

    Stores scoring breakdown for niche viability assessment.
    """

    __tablename__ = "niche_scores"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    niche_id = Column(
        UUID(as_uuid=True),
        ForeignKey("niches.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    market_size_score = Column(Integer, nullable=False)
    competition_score = Column(Integer, nullable=False)
    reachability_score = Column(Integer, nullable=False)
    value_score = Column(Integer, nullable=False)
    overall_score = Column(Numeric, nullable=False)
    recommendation = Column(Text, nullable=False)  # 'proceed', 'review', 'reject'
    data_sources = Column(ARRAY(Text), nullable=True, server_default="{}")
    confidence_level = Column(Numeric, nullable=True)
    researched_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Relationship
    niche = relationship("NicheModel", back_populates="scores")

    __table_args__ = (Index("ix_niche_scores_niche_id", "niche_id"),)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "niche_id": str(self.niche_id),
            "market_size_score": self.market_size_score,
            "competition_score": self.competition_score,
            "reachability_score": self.reachability_score,
            "value_score": self.value_score,
            "overall_score": float(self.overall_score) if self.overall_score else 0,
            "recommendation": self.recommendation,
            "data_sources": self.data_sources or [],
            "confidence_level": float(self.confidence_level) if self.confidence_level else None,
            "researched_at": self.researched_at,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class NicheResearchDataModel(Base):
    """
    SQLAlchemy model for niche_research_data table.

    Stores comprehensive research findings from niche analysis.
    """

    __tablename__ = "niche_research_data"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    niche_id = Column(
        UUID(as_uuid=True),
        ForeignKey("niches.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    # Market Size Research
    market_size_estimate = Column(Text, nullable=True)
    company_count_estimate = Column(Integer, nullable=True)
    persona_count_estimate = Column(Integer, nullable=True)
    growth_rate = Column(Text, nullable=True)
    market_data_sources = Column(JSONB, nullable=True, server_default="{}")

    # Competition Research
    competitors_found = Column(JSONB, nullable=True, server_default="{}")
    saturation_level = Column(Text, nullable=True)
    differentiation_opportunities = Column(JSONB, nullable=True, server_default="[]")
    inbox_fatigue_indicators = Column(JSONB, nullable=True, server_default="[]")

    # Reachability Research
    linkedin_presence = Column(Text, nullable=True)
    data_availability = Column(Text, nullable=True)
    email_findability = Column(Text, nullable=True)
    public_presence_level = Column(Text, nullable=True)
    data_sources_found = Column(JSONB, nullable=True, server_default="{}")

    # Pain Points Research
    pain_points_detailed = Column(JSONB, nullable=True, server_default="[]")
    pain_intensity = Column(Text, nullable=True)
    pain_urgency = Column(Text, nullable=True)
    pain_point_quotes = Column(JSONB, nullable=True, server_default="[]")
    evidence_sources = Column(JSONB, nullable=True, server_default="{}")

    # Budget Authority Research
    has_budget_authority = Column(Boolean, nullable=True)
    typical_budget_range = Column(Text, nullable=True)
    decision_process = Column(Text, nullable=True)
    buying_triggers = Column(JSONB, nullable=True, server_default="[]")

    # Meta
    research_duration_ms = Column(Integer, nullable=True)
    tools_used = Column(JSONB, nullable=True, server_default="[]")
    queries_executed = Column(JSONB, nullable=True, server_default="[]")
    created_at = Column(DateTime(timezone=True), nullable=True, server_default=func.now())

    # Relationship
    niche = relationship("NicheModel", back_populates="research_data")

    __table_args__ = (Index("ix_niche_research_data_niche_id", "niche_id"),)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "niche_id": str(self.niche_id),
            "market_size_estimate": self.market_size_estimate,
            "company_count_estimate": self.company_count_estimate,
            "persona_count_estimate": self.persona_count_estimate,
            "growth_rate": self.growth_rate,
            "market_data_sources": self.market_data_sources or {},
            "competitors_found": self.competitors_found or {},
            "saturation_level": self.saturation_level,
            "differentiation_opportunities": self.differentiation_opportunities or [],
            "inbox_fatigue_indicators": self.inbox_fatigue_indicators or [],
            "linkedin_presence": self.linkedin_presence,
            "data_availability": self.data_availability,
            "email_findability": self.email_findability,
            "public_presence_level": self.public_presence_level,
            "data_sources_found": self.data_sources_found or {},
            "pain_points_detailed": self.pain_points_detailed or [],
            "pain_intensity": self.pain_intensity,
            "pain_urgency": self.pain_urgency,
            "pain_point_quotes": self.pain_point_quotes or [],
            "evidence_sources": self.evidence_sources or {},
            "has_budget_authority": self.has_budget_authority,
            "typical_budget_range": self.typical_budget_range,
            "decision_process": self.decision_process,
            "buying_triggers": self.buying_triggers or [],
            "research_duration_ms": self.research_duration_ms,
            "tools_used": self.tools_used or [],
            "queries_executed": self.queries_executed or [],
            "created_at": self.created_at,
        }


class PersonaModel(Base):
    """
    SQLAlchemy model for personas table.

    Stores buyer persona definitions with pain points and messaging.
    """

    __tablename__ = "personas"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    niche_id = Column(
        UUID(as_uuid=True),
        ForeignKey("niches.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    job_titles = Column(ARRAY(Text), nullable=True)
    seniority_levels = Column(ARRAY(Text), nullable=True)
    departments = Column(ARRAY(Text), nullable=True)
    company_sizes = Column(ARRAY(Text), nullable=True)
    industries = Column(ARRAY(Text), nullable=True)
    goals = Column(ARRAY(Text), nullable=True)
    challenges = Column(ARRAY(Text), nullable=True)  # This is pain_points in agent code
    motivations = Column(ARRAY(Text), nullable=True)
    objections = Column(ARRAY(Text), nullable=True)
    preferred_channels = Column(ARRAY(Text), nullable=True)
    messaging_tone = Column(String(50), nullable=True)
    value_propositions = Column(ARRAY(Text), nullable=True)
    tags = Column(ARRAY(Text), nullable=True, server_default="{}")
    custom_fields = Column(JSONB, nullable=True, server_default="{}")
    created_at = Column(DateTime(timezone=True), nullable=True, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=True, server_default=func.now())

    # Relationships
    niche = relationship("NicheModel", backref="personas")
    research_data = relationship("PersonaResearchDataModel", back_populates="persona")

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for agent consumption."""
        return {
            "id": str(self.id),
            "niche_id": str(self.niche_id) if self.niche_id else None,
            "name": self.name,
            "description": self.description,
            "job_titles": self.job_titles or [],
            "seniority_levels": self.seniority_levels or [],
            "departments": self.departments or [],
            "company_sizes": self.company_sizes or [],
            "industries": self.industries or [],
            "goals": self.goals or [],
            "challenges": self.challenges or [],
            "pain_points": self.challenges or [],  # Alias for agent compatibility
            "motivations": self.motivations or [],
            "objections": self.objections or [],
            "preferred_channels": self.preferred_channels or [],
            "messaging_tone": self.messaging_tone,
            "value_propositions": self.value_propositions or [],
            "tags": self.tags or [],
            "custom_fields": self.custom_fields or {},
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class PersonaResearchDataModel(Base):
    """
    SQLAlchemy model for persona_research_data table.

    Stores raw research data collected during persona research for audit trail.
    """

    __tablename__ = "persona_research_data"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    persona_id = Column(
        UUID(as_uuid=True),
        ForeignKey("personas.id", ondelete="CASCADE"),
        nullable=False,
    )
    research_type = Column(String(50), nullable=False)  # reddit, linkedin, web
    key_phrases = Column(ARRAY(Text), nullable=True, server_default="{}")
    pain_point_triggers = Column(ARRAY(Text), nullable=True, server_default="{}")
    common_objections = Column(ARRAY(Text), nullable=True, server_default="{}")
    successful_angles = Column(ARRAY(Text), nullable=True, server_default="{}")
    data_sources = Column(ARRAY(Text), nullable=True, server_default="{}")
    source_urls = Column(ARRAY(Text), nullable=True, server_default="{}")
    confidence_score = Column(Numeric, nullable=True)
    researched_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Relationship
    persona = relationship("PersonaModel", back_populates="research_data")

    __table_args__ = (Index("ix_persona_research_data_persona_id", "persona_id"),)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "persona_id": str(self.persona_id),
            "research_type": self.research_type,
            "key_phrases": self.key_phrases or [],
            "pain_point_triggers": self.pain_point_triggers or [],
            "common_objections": self.common_objections or [],
            "successful_angles": self.successful_angles or [],
            "data_sources": self.data_sources or [],
            "source_urls": self.source_urls or [],
            "confidence_score": float(self.confidence_score) if self.confidence_score else None,
            "researched_at": self.researched_at,
            "created_at": self.created_at,
        }


class IndustryFitScoreModel(Base):
    """
    SQLAlchemy model for industry_fit_scores table.

    Stores industry fit scores for lead scoring.
    """

    __tablename__ = "industry_fit_scores"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    niche_id = Column(
        UUID(as_uuid=True),
        ForeignKey("niches.id", ondelete="CASCADE"),
        nullable=True,
    )
    industry = Column(String(255), nullable=False)
    fit_score = Column(Integer, nullable=False)
    reasoning = Column(Text, nullable=True)
    pain_point_alignment = Column(ARRAY(Text), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Relationship
    niche = relationship("NicheModel", back_populates="industry_fit_scores")

    __table_args__ = (
        Index("ix_industry_fit_scores_niche_id", "niche_id"),
        Index("ix_industry_fit_scores_niche_industry", "niche_id", "industry", unique=True),
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "niche_id": str(self.niche_id) if self.niche_id else None,
            "industry": self.industry,
            "fit_score": self.fit_score,
            "reasoning": self.reasoning,
            "pain_point_alignment": self.pain_point_alignment or [],
            "created_at": self.created_at,
        }


# =============================================================================
# Phase 2: Lead Acquisition Models
# =============================================================================

# Enum values for Phase 2
CAMPAIGN_STATUS_VALUES = (
    "draft",
    "building",
    "leads_scraped",
    "validated",
    "deduplicated",
    "cross_deduplicated",
    "scored",
    "import_complete",
    "leads_approved",
    "leads_rejected",
    "active",
    "paused",
    "completed",
)

LEAD_STATUS_VALUES = (
    "new",
    "validated",
    "invalid",
    "duplicate",
    "cross_campaign_duplicate",
    "scored",
    "enriched",
    "verified",
    "ready",
    "contacted",
    "replied",
    "converted",
    "bounced",
    "unsubscribed",
)

LEAD_TIER_VALUES = ("A", "B", "C", "D")


class CampaignModel(Base):
    """
    SQLAlchemy model for campaigns table.

    Stores campaign data including Phase 2 lead acquisition metrics.
    """

    __tablename__ = "campaigns"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    niche_id = Column(UUID(as_uuid=True), ForeignKey("niches.id"), nullable=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(50), nullable=True, default="draft", index=True)

    # Target settings
    target_leads = Column(Integer, nullable=True, default=50000)

    # Phase 2: Lead Scraping (Agent 2.1)
    total_leads_scraped = Column(Integer, nullable=True, default=0)
    scraping_cost = Column(Numeric(10, 2), nullable=True, default=0)

    # Phase 2: Validation (Agent 2.2)
    total_leads_valid = Column(Integer, nullable=True, default=0)
    total_leads_invalid = Column(Integer, nullable=True, default=0)
    validation_completed_at = Column(DateTime(timezone=True), nullable=True)

    # Phase 2: Deduplication (Agent 2.3)
    total_duplicates_found = Column(Integer, nullable=True, default=0)
    total_leads_unique = Column(Integer, nullable=True, default=0)
    dedup_completed_at = Column(DateTime(timezone=True), nullable=True)

    # Phase 2: Cross-Campaign Dedup (Agent 2.4)
    total_cross_duplicates = Column(Integer, nullable=True, default=0)
    total_leads_available = Column(Integer, nullable=True, default=0)
    cross_dedup_completed_at = Column(DateTime(timezone=True), nullable=True)

    # Phase 2: Scoring (Agent 2.5)
    leads_scored = Column(Integer, nullable=True, default=0)
    avg_lead_score = Column(Numeric(5, 2), nullable=True, default=0)
    leads_tier_a = Column(Integer, nullable=True, default=0)
    leads_tier_b = Column(Integer, nullable=True, default=0)
    leads_tier_c = Column(Integer, nullable=True, default=0)
    scoring_completed_at = Column(DateTime(timezone=True), nullable=True)

    # Phase 2: Import Finalization (Agent 2.6)
    lead_list_url = Column(Text, nullable=True)
    import_summary = Column(JSONB, nullable=True, server_default="{}")
    import_completed_at = Column(DateTime(timezone=True), nullable=True)
    leads_approved_at = Column(DateTime(timezone=True), nullable=True)
    leads_approved_by = Column(String(255), nullable=True)

    # Phase 3: Verification (Agent 3.3)
    verified_lead_list_url = Column(Text, nullable=True)
    verification_summary = Column(JSONB, nullable=True, server_default="{}")
    total_leads_ready = Column(Integer, nullable=True)

    # Phase 4: Personalization (Agent 4.4)
    email_samples_url = Column(Text, nullable=True)
    personalization_summary = Column(JSONB, nullable=True, server_default="{}")
    total_emails_generated = Column(Integer, nullable=True)
    avg_email_quality = Column(Numeric(precision=5, scale=2), nullable=True)
    personalization_completed_at = Column(DateTime(timezone=True), nullable=True)

    # Phase 5: Sending
    sending_status = Column(String(50), nullable=True)
    setup_completed_at = Column(DateTime(timezone=True), nullable=True)
    sending_approved_at = Column(DateTime(timezone=True), nullable=True)
    sending_approved_by = Column(String(255), nullable=True)
    sending_scope = Column(String(50), nullable=True)
    leads_queued = Column(Integer, nullable=True)

    # Niche name (denormalized for convenience)
    niche_name = Column(String(255), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=True, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=True, server_default=func.now())

    # Relationships
    niche = relationship("NicheModel", backref="campaigns")
    leads = relationship("LeadModel", back_populates="campaign", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_campaigns_niche_id", "niche_id"),
        Index("ix_campaigns_status", "status"),
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "niche_id": str(self.niche_id) if self.niche_id else None,
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "target_leads": self.target_leads,
            "total_leads_scraped": self.total_leads_scraped,
            "scraping_cost": float(self.scraping_cost) if self.scraping_cost else 0,
            "total_leads_valid": self.total_leads_valid,
            "total_leads_invalid": self.total_leads_invalid,
            "total_duplicates_found": self.total_duplicates_found,
            "total_leads_unique": self.total_leads_unique,
            "total_cross_duplicates": self.total_cross_duplicates,
            "total_leads_available": self.total_leads_available,
            "leads_scored": self.leads_scored,
            "avg_lead_score": float(self.avg_lead_score) if self.avg_lead_score else 0,
            "leads_tier_a": self.leads_tier_a,
            "leads_tier_b": self.leads_tier_b,
            "leads_tier_c": self.leads_tier_c,
            "lead_list_url": self.lead_list_url,
            "import_summary": self.import_summary or {},
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class LeadModel(Base):
    """
    SQLAlchemy model for leads table.

    Stores lead data with Phase 2 validation, dedup, and scoring fields.
    """

    __tablename__ = "leads"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    campaign_id = Column(
        UUID(as_uuid=True),
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # Basic info
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    full_name = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True, index=True)
    phone = Column(String(50), nullable=True)

    # LinkedIn
    linkedin_url = Column(String(500), nullable=True, index=True)
    linkedin_id = Column(String(100), nullable=True)

    # Job info
    title = Column(String(255), nullable=True)  # Note: DB uses 'title', not 'job_title'
    seniority = Column(String(50), nullable=True)
    seniority_level = Column(String(50), nullable=True)
    department = Column(String(100), nullable=True)
    headline = Column(Text, nullable=True)

    # Company info
    company_name = Column(String(255), nullable=True, index=True)
    company_linkedin_url = Column(String(500), nullable=True)
    company_domain = Column(String(255), nullable=True)
    company_size = Column(String(50), nullable=True)
    company_industry = Column(String(255), nullable=True)
    industry = Column(String(255), nullable=True)

    # Location
    location = Column(String(255), nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    country = Column(String(100), nullable=True)

    # Status and tracking
    status = Column(String(50), nullable=True, default="new", index=True)
    source = Column(String(100), nullable=True)
    source_url = Column(Text, nullable=True)

    # Phase 2: Validation (Agent 2.2)
    validation_status = Column(String(50), nullable=True)
    validation_errors = Column(JSONB, nullable=True, server_default="[]")

    # Phase 2: Deduplication (Agent 2.3)
    duplicate_of = Column(UUID(as_uuid=True), ForeignKey("leads.id"), nullable=True)
    merged_from = Column(JSONB, nullable=True, server_default="[]")

    # Phase 2: Cross-Campaign Dedup (Agent 2.4)
    exclusion_reason = Column(String(100), nullable=True)
    excluded_due_to_campaign = Column(UUID(as_uuid=True), nullable=True)

    # Phase 2: Scoring (Agent 2.5)
    lead_score = Column(Integer, nullable=True)
    score_breakdown = Column(JSONB, nullable=True, server_default="{}")
    lead_tier = Column(String(1), nullable=True)
    persona_tags = Column(ARRAY(Text), nullable=True, server_default="{}")

    # Email tracking
    email_status = Column(String(50), nullable=True)
    last_contacted_at = Column(DateTime(timezone=True), nullable=True)

    # Phase 3: Enrichment (Agent 3.2 - Waterfall Enrichment)
    company_description = Column(Text, nullable=True)
    company_employee_count = Column(Integer, nullable=True)
    company_revenue_range = Column(String(50), nullable=True)
    company_founded_year = Column(Integer, nullable=True)
    company_tech_stack = Column(JSONB, nullable=True, server_default="[]")
    company_keywords = Column(JSONB, nullable=True, server_default="[]")
    enrichment_data = Column(JSONB, nullable=True, server_default="{}")
    enrichment_status = Column(String(50), nullable=True)
    enrichment_cost = Column(Numeric(precision=10, scale=2), nullable=True)
    enrichment_completed_at = Column(DateTime(timezone=True), nullable=True)

    # Phase 4: Research & Email Generation
    company_research_id = Column(UUID(as_uuid=True), nullable=True)
    lead_research_id = Column(UUID(as_uuid=True), nullable=True)
    generated_email_id = Column(UUID(as_uuid=True), nullable=True)
    email_generation_status = Column(String(50), nullable=True)

    # Phase 5: Sending
    sending_status = Column(String(50), nullable=True)
    queued_at = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=True, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=True, server_default=func.now())

    # Relationships
    campaign = relationship("CampaignModel", back_populates="leads")
    generated_email = relationship("GeneratedEmailModel", back_populates="lead", uselist=False)

    __table_args__ = (
        Index("ix_leads_campaign_id", "campaign_id"),
        Index("ix_leads_linkedin_url", "linkedin_url"),
        Index("ix_leads_email", "email"),
        Index("ix_leads_status", "status"),
        Index("ix_leads_lead_tier", "lead_tier"),
        Index("ix_leads_enrichment_status", "enrichment_status"),
        Index(
            "ix_leads_duplicate_of",
            "duplicate_of",
            postgresql_where=Column("duplicate_of").isnot(None),
        ),
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "campaign_id": str(self.campaign_id) if self.campaign_id else None,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "full_name": self.full_name,
            "email": self.email,
            "phone": self.phone,
            "linkedin_url": self.linkedin_url,
            "title": self.title,
            "job_title": self.title,  # Alias for agent compatibility
            "seniority": self.seniority,
            "department": self.department,
            "company_name": self.company_name,
            "company_domain": self.company_domain,
            "company_size": self.company_size,
            "company_industry": self.company_industry,
            "location": self.location,
            "city": self.city,
            "state": self.state,
            "country": self.country,
            "status": self.status,
            "source": self.source,
            "validation_status": self.validation_status,
            "validation_errors": self.validation_errors or [],
            "lead_score": self.lead_score,
            "score_breakdown": self.score_breakdown or {},
            "lead_tier": self.lead_tier,
            "persona_tags": self.persona_tags or [],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class DedupLogModel(Base):
    """
    SQLAlchemy model for dedup_logs table.

    Logs within-campaign deduplication runs (Agent 2.3).
    """

    __tablename__ = "dedup_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    campaign_id = Column(
        UUID(as_uuid=True),
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Counts
    total_checked = Column(Integer, nullable=False, default=0)
    exact_duplicates = Column(Integer, nullable=True, default=0)
    fuzzy_duplicates = Column(Integer, nullable=True, default=0)
    total_merged = Column(Integer, nullable=True, default=0)

    # Details
    detection_details = Column(JSONB, nullable=True, server_default="{}")

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "campaign_id": str(self.campaign_id),
            "total_checked": self.total_checked,
            "exact_duplicates": self.exact_duplicates,
            "fuzzy_duplicates": self.fuzzy_duplicates,
            "total_merged": self.total_merged,
            "detection_details": self.detection_details or {},
            "created_at": self.created_at,
        }


class CrossCampaignDedupLogModel(Base):
    """
    SQLAlchemy model for cross_campaign_dedup_logs table.

    Logs cross-campaign deduplication runs (Agent 2.4).
    """

    __tablename__ = "cross_campaign_dedup_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    campaign_id = Column(
        UUID(as_uuid=True),
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Counts
    total_checked = Column(Integer, nullable=False, default=0)
    previously_contacted = Column(Integer, nullable=True, default=0)
    bounced_excluded = Column(Integer, nullable=True, default=0)
    unsubscribed_excluded = Column(Integer, nullable=True, default=0)
    suppression_list_excluded = Column(Integer, nullable=True, default=0)
    remaining_leads = Column(Integer, nullable=False, default=0)

    # Settings
    lookback_days = Column(Integer, nullable=True, default=90)

    # Details
    detection_details = Column(JSONB, nullable=True, server_default="{}")

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "campaign_id": str(self.campaign_id),
            "total_checked": self.total_checked,
            "previously_contacted": self.previously_contacted,
            "bounced_excluded": self.bounced_excluded,
            "unsubscribed_excluded": self.unsubscribed_excluded,
            "suppression_list_excluded": self.suppression_list_excluded,
            "remaining_leads": self.remaining_leads,
            "lookback_days": self.lookback_days,
            "detection_details": self.detection_details or {},
            "created_at": self.created_at,
            "completed_at": self.completed_at,
        }


class SuppressionListModel(Base):
    """
    SQLAlchemy model for suppression_list table.

    Stores globally suppressed emails (do-not-contact list).
    """

    __tablename__ = "suppression_list"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    email = Column(String(255), nullable=False, unique=True, index=True)
    reason = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    added_by = Column(String(255), nullable=True)
    suppressed_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "email": self.email,
            "reason": self.reason,
            "notes": self.notes,
            "added_by": self.added_by,
            "suppressed_at": self.suppressed_at,
            "created_at": self.created_at,
        }


class CampaignAuditLogModel(Base):
    """
    SQLAlchemy model for campaign_audit_log table.

    Tracks all actions on campaigns for audit trail.
    """

    __tablename__ = "campaign_audit_log"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    campaign_id = Column(
        UUID(as_uuid=True),
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    action = Column(String(100), nullable=False)
    actor = Column(String(255), nullable=True)
    actor_type = Column(String(50), nullable=True)  # 'agent', 'user', 'system'
    details = Column(JSONB, nullable=True, server_default="{}")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "campaign_id": str(self.campaign_id),
            "action": self.action,
            "actor": self.actor,
            "actor_type": self.actor_type,
            "details": self.details or {},
            "created_at": self.created_at,
        }


# =============================================================================
# Phase 4: Research & Personalization Models
# =============================================================================


class CompanyResearchDataModel(Base):
    """
    SQLAlchemy model for company_research_data table.

    Stores company research results from Phase 4 Company Research Agent.
    Each record contains web search findings, news, funding, and personalization hooks.
    """

    __tablename__ = "company_research_data"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    campaign_id = Column(
        UUID(as_uuid=True),
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    company_domain = Column(String(255), nullable=False, index=True)
    company_name = Column(String(255), nullable=True)

    # Research results
    research_type = Column(String(100), nullable=True, default="company_overview")
    data_source = Column(String(100), nullable=True, default="web_search")
    headline = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)
    content = Column(JSONB, nullable=True, server_default="{}")

    # Source info
    primary_source_url = Column(Text, nullable=True)
    source_urls = Column(ARRAY(Text), nullable=True, server_default="{}")
    latest_news_date = Column(DateTime(timezone=True), nullable=True)

    # Analysis
    relevance_score = Column(Numeric(5, 4), nullable=True)
    sentiment = Column(String(50), nullable=True)
    key_insights = Column(JSONB, nullable=True, server_default="[]")
    personalization_hooks = Column(JSONB, nullable=True, server_default="[]")
    primary_hook = Column(Text, nullable=True)

    # Research categories found
    has_recent_news = Column(Boolean, nullable=True, default=False)
    has_funding = Column(Boolean, nullable=True, default=False)
    has_hiring = Column(Boolean, nullable=True, default=False)
    has_product_launch = Column(Boolean, nullable=True, default=False)

    # Cost tracking
    research_cost = Column(Numeric(10, 4), nullable=True, default=0)
    tools_used = Column(JSONB, nullable=True, server_default="[]")

    # Timestamps
    researched_at = Column(DateTime(timezone=True), nullable=True, server_default=func.now())
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Relationships
    facts = relationship(
        "ExtractedFactsModel",
        back_populates="company_research",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("idx_company_research_campaign", "campaign_id"),
        Index("idx_company_research_domain", "company_domain"),
        Index(
            "uq_company_research_campaign_domain",
            "campaign_id",
            "company_domain",
            unique=True,
        ),
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "campaign_id": str(self.campaign_id),
            "company_domain": self.company_domain,
            "company_name": self.company_name,
            "research_type": self.research_type,
            "data_source": self.data_source,
            "headline": self.headline,
            "summary": self.summary,
            "content": self.content or {},
            "primary_source_url": self.primary_source_url,
            "source_urls": self.source_urls or [],
            "latest_news_date": self.latest_news_date,
            "relevance_score": float(self.relevance_score) if self.relevance_score else None,
            "sentiment": self.sentiment,
            "key_insights": self.key_insights or [],
            "personalization_hooks": self.personalization_hooks or [],
            "primary_hook": self.primary_hook,
            "has_recent_news": self.has_recent_news,
            "has_funding": self.has_funding,
            "has_hiring": self.has_hiring,
            "has_product_launch": self.has_product_launch,
            "research_cost": float(self.research_cost) if self.research_cost else 0,
            "tools_used": self.tools_used or [],
            "researched_at": self.researched_at,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class ExtractedFactsModel(Base):
    """
    SQLAlchemy model for extracted_facts table.

    Stores individual facts extracted from company research with scoring.
    Facts are scored by recency, specificity, business relevance, and emotional hook.
    """

    __tablename__ = "extracted_facts"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    company_research_id = Column(
        UUID(as_uuid=True),
        ForeignKey("company_research_data.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    session_id = Column(String(255), nullable=True, index=True)

    # Fact content
    fact_text = Column(Text, nullable=False)
    source_type = Column(String(100), nullable=True)
    source_url = Column(Text, nullable=True)
    fact_date = Column(DateTime(timezone=True), nullable=True)
    recency_days = Column(Integer, nullable=True)

    # Categorization
    category = Column(String(100), nullable=True)  # news, funding, hiring, product, etc.

    # Scoring (weights: recency 30%, specificity 25%, business_relevance 25%, emotional 20%)
    recency_score = Column(Numeric(5, 4), nullable=True)
    specificity_score = Column(Numeric(5, 4), nullable=True)
    business_relevance_score = Column(Numeric(5, 4), nullable=True)
    emotional_hook_score = Column(Numeric(5, 4), nullable=True)
    total_score = Column(Numeric(5, 4), nullable=True)

    # Context for email writing
    context_notes = Column(Text, nullable=True)
    suggested_angle = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Relationships
    company_research = relationship("CompanyResearchDataModel", back_populates="facts")

    __table_args__ = (
        Index("idx_extracted_facts_research", "company_research_id"),
        Index("idx_extracted_facts_category", "category"),
        Index("idx_extracted_facts_score", "total_score"),
        Index("idx_extracted_facts_session", "session_id"),
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "company_research_id": str(self.company_research_id),
            "session_id": self.session_id,
            "fact_text": self.fact_text,
            "source_type": self.source_type,
            "source_url": self.source_url,
            "fact_date": self.fact_date,
            "recency_days": self.recency_days,
            "category": self.category,
            "recency_score": float(self.recency_score) if self.recency_score else None,
            "specificity_score": float(self.specificity_score) if self.specificity_score else None,
            "business_relevance_score": (
                float(self.business_relevance_score) if self.business_relevance_score else None
            ),
            "emotional_hook_score": (
                float(self.emotional_hook_score) if self.emotional_hook_score else None
            ),
            "total_score": float(self.total_score) if self.total_score else None,
            "context_notes": self.context_notes,
            "suggested_angle": self.suggested_angle,
            "created_at": self.created_at,
        }


# =============================================================================
# Workflow Checkpoint Models
# =============================================================================

CHECKPOINT_STATUS_VALUES = ("in_progress", "completed", "failed", "pending")


class WorkflowCheckpointModel(Base):
    """
    SQLAlchemy model for workflow_checkpoints table.

    Enables checkpoint/resume capability for long-running agent workflows.
    Used by Phase 1, 2, and 3 orchestrators for idempotency and recovery.
    """

    __tablename__ = "workflow_checkpoints"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())

    # Workflow identification
    workflow_id = Column(String(255), nullable=False, index=True)
    workflow_type = Column(String(100), nullable=False, index=True)

    # Agent tracking
    agent_id = Column(String(100), nullable=False, index=True)
    step_id = Column(String(100), nullable=False)

    # Status tracking
    status = Column(String(50), nullable=False, default="in_progress")

    # Data storage
    input_data = Column(JSONB, nullable=True, server_default="{}")
    output_data = Column(JSONB, nullable=True, server_default="{}")
    error_message = Column(Text, nullable=True)

    # External references
    campaign_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    niche_id = Column(UUID(as_uuid=True), nullable=True)
    apify_run_ids = Column(ARRAY(Text), nullable=True)

    # Progress tracking
    items_processed = Column(Integer, nullable=True, default=0)
    items_total = Column(Integer, nullable=True)

    # Timestamps
    started_at = Column(DateTime(timezone=True), nullable=True, server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        Index("idx_checkpoints_workflow", "workflow_id"),
        Index("idx_checkpoints_status", "status"),
        Index("idx_checkpoints_campaign", "campaign_id"),
        Index("idx_checkpoints_workflow_type", "workflow_type"),
        Index("idx_checkpoints_agent", "agent_id"),
        Index("idx_checkpoints_workflow_status", "workflow_id", "status"),
        # Unique constraint for idempotency
        Index(
            "uq_workflow_agent_step",
            "workflow_id",
            "agent_id",
            "step_id",
            unique=True,
        ),
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "workflow_id": self.workflow_id,
            "workflow_type": self.workflow_type,
            "agent_id": self.agent_id,
            "step_id": self.step_id,
            "status": self.status,
            "input_data": self.input_data or {},
            "output_data": self.output_data or {},
            "error_message": self.error_message,
            "campaign_id": str(self.campaign_id) if self.campaign_id else None,
            "niche_id": str(self.niche_id) if self.niche_id else None,
            "apify_run_ids": self.apify_run_ids or [],
            "items_processed": self.items_processed,
            "items_total": self.items_total,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


# =============================================================================
# Phase 4: Email Generation Models
# =============================================================================


class GeneratedEmailModel(Base):
    """
    SQLAlchemy model for generated_emails table.

    Stores AI-generated personalized emails from Phase 4 (Agent 4.3).
    """

    __tablename__ = "generated_emails"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    lead_id = Column(
        UUID(as_uuid=True),
        ForeignKey("leads.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    campaign_id = Column(
        UUID(as_uuid=True),
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Email content
    subject_line = Column(String(255), nullable=False)
    opening_line = Column(Text, nullable=True)
    body = Column(Text, nullable=False)
    cta = Column(Text, nullable=True)
    full_email = Column(Text, nullable=False)

    # Generation metadata
    framework_used = Column(String(50), nullable=True)
    personalization_level = Column(String(50), nullable=True)
    quality_score = Column(Integer, nullable=True)
    score_breakdown = Column(JSONB, nullable=True, server_default="{}")

    # Generation info
    generation_prompt = Column(Text, nullable=True)
    generation_model = Column(String(100), nullable=True)

    # Research references
    company_research_id = Column(UUID(as_uuid=True), nullable=True)
    lead_research_id = Column(UUID(as_uuid=True), nullable=True)

    # Timestamps
    generated_at = Column(DateTime(timezone=True), nullable=True, server_default=func.now())
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Relationships
    lead = relationship("LeadModel", back_populates="generated_email")
    campaign = relationship("CampaignModel", backref="generated_emails")

    __table_args__ = (
        Index("idx_generated_emails_lead_id", "lead_id"),
        Index("idx_generated_emails_campaign_id", "campaign_id"),
        Index("idx_generated_emails_quality_score", "quality_score"),
        Index("idx_generated_emails_campaign_quality", "campaign_id", "quality_score"),
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "lead_id": str(self.lead_id),
            "campaign_id": str(self.campaign_id),
            "subject_line": self.subject_line,
            "opening_line": self.opening_line,
            "body": self.body,
            "cta": self.cta,
            "full_email": self.full_email,
            "framework_used": self.framework_used,
            "personalization_level": self.personalization_level,
            "quality_score": self.quality_score,
            "score_breakdown": self.score_breakdown or {},
            "generation_prompt": self.generation_prompt,
            "generation_model": self.generation_model,
            "company_research_id": str(self.company_research_id)
            if self.company_research_id
            else None,
            "lead_research_id": str(self.lead_research_id) if self.lead_research_id else None,
            "generated_at": self.generated_at,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

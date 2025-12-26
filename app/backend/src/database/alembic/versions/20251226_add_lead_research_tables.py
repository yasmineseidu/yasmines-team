"""Add lead research tables for Phase 4 Agent 4.2.

Revision ID: 20251226_lead_research
Revises: 20251226_phase4_5
Create Date: 2025-12-26 12:40:00.000000

Purpose: Add tables required for Lead Research Agent (4.2):
- lead_research_data: Store research results per lead
- extracted_facts: Store individual facts with scores
- ranked_angles: Store ranked personalization angles

Adds columns to leads:
- research_depth: The research depth used (deep/standard/basic)
- research_quality_score: Quality score of research found
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

# revision identifiers, used by Alembic.
revision: str = "20251226_lead_research"
down_revision: str | None = "20251226_phase4_5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # =========================================================================
    # CREATE LEAD_RESEARCH_DATA TABLE
    # =========================================================================
    op.create_table(
        "lead_research_data",
        # Primary key
        sa.Column(
            "id",
            UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        # Foreign key to lead
        sa.Column(
            "lead_id",
            UUID(as_uuid=True),
            sa.ForeignKey("leads.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        # Research metadata
        sa.Column("research_type", sa.String(50), nullable=False, server_default="personalization"),
        sa.Column("data_source", sa.String(100), nullable=True),
        sa.Column("research_depth", sa.String(20), nullable=True),  # deep/standard/basic
        # Profile info
        sa.Column("profile_headline", sa.Text, nullable=True),
        sa.Column("recent_activity", sa.Text, nullable=True),
        sa.Column("key_interests", sa.ARRAY(sa.Text), nullable=True),
        # LinkedIn posts
        sa.Column("recent_posts", JSONB, server_default="[]"),
        # Research content
        sa.Column("headline", sa.Text, nullable=True),  # Primary hook
        sa.Column("summary", sa.Text, nullable=True),
        sa.Column("content", sa.Text, nullable=True),  # Full research content
        sa.Column("url", sa.Text, nullable=True),  # Primary source URL
        # Scoring
        sa.Column("relevance_score", sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column("quality_score", sa.Numeric(precision=5, scale=4), nullable=True),
        # Cost tracking
        sa.Column("research_cost", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column("queries_used", sa.Integer, nullable=True),
        # Timestamps
        sa.Column(
            "researched_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    # Create indexes for lead_research_data
    op.create_index("idx_lead_research_data_lead_id", "lead_research_data", ["lead_id"])
    op.create_index("idx_lead_research_data_research_type", "lead_research_data", ["research_type"])
    op.create_index("idx_lead_research_data_quality", "lead_research_data", ["quality_score"])

    # =========================================================================
    # CREATE EXTRACTED_FACTS TABLE
    # =========================================================================
    op.create_table(
        "extracted_facts",
        # Primary key
        sa.Column(
            "id",
            UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        # Foreign key to lead_research_data
        sa.Column(
            "lead_research_id",
            UUID(as_uuid=True),
            sa.ForeignKey("lead_research_data.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # Session tracking
        sa.Column("session_id", sa.String(255), nullable=True),
        # Fact content
        sa.Column("fact_text", sa.Text, nullable=False),
        sa.Column("source_type", sa.String(50), nullable=True),  # linkedin_post, article, etc.
        sa.Column("source_url", sa.Text, nullable=True),
        sa.Column("fact_date", sa.Date, nullable=True),
        sa.Column("recency_days", sa.Integer, nullable=True),
        # Categorization
        sa.Column(
            "category",
            sa.String(50),
            nullable=True,
        ),  # linkedin_post, article, podcast, talk, career_move, achievement
        # Scoring
        sa.Column("recency_score", sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column("specificity_score", sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column("business_relevance_score", sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column("emotional_hook_score", sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column("total_score", sa.Numeric(precision=5, scale=4), nullable=True),
        # Context
        sa.Column("context_notes", sa.Text, nullable=True),
        # Timestamps
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    # Create indexes for extracted_facts
    op.create_index("idx_extracted_facts_lead_research_id", "extracted_facts", ["lead_research_id"])
    op.create_index("idx_extracted_facts_category", "extracted_facts", ["category"])
    op.create_index("idx_extracted_facts_total_score", "extracted_facts", ["total_score"])
    op.create_index(
        "idx_extracted_facts_research_score",
        "extracted_facts",
        ["lead_research_id", "total_score"],
    )

    # =========================================================================
    # CREATE RANKED_ANGLES TABLE
    # =========================================================================
    op.create_table(
        "ranked_angles",
        # Primary key
        sa.Column(
            "id",
            UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        # Foreign keys
        sa.Column(
            "lead_id",
            UUID(as_uuid=True),
            sa.ForeignKey("leads.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "fact_id",
            UUID(as_uuid=True),
            sa.ForeignKey("extracted_facts.id", ondelete="CASCADE"),
            nullable=True,
        ),
        # Ranking
        sa.Column("rank_position", sa.Integer, nullable=False),
        sa.Column("angle_type", sa.String(50), nullable=True),  # linkedin_post, article, etc.
        sa.Column("angle_text", sa.Text, nullable=True),  # Generated opening line template
        # Scoring breakdown
        sa.Column("recency_score", sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column("specificity_score", sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column("business_relevance_score", sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column("emotional_hook_score", sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column("total_score", sa.Numeric(precision=5, scale=4), nullable=True),
        # Usage tracking
        sa.Column("is_fallback", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("used_in_email", sa.Boolean, nullable=False, server_default="false"),
        # Timestamps
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    # Create indexes for ranked_angles
    op.create_index("idx_ranked_angles_lead_id", "ranked_angles", ["lead_id"])
    op.create_index("idx_ranked_angles_fact_id", "ranked_angles", ["fact_id"])
    op.create_index("idx_ranked_angles_rank", "ranked_angles", ["lead_id", "rank_position"])
    op.create_index("idx_ranked_angles_total_score", "ranked_angles", ["total_score"])

    # =========================================================================
    # ADD COLUMNS TO LEADS TABLE
    # =========================================================================

    # Add research_depth column
    op.add_column(
        "leads",
        sa.Column(
            "research_depth",
            sa.String(20),
            nullable=True,
            comment="Research depth used: deep, standard, basic",
        ),
    )

    # Add research_quality_score column
    op.add_column(
        "leads",
        sa.Column(
            "research_quality_score",
            sa.Numeric(precision=5, scale=4),
            nullable=True,
            comment="Quality score of research found",
        ),
    )

    # Create index for research_depth
    op.create_index("idx_leads_research_depth", "leads", ["research_depth"])


def downgrade() -> None:
    # =========================================================================
    # DROP COLUMNS FROM LEADS TABLE
    # =========================================================================
    op.drop_index("idx_leads_research_depth", table_name="leads")
    op.drop_column("leads", "research_quality_score")
    op.drop_column("leads", "research_depth")

    # =========================================================================
    # DROP RANKED_ANGLES TABLE
    # =========================================================================
    op.drop_index("idx_ranked_angles_total_score", table_name="ranked_angles")
    op.drop_index("idx_ranked_angles_rank", table_name="ranked_angles")
    op.drop_index("idx_ranked_angles_fact_id", table_name="ranked_angles")
    op.drop_index("idx_ranked_angles_lead_id", table_name="ranked_angles")
    op.drop_table("ranked_angles")

    # =========================================================================
    # DROP EXTRACTED_FACTS TABLE
    # =========================================================================
    op.drop_index("idx_extracted_facts_research_score", table_name="extracted_facts")
    op.drop_index("idx_extracted_facts_total_score", table_name="extracted_facts")
    op.drop_index("idx_extracted_facts_category", table_name="extracted_facts")
    op.drop_index("idx_extracted_facts_lead_research_id", table_name="extracted_facts")
    op.drop_table("extracted_facts")

    # =========================================================================
    # DROP LEAD_RESEARCH_DATA TABLE
    # =========================================================================
    op.drop_index("idx_lead_research_data_quality", table_name="lead_research_data")
    op.drop_index("idx_lead_research_data_research_type", table_name="lead_research_data")
    op.drop_index("idx_lead_research_data_lead_id", table_name="lead_research_data")
    op.drop_table("lead_research_data")

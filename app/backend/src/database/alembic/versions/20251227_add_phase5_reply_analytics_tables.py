"""Add Phase 5 reply monitoring and analytics tables.

Revision ID: 20251227_phase5_reply_analytics
Revises: 20251226_lead_research
Create Date: 2025-12-27 10:00:00.000000

Purpose: Add tables required for Phase 5 agents:
- Agent 5.3 (Reply Monitoring):
  - email_replies: Store and categorize email replies
  - reply_monitoring_state: Track monitoring checkpoints
- Agent 5.4 (Campaign Analytics):
  - campaign_metrics: Store metrics snapshots
  - campaign_alerts: Track triggered alerts

Adds columns to leads:
- instantly_lead_id: ID from Instantly.ai
- reply_status: Current reply status
- replied_at: When lead replied
- reply_count: Number of replies

Adds columns to campaigns:
- total_replies: Total reply count
- interested_count: Count of interested replies
- meetings_booked: Count of meeting requests
- bounce_count: Count of bounced emails
- last_metrics_at: When metrics were last collected
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

# revision identifiers, used by Alembic.
revision: str = "20251227_phase5_reply_analytics"
down_revision: str | None = "20251226_lead_research"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # =========================================================================
    # DROP EXISTING EMAIL_REPLIES TABLE (if empty, recreate with proper schema)
    # =========================================================================
    # Note: The email_replies table may have been created manually.
    # We drop and recreate it with the proper schema.
    op.execute("DROP TABLE IF EXISTS email_replies CASCADE")

    # =========================================================================
    # CREATE EMAIL_REPLIES TABLE
    # =========================================================================
    op.create_table(
        "email_replies",
        # Primary key
        sa.Column(
            "id",
            UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        # Foreign keys
        sa.Column(
            "campaign_id",
            UUID(as_uuid=True),
            sa.ForeignKey("campaigns.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "lead_id",
            UUID(as_uuid=True),
            sa.ForeignKey("leads.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "instantly_campaign_id",
            UUID(as_uuid=True),
            sa.ForeignKey("instantly_campaigns.id", ondelete="SET NULL"),
            nullable=True,
        ),
        # Instantly.ai identifiers
        sa.Column("instantly_reply_id", sa.String(255), nullable=True, unique=True),
        sa.Column("instantly_lead_id", sa.String(255), nullable=True),
        # Reply content
        sa.Column("reply_subject", sa.String(500), nullable=True),
        sa.Column("reply_text", sa.Text, nullable=False),
        sa.Column("reply_html", sa.Text, nullable=True),
        # Classification
        sa.Column(
            "category",
            sa.String(50),
            nullable=False,
            comment="interested, meeting_request, not_interested, out_of_office, wrong_person, question, bounce",
        ),
        sa.Column(
            "confidence",
            sa.Numeric(precision=5, scale=4),
            nullable=True,
            comment="Classification confidence 0.0-1.0",
        ),
        sa.Column(
            "sentiment",
            sa.String(20),
            nullable=True,
            comment="positive, neutral, negative",
        ),
        # Classification metadata
        sa.Column("classification_model", sa.String(100), nullable=True),
        sa.Column("classification_prompt", sa.Text, nullable=True),
        sa.Column("raw_classification", JSONB, nullable=True),
        # Action taken
        sa.Column(
            "action_taken",
            sa.String(50),
            nullable=True,
            comment="notify_sales, send_calendar_link, mark_not_interested, etc.",
        ),
        sa.Column("action_details", JSONB, nullable=True),
        sa.Column("action_completed_at", sa.DateTime(timezone=True), nullable=True),
        # Threading
        sa.Column("in_reply_to_email_id", UUID(as_uuid=True), nullable=True),
        sa.Column("thread_position", sa.Integer, nullable=True),
        # Timestamps
        sa.Column(
            "received_at",
            sa.DateTime(timezone=True),
            nullable=False,
            comment="When Instantly received the reply",
        ),
        sa.Column(
            "processed_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="When we processed/classified the reply",
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

    # Create indexes for email_replies
    op.create_index("idx_email_replies_campaign_id", "email_replies", ["campaign_id"])
    op.create_index("idx_email_replies_lead_id", "email_replies", ["lead_id"])
    op.create_index("idx_email_replies_category", "email_replies", ["category"])
    op.create_index("idx_email_replies_received_at", "email_replies", ["received_at"])
    op.create_index(
        "idx_email_replies_campaign_category",
        "email_replies",
        ["campaign_id", "category"],
    )
    op.create_index(
        "idx_email_replies_campaign_received",
        "email_replies",
        ["campaign_id", "received_at"],
    )

    # =========================================================================
    # CREATE REPLY_MONITORING_STATE TABLE
    # =========================================================================
    op.create_table(
        "reply_monitoring_state",
        # Primary key
        sa.Column(
            "id",
            UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        # Foreign key - unique per campaign
        sa.Column(
            "campaign_id",
            UUID(as_uuid=True),
            sa.ForeignKey("campaigns.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        # Checkpoint state
        sa.Column(
            "last_reply_id",
            sa.String(255),
            nullable=True,
            comment="Last Instantly reply ID processed",
        ),
        sa.Column(
            "last_checked_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="When we last checked for replies",
        ),
        # Cumulative stats
        sa.Column("total_replies", sa.Integer, server_default="0"),
        sa.Column("interested_count", sa.Integer, server_default="0"),
        sa.Column("not_interested_count", sa.Integer, server_default="0"),
        sa.Column("meetings_count", sa.Integer, server_default="0"),
        sa.Column("bounces_count", sa.Integer, server_default="0"),
        sa.Column("ooo_count", sa.Integer, server_default="0"),
        # Processing stats
        sa.Column("last_batch_size", sa.Integer, nullable=True),
        sa.Column("last_batch_duration_ms", sa.Integer, nullable=True),
        sa.Column("errors_count", sa.Integer, server_default="0"),
        sa.Column("last_error", sa.Text, nullable=True),
        sa.Column("last_error_at", sa.DateTime(timezone=True), nullable=True),
        # Monitoring status
        sa.Column(
            "status",
            sa.String(50),
            nullable=False,
            server_default="active",
            comment="active, paused, stopped, error",
        ),
        sa.Column("paused_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("pause_reason", sa.Text, nullable=True),
        # Timestamps
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

    # Create index for reply_monitoring_state
    op.create_index(
        "idx_reply_monitoring_state_campaign_id",
        "reply_monitoring_state",
        ["campaign_id"],
    )
    op.create_index("idx_reply_monitoring_state_status", "reply_monitoring_state", ["status"])

    # =========================================================================
    # CREATE CAMPAIGN_METRICS TABLE
    # =========================================================================
    op.create_table(
        "campaign_metrics",
        # Primary key
        sa.Column(
            "id",
            UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        # Foreign key
        sa.Column(
            "campaign_id",
            UUID(as_uuid=True),
            sa.ForeignKey("campaigns.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # Snapshot type
        sa.Column(
            "snapshot_type",
            sa.String(50),
            nullable=False,
            comment="hourly, daily, weekly, manual",
        ),
        # Raw metrics from Instantly
        sa.Column(
            "metrics",
            JSONB,
            nullable=False,
            server_default="{}",
            comment="Raw metrics: emails_sent, delivered, opened, clicked, replied, bounced",
        ),
        # Calculated rates
        sa.Column(
            "calculated_rates",
            JSONB,
            nullable=False,
            server_default="{}",
            comment="Calculated rates: delivery_rate, open_rate, click_rate, reply_rate, bounce_rate",
        ),
        # Outcome metrics
        sa.Column(
            "outcome_metrics",
            JSONB,
            nullable=False,
            server_default="{}",
            comment="interested_leads, meetings_booked, conversion_rate",
        ),
        # Cost metrics
        sa.Column(
            "cost_metrics",
            JSONB,
            nullable=False,
            server_default="{}",
            comment="total_cost, cost_per_lead, cost_per_interested, cost_per_meeting",
        ),
        # Benchmark status
        sa.Column(
            "benchmark_status",
            JSONB,
            nullable=False,
            server_default="{}",
            comment="Status vs benchmarks: good, warning, critical per metric",
        ),
        # Tier breakdown
        sa.Column(
            "tier_breakdown",
            JSONB,
            nullable=False,
            server_default="{}",
            comment="Performance breakdown by lead tier",
        ),
        # Comparison
        sa.Column("compared_to_previous", JSONB, nullable=True),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=True),
        # Timestamps
        sa.Column(
            "collected_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    # Create indexes for campaign_metrics
    op.create_index("idx_campaign_metrics_campaign_id", "campaign_metrics", ["campaign_id"])
    op.create_index("idx_campaign_metrics_snapshot_type", "campaign_metrics", ["snapshot_type"])
    op.create_index("idx_campaign_metrics_collected_at", "campaign_metrics", ["collected_at"])
    op.create_index(
        "idx_campaign_metrics_campaign_type_collected",
        "campaign_metrics",
        ["campaign_id", "snapshot_type", "collected_at"],
    )

    # =========================================================================
    # CREATE CAMPAIGN_ALERTS TABLE
    # =========================================================================
    op.create_table(
        "campaign_alerts",
        # Primary key
        sa.Column(
            "id",
            UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        # Foreign key
        sa.Column(
            "campaign_id",
            UUID(as_uuid=True),
            sa.ForeignKey("campaigns.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # Alert details
        sa.Column(
            "alert_type",
            sa.String(100),
            nullable=False,
            comment="high_bounce_rate, low_open_rate, no_replies, etc.",
        ),
        sa.Column(
            "severity",
            sa.String(20),
            nullable=False,
            comment="info, warning, critical",
        ),
        sa.Column("message", sa.Text, nullable=False),
        sa.Column("details", JSONB, nullable=True),
        # Threshold info
        sa.Column("metric_name", sa.String(100), nullable=True),
        sa.Column("metric_value", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column("threshold_value", sa.Numeric(precision=10, scale=4), nullable=True),
        # Action taken
        sa.Column(
            "action_taken",
            sa.String(100),
            nullable=True,
            comment="notify, pause_and_notify, pause_campaign",
        ),
        sa.Column("action_completed_at", sa.DateTime(timezone=True), nullable=True),
        # Status
        sa.Column(
            "status",
            sa.String(50),
            nullable=False,
            server_default="active",
            comment="active, acknowledged, resolved, dismissed",
        ),
        sa.Column("acknowledged_by", sa.String(255), nullable=True),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolution_notes", sa.Text, nullable=True),
        # Timestamps
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

    # Create indexes for campaign_alerts
    op.create_index("idx_campaign_alerts_campaign_id", "campaign_alerts", ["campaign_id"])
    op.create_index("idx_campaign_alerts_alert_type", "campaign_alerts", ["alert_type"])
    op.create_index("idx_campaign_alerts_severity", "campaign_alerts", ["severity"])
    op.create_index("idx_campaign_alerts_status", "campaign_alerts", ["status"])
    op.create_index(
        "idx_campaign_alerts_campaign_status",
        "campaign_alerts",
        ["campaign_id", "status"],
    )
    op.create_index("idx_campaign_alerts_created_at", "campaign_alerts", ["created_at"])

    # =========================================================================
    # ADD COLUMNS TO LEADS TABLE (idempotent - skip if exists)
    # =========================================================================

    # Use raw SQL to add columns only if they don't exist
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                          WHERE table_name='leads' AND column_name='instantly_lead_id') THEN
                ALTER TABLE leads ADD COLUMN instantly_lead_id VARCHAR(255);
                COMMENT ON COLUMN leads.instantly_lead_id IS 'Lead ID from Instantly.ai after upload';
            END IF;

            IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                          WHERE table_name='leads' AND column_name='reply_status') THEN
                ALTER TABLE leads ADD COLUMN reply_status VARCHAR(50);
                COMMENT ON COLUMN leads.reply_status IS 'interested, not_interested, meeting_request, out_of_office, question, bounce';
            END IF;

            IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                          WHERE table_name='leads' AND column_name='replied_at') THEN
                ALTER TABLE leads ADD COLUMN replied_at TIMESTAMPTZ;
                COMMENT ON COLUMN leads.replied_at IS 'When lead first replied';
            END IF;

            IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                          WHERE table_name='leads' AND column_name='reply_count') THEN
                ALTER TABLE leads ADD COLUMN reply_count INTEGER DEFAULT 0;
                COMMENT ON COLUMN leads.reply_count IS 'Number of replies received';
            END IF;
        END $$;
    """)

    # Create indexes (skip if exists)
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_leads_instantly_lead_id ON leads (instantly_lead_id)"
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_leads_reply_status ON leads (reply_status)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_leads_replied_at ON leads (replied_at)")

    # =========================================================================
    # ADD COLUMNS TO CAMPAIGNS TABLE (idempotent - skip if exists)
    # =========================================================================

    # Use raw SQL to add columns only if they don't exist
    op.execute("""
        DO $$
        BEGIN
            -- Reply statistics
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                          WHERE table_name='campaigns' AND column_name='total_replies') THEN
                ALTER TABLE campaigns ADD COLUMN total_replies INTEGER DEFAULT 0;
                COMMENT ON COLUMN campaigns.total_replies IS 'Total number of replies received';
            END IF;

            IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                          WHERE table_name='campaigns' AND column_name='interested_count') THEN
                ALTER TABLE campaigns ADD COLUMN interested_count INTEGER DEFAULT 0;
                COMMENT ON COLUMN campaigns.interested_count IS 'Number of interested replies';
            END IF;

            IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                          WHERE table_name='campaigns' AND column_name='meetings_booked') THEN
                ALTER TABLE campaigns ADD COLUMN meetings_booked INTEGER DEFAULT 0;
                COMMENT ON COLUMN campaigns.meetings_booked IS 'Number of meeting requests';
            END IF;

            IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                          WHERE table_name='campaigns' AND column_name='bounce_count') THEN
                ALTER TABLE campaigns ADD COLUMN bounce_count INTEGER DEFAULT 0;
                COMMENT ON COLUMN campaigns.bounce_count IS 'Number of bounced emails';
            END IF;

            -- Analytics tracking
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                          WHERE table_name='campaigns' AND column_name='last_metrics_at') THEN
                ALTER TABLE campaigns ADD COLUMN last_metrics_at TIMESTAMPTZ;
                COMMENT ON COLUMN campaigns.last_metrics_at IS 'When metrics were last collected';
            END IF;

            IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                          WHERE table_name='campaigns' AND column_name='current_open_rate') THEN
                ALTER TABLE campaigns ADD COLUMN current_open_rate NUMERIC(5,2);
                COMMENT ON COLUMN campaigns.current_open_rate IS 'Current open rate percentage';
            END IF;

            IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                          WHERE table_name='campaigns' AND column_name='current_reply_rate') THEN
                ALTER TABLE campaigns ADD COLUMN current_reply_rate NUMERIC(5,2);
                COMMENT ON COLUMN campaigns.current_reply_rate IS 'Current reply rate percentage';
            END IF;

            IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                          WHERE table_name='campaigns' AND column_name='current_bounce_rate') THEN
                ALTER TABLE campaigns ADD COLUMN current_bounce_rate NUMERIC(5,2);
                COMMENT ON COLUMN campaigns.current_bounce_rate IS 'Current bounce rate percentage';
            END IF;

            -- Instantly sync
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                          WHERE table_name='campaigns' AND column_name='instantly_campaign_id') THEN
                ALTER TABLE campaigns ADD COLUMN instantly_campaign_id VARCHAR(255);
                COMMENT ON COLUMN campaigns.instantly_campaign_id IS 'Instantly.ai campaign ID';
            END IF;
        END $$;
    """)

    # Create index (skip if exists)
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_campaigns_instantly_campaign_id ON campaigns (instantly_campaign_id)"
    )


def downgrade() -> None:
    # =========================================================================
    # DROP COLUMNS FROM CAMPAIGNS TABLE
    # =========================================================================
    op.drop_index("idx_campaigns_instantly_campaign_id", table_name="campaigns")

    op.drop_column("campaigns", "instantly_campaign_id")
    op.drop_column("campaigns", "current_bounce_rate")
    op.drop_column("campaigns", "current_reply_rate")
    op.drop_column("campaigns", "current_open_rate")
    op.drop_column("campaigns", "last_metrics_at")
    op.drop_column("campaigns", "bounce_count")
    op.drop_column("campaigns", "meetings_booked")
    op.drop_column("campaigns", "interested_count")
    op.drop_column("campaigns", "total_replies")

    # =========================================================================
    # DROP COLUMNS FROM LEADS TABLE
    # =========================================================================
    op.drop_index("idx_leads_replied_at", table_name="leads")
    op.drop_index("idx_leads_reply_status", table_name="leads")
    op.drop_index("idx_leads_instantly_lead_id", table_name="leads")

    op.drop_column("leads", "reply_count")
    op.drop_column("leads", "replied_at")
    op.drop_column("leads", "reply_status")
    op.drop_column("leads", "instantly_lead_id")

    # =========================================================================
    # DROP CAMPAIGN_ALERTS TABLE
    # =========================================================================
    op.drop_index("idx_campaign_alerts_created_at", table_name="campaign_alerts")
    op.drop_index("idx_campaign_alerts_campaign_status", table_name="campaign_alerts")
    op.drop_index("idx_campaign_alerts_status", table_name="campaign_alerts")
    op.drop_index("idx_campaign_alerts_severity", table_name="campaign_alerts")
    op.drop_index("idx_campaign_alerts_alert_type", table_name="campaign_alerts")
    op.drop_index("idx_campaign_alerts_campaign_id", table_name="campaign_alerts")
    op.drop_table("campaign_alerts")

    # =========================================================================
    # DROP CAMPAIGN_METRICS TABLE
    # =========================================================================
    op.drop_index("idx_campaign_metrics_campaign_type_collected", table_name="campaign_metrics")
    op.drop_index("idx_campaign_metrics_collected_at", table_name="campaign_metrics")
    op.drop_index("idx_campaign_metrics_snapshot_type", table_name="campaign_metrics")
    op.drop_index("idx_campaign_metrics_campaign_id", table_name="campaign_metrics")
    op.drop_table("campaign_metrics")

    # =========================================================================
    # DROP REPLY_MONITORING_STATE TABLE
    # =========================================================================
    op.drop_index("idx_reply_monitoring_state_status", table_name="reply_monitoring_state")
    op.drop_index("idx_reply_monitoring_state_campaign_id", table_name="reply_monitoring_state")
    op.drop_table("reply_monitoring_state")

    # =========================================================================
    # DROP EMAIL_REPLIES TABLE
    # =========================================================================
    op.drop_index("idx_email_replies_campaign_received", table_name="email_replies")
    op.drop_index("idx_email_replies_campaign_category", table_name="email_replies")
    op.drop_index("idx_email_replies_received_at", table_name="email_replies")
    op.drop_index("idx_email_replies_category", table_name="email_replies")
    op.drop_index("idx_email_replies_lead_id", table_name="email_replies")
    op.drop_index("idx_email_replies_campaign_id", table_name="email_replies")
    op.drop_table("email_replies")

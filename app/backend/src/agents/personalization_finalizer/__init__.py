"""
Personalization Finalizer Agent (Phase 4.4).

Compiles personalization statistics, exports email samples to Google Sheets
for human review, and sends approval notifications before Phase 5.
"""

from src.agents.personalization_finalizer.agent import (
    PersonalizationFinalizerAgent,
    PersonalizationFinalizerConfig,
    run_personalization_finalizer,
)
from src.agents.personalization_finalizer.exports import (
    EmailSamplesExporter,
    SheetsExportError,
)
from src.agents.personalization_finalizer.reports import (
    FrameworkUsage,
    PersonalizationFinalizerResult,
    PersonalizationLevelStats,
    PersonalizationReport,
    QualityDistribution,
    TierPersonalizationBreakdown,
)
from src.agents.personalization_finalizer.tools import (
    create_personalization_finalizer_tools_server,
    export_emails_to_sheets,
    generate_personalization_report,
    get_email_samples,
    get_personalization_stats,
    send_phase4_approval_notification,
    update_campaign_personalization_complete,
)

__all__ = [
    # Agent
    "PersonalizationFinalizerAgent",
    "PersonalizationFinalizerConfig",
    "run_personalization_finalizer",
    # Reports
    "PersonalizationReport",
    "PersonalizationFinalizerResult",
    "TierPersonalizationBreakdown",
    "FrameworkUsage",
    "PersonalizationLevelStats",
    "QualityDistribution",
    # Exports
    "EmailSamplesExporter",
    "SheetsExportError",
    # Tools
    "create_personalization_finalizer_tools_server",
    "get_personalization_stats",
    "generate_personalization_report",
    "get_email_samples",
    "export_emails_to_sheets",
    "send_phase4_approval_notification",
    "update_campaign_personalization_complete",
]

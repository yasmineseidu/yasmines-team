"""Research Export Agent package."""

from src.agents.research_export.agent import (
    DocumentCreationError,
    FolderCreationError,
    ResearchExportAgent,
    ResearchExportAgentError,
    export_niche_research_tool,
    run_research_export_agent,
)
from src.agents.research_export.docs_builder import DocsBuilder
from src.agents.research_export.templates import (
    render_messaging_angles_doc,
    render_niche_overview_doc,
    render_pain_points_doc,
    render_persona_profiles_doc,
)

__all__ = [
    "ResearchExportAgent",
    "ResearchExportAgentError",
    "FolderCreationError",
    "DocumentCreationError",
    "export_niche_research_tool",
    "run_research_export_agent",
    "DocsBuilder",
    "render_niche_overview_doc",
    "render_persona_profiles_doc",
    "render_pain_points_doc",
    "render_messaging_angles_doc",
]

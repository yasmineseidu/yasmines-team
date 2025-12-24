"""
Research Export Agent - Phase 1, Agent 1.3.

Compiles niche and persona research into professionally formatted Google Docs
for human review. Creates folder structure with 4 comprehensive documents.

Uses Claude Agent SDK with Google Drive/Docs APIs for document generation.

Phase 1 Export Steps:
1. Load research data from database tables
2. Create Google Drive folder structure
3. Generate 4 formatted documents:
   - Niche Overview
   - Persona Profiles
   - Pain Points Analysis
   - Messaging Angles
4. Update database with folder URL
5. Trigger human approval gate

This agent uses Claude Agent SDK with SDK MCP tools for in-process execution.
"""

import json
import logging
import os
from datetime import datetime
from typing import Any

import httpx
from claude_agent_sdk import ClaudeAgentOptions, create_sdk_mcp_server, query, tool
from claude_agent_sdk.types import AssistantMessage, TextBlock
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.integrations.google_docs.client import (
    GoogleDocsAuthError,
    GoogleDocsClient,
    GoogleDocsError,
    GoogleDocsRateLimitError,
)
from src.integrations.google_drive.client import GoogleDriveClient
from src.integrations.google_drive.exceptions import (
    GoogleDriveAuthError,
    GoogleDriveError,
    GoogleDriveRateLimitError,
)

logger = logging.getLogger(__name__)


# ============================================================================
# Constants
# ============================================================================

# Parent folder for all research exports (from user)
RESEARCH_PARENT_FOLDER_ID = "1q2CuAABTE9HLML8cMd5YaOC3Y1ev6JC4"

# Document titles
NICHE_OVERVIEW_TITLE = "1. Niche Overview"
PERSONA_PROFILES_TITLE = "2. Persona Profiles"
PAIN_POINTS_TITLE = "3. Pain Points Analysis"
MESSAGING_ANGLES_TITLE = "4. Messaging Angles"


# ============================================================================
# Exceptions
# ============================================================================


class ResearchExportAgentError(Exception):
    """Exception raised for research export agent errors."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class DatabaseReadError(ResearchExportAgentError):
    """Raised when database read fails."""

    def __init__(self, table: str, error: Exception) -> None:
        super().__init__(
            f"Failed to read from {table}: {error}",
            {"table": table, "error": str(error)},
        )


class DocumentCreationError(ResearchExportAgentError):
    """Raised when document creation fails."""

    def __init__(self, doc_name: str, error: Exception) -> None:
        super().__init__(
            f"Failed to create document '{doc_name}': {error}",
            {"doc_name": doc_name, "error": str(error)},
        )


class FolderCreationError(ResearchExportAgentError):
    """Raised when folder creation fails."""

    def __init__(self, folder_name: str, error: Exception) -> None:
        super().__init__(
            f"Failed to create folder '{folder_name}': {error}",
            {"folder_name": folder_name, "error": str(error)},
        )


# ============================================================================
# Research Export Agent
# ============================================================================


class ResearchExportAgent:
    """
    Research Export Agent for compiling research into Google Docs.

    Attributes:
        drive_client: Google Drive API client
        docs_client: Google Docs API client
        parent_folder_id: Parent folder ID for research exports
    """

    def __init__(
        self,
        google_credentials: dict[str, Any] | None = None,
        parent_folder_id: str = RESEARCH_PARENT_FOLDER_ID,
    ) -> None:
        """
        Initialize Research Export Agent.

        Args:
            google_credentials: Google service account credentials JSON
            parent_folder_id: Parent folder ID for all research exports
        """
        # Remove ANTHROPIC_API_KEY if present (LEARN-001)
        os.environ.pop("ANTHROPIC_API_KEY", None)

        self.parent_folder_id = parent_folder_id

        # Initialize Google clients
        self.drive_client = GoogleDriveClient(
            credentials_json=google_credentials or self._load_google_credentials(),
            timeout=30.0,
            max_retries=3,
        )

        self.docs_client = GoogleDocsClient(
            credentials_json=google_credentials or self._load_google_credentials(),
            timeout=30.0,
            max_retries=3,
        )

        logger.info("ResearchExportAgent initialized")

    def _load_google_credentials(self) -> dict[str, Any]:
        """
        Load Google credentials from environment.

        Returns:
            Google service account credentials dictionary

        Raises:
            ResearchExportAgentError: If credentials not found
        """
        credentials_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
        if not credentials_json:
            raise ResearchExportAgentError(
                "GOOGLE_SERVICE_ACCOUNT_JSON environment variable not set",
                {"required_env": "GOOGLE_SERVICE_ACCOUNT_JSON"},
            )

        try:
            return json.loads(credentials_json)  # type: ignore[no-any-return]
        except json.JSONDecodeError as e:
            raise ResearchExportAgentError(
                "Invalid GOOGLE_SERVICE_ACCOUNT_JSON format",
                {"error": str(e)},
            ) from e

    @retry(  # type: ignore[misc]
        retry=retry_if_exception_type(
            (GoogleDriveRateLimitError, GoogleDocsRateLimitError, httpx.TimeoutException)
        ),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=2, max=30),
        before_sleep=before_sleep_log(logger, logging.WARNING),
    )
    async def create_research_folder(
        self,
        niche_name: str,
        niche_slug: str,
    ) -> tuple[str, str]:
        """
        Create Google Drive folder for research export.

        Args:
            niche_name: Human-readable niche name
            niche_slug: URL-safe niche slug

        Returns:
            Tuple of (folder_id, folder_url)

        Raises:
            FolderCreationError: If folder creation fails
        """
        # Authenticate if needed
        if not self.drive_client.access_token:
            await self.drive_client.authenticate()

        # Create folder name with timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d")
        folder_name = f"{niche_name} - Research Export - {timestamp}"

        try:
            # Create folder as subfolder of parent
            folder = await self.drive_client.create_folder(
                name=folder_name,
                parent_id=self.parent_folder_id,
            )

            # Share folder with anyone who has the link (view only)
            await self.drive_client.share_file(
                file_id=folder["id"],
                role="reader",
                share_type="anyone",
            )

            folder_url = f"https://drive.google.com/drive/folders/{folder['id']}"

            logger.info(
                f"Created research folder: {folder_name}",
                extra={"folder_id": folder["id"], "folder_url": folder_url},
            )

            return folder["id"], folder_url

        except (GoogleDriveError, GoogleDriveAuthError) as e:
            logger.error(f"Failed to create folder: {e}")
            raise FolderCreationError(folder_name, e) from e

    @retry(  # type: ignore[misc]
        retry=retry_if_exception_type((GoogleDocsRateLimitError, httpx.TimeoutException)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=2, max=30),
        before_sleep=before_sleep_log(logger, logging.WARNING),
    )
    async def create_document_from_content(
        self,
        title: str,
        content: str,
        folder_id: str,
    ) -> dict[str, str]:
        """
        Create Google Doc from markdown-like content.

        Args:
            title: Document title
            content: Document content (markdown-like)
            folder_id: Parent folder ID

        Returns:
            Dictionary with doc_id and doc_url

        Raises:
            DocumentCreationError: If document creation fails
        """
        # Authenticate if needed
        if not self.docs_client.access_token:
            await self.docs_client.authenticate()

        try:
            # Create blank document
            doc = await self.docs_client.create_document(title=title)

            # Insert content into document
            await self.docs_client.insert_text(
                document_id=doc["documentId"],
                text=content,
                index=1,  # Start of document body
            )

            # Move to folder using Drive API
            await self.drive_client.move_file_to_folder(
                file_id=doc["documentId"],
                folder_id=folder_id,
            )

            # Share document with anyone who has the link (view only)
            await self.drive_client.share_file(
                file_id=doc["documentId"],
                role="reader",
                share_type="anyone",
            )

            doc_url = f"https://docs.google.com/document/d/{doc['documentId']}/edit"

            logger.info(
                f"Created document: {title}",
                extra={"doc_id": doc["documentId"], "doc_url": doc_url},
            )

            return {
                "doc_id": doc["documentId"],
                "doc_url": doc_url,
                "name": title,
            }

        except (GoogleDocsError, GoogleDocsAuthError, GoogleDriveError) as e:
            logger.error(f"Failed to create document '{title}': {e}")
            raise DocumentCreationError(title, e) from e

    async def export_research(
        self,
        niche_id: str,
        niche_data: dict[str, Any],
        niche_scores: dict[str, Any],
        niche_research_data: dict[str, Any] | None,
        personas: list[dict[str, Any]],
        persona_research_data: list[dict[str, Any]],
        industry_scores: list[dict[str, Any]],
        consolidated_pain_points: list[str],
    ) -> dict[str, Any]:
        """
        Export complete research to Google Docs.

        Args:
            niche_id: Niche UUID
            niche_data: Niche metadata from niches table
            niche_scores: Scoring data from niche_scores table
            niche_research_data: Full research findings from niche_research_data table
            personas: List of personas from personas table
            persona_research_data: Research sources from persona_research_data table
            industry_scores: Industry fit scores from industry_fit_scores table
            consolidated_pain_points: Consolidated pain points from handoff

        Returns:
            Export result with folder_url and documents list

        Raises:
            ResearchExportAgentError: If export fails
        """
        logger.info(f"Starting research export for niche: {niche_data.get('name')}")

        # Import templates
        from src.agents.research_export.templates import (
            render_messaging_angles_doc,
            render_niche_overview_doc,
            render_pain_points_doc,
            render_persona_profiles_doc,
        )

        # Step 1: Create folder
        folder_id, folder_url = await self.create_research_folder(
            niche_name=niche_data.get("name", "Unknown Niche"),
            niche_slug=niche_data.get("slug", "unknown"),
        )

        documents = []

        try:
            # Step 2: Create Niche Overview document
            niche_overview_content = render_niche_overview_doc(
                niche=niche_data,
                scores=niche_scores,
                research_data=niche_research_data or {},
            )
            niche_overview_doc = await self.create_document_from_content(
                title=f"{NICHE_OVERVIEW_TITLE} - {niche_data.get('name')}",
                content=niche_overview_content,
                folder_id=folder_id,
            )
            documents.append(niche_overview_doc)

            # Step 3: Create Persona Profiles document
            persona_profiles_content = render_persona_profiles_doc(
                niche=niche_data,
                personas=personas,
            )
            persona_profiles_doc = await self.create_document_from_content(
                title=f"{PERSONA_PROFILES_TITLE} - {niche_data.get('name')}",
                content=persona_profiles_content,
                folder_id=folder_id,
            )
            documents.append(persona_profiles_doc)

            # Step 4: Create Pain Points Analysis document
            pain_points_content = render_pain_points_doc(
                niche=niche_data,
                consolidated_pain_points=consolidated_pain_points,
                niche_research_data=niche_research_data or {},
                persona_research_data=persona_research_data,
                industry_scores=industry_scores,
            )
            pain_points_doc = await self.create_document_from_content(
                title=f"{PAIN_POINTS_TITLE} - {niche_data.get('name')}",
                content=pain_points_content,
                folder_id=folder_id,
            )
            documents.append(pain_points_doc)

            # Step 5: Create Messaging Angles document
            messaging_content = render_messaging_angles_doc(
                niche=niche_data,
                personas=personas,
                niche_research_data=niche_research_data or {},
            )
            messaging_doc = await self.create_document_from_content(
                title=f"{MESSAGING_ANGLES_TITLE} - {niche_data.get('name')}",
                content=messaging_content,
                folder_id=folder_id,
            )
            documents.append(messaging_doc)

            logger.info(
                f"Successfully exported research for niche: {niche_data.get('name')}",
                extra={
                    "folder_url": folder_url,
                    "documents_created": len(documents),
                },
            )

            return {
                "folder_url": folder_url,
                "folder_id": folder_id,
                "documents": documents,
                "notification_sent": False,  # TODO: Implement Slack notification
            }

        except Exception as e:
            logger.error(f"Failed to export research: {e}")
            # Cleanup: attempt to delete partial folder
            try:
                await self.drive_client.delete_file(folder_id)
                logger.info(f"Cleaned up partial folder: {folder_id}")
            except Exception as cleanup_error:
                logger.warning(f"Failed to cleanup folder {folder_id}: {cleanup_error}")

            raise ResearchExportAgentError(
                f"Research export failed: {e}",
                {"niche_id": niche_id, "error": str(e)},
            ) from e


# ============================================================================
# SDK MCP Tools
# ============================================================================


@tool(  # type: ignore[misc]
    "export_niche_research",
    "Export niche and persona research to Google Docs for human review",
    {
        "niche_id": str,
        "niche_data": dict,
        "niche_scores": dict,
        "niche_research_data": dict,
        "personas": list,
        "persona_research_data": list,
        "industry_scores": list,
        "consolidated_pain_points": list,
    },
)
async def export_niche_research_tool(args: dict[str, Any]) -> dict[str, Any]:
    """
    SDK MCP tool for exporting research to Google Docs.

    Args:
        args: Tool arguments containing research data

    Returns:
        Tool result with folder URL and documents
    """
    try:
        # Create agent instance (credentials loaded from env)
        agent = ResearchExportAgent()

        # Perform export
        result = await agent.export_research(
            niche_id=args["niche_id"],
            niche_data=args["niche_data"],
            niche_scores=args["niche_scores"],
            niche_research_data=args.get("niche_research_data"),
            personas=args["personas"],
            persona_research_data=args.get("persona_research_data", []),
            industry_scores=args.get("industry_scores", []),
            consolidated_pain_points=args.get("consolidated_pain_points", []),
        )

        return {
            "content": [
                {
                    "type": "text",
                    "text": f"Research exported successfully!\n\n"
                    f"Folder: {result['folder_url']}\n\n"
                    f"Documents created: {len(result['documents'])}\n"
                    + "\n".join(
                        f"- {doc['name']}: {doc['doc_url']}" for doc in result["documents"]
                    ),
                }
            ],
            "is_error": False,
        }

    except Exception as e:
        logger.error(f"Tool execution failed: {e}")
        return {
            "content": [{"type": "text", "text": f"Error: {str(e)}"}],
            "is_error": True,
        }


# ============================================================================
# Agent Execution
# ============================================================================


async def run_research_export_agent(
    niche_id: str,
    persona_ids: list[str],
    consolidated_pain_points: list[str],
) -> dict[str, Any]:
    """
    Run the Research Export Agent using Claude Agent SDK.

    Args:
        niche_id: Niche UUID
        persona_ids: List of persona UUIDs
        consolidated_pain_points: Consolidated pain points from handoff

    Returns:
        Agent execution result with folder URL and documents

    Raises:
        ResearchExportAgentError: If agent execution fails
    """
    # Remove ANTHROPIC_API_KEY (LEARN-001)
    os.environ.pop("ANTHROPIC_API_KEY", None)

    # Create SDK MCP server with export tool
    research_export_server = create_sdk_mcp_server(
        name="research_export",
        version="1.0.0",
        tools=[export_niche_research_tool],
    )

    # Configure agent options
    options = ClaudeAgentOptions(
        system_prompt={
            "type": "preset",
            "preset": "claude_code",
            "append": """
You are a documentation specialist responsible for compiling market research
into professional, readable documents for human review.

## Your Role
- Organize complex research data into clear, scannable documents
- Highlight key insights and recommendations
- Present data in tables and lists for easy consumption
- Maintain consistent formatting across all documents
- Include all relevant quotes and sources

## Document Standards
- Use clear headers and subheaders
- Include executive summary at the top
- Present scores and metrics in tables
- Quote research sources with proper attribution
- Use bullet points for lists
- Highlight actionable recommendations

## Quality Checks
Before finalizing documents:
- Verify all data is included
- Check formatting consistency
- Ensure all URLs are clickable
- Confirm persona details are complete
- Validate scoring data accuracy
""",
        },
        mcp_servers={"research_export": research_export_server},
        allowed_tools=[
            "mcp__research_export__export_niche_research",
        ],
        permission_mode="acceptEdits",
        setting_sources=["project"],
        model="sonnet",
    )

    # Execute agent
    prompt = f"""
Export niche research to Google Docs for niche_id: {niche_id}

Persona IDs: {persona_ids}
Consolidated Pain Points: {consolidated_pain_points[:3]}... ({len(consolidated_pain_points)} total)

Use the export_niche_research tool to create formatted Google Docs.
Ensure all 4 documents are created with professional formatting.
"""

    result = {}
    async for message in query(prompt=prompt, options=options):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    logger.info(f"Agent: {block.text}")

        # Check for result message
        if hasattr(message, "result"):
            result = message.result

    return result

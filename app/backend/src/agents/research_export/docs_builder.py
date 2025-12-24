"""
Document builder utilities for Research Export Agent.

Provides utility functions for enhancing document formatting,
adding professional styling, and post-processing Google Docs.

Future enhancements could include:
- Table of contents generation
- Custom styling and formatting
- Document templates with branding
- Advanced formatting (colors, fonts, etc.)
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class DocsBuilder:
    """
    Utility class for building and enhancing Google Docs.

    Provides helper methods for document formatting and styling.
    Currently minimal implementation - can be extended for advanced formatting.
    """

    @staticmethod
    def format_markdown_to_google_docs(content: str) -> str:
        """
        Convert markdown-like content to Google Docs friendly format.

        Google Docs API accepts plain text with basic formatting.
        This method ensures content is properly formatted.

        Args:
            content: Markdown-like content

        Returns:
            Formatted content for Google Docs
        """
        # For now, pass through as-is
        # Google Docs will handle basic markdown formatting
        return content

    @staticmethod
    def add_table_of_contents(content: str) -> str:
        """
        Add a table of contents to document content.

        Args:
            content: Document content

        Returns:
            Content with TOC prepended
        """
        # Extract headers
        lines = content.split("\n")
        toc_lines = ["# Table of Contents\n"]

        for line in lines:
            if line.startswith("##") and not line.startswith("###"):
                # Second-level header
                header = line.replace("##", "").strip()
                toc_lines.append(f"- {header}")

        # Add separator
        toc_lines.append("\n---\n")

        # Prepend TOC to content
        return "\n".join(toc_lines) + "\n" + content

    @staticmethod
    def validate_document_structure(content: str) -> dict[str, Any]:
        """
        Validate document structure and return metrics.

        Args:
            content: Document content

        Returns:
            Validation metrics
        """
        lines = content.split("\n")

        return {
            "total_lines": len(lines),
            "has_title": lines[0].startswith("#") if lines else False,
            "header_count": sum(1 for line in lines if line.startswith("#")),
            "table_count": sum(1 for line in lines if line.startswith("|")),
            "list_item_count": sum(1 for line in lines if line.strip().startswith("-")),
        }

    @staticmethod
    def enhance_formatting(content: str) -> str:
        """
        Enhance document formatting for professional appearance.

        Args:
            content: Raw content

        Returns:
            Enhanced content
        """
        # Ensure proper spacing after headers
        lines = content.split("\n")
        enhanced = []

        for i, line in enumerate(lines):
            enhanced.append(line)

            # Add extra space after headers
            if line.startswith("#") and i < len(lines) - 1 and lines[i + 1].strip() != "":
                enhanced.append("")

        return "\n".join(enhanced)

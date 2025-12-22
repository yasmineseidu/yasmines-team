"""
Google Drive tools for agent integration.

Provides MCP tools for agents to interact with Google Drive API.
"""

import logging
from typing import Any

from src.integrations.google_drive.client import GoogleDriveClient

logger = logging.getLogger(__name__)


async def list_files_tool(
    page_size: int = 10,
    query: str | None = None,
    order_by: str | None = None,
    page_token: str | None = None,
) -> dict[str, Any]:
    """
    List files from Google Drive.

    Args:
        page_size: Number of files to return (1-1000)
        query: Google Drive query filter (e.g., "name contains 'proposal'")
        order_by: Sort order (e.g., "modifiedTime desc")
        page_token: Token for pagination

    Returns:
        Dictionary with files list and nextPageToken if more results exist

    Raises:
        GoogleDriveError: If operation fails
    """
    client = GoogleDriveClient()
    await client.authenticate()

    try:
        return await client.list_files(
            page_size=page_size,
            query=query,
            order_by=order_by,
            page_token=page_token,
        )
    finally:
        await client.close()


async def get_file_metadata_tool(file_id: str) -> dict[str, Any]:
    """
    Get file metadata from Google Drive.

    Args:
        file_id: Google Drive file ID

    Returns:
        File metadata with id, name, mimeType, size, timestamps, etc.

    Raises:
        GoogleDriveError: If file not found or operation fails
    """
    client = GoogleDriveClient()
    await client.authenticate()

    try:
        metadata = await client.get_file_metadata(file_id)
        return metadata.model_dump()
    finally:
        await client.close()


async def read_document_tool(file_id: str) -> str:
    """
    Read document content from Google Drive.

    Supports Google Docs, Sheets, and PDF documents.

    Args:
        file_id: Google Drive file ID

    Returns:
        Document content as text

    Raises:
        GoogleDriveError: If document type not supported or read fails
    """
    client = GoogleDriveClient()
    await client.authenticate()

    try:
        return await client.read_document_content(file_id)
    finally:
        await client.close()


async def create_document_tool(
    title: str,
    mime_type: str = "application/vnd.google-apps.document",
    parent_folder_id: str | None = None,
) -> dict[str, Any]:
    """
    Create a new document in Google Drive.

    Supports Google Docs, Sheets, Slides, and other types.

    Args:
        title: Document title
        mime_type: Document MIME type (default: Google Docs)
        parent_folder_id: Parent folder ID (optional)

    Returns:
        File metadata including id and webViewLink

    Raises:
        GoogleDriveError: If creation fails
    """
    client = GoogleDriveClient()
    await client.authenticate()

    try:
        return await client.create_document(
            title=title,
            mime_type=mime_type,
            parent_folder_id=parent_folder_id,
        )
    finally:
        await client.close()


async def upload_file_tool(
    file_name: str,
    file_content: str,
    mime_type: str = "application/octet-stream",
    parent_folder_id: str | None = None,
) -> dict[str, Any]:
    """
    Upload file to Google Drive.

    Args:
        file_name: Name of file in Drive
        file_content: File content as string
        mime_type: File MIME type (default: application/octet-stream)
        parent_folder_id: Parent folder ID (optional)

    Returns:
        File metadata with id and upload status

    Raises:
        GoogleDriveError: If upload fails
    """
    client = GoogleDriveClient()
    await client.authenticate()

    try:
        return await client.upload_file(
            file_name=file_name,
            file_content=file_content,
            mime_type=mime_type,
            parent_folder_id=parent_folder_id,
        )
    finally:
        await client.close()


async def delete_file_tool(file_id: str, permanently: bool = False) -> dict[str, Any]:
    """
    Delete file from Google Drive.

    Args:
        file_id: Google Drive file ID
        permanently: If True, delete permanently; if False, move to trash

    Returns:
        Success confirmation

    Raises:
        GoogleDriveError: If deletion fails
    """
    client = GoogleDriveClient()
    await client.authenticate()

    try:
        await client.delete_file(file_id, permanently=permanently)
        action = "permanently deleted" if permanently else "moved to trash"
        return {"success": True, "message": f"File {action}: {file_id}"}
    finally:
        await client.close()


async def share_file_tool(
    file_id: str,
    email: str | None = None,
    role: str = "reader",
) -> dict[str, Any]:
    """
    Share file with user.

    Args:
        file_id: Google Drive file ID
        email: Email address to share with (required for user share)
        role: Permission level (owner, writer, commenter, reader)

    Returns:
        Permission object with id and details

    Raises:
        GoogleDriveError: If sharing fails
    """
    client = GoogleDriveClient()
    await client.authenticate()

    try:
        return await client.share_file(
            file_id=file_id,
            email=email,
            role=role,
            share_type="user" if email else "domain",
        )
    finally:
        await client.close()


async def export_document_tool(
    file_id: str,
    export_format: str = "pdf",
) -> dict[str, Any]:
    """
    Export document in specified format.

    Supported formats: pdf, docx, xlsx, csv, json, odt, ods, rtf, txt, zip

    Args:
        file_id: Google Drive file ID
        export_format: Export format (default: pdf)

    Returns:
        Export metadata with format and status

    Raises:
        GoogleDriveError: If export fails or format not supported
    """
    client = GoogleDriveClient()
    await client.authenticate()

    try:
        content = await client.export_document(file_id, export_format)
        return {
            "success": True,
            "file_id": file_id,
            "format": export_format,
            "size_bytes": len(content),
        }
    finally:
        await client.close()


# Tool definitions for MCP integration
GOOGLE_DRIVE_TOOLS = {
    "list_files": {
        "name": "list_files",
        "description": "List files from Google Drive with optional filtering",
        "function": list_files_tool,
        "parameters": {
            "type": "object",
            "properties": {
                "page_size": {
                    "type": "integer",
                    "description": "Number of files to return (1-1000)",
                    "default": 10,
                },
                "query": {
                    "type": "string",
                    "description": "Google Drive query filter (e.g., name contains 'proposal')",
                },
                "order_by": {
                    "type": "string",
                    "description": "Sort order (e.g., modifiedTime desc)",
                },
                "page_token": {
                    "type": "string",
                    "description": "Token for pagination",
                },
            },
        },
    },
    "get_file_metadata": {
        "name": "get_file_metadata",
        "description": "Get detailed metadata for a specific file",
        "function": get_file_metadata_tool,
        "parameters": {
            "type": "object",
            "properties": {
                "file_id": {
                    "type": "string",
                    "description": "Google Drive file ID",
                }
            },
            "required": ["file_id"],
        },
    },
    "read_document": {
        "name": "read_document",
        "description": "Read content from Google Docs, Sheets, or PDF documents",
        "function": read_document_tool,
        "parameters": {
            "type": "object",
            "properties": {
                "file_id": {
                    "type": "string",
                    "description": "Google Drive file ID",
                }
            },
            "required": ["file_id"],
        },
    },
    "create_document": {
        "name": "create_document",
        "description": "Create a new Google Doc, Sheet, or other document type",
        "function": create_document_tool,
        "parameters": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Document title",
                },
                "mime_type": {
                    "type": "string",
                    "description": "Document MIME type (default: Google Docs)",
                    "default": "application/vnd.google-apps.document",
                },
                "parent_folder_id": {
                    "type": "string",
                    "description": "Parent folder ID (optional)",
                },
            },
            "required": ["title"],
        },
    },
    "upload_file": {
        "name": "upload_file",
        "description": "Upload file to Google Drive",
        "function": upload_file_tool,
        "parameters": {
            "type": "object",
            "properties": {
                "file_name": {
                    "type": "string",
                    "description": "Name of file in Drive",
                },
                "file_content": {
                    "type": "string",
                    "description": "File content as string",
                },
                "mime_type": {
                    "type": "string",
                    "description": "File MIME type",
                    "default": "application/octet-stream",
                },
                "parent_folder_id": {
                    "type": "string",
                    "description": "Parent folder ID (optional)",
                },
            },
            "required": ["file_name", "file_content"],
        },
    },
    "delete_file": {
        "name": "delete_file",
        "description": "Delete file from Google Drive (move to trash or permanently delete)",
        "function": delete_file_tool,
        "parameters": {
            "type": "object",
            "properties": {
                "file_id": {
                    "type": "string",
                    "description": "Google Drive file ID",
                },
                "permanently": {
                    "type": "boolean",
                    "description": "Permanently delete instead of moving to trash",
                    "default": False,
                },
            },
            "required": ["file_id"],
        },
    },
    "share_file": {
        "name": "share_file",
        "description": "Share file with user and set permission level",
        "function": share_file_tool,
        "parameters": {
            "type": "object",
            "properties": {
                "file_id": {
                    "type": "string",
                    "description": "Google Drive file ID",
                },
                "email": {
                    "type": "string",
                    "description": "Email address to share with",
                },
                "role": {
                    "type": "string",
                    "description": "Permission level (owner, writer, commenter, reader)",
                    "default": "reader",
                },
            },
            "required": ["file_id"],
        },
    },
    "export_document": {
        "name": "export_document",
        "description": "Export document in specified format (pdf, docx, xlsx, csv, etc.)",
        "function": export_document_tool,
        "parameters": {
            "type": "object",
            "properties": {
                "file_id": {
                    "type": "string",
                    "description": "Google Drive file ID",
                },
                "export_format": {
                    "type": "string",
                    "description": "Export format (pdf, docx, xlsx, csv, json, odt, ods, rtf, txt, zip)",
                    "default": "pdf",
                },
            },
            "required": ["file_id"],
        },
    },
}

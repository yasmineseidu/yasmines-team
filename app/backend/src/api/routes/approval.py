"""
Approval workflow API routes.

REST API endpoints for managing approval requests programmatically.
Supports creating, retrieving, updating, and listing approvals.

Example:
    >>> # Register routes with FastAPI app
    >>> from src.api.routes.approval import router
    >>> app.include_router(router, prefix="/api/approvals")
"""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from src.api.routes.telegram import get_approval_service
from src.integrations.telegram import TelegramError
from src.models.approval import ApprovalContentType, ApprovalStatus

logger = logging.getLogger(__name__)

router = APIRouter(tags=["approvals"])


class CreateApprovalRequest(BaseModel):
    """Request body for creating an approval request."""

    title: str = Field(..., min_length=1, max_length=255, description="Request title")
    content: str = Field(..., min_length=1, description="Request content/description")
    requester_id: int = Field(..., gt=0, description="User ID of requester")
    approver_id: int = Field(..., gt=0, description="User ID of approver")
    telegram_chat_id: int = Field(..., description="Telegram chat ID to send to")
    content_type: str = Field(default="custom", description="Type of content")
    data: dict[str, Any] = Field(default_factory=dict, description="Additional data")

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "title": "Q4 Marketing Budget",
                "content": "Requesting approval for $50,000 marketing budget",
                "requester_id": 123,
                "approver_id": 456,
                "telegram_chat_id": 789012345,
                "content_type": "budget",
                "data": {"amount": 50000, "department": "Marketing"},
            }
        }


class UpdateApprovalRequest(BaseModel):
    """Request body for updating an approval request."""

    status: str = Field(..., description="New status")
    actor_id: int = Field(..., gt=0, description="User ID taking action")
    actor_username: str | None = Field(None, description="Username of actor")
    comment: str | None = Field(None, description="Comment/reason for action")


class ApprovalResponse(BaseModel):
    """Response model for approval request."""

    id: str
    title: str
    content: str
    content_type: str
    status: str
    requester_id: int
    approver_id: int
    telegram_chat_id: int
    telegram_message_id: int | None
    data: dict[str, Any]
    created_at: str | None
    updated_at: str | None


class ApprovalListResponse(BaseModel):
    """Response model for listing approval requests."""

    total: int
    requests: list[ApprovalResponse]


@router.post("", response_model=dict[str, str], status_code=status.HTTP_201_CREATED)  # type: ignore[misc]
async def create_approval(request: CreateApprovalRequest) -> dict[str, str]:
    """
    Create a new approval request.

    Sends an approval message to the specified Telegram chat
    with interactive approve/disapprove/edit buttons.

    Args:
        request: Approval request data.

    Returns:
        Created request ID.

    Raises:
        HTTPException: If creation fails.
    """
    try:
        service = get_approval_service()

        # Convert content_type to enum
        try:
            content_type = ApprovalContentType(request.content_type)
        except ValueError:
            content_type = ApprovalContentType.CUSTOM

        request_id = await service.send_approval_request(
            request_data={
                "title": request.title,
                "content": request.content,
                "requester_id": request.requester_id,
                "approver_id": request.approver_id,
                "telegram_chat_id": request.telegram_chat_id,
                "content_type": content_type.value,
                "data": request.data,
            }
        )

        return {"id": request_id, "status": "created"}

    except ValueError as e:
        logger.warning(f"Invalid approval request: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from None

    except TelegramError as e:
        logger.error(f"Telegram error creating approval: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to send Telegram message: {e}",
        ) from None


@router.get("/{request_id}", response_model=ApprovalResponse)  # type: ignore[misc]
async def get_approval(request_id: str) -> ApprovalResponse:
    """
    Get an approval request by ID.

    Args:
        request_id: UUID of the approval request.

    Returns:
        Approval request details.

    Raises:
        HTTPException: If request not found.
    """
    try:
        service = get_approval_service()
        request = await service.get_approval_request(request_id)

        return ApprovalResponse(
            id=request.id,
            title=request.title,
            content=request.content,
            content_type=request.content_type.value,
            status=request.status.value,
            requester_id=request.requester_id,
            approver_id=request.approver_id,
            telegram_chat_id=request.telegram_chat_id,
            telegram_message_id=request.telegram_message_id,
            data=request.data,
            created_at=request.created_at.isoformat() if request.created_at else None,
            updated_at=request.updated_at.isoformat() if request.updated_at else None,
        )

    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Approval request {request_id} not found",
        ) from None


@router.patch("/{request_id}", response_model=dict[str, str])  # type: ignore[misc]
async def update_approval(request_id: str, update: UpdateApprovalRequest) -> dict[str, str]:
    """
    Update an approval request status.

    Args:
        request_id: UUID of the approval request.
        update: Update data.

    Returns:
        Update confirmation.

    Raises:
        HTTPException: If update fails.
    """
    try:
        service = get_approval_service()

        # Convert status to enum
        try:
            new_status = ApprovalStatus(update.status)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {update.status}",
            ) from None

        success = await service.update_approval_status(
            request_id=request_id,
            status=new_status,
            actor_id=update.actor_id,
            actor_username=update.actor_username,
            comment=update.comment,
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Approval request {request_id} not found",
            )

        return {"id": request_id, "status": new_status.value}

    except ValueError as e:
        logger.warning(f"Invalid update request: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from None


@router.get("", response_model=ApprovalListResponse)  # type: ignore[misc]
async def list_approvals(
    approver_id: int = Query(..., gt=0, description="Approver user ID"),
    status_filter: str | None = Query(None, description="Filter by status"),
) -> ApprovalListResponse:
    """
    List approval requests for an approver.

    Args:
        approver_id: User ID of the approver.
        status_filter: Optional status filter (pending, approved, etc.).

    Returns:
        List of approval requests.
    """
    service = get_approval_service()

    # Get pending approvals (could extend to support other filters)
    requests = await service.list_pending_approvals(approver_id)

    # Apply status filter if provided
    if status_filter:
        try:
            filter_status = ApprovalStatus(status_filter)
            requests = [r for r in requests if r.status == filter_status]
        except ValueError:
            pass  # Invalid filter, return unfiltered

    response_items = [
        ApprovalResponse(
            id=r.id,
            title=r.title,
            content=r.content,
            content_type=r.content_type.value,
            status=r.status.value,
            requester_id=r.requester_id,
            approver_id=r.approver_id,
            telegram_chat_id=r.telegram_chat_id,
            telegram_message_id=r.telegram_message_id,
            data=r.data,
            created_at=r.created_at.isoformat() if r.created_at else None,
            updated_at=r.updated_at.isoformat() if r.updated_at else None,
        )
        for r in requests
    ]

    return ApprovalListResponse(
        total=len(response_items),
        requests=response_items,
    )


@router.post("/{request_id}/edit-token", response_model=dict[str, str])  # type: ignore[misc]
async def generate_edit_token(request_id: str) -> dict[str, str]:
    """
    Generate an edit token for web-based editing.

    Args:
        request_id: UUID of the approval request.

    Returns:
        Edit token and URL.

    Raises:
        HTTPException: If request not found.
    """
    try:
        service = get_approval_service()
        token = await service.generate_edit_token(request_id)

        edit_url = f"{service.edit_form_base_url}/{request_id}/edit?token={token}"

        return {
            "token": token,
            "url": edit_url,
            "expires_in_hours": str(service.edit_token_expiry_hours),
        }

    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Approval request {request_id} not found",
        ) from None


@router.get("/by-token/{token}", response_model=ApprovalResponse)  # type: ignore[misc]
async def get_approval_by_token(token: str) -> ApprovalResponse:
    """
    Get an approval request by edit token.

    Used by the edit form to load request data.

    Args:
        token: Edit token.

    Returns:
        Approval request details.

    Raises:
        HTTPException: If token invalid or expired.
    """
    service = get_approval_service()
    request = await service.get_request_by_edit_token(token)

    if not request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid or expired edit token",
        )

    return ApprovalResponse(
        id=request.id,
        title=request.title,
        content=request.content,
        content_type=request.content_type.value,
        status=request.status.value,
        requester_id=request.requester_id,
        approver_id=request.approver_id,
        telegram_chat_id=request.telegram_chat_id,
        telegram_message_id=request.telegram_message_id,
        data=request.data,
        created_at=request.created_at.isoformat() if request.created_at else None,
        updated_at=request.updated_at.isoformat() if request.updated_at else None,
    )

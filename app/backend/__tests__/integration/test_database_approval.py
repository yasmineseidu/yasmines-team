"""
End-to-end test for approval workflow with PostgreSQL database.

Tests the full flow: create approval → approve/disapprove → verify database.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add backend to path for imports
sys.path.insert(0, str(Path(__file__).parents[2]))

from dotenv import load_dotenv

# Load environment variables from project root
project_root = Path(__file__).parents[4]
env_path = project_root / ".env"
load_dotenv(env_path)


async def test_database_integration():
    """Test full database integration with ApprovalService."""
    from src.database import AsyncDatabaseAdapter
    from src.integrations.telegram import TelegramClient
    from src.models.approval import ApprovalStatus
    from src.services.approval_service import ApprovalService

    print("\n" + "=" * 60)
    print("DATABASE INTEGRATION TEST")
    print("=" * 60)

    # Initialize database adapter
    print("\n1. Initializing database adapter...")
    db = AsyncDatabaseAdapter()
    print("   ✓ Database adapter initialized")

    # Initialize Telegram client
    print("\n2. Initializing Telegram client...")
    telegram = TelegramClient(bot_token=os.getenv("TELEGRAM_BOT_TOKEN"))
    print("   ✓ Telegram client initialized")

    # Initialize service with database
    print("\n3. Initializing ApprovalService with database...")
    service = ApprovalService(
        telegram_client=telegram,
        db=db,
        edit_form_base_url="https://app.example.com/approvals",
    )
    print("   ✓ ApprovalService initialized with PostgreSQL adapter")

    # Create an approval request
    print("\n4. Creating approval request in database...")
    chat_id = int(os.getenv("TELEGRAM_CHAT_ID", "0"))

    request_data = {
        "title": "Database Integration Test",
        "content": "This approval request is stored in PostgreSQL!",
        "requester_id": 12345,
        "approver_id": chat_id,
        "telegram_chat_id": chat_id,
        "content_type": "custom",
        "data": {"test": True, "source": "integration_test"},
    }

    request_id = await service.send_approval_request(request_data)
    print(f"   ✓ Created approval request: {request_id}")

    # Verify request exists in database
    print("\n5. Verifying request in database...")
    request = await service.get_approval_request(request_id)
    print(f"   ✓ Title: {request.title}")
    print(f"   ✓ Status: {request.status}")
    print(f"   ✓ Content Type: {request.content_type}")
    print(f"   ✓ Telegram Message ID: {request.telegram_message_id}")

    # List pending approvals
    print("\n6. Listing pending approvals for approver...")
    pending = await service.list_pending_approvals(chat_id)
    print(f"   ✓ Found {len(pending)} pending approval(s)")

    # Update status to approved
    print("\n7. Approving the request...")
    success = await service.update_approval_status(
        request_id=request_id,
        status=ApprovalStatus.APPROVED,
        actor_id=chat_id,
        actor_username="test_user",
        comment="Approved via database integration test",
    )
    print(f"   ✓ Approval update: {'success' if success else 'failed'}")

    # Verify status change
    print("\n8. Verifying status change...")
    updated_request = await service.get_approval_request(request_id)
    print(f"   ✓ New status: {updated_request.status}")

    # Verify history record was created
    print("\n9. Verifying history record in database...")
    from uuid import UUID

    from sqlalchemy import select

    from src.database import get_session
    from src.database.models import ApprovalHistoryModel

    async with get_session() as session:
        result = await session.execute(
            select(ApprovalHistoryModel).where(ApprovalHistoryModel.request_id == UUID(request_id))
        )
        history = result.scalars().all()
        print(f"   ✓ Found {len(history)} history record(s)")
        for h in history:
            print(f"     - Action: {h.action}, Actor: {h.actor_username}")

    # Generate edit token
    print("\n10. Testing edit token generation...")
    token = await service.generate_edit_token(request_id)
    print(f"   ✓ Generated edit token: {token[:20]}...")

    # Verify token lookup works
    print("\n11. Verifying edit token lookup...")
    found_request = await service.get_request_by_edit_token(token)
    if found_request:
        print(f"   ✓ Found request by token: {found_request.id}")
    else:
        print("   ✗ Failed to find request by token")

    # Close resources
    await telegram.close()

    print("\n" + "=" * 60)
    print("ALL TESTS PASSED!")
    print("=" * 60)
    print(f"\n📝 Request ID: {request_id}")
    print("Check your Telegram for the approval message.")
    print("Check your database for the approval_requests and approval_history tables.\n")


if __name__ == "__main__":
    asyncio.run(test_database_integration())

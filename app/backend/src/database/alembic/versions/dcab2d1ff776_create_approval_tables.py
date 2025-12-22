"""create_approval_tables

Revision ID: dcab2d1ff776
Revises:
Create Date: 2025-12-22 06:44:36.928752

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID, ENUM


# revision identifiers, used by Alembic.
revision: str = 'dcab2d1ff776'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Define enum types - create_type=False prevents auto-creation in table
approval_status_enum = ENUM(
    'pending', 'approved', 'disapproved', 'editing', 'expired', 'cancelled',
    name='approval_status',
    create_type=False
)

approval_content_type_enum = ENUM(
    'budget', 'document', 'content', 'custom',
    name='approval_content_type',
    create_type=False
)

approval_action_enum = ENUM(
    'approve', 'disapprove', 'edit', 'cancel', 'expire', 'resubmit', 'notify',
    name='approval_action',
    create_type=False
)


def upgrade() -> None:
    # Create enum types first using raw SQL (IF NOT EXISTS for safety)
    op.execute("CREATE TYPE approval_status AS ENUM ('pending', 'approved', 'disapproved', 'editing', 'expired', 'cancelled')")
    op.execute("CREATE TYPE approval_content_type AS ENUM ('budget', 'document', 'content', 'custom')")
    op.execute("CREATE TYPE approval_action AS ENUM ('approve', 'disapprove', 'edit', 'cancel', 'expire', 'resubmit', 'notify')")

    # Create approval_requests table
    op.create_table(
        'approval_requests',
        sa.Column('id', UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), primary_key=True),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('content_type', approval_content_type_enum, nullable=False, server_default='custom'),
        sa.Column('status', approval_status_enum, nullable=False, server_default='pending'),
        sa.Column('requester_id', sa.BigInteger, nullable=False),
        sa.Column('approver_id', sa.BigInteger, nullable=False),
        sa.Column('telegram_chat_id', sa.BigInteger, nullable=False),
        sa.Column('telegram_message_id', sa.BigInteger, nullable=True),
        sa.Column('data', JSONB, nullable=False, server_default='{}'),
        sa.Column('edit_token', sa.String(64), nullable=True, unique=True),
        sa.Column('edit_token_expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
    )

    # Create indexes on approval_requests
    op.create_index('ix_approval_requests_status', 'approval_requests', ['status'])
    op.create_index('ix_approval_requests_approver_id', 'approval_requests', ['approver_id'])
    op.create_index('ix_approval_requests_telegram_message_id', 'approval_requests', ['telegram_message_id'])
    op.create_index('ix_approval_requests_approver_created', 'approval_requests', ['approver_id', 'created_at'])
    op.create_index('ix_approval_requests_status_created', 'approval_requests', ['status', 'created_at'])

    # Create approval_history table
    op.create_table(
        'approval_history',
        sa.Column('id', UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), primary_key=True),
        sa.Column('request_id', UUID(as_uuid=True), sa.ForeignKey('approval_requests.id', ondelete='CASCADE'), nullable=False),
        sa.Column('action', approval_action_enum, nullable=False),
        sa.Column('actor_id', sa.BigInteger, nullable=False),
        sa.Column('actor_username', sa.String(255), nullable=True),
        sa.Column('comment', sa.Text, nullable=True),
        sa.Column('edited_data', JSONB, nullable=True),
        sa.Column('previous_status', approval_status_enum, nullable=True),
        sa.Column('new_status', approval_status_enum, nullable=True),
        sa.Column('telegram_callback_query_id', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
    )

    # Create index on approval_history
    op.create_index('ix_approval_history_request_id', 'approval_history', ['request_id'])


def downgrade() -> None:
    # Drop tables
    op.drop_table('approval_history')
    op.drop_table('approval_requests')

    # Drop enum types
    op.execute('DROP TYPE IF EXISTS approval_action')
    op.execute('DROP TYPE IF EXISTS approval_content_type')
    op.execute('DROP TYPE IF EXISTS approval_status')

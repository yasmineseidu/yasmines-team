-- Migration: 009_approval_tables.sql
-- Description: Create approval workflow tables for Telegram-based approval system
-- Created: 2025-12-22
-- Author: Claude Agent SDK

-- ============================================================================
-- UP MIGRATION
-- ============================================================================

-- Create approval status enum
CREATE TYPE approval_status AS ENUM ('pending', 'approved', 'disapproved', 'editing', 'expired', 'cancelled');

-- Create approval content type enum
CREATE TYPE approval_content_type AS ENUM ('budget', 'document', 'content', 'custom');

-- ============================================================================
-- APPROVAL_REQUESTS TABLE
-- Main table for storing approval requests
-- ============================================================================
CREATE TABLE IF NOT EXISTS approval_requests (
    -- Primary key
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Request identification
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    content_type approval_content_type NOT NULL DEFAULT 'custom',

    -- Status tracking
    status approval_status NOT NULL DEFAULT 'pending',

    -- User references
    requester_id INTEGER NOT NULL,
    approver_id INTEGER NOT NULL,

    -- Telegram references (for message editing)
    telegram_message_id BIGINT,
    telegram_chat_id BIGINT NOT NULL,

    -- Flexible data storage for different approval types
    data JSONB NOT NULL DEFAULT '{}',

    -- Edit token for web-based editing
    edit_token VARCHAR(255),
    edit_token_expires_at TIMESTAMP WITH TIME ZONE,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE,

    -- Constraints
    CONSTRAINT approval_requests_title_length CHECK (LENGTH(title) >= 1 AND LENGTH(title) <= 255),
    CONSTRAINT approval_requests_content_length CHECK (LENGTH(content) >= 1)
);

-- ============================================================================
-- APPROVAL_HISTORY TABLE
-- Audit trail for all approval actions
-- ============================================================================
CREATE TABLE IF NOT EXISTS approval_history (
    -- Primary key
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Reference to approval request
    request_id UUID NOT NULL REFERENCES approval_requests(id) ON DELETE CASCADE,

    -- Action taken
    action VARCHAR(50) NOT NULL,

    -- Who took the action
    actor_id INTEGER NOT NULL,
    actor_username VARCHAR(255),

    -- Additional details
    comment TEXT,
    edited_data JSONB,
    previous_status approval_status,
    new_status approval_status,

    -- Telegram context
    telegram_callback_query_id VARCHAR(255),

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),

    -- Constraints
    CONSTRAINT approval_history_action_valid CHECK (
        action IN ('approve', 'disapprove', 'edit', 'cancel', 'expire', 'resubmit', 'notify')
    )
);

-- ============================================================================
-- INDEXES
-- Optimized for common query patterns
-- ============================================================================

-- Filter by status (list pending approvals)
CREATE INDEX idx_approval_requests_status
    ON approval_requests(status);

-- List pending approvals for specific approver
CREATE INDEX idx_approval_requests_approver_pending
    ON approval_requests(approver_id, created_at DESC)
    WHERE status = 'pending';

-- List all approvals for specific approver
CREATE INDEX idx_approval_requests_approver
    ON approval_requests(approver_id, created_at DESC);

-- List all approvals by requester
CREATE INDEX idx_approval_requests_requester
    ON approval_requests(requester_id, created_at DESC);

-- Find by Telegram message ID (for callback handling)
CREATE INDEX idx_approval_requests_telegram_message
    ON approval_requests(telegram_chat_id, telegram_message_id)
    WHERE telegram_message_id IS NOT NULL;

-- Lookup by edit token
CREATE INDEX idx_approval_requests_edit_token
    ON approval_requests(edit_token)
    WHERE edit_token IS NOT NULL;

-- Find expired requests
CREATE INDEX idx_approval_requests_expires
    ON approval_requests(expires_at)
    WHERE expires_at IS NOT NULL AND status = 'pending';

-- Audit trail for specific request
CREATE INDEX idx_approval_history_request
    ON approval_history(request_id, created_at DESC);

-- Actor's history
CREATE INDEX idx_approval_history_actor
    ON approval_history(actor_id, created_at DESC);

-- ============================================================================
-- TRIGGERS
-- ============================================================================

-- Update updated_at timestamp on modification
CREATE OR REPLACE FUNCTION update_approval_requests_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_approval_requests_updated_at
    BEFORE UPDATE ON approval_requests
    FOR EACH ROW
    EXECUTE FUNCTION update_approval_requests_updated_at();

-- ============================================================================
-- DOWN MIGRATION
-- ============================================================================
-- To rollback, run these commands:
-- DROP TRIGGER IF EXISTS trigger_approval_requests_updated_at ON approval_requests;
-- DROP FUNCTION IF EXISTS update_approval_requests_updated_at();
-- DROP TABLE IF EXISTS approval_history;
-- DROP TABLE IF EXISTS approval_requests;
-- DROP TYPE IF EXISTS approval_content_type;
-- DROP TYPE IF EXISTS approval_status;

-- ============================================================================
-- COMMENTS
-- ============================================================================
COMMENT ON TABLE approval_requests IS 'Stores approval requests sent via Telegram';
COMMENT ON TABLE approval_history IS 'Audit trail for all approval actions';
COMMENT ON COLUMN approval_requests.data IS 'Flexible JSONB field for type-specific data (budget amounts, file URLs, etc.)';
COMMENT ON COLUMN approval_requests.edit_token IS 'JWT or UUID token for secure web-based editing';
COMMENT ON COLUMN approval_history.edited_data IS 'Stores what was changed during edit actions';

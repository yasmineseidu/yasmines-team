# Telegram Approval Workflow

## Overview

The Telegram Approval Workflow system enables human-in-the-loop approval processes through Telegram's messaging platform. It supports budget approvals, document reviews, content approvals, and custom approval types.

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  ApprovalAgent  │────▶│ ApprovalService  │────▶│ TelegramClient  │
│  (Orchestrator) │     │ (Business Logic) │     │ (API Interface) │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                               │
                               ▼
                        ┌──────────────────┐
                        │ ApprovalHandler  │
                        │ (Telegram Events)│
                        └──────────────────┘
```

## Components

### ApprovalAgent (`src/agents/approval_agent.py`)
- Orchestrates the approval workflow
- Provides high-level API for sending approvals
- Manages Telegram polling or webhook mode
- Handles agent lifecycle (initialize, health check, close)

### ApprovalService (`src/services/approval_service.py`)
- Business logic for approval operations
- Formats messages for different content types
- Manages approval state transitions
- Generates edit tokens for secure modifications

### ApprovalBotHandler (`src/integrations/approval_handler.py`)
- Processes Telegram updates (messages, callbacks)
- Routes approve/disapprove/edit button clicks
- Handles disapproval reason collection
- Updates message UI after actions

### API Routes
- `src/api/routes/telegram.py` - Webhook endpoints
- `src/api/routes/approval.py` - REST API endpoints

## Approval Types

| Type | Icon | Use Case |
|------|------|----------|
| Budget | 📊 | Financial approvals with amount and department |
| Document | 📄 | File reviews with URL and document type |
| Content | 📝 | Blog posts, marketing materials with tags |
| Custom | 📋 | Generic approvals with custom data |

## Status Lifecycle

```
PENDING ──┬──▶ APPROVED
          │
          ├──▶ DISAPPROVED
          │
          ├──▶ EDITING ──▶ PENDING (resubmit)
          │
          ├──▶ CANCELLED
          │
          └──▶ EXPIRED
```

## Message Format

Approval messages include:
- Type-specific emoji and header
- Title and description
- Type-specific metadata (amount, URL, tags)
- Three action buttons: Approve, Disapprove, Edit

Example budget approval:

```
📊 Budget Approval Request

Title: Q4 Marketing Budget
Amount: $50,000
Department: Marketing

Budget allocation for Q4 marketing campaigns...

[✅ Approve] [❌ Disapprove] [✏️ Edit]
```

## Button Actions

### Approve
1. User clicks "Approve"
2. System verifies user is the designated approver
3. Status updates to APPROVED
4. Message updates with approval confirmation
5. Requester receives notification

### Disapprove
1. User clicks "Disapprove"
2. Bot prompts for reason
3. User replies with reason text
4. Status updates to DISAPPROVED with reason
5. Message updates with disapproval details
6. Requester receives notification

### Edit
1. User clicks "Edit"
2. System generates secure edit token (24h expiry)
3. Bot sends edit form URL
4. User makes changes in web form
5. Status returns to PENDING for re-approval

## Database Schema

### approval_requests
| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| title | VARCHAR(500) | Request title |
| content | TEXT | Request description |
| content_type | ENUM | budget/document/content/custom |
| status | ENUM | pending/approved/disapproved/etc |
| requester_id | BIGINT | Telegram user ID of requester |
| approver_id | BIGINT | Telegram user ID of approver |
| telegram_chat_id | BIGINT | Chat where message was sent |
| telegram_message_id | BIGINT | Message ID for editing |
| data | JSONB | Type-specific metadata |
| edit_token | VARCHAR(64) | Secure token for edit access |
| edit_token_expires_at | TIMESTAMP | Token expiration |
| approved_at/disapproved_at | TIMESTAMP | Action timestamps |
| approval_reason/disapproval_reason | TEXT | Optional reasons |

### approval_history
Audit log of all status changes with actor, action, and details.

## Configuration

Environment variables:
- `TELEGRAM_BOT_TOKEN` - Bot token from @BotFather
- `APPROVAL_EDIT_FORM_URL` - Base URL for edit forms
- `TELEGRAM_WEBHOOK_URL` - Webhook URL (if using webhooks)
- `TELEGRAM_WEBHOOK_SECRET` - Webhook verification token

## Security

- **Approver Verification**: Only designated approver can take action
- **Edit Tokens**: Cryptographically secure, time-limited tokens
- **Webhook Verification**: Secret token validates webhook requests
- **Rate Limiting**: Respects Telegram API limits (1 msg/sec/chat)

## Integration Points

The approval workflow integrates with:
- **Telegram Bot API**: Message sending and updates
- **Database**: PostgreSQL with JSONB for flexible metadata
- **Web Application**: Edit form for modifications
- **Notification System**: Alerts for status changes

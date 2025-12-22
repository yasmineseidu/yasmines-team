# Task: Create Approval Database Schema

**Status:** Pending
**Domain:** Backend
**Source:** Telegram Approval Workflow System
**Created:** 2025-12-22

## Summary

Create database schema for approval request tracking system with two main tables: `approval_requests` for storing approval requests and `approval_history` for tracking approval actions. This is the foundation for the entire approval workflow.

## Files to Create/Modify

- [ ] `app/backend/src/database/migrations/[timestamp]_create_approval_tables.sql`
- [ ] `app/backend/src/models/approval.py` (dataclasses for ORM mapping)

## Implementation Checklist

- [ ] Create `approval_requests` table with:
  - `id` UUID PRIMARY KEY
  - `title` VARCHAR(255)
  - `content` TEXT
  - `status` ENUM('pending', 'approved', 'disapproved', 'editing')
  - `requester_id` INT
  - `approver_id` INT
  - `telegram_message_id` INT
  - `telegram_chat_id` INT
  - `data` JSONB (for storing request-specific data)
  - `created_at` TIMESTAMP DEFAULT NOW()
  - `updated_at` TIMESTAMP DEFAULT NOW()

- [ ] Create `approval_history` table with:
  - `id` UUID PRIMARY KEY
  - `request_id` UUID REFERENCES approval_requests(id) ON DELETE CASCADE
  - `action` VARCHAR(50) ('approve', 'disapprove', 'edit')
  - `approver_id` INT
  - `comment` TEXT
  - `edited_data` JSONB
  - `created_at` TIMESTAMP DEFAULT NOW()

- [ ] Create indexes:
  - `approval_requests (status)` for filtering by status
  - `approval_requests (approver_id, created_at)` for listing pending approvals
  - `approval_requests (telegram_message_id)` for finding messages
  - `approval_history (request_id)` for audit trail

- [ ] Create migration file with:
  - UP migration (create tables and indexes)
  - DOWN migration (drop tables)

- [ ] Define Python dataclasses for ORM mapping
- [ ] Add migration to version control

## Verification

```bash
# List migrations
ls -la app/backend/src/database/migrations/ | grep approval

# Check migration file exists
cat app/backend/src/database/migrations/*/create_approval_tables.sql

# Verify schema (after migration runs)
psql $DATABASE_URL -c "\dt approval_*"
psql $DATABASE_URL -c "\di approval_*"
```

## Notes

- Use existing database connection (Supabase PostgreSQL)
- Follow project migration pattern (timestamp prefix)
- JSONB allows flexible storage of approval-specific data
- Cascade delete on request deletion for data integrity

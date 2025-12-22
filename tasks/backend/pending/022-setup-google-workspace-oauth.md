# Task: Setup Google Workspace OAuth Infrastructure

**Status:** Pending
**Domain:** backend
**Source:** Smarter Team - Integration Registry
**Created:** 2025-12-21
**Priority:** HIGH

## Summary

Implement unified Google Workspace OAuth infrastructure that supports all Google services (Gmail, Calendar, Drive, Tasks, Docs, Sheets, Forms, Meet). This is foundational for all Google service integrations.

## Files to Create/Modify

- [ ] `src/integrations/google_oauth.py` - Unified Google OAuth client
- [ ] `src/integrations/google_workspace_base.py` - Base class for Google services
- [ ] `src/integrations/__init__.py` - Export Google OAuth client
- [ ] `tests/unit/integrations/test_google_oauth.py` - Unit tests
- [ ] `.env.example` - Add GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REDIRECT_URI
- [ ] `docs/integrations/google-oauth-setup.md` - Comprehensive setup guide
- [ ] `docs/integrations/google-workspace-scopes.md` - Scopes documentation

## Implementation Checklist

- [ ] Create Google Cloud Console project setup guide
- [ ] Document OAuth consent screen configuration
- [ ] Create unified Google OAuth client extending `BaseIntegrationClient`
- [ ] Implement PKCE (Proof Key for Code Exchange) flow
- [ ] Implement authorization URL generation with state parameter
- [ ] Implement token exchange mechanism
- [ ] Implement token refresh logic (tokens expire in 1 hour)
- [ ] Add encrypted token storage in database
- [ ] Implement scope minimization for security
- [ ] Add CSRF protection via state parameter validation
- [ ] Create base class for Google service clients
- [ ] Add comprehensive error handling
- [ ] Write unit tests with >85% coverage
- [ ] Document all required scopes per service
- [ ] Create token rotation strategy
- [ ] Add health check endpoint for token validity

## Scopes Required (by Service)

- **Gmail:** gmail.send, gmail.readonly, gmail.modify
- **Google Calendar:** calendar, calendar.events, calendar.readonly
- **Google Drive:** drive, drive.file, drive.readonly
- **Google Tasks:** tasks, tasks.readonly
- **Google Docs:** documents, documents.readonly, drive.file
- **Google Sheets:** spreadsheets, spreadsheets.readonly, drive.file
- **Google Forms:** forms, forms.body, forms.responses.readonly
- **Google Meet:** meetings.space.created, meetings.space.readonly

## Verification

```bash
# Test unit tests pass
uv run pytest tests/unit/integrations/test_google_oauth.py -v --cov=src/integrations/google_oauth --cov-report=term-missing

# Verify coverage >85%
uv run pytest tests/unit/integrations/test_google_oauth.py --cov=src/integrations/google_oauth --cov-report=html

# Check health endpoint
curl http://localhost:8000/health/integrations/google_oauth

# Test OAuth flow (manual)
# 1. Get authorization URL
# 2. Redirect user to Google consent screen
# 3. Exchange code for token
# 4. Verify refresh token storage
```

## Notes

- **Cost:** FREE (Google Workspace APIs are free)
- **Rate Limits:** Vary by service (250 QPS for Gmail, 100 read/write per 100s for Sheets)
- **Token Expiry:** 1 hour (use refresh token to get new access token)
- **Security:** Requires Client ID and Client Secret from Google Cloud Console
- **Scope Minimization:** Only request scopes needed for each service
- **Phase:** Phase 1 (Social & Google Workspace - Week 1-2)
- **Depends On:** Database for token storage, encryption library

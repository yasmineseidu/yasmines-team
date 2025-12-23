# Google Integrations Learning Log

**Purpose:** Document mistakes, errors, and learnings during Google Tasks and Google Contacts integration implementation. No verbosity - captured for next agent to learn from.

---

## Google Tasks Integration Learnings

### Mistakes to Avoid

- [ ] **Scope Mismatch Error**
  - Problem: Requesting `tasks.readonly` scope when only `tasks` is authorized
  - Solution: Use single broad scope for domain-wide delegation
  - Commit: If error occurs during live testing, document here

- [ ] **API Endpoint Issues**
  - Problem: Task creation/update fields don't match API spec
  - Solution: Reference official Google Tasks API v1 documentation
  - Commit: If issue found, document the exact field mismatch

- [ ] **Timezone Handling**
  - Problem: Task due dates lose timezone information
  - Solution: Store as ISO 8601 with timezone or UTC
  - Commit: If timezone bug found during testing, document behavior

- [ ] **Pagination Problems**
  - Problem: list_tasks() doesn't handle nextPageToken correctly
  - Solution: Keep requesting with token until response.pageToken is None
  - Commit: If pagination fails, document limit encountered

### Performance Baseline

Once live API testing completes:
- [ ] Record create_task() response time: _____ ms
- [ ] Record update_task() response time: _____ ms
- [ ] Record list_tasks() (10 items) response time: _____ ms
- [ ] Record delete_task() response time: _____ ms

---

## Google Contacts Integration Learnings

### Mistakes to Avoid

- [ ] **Contact Fields Validation**
  - Problem: Not all contact fields are editable or returned consistently
  - Solution: Check `displayName` vs `names` array, handle both
  - Commit: If field mapping issue found, document here

- [ ] **Search Operator Issues**
  - Problem: search_contacts() doesn't support free-form queries
  - Solution: Use query operators: `name:"John"`, `email:"user@example.com"`
  - Commit: If search limitation found, document operators supported

- [ ] **Contact Group Membership**
  - Problem: Adding contact to group requires separate API call
  - Solution: Use memberships array or separate groupMembership methods
  - Commit: If group membership fails, document the approach needed

- [ ] **Duplicate Detection**
  - Problem: No built-in duplicate detection in Google Contacts API
  - Solution: Implement client-side deduplication by email/phone
  - Commit: If duplicates created during testing, document dedup logic

- [ ] **Deleted Contacts Recovery**
  - Problem: Deleted contacts may still be retrievable
  - Solution: Check API documentation for soft-delete vs hard-delete behavior
  - Commit: If deletion behavior unexpected, document actual behavior

### Performance Baseline

Once live API testing completes:
- [ ] Record create_contact() response time: _____ ms
- [ ] Record update_contact() response time: _____ ms
- [ ] Record list_contacts() (10 items) response time: _____ ms
- [ ] Record search_contacts() response time: _____ ms
- [ ] Record delete_contact() response time: _____ ms

---

## Pre-commit Hook Failures to Document

### If Ruff Linting Fails
- Issue: _________________________________
- Fix Applied: _________________________________
- Root Cause: _________________________________

### If MyPy Type Checking Fails
- Issue: _________________________________
- Fix Applied: _________________________________
- Root Cause: _________________________________

### If Security Checks Fail
- Issue: _________________________________
- Fix Applied: _________________________________
- Root Cause: _________________________________

---

## Live API Testing Issues

### Google Tasks API
- [ ] Endpoint: create_task() - Status: _____ - Issue: _______
- [ ] Endpoint: get_task() - Status: _____ - Issue: _______
- [ ] Endpoint: update_task() - Status: _____ - Issue: _______
- [ ] Endpoint: delete_task() - Status: _____ - Issue: _______
- [ ] Endpoint: list_tasks() - Status: _____ - Issue: _______
- [ ] Endpoint: create_task_list() - Status: _____ - Issue: _______
- [ ] Endpoint: list_task_lists() - Status: _____ - Issue: _______

### Google Contacts API
- [ ] Endpoint: create_contact() - Status: _____ - Issue: _______
- [ ] Endpoint: get_contact() - Status: _____ - Issue: _______
- [ ] Endpoint: update_contact() - Status: _____ - Issue: _______
- [ ] Endpoint: delete_contact() - Status: _____ - Issue: _______
- [ ] Endpoint: list_contacts() - Status: _____ - Issue: _______
- [ ] Endpoint: search_contacts() - Status: _____ - Issue: _______
- [ ] Endpoint: create_contact_group() - Status: _____ - Issue: _______
- [ ] Endpoint: list_contact_groups() - Status: _____ - Issue: _______

---

## Coverage Gaps

### Unit Test Coverage Issues
- Missing coverage: _________________________________
- Why it matters: _________________________________
- How to fix: _________________________________

### Integration Test Gaps
- Missing scenario: _________________________________
- Why critical: _________________________________
- Test to add: _________________________________

---

## Deployment Issues

### Git Commit Problems
- Issue: _________________________________
- Error Message: _________________________________
- Resolution: _________________________________

### API Key Leakage
- Scope: _________________________________
- How Detected: _________________________________
- Fixed By: _________________________________

### GitHub Push Failures
- Error: _________________________________
- Root Cause: _________________________________
- Solution: _________________________________

---

## Patterns Discovered

### What Worked Well
1. ___________________________________________
2. ___________________________________________
3. ___________________________________________

### What to Improve
1. ___________________________________________
2. ___________________________________________
3. ___________________________________________

---

## Next Agent Quick Reference

**If re-running Google Tasks Integration:**
- Start with: `tasks/backend/pending/019-implement-google-tasks-integration.md`
- Most common issue: _________________________________
- Watch out for: _________________________________
- Fast fix for: _________________________________

**If re-running Google Contacts Integration:**
- Start with: `tasks/backend/pending/020-implement-google-contacts-integration.md`
- Most common issue: _________________________________
- Watch out for: _________________________________
- Fast fix for: _________________________________

**Scope Authorization (Already Done):**
- Service Account: `smarterteam@smarter-team.iam.gserviceaccount.com`
- Authorized Scopes: See `.claude/context/SELF-HEALING.md` (lines 264-278)
- Additional Scope Needed: `https://www.googleapis.com/auth/contacts`

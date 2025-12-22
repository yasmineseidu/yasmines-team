# Task: Setup Cloudflare Integration

**Status:** Pending
**Domain:** backend
**Source:** Smarter Team - Integration Registry
**Created:** 2025-12-21
**Priority:** HIGH

## Summary

Implement Cloudflare integration for CDN, DDoS protection, DNS management, and R2 object storage (S3-compatible, cheaper alternative).

## Files to Create/Modify

- [ ] `src/integrations/cloudflare.py` - Cloudflare API client
- [ ] `src/integrations/cloudflare_r2.py` - R2 storage operations
- [ ] `src/integrations/__init__.py` - Export Cloudflare clients
- [ ] `tests/unit/integrations/test_cloudflare.py` - Unit tests
- [ ] `.env.example` - Add CLOUDFLARE_API_TOKEN, CLOUDFLARE_ACCOUNT_ID, CLOUDFLARE_ZONE_ID
- [ ] `docs/integrations/cloudflare-setup.md` - Setup documentation

## Implementation Checklist

- [ ] Create Cloudflare API client extending `BaseIntegrationClient`
- [ ] Implement DNS record management (A, CNAME, MX, TXT)
- [ ] Implement zone management operations
- [ ] Implement R2 bucket creation and management
- [ ] Implement R2 object upload with encryption
- [ ] Implement R2 object download
- [ ] Implement R2 object listing and filtering
- [ ] Implement R2 presigned URL generation
- [ ] Implement CDN cache purge
- [ ] Implement DDoS protection rules
- [ ] Implement page rules and redirects
- [ ] Add rate limiting per API endpoint
- [ ] Add comprehensive error handling
- [ ] Write unit tests with >85% coverage
- [ ] Add health check endpoint
- [ ] Compare with AWS S3 for cost/benefits

## Verification

```bash
# Test unit tests pass
uv run pytest tests/unit/integrations/test_cloudflare.py -v --cov=src/integrations/cloudflare --cov-report=term-missing

# Verify coverage >85%
uv run pytest tests/unit/integrations/test_cloudflare.py --cov=src/integrations/cloudflare --cov-report=html

# Check health endpoint
curl http://localhost:8000/health/integrations/cloudflare

# Test R2 upload
python -c "from src.integrations import CloudflareR2Client; client = CloudflareR2Client(...); client.upload_file('local.pdf', 'remote.pdf')"
```

## Notes

- **Cost:** ~$20-100/month (much cheaper than AWS S3, especially for egress)
- **R2 Benefit:** FREE egress (vs S3 ~$0.09/GB), same API as S3
- **Rate Limits:** Vary by endpoint, generally generous
- **Setup:** Requires API token and Account ID from Cloudflare dashboard
- **R2:** S3-compatible object storage, cheaper alternative to AWS
- **CDN:** Global content delivery, DDoS protection included
- **DNS:** Advanced DNS management, security features
- **Phase:** Phase 3 (Cloud Infrastructure - Week 4-6)
- **Strategy:** Use for file storage (free egress), AWS Lambda for compute

"""
Test fixtures for Apify integration client.

Provides mock data for unit and integration tests.

Waterfall Actors (in priority order):
1. Leads Finder Primary (IoSHqwTR9YGhzccez) - $1.5/1k leads
2. Leads Scraper PPE (T1XDXWc1L92AfIJtd) - Fallback
3. Leads Scraper Multi (VYRyEF4ygTTkaIghe) - Last resort
"""

# Sample primary lead scraper response (Leads Finder Primary)
PRIMARY_ACTOR_RUN_RESPONSE = {
    "id": "run_abc123",
    "actId": "IoSHqwTR9YGhzccez",
    "status": "SUCCEEDED",
    "defaultDatasetId": "dataset_xyz789",
    "startedAt": "2025-01-15T10:00:00.000Z",
    "finishedAt": "2025-01-15T10:05:30.000Z",
    "usage": {
        "COMPUTE_UNITS": 0.5,
        "TOTAL_USD": 1.50,  # $1.5/1k leads
    },
}

# Fallback actor response (Leads Scraper PPE)
FALLBACK_ACTOR_RUN_RESPONSE = {
    "id": "run_fallback123",
    "actId": "T1XDXWc1L92AfIJtd",
    "status": "SUCCEEDED",
    "defaultDatasetId": "dataset_fallback789",
    "startedAt": "2025-01-15T10:00:00.000Z",
    "finishedAt": "2025-01-15T10:06:00.000Z",
    "usage": {
        "COMPUTE_UNITS": 0.6,
        "TOTAL_USD": 2.00,
    },
}

# Last resort actor response (Leads Scraper Multi)
LAST_RESORT_ACTOR_RUN_RESPONSE = {
    "id": "run_lastresort123",
    "actId": "VYRyEF4ygTTkaIghe",
    "status": "SUCCEEDED",
    "defaultDatasetId": "dataset_lastresort789",
    "startedAt": "2025-01-15T10:00:00.000Z",
    "finishedAt": "2025-01-15T10:08:00.000Z",
    "usage": {
        "COMPUTE_UNITS": 0.8,
        "TOTAL_USD": 3.00,
    },
}

# Dataset items from lead scrapers (various field name formats)
LEAD_DATASET_ITEMS = [
    {
        "firstName": "John",
        "lastName": "Smith",
        "fullName": "John Smith",
        "email": "john.smith@techcorp.com",
        "linkedinUrl": "https://linkedin.com/in/johnsmith",
        "linkedinId": "johnsmith123",
        "headline": "VP of Engineering at TechCorp",
        "jobTitle": "VP of Engineering",
        "seniority": "VP",
        "department": "Engineering",
        "companyName": "TechCorp Inc",
        "companyLinkedinUrl": "https://linkedin.com/company/techcorp",
        "companyDomain": "techcorp.com",
        "companySize": "201-500",
        "industry": "Technology",
        "location": "San Francisco, CA",
        "city": "San Francisco",
        "state": "California",
        "country": "United States",
    },
    {
        "firstName": "Jane",
        "lastName": "Doe",
        "fullName": "Jane Doe",
        "email": "jane.doe@startup.io",
        "linkedinUrl": "https://linkedin.com/in/janedoe",
        "linkedinId": "janedoe456",
        "headline": "CTO at Startup.io",
        "jobTitle": "CTO",
        "seniority": "CXO",
        "department": "Technology",
        "companyName": "Startup.io",
        "companyLinkedinUrl": "https://linkedin.com/company/startup-io",
        "companyDomain": "startup.io",
        "companySize": "51-200",
        "industry": "Software",
        "location": "New York, NY",
        "city": "New York",
        "state": "New York",
        "country": "United States",
    },
    {
        "firstName": "Bob",
        "lastName": "Johnson",
        "fullName": "Bob Johnson",
        "email": None,  # No email found
        "linkedinUrl": "https://linkedin.com/in/bobjohnson",
        "linkedinId": "bobjohnson789",
        "headline": "Director of Sales at Enterprise Co",
        "jobTitle": "Director of Sales",
        "seniority": "Director",
        "department": "Sales",
        "companyName": "Enterprise Co",
        "companyLinkedinUrl": "https://linkedin.com/company/enterprise-co",
        "companyDomain": "enterprise.co",
        "companySize": "1001-5000",
        "industry": "Enterprise Software",
        "location": "Austin, TX",
        "city": "Austin",
        "state": "Texas",
        "country": "United States",
    },
]

# Sample Apollo.io scraper response
APOLLO_DATASET_ITEMS = [
    {
        "first_name": "Alice",
        "last_name": "Williams",
        "name": "Alice Williams",
        "email": "alice@fintech.com",
        "linkedin_url": "https://linkedin.com/in/alicewilliams",
        "title": "Head of Product",
        "seniority": "VP",
        "department": "Product",
        "organization": {
            "name": "FinTech Solutions",
            "primary_domain": "fintech.com",
            "estimated_num_employees": "500-1000",
            "industry": "Financial Services",
        },
        "city": "Chicago",
        "state": "Illinois",
        "country": "United States",
    },
    {
        "first_name": "Charlie",
        "last_name": "Brown",
        "name": "Charlie Brown",
        "email": "charlie@healthtech.org",
        "linkedin_url": "https://linkedin.com/in/charliebrown",
        "title": "CEO",
        "seniority": "CXO",
        "department": "Executive",
        "organization": {
            "name": "HealthTech Org",
            "primary_domain": "healthtech.org",
            "estimated_num_employees": "100-250",
            "industry": "Healthcare",
        },
        "city": "Boston",
        "state": "Massachusetts",
        "country": "United States",
    },
]

# Failed run response (primary actor)
FAILED_ACTOR_RUN_RESPONSE = {
    "id": "run_failed123",
    "actId": "IoSHqwTR9YGhzccez",  # Primary actor
    "status": "FAILED",
    "defaultDatasetId": None,
    "startedAt": "2025-01-15T10:00:00.000Z",
    "finishedAt": "2025-01-15T10:01:00.000Z",
    "usage": {
        "COMPUTE_UNITS": 0.1,
        "TOTAL_USD": 0.50,
    },
}

# Timed out run response (primary actor)
TIMED_OUT_ACTOR_RUN_RESPONSE = {
    "id": "run_timeout123",
    "actId": "IoSHqwTR9YGhzccez",  # Primary actor
    "status": "TIMED-OUT",
    "defaultDatasetId": None,
    "startedAt": "2025-01-15T10:00:00.000Z",
    "finishedAt": "2025-01-15T10:10:00.000Z",
    "usage": {
        "COMPUTE_UNITS": 1.0,
        "TOTAL_USD": 5.00,
    },
}

# User info response for health check
USER_INFO_RESPONSE = {
    "id": "user_12345",
    "username": "testuser",
    "email": "test@example.com",
    "plan": {
        "id": "plan_free",
        "monthlyBasePriceCents": 0,
    },
}

# Expected parsed leads from lead scraper items (using unified parser)
EXPECTED_PARSED_LEADS = [
    {
        "first_name": "John",
        "last_name": "Smith",
        "full_name": "John Smith",
        "email": "john.smith@techcorp.com",
        "linkedin_url": "https://linkedin.com/in/johnsmith",
        "linkedin_id": "johnsmith123",
        "headline": "VP of Engineering at TechCorp",
        "title": "VP of Engineering",
        "seniority": "VP",
        "department": "Engineering",
        "company_name": "TechCorp Inc",
        "company_linkedin_url": "https://linkedin.com/company/techcorp",
        "company_domain": "techcorp.com",
        "company_size": "201-500",
        "company_industry": "Technology",
        "location": "San Francisco, CA",
        "city": "San Francisco",
        "state": "California",
        "country": "United States",
        "source": "apify",
        "source_url": "https://linkedin.com/in/johnsmith",
    },
    {
        "first_name": "Jane",
        "last_name": "Doe",
        "full_name": "Jane Doe",
        "email": "jane.doe@startup.io",
        "linkedin_url": "https://linkedin.com/in/janedoe",
        "linkedin_id": "janedoe456",
        "headline": "CTO at Startup.io",
        "title": "CTO",
        "seniority": "CXO",
        "department": "Technology",
        "company_name": "Startup.io",
        "company_linkedin_url": "https://linkedin.com/company/startup-io",
        "company_domain": "startup.io",
        "company_size": "51-200",
        "company_industry": "Software",
        "location": "New York, NY",
        "city": "New York",
        "state": "New York",
        "country": "United States",
        "source": "apify",
        "source_url": "https://linkedin.com/in/janedoe",
    },
    {
        "first_name": "Bob",
        "last_name": "Johnson",
        "full_name": "Bob Johnson",
        "email": None,
        "linkedin_url": "https://linkedin.com/in/bobjohnson",
        "linkedin_id": "bobjohnson789",
        "headline": "Director of Sales at Enterprise Co",
        "title": "Director of Sales",
        "seniority": "Director",
        "department": "Sales",
        "company_name": "Enterprise Co",
        "company_linkedin_url": "https://linkedin.com/company/enterprise-co",
        "company_domain": "enterprise.co",
        "company_size": "1001-5000",
        "company_industry": "Enterprise Software",
        "location": "Austin, TX",
        "city": "Austin",
        "state": "Texas",
        "country": "United States",
        "source": "apify",
        "source_url": "https://linkedin.com/in/bobjohnson",
    },
]

# Expected parsed leads from snake_case format items (alternative actor output)
EXPECTED_SNAKE_CASE_LEADS = [
    {
        "first_name": "Alice",
        "last_name": "Williams",
        "full_name": "Alice Williams",
        "email": "alice@fintech.com",
        "linkedin_url": "https://linkedin.com/in/alicewilliams",
        "linkedin_id": None,
        "headline": None,
        "title": "Head of Product",
        "seniority": "VP",
        "department": "Product",
        "company_name": "FinTech Solutions",
        "company_linkedin_url": None,
        "company_domain": "fintech.com",
        "company_size": "500-1000",
        "company_industry": "Financial Services",
        "location": "Chicago",
        "city": "Chicago",
        "state": "Illinois",
        "country": "United States",
        "source": "apify",
        "source_url": None,
    },
    {
        "first_name": "Charlie",
        "last_name": "Brown",
        "full_name": "Charlie Brown",
        "email": "charlie@healthtech.org",
        "linkedin_url": "https://linkedin.com/in/charliebrown",
        "linkedin_id": None,
        "headline": None,
        "title": "CEO",
        "seniority": "CXO",
        "department": "Executive",
        "company_name": "HealthTech Org",
        "company_linkedin_url": None,
        "company_domain": "healthtech.org",
        "company_size": "100-250",
        "company_industry": "Healthcare",
        "location": "Boston",
        "city": "Boston",
        "state": "Massachusetts",
        "country": "United States",
        "source": "apify",
        "source_url": None,
    },
]

# Backwards compatibility aliases
LINKEDIN_ACTOR_RUN_RESPONSE = PRIMARY_ACTOR_RUN_RESPONSE
LINKEDIN_DATASET_ITEMS = LEAD_DATASET_ITEMS
EXPECTED_LINKEDIN_LEADS = EXPECTED_PARSED_LEADS
EXPECTED_APOLLO_LEADS = EXPECTED_SNAKE_CASE_LEADS

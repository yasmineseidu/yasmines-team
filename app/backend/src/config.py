"""
Application configuration management.

This module loads and manages all application settings from environment variables.
Configuration is separated by domain (database, cache, API, integrations, etc.)

Usage:
    from src.config import settings
    print(settings.database_url)
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings from environment variables."""

    # Application
    app_name: str = "smarter-team"
    environment: str = "development"
    debug: bool = True
    secret_key: str = "change-me-in-production"

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_prefix: str = "/api"
    allowed_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:8000",
    ]

    # Database
    database_url: str
    db_pool_size: int = 20
    db_max_overflow: int = 40
    db_pool_recycle: int = 3600
    db_pool_pre_ping: bool = True

    # Supabase
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_servicerole_key: str = ""

    # Redis
    redis_url: str
    redis_password: str = ""

    # Celery
    celery_broker_url: str | None = None
    celery_result_backend: str | None = None
    celery_task_serializer: str = "json"
    celery_timezone: str = "UTC"

    # Claude Agent SDK
    anthropic_api_key: str
    anthropic_model: str = "claude-opus-4-20250514"
    anthropic_request_timeout: int = 300

    # Pinecone
    pinecone_api_key: str = ""
    pinecone_environment: str = "us-west-2"
    pinecone_index_name: str = "smarter-team"

    # Zep
    zep_api_key: str = ""
    zep_base_url: str = "https://api.getzep.com"

    # Lead Enrichment - Anymailfinder (first in waterfall)
    anymailfinder_api_key: str = ""

    # JWT
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24
    jwt_refresh_expiration_days: int = 30

    # OAuth
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/api/auth/google/callback"

    quickbooks_client_id: str = ""
    quickbooks_client_secret: str = ""
    quickbooks_redirect_uri: str = "http://localhost:8000/api/integrations/quickbooks/callback"

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"
    log_file: str = "logs/app.log"

    # Feature Flags
    enable_webhooks: bool = True
    enable_rate_limiting: bool = True
    enable_audit_logging: bool = True
    enable_learning_system: bool = True

    # Rate Limiting
    rate_limit_requests_per_minute: int = 100
    rate_limit_requests_per_hour: int = 10000

    # Agent Settings
    max_agent_timeout_seconds: int = 300
    max_task_retries: int = 3
    task_retry_base_delay_ms: int = 100
    task_retry_max_delay_ms: int = 30000

    # Testing
    test_database_url: str = "sqlite+aiosqlite:///./test.db"
    skip_external_api_calls: bool = False
    use_mock_integrations: bool = True

    class Config:
        """Pydantic configuration."""

        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()

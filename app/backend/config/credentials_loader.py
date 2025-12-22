"""Load service account credentials from file or environment variables."""

import json
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


def load_gmail_service_account() -> dict | None:
    """Load Gmail service account credentials from file or environment.

    Tries three methods in order:
    1. GMAIL_SERVICE_ACCOUNT_JSON environment variable (JSON string)
    2. GMAIL_SERVICE_ACCOUNT_PATH environment variable (file path)
    3. Default path: config/credentials/gmail-service-account.json

    Returns:
        Service account credentials dict, or None if not found

    Example:
        >>> creds = load_gmail_service_account()
        >>> if creds:
        ...     client = GmailClient(credentials_json=creds)
        ...     await client.authenticate()
    """
    # Method 1: Check for inline JSON in environment
    json_str = os.getenv("GMAIL_SERVICE_ACCOUNT_JSON")
    if json_str:
        try:
            creds = json.loads(json_str)
            logger.info(
                "Loaded Gmail service account from GMAIL_SERVICE_ACCOUNT_JSON environment variable"
            )
            return creds
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse GMAIL_SERVICE_ACCOUNT_JSON: {e}")
            return None

    # Method 2: Check for file path in environment
    creds_path = os.getenv("GMAIL_SERVICE_ACCOUNT_PATH")
    if creds_path:
        return _load_credentials_from_file(creds_path)

    # Method 3: Check default path
    default_path = Path("config/credentials/gmail-service-account.json")
    if default_path.exists():
        return _load_credentials_from_file(str(default_path))

    logger.warning(
        "Gmail service account not found. Set GMAIL_SERVICE_ACCOUNT_JSON or "
        "GMAIL_SERVICE_ACCOUNT_PATH, or place credentials at "
        "config/credentials/gmail-service-account.json"
    )
    return None


def _load_credentials_from_file(file_path: str) -> dict | None:
    """Load credentials from a JSON file.

    Args:
        file_path: Path to service account JSON file

    Returns:
        Credentials dict, or None if file not found or invalid
    """
    path = Path(file_path)

    if not path.exists():
        logger.warning(f"Service account file not found: {file_path}")
        return None

    try:
        with open(path) as f:
            creds = json.load(f)
        logger.info(f"Loaded service account credentials from {file_path}")
        return creds
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse credentials file {file_path}: {e}")
        return None
    except Exception as e:
        logger.error(f"Failed to load credentials from {file_path}: {e}")
        return None


def get_gmail_client_config() -> dict | None:
    """Get Gmail client configuration from environment or credentials file.

    Returns configuration suitable for GmailClient initialization.

    Returns:
        Config dict with credentials, or None if not available

    Example:
        >>> config = get_gmail_client_config()
        >>> if config:
        ...     client = GmailClient(**config)
        ...     await client.authenticate()
    """
    # Try service account first
    service_account = load_gmail_service_account()
    if service_account:
        return {"credentials_json": service_account}

    # Fall back to OAuth 2.0 environment variables
    access_token = os.getenv("GMAIL_ACCESS_TOKEN")
    if access_token:
        return {
            "access_token": access_token,
            "refresh_token": os.getenv("GMAIL_REFRESH_TOKEN"),
            "client_id": os.getenv("GOOGLE_CLIENT_ID"),
            "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
        }

    logger.warning("No Gmail credentials found in environment or config/credentials/")
    return None

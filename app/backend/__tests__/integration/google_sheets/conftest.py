"""Pytest configuration and fixtures for Google Sheets integration tests.

Provides fixtures for OAuth token management and test data configuration.
"""

import json
import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

# Load .env file from project root (yasmines-team/)
# Path: conftest.py -> google_sheets -> integration -> __tests__ -> backend -> app -> yasmines-team
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")


def _resolve_path(path_str: str) -> Path:
    """Resolve a path that may be relative to project root."""
    path = Path(path_str)
    if path.is_absolute():
        return path
    # Try relative to project root
    resolved = PROJECT_ROOT / path
    if resolved.exists():
        return resolved
    return path


@pytest.fixture(scope="session")
def google_service_account_json() -> dict | None:
    """Get Google Service Account credentials from environment.

    Supports multiple env var names for compatibility:
    - GOOGLE_SERVICE_ACCOUNT_FILE
    - GOOGLE_SERVICE_ACCOUNT_PATH
    - GOOGLE_SHEETS_CREDENTIALS_JSON
    - GOOGLE_WORKSPACE_CREDENTIALS_JSON
    """
    # Try multiple env var names
    sa_file = (
        os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE")
        or os.getenv("GOOGLE_SERVICE_ACCOUNT_PATH")
        or os.getenv("GOOGLE_SHEETS_CREDENTIALS_JSON")
        or os.getenv("GOOGLE_WORKSPACE_CREDENTIALS_JSON")
    )

    if sa_file:
        resolved = _resolve_path(sa_file)
        if resolved.exists():
            with open(resolved) as f:
                return json.load(f)

    return None


@pytest.fixture(scope="session")
def google_delegated_user() -> str | None:
    """Get delegated user email for domain-wide delegation.

    Supports multiple env var names:
    - GOOGLE_DELEGATED_USER
    - GMAIL_USER_EMAIL
    """
    return os.getenv("GOOGLE_DELEGATED_USER") or os.getenv("GMAIL_USER_EMAIL")


@pytest.fixture(scope="session")
def google_sheets_access_token(
    google_service_account_json: dict | None,
    google_delegated_user: str | None,
) -> str:
    """Get Google access token for Sheets API integration tests.

    Uses domain-wide delegation with the spreadsheets scope.
    """
    if not google_service_account_json:
        pytest.skip(
            "Google Sheets authentication skipped: No service account\n\n"
            "To run live API tests:\n"
            "  1. Create service account in Google Cloud Console\n"
            "  2. Enable Google Sheets API\n"
            "  3. Set up domain-wide delegation in Google Admin\n"
            "  4. Download JSON key file\n"
            "  5. Set one of: GOOGLE_SERVICE_ACCOUNT_FILE, GOOGLE_SERVICE_ACCOUNT_PATH\n"
            "  6. Set one of: GOOGLE_DELEGATED_USER, GMAIL_USER_EMAIL\n"
            "  7. Run tests"
        )

    from google.auth.transport.requests import Request
    from google.oauth2.service_account import Credentials

    # Use single broad scope for domain-wide delegation
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]

    if google_delegated_user:
        try:
            credentials = Credentials.from_service_account_info(
                google_service_account_json,
                scopes=scopes,
                subject=google_delegated_user,
            )
            request = Request()
            credentials.refresh(request)
            print(f"✅ Using domain-wide delegation as: {google_delegated_user}")
            return credentials.token
        except Exception as e:
            pytest.skip(f"Domain-wide delegation failed: {e}")
    else:
        pytest.skip(
            "GOOGLE_DELEGATED_USER not set. Domain-wide delegation required for Sheets API."
        )


@pytest.fixture
def test_spreadsheet_data() -> dict:
    """Fixture providing test spreadsheet configuration."""
    return {
        "title": "Claude Code Test Spreadsheet",
        "sheets": [
            {"title": "Data"},
            {"title": "Summary"},
        ],
    }


@pytest.fixture
def sample_values() -> list[list]:
    """Fixture providing sample values for testing."""
    return [
        ["Name", "Age", "City", "Country"],
        ["Alice", 30, "New York", "USA"],
        ["Bob", 25, "London", "UK"],
        ["Charlie", 35, "Paris", "France"],
        ["Diana", 28, "Tokyo", "Japan"],
    ]


@pytest.fixture
def sample_formulas() -> list[list]:
    """Fixture providing sample formulas for testing."""
    return [
        ["Value1", "Value2", "Sum", "Average"],
        [10, 20, "=A2+B2", "=AVERAGE(A2:B2)"],
        [15, 25, "=A3+B3", "=AVERAGE(A3:B3)"],
        [100, 200, "=A4+B4", "=AVERAGE(A4:B4)"],
    ]


# ============ Comprehensive Sample Data Fixtures ============


@pytest.fixture
def sample_employee_data() -> list[list]:
    """Employee database sample data."""
    return [
        ["ID", "Name", "Department", "Salary", "Start Date", "Active"],
        [1001, "Alice Johnson", "Engineering", 95000, "2022-01-15", True],
        [1002, "Bob Smith", "Marketing", 72000, "2021-06-01", True],
        [1003, "Carol Williams", "Engineering", 105000, "2020-03-10", True],
        [1004, "David Brown", "Sales", 68000, "2023-02-20", True],
        [1005, "Eve Davis", "HR", 62000, "2019-11-05", False],
        [1006, "Frank Miller", "Engineering", 88000, "2022-08-15", True],
        [1007, "Grace Wilson", "Finance", 78000, "2021-04-01", True],
        [1008, "Henry Taylor", "Sales", 71000, "2022-12-01", True],
    ]


@pytest.fixture
def sample_sales_data() -> list[list]:
    """Sales tracking sample data with formulas."""
    return [
        ["Month", "Product A", "Product B", "Product C", "Total", "Growth %"],
        ["January", 15000, 22000, 8500, "=SUM(B2:D2)", ""],
        ["February", 18000, 19500, 9200, "=SUM(B3:D3)", "=((E3-E2)/E2)*100"],
        ["March", 21000, 24000, 11000, "=SUM(B4:D4)", "=((E4-E3)/E3)*100"],
        ["April", 19500, 26500, 12500, "=SUM(B5:D5)", "=((E5-E4)/E4)*100"],
        ["May", 23000, 28000, 14000, "=SUM(B6:D6)", "=((E6-E5)/E5)*100"],
        ["June", 25500, 31000, 15500, "=SUM(B7:D7)", "=((E7-E6)/E6)*100"],
    ]


@pytest.fixture
def sample_inventory_data() -> list[list]:
    """Inventory tracking sample data."""
    return [
        [
            "SKU",
            "Product Name",
            "Category",
            "Quantity",
            "Unit Price",
            "Total Value",
            "Reorder Level",
        ],
        ["SKU-001", "Widget A", "Electronics", 150, 29.99, "=D2*E2", 50],
        ["SKU-002", "Widget B", "Electronics", 75, 49.99, "=D3*E3", 25],
        ["SKU-003", "Gadget X", "Accessories", 200, 15.99, "=D4*E4", 100],
        ["SKU-004", "Gadget Y", "Accessories", 30, 89.99, "=D5*E5", 20],
        ["SKU-005", "Device Z", "Hardware", 45, 199.99, "=D6*E6", 15],
    ]


@pytest.fixture
def sample_project_tracker() -> list[list]:
    """Project tracking sample data."""
    return [
        ["Task ID", "Task Name", "Assignee", "Status", "Priority", "Due Date", "% Complete"],
        ["T-001", "Design mockups", "Alice", "Completed", "High", "2024-01-15", 100],
        ["T-002", "Backend API", "Bob", "In Progress", "High", "2024-01-25", 75],
        ["T-003", "Frontend UI", "Carol", "In Progress", "Medium", "2024-02-01", 50],
        ["T-004", "Testing", "David", "Not Started", "High", "2024-02-10", 0],
        ["T-005", "Documentation", "Eve", "Not Started", "Low", "2024-02-15", 0],
        ["T-006", "Deployment", "Frank", "Blocked", "Critical", "2024-02-20", 0],
    ]


@pytest.fixture
def sample_financial_data() -> list[list]:
    """Financial report sample data with complex formulas."""
    return [
        ["Category", "Q1", "Q2", "Q3", "Q4", "Annual Total", "YoY Change"],
        ["Revenue", 250000, 285000, 310000, 340000, "=SUM(B2:E2)", ""],
        ["COGS", 100000, 114000, 124000, 136000, "=SUM(B3:E3)", ""],
        ["Gross Profit", "=B2-B3", "=C2-C3", "=D2-D3", "=E2-E3", "=SUM(B4:E4)", ""],
        ["Operating Expenses", 75000, 78000, 82000, 85000, "=SUM(B5:E5)", ""],
        ["Net Income", "=B4-B5", "=C4-C5", "=D4-D5", "=E4-E5", "=SUM(B6:E6)", ""],
    ]


@pytest.fixture
def sample_mixed_types() -> list[list]:
    """Sample data with various data types."""
    return [
        ["String", "Integer", "Float", "Boolean", "Date", "Currency", "Percentage"],
        ["Hello", 42, 3.14159, True, "2024-01-15", "$1,234.56", "75%"],
        ["World", -100, 2.71828, False, "2024-06-30", "$9,876.54", "100%"],
        ["Test", 0, 0.0, True, "2024-12-31", "$0.00", "0%"],
        ["Data", 999999, 1.41421, False, "2025-01-01", "$50,000.00", "50.5%"],
    ]


@pytest.fixture
def sample_unicode_data() -> list[list]:
    """Sample data with unicode characters."""
    return [
        ["Language", "Greeting", "Symbol", "Emoji"],
        ["English", "Hello", "©", "👋"],
        ["Spanish", "Hola", "®", "🌮"],
        ["Japanese", "こんにちは", "™", "🗾"],
        ["Arabic", "مرحبا", "€", "🕌"],
        ["Chinese", "你好", "¥", "🐉"],
        ["Russian", "Привет", "£", "🪆"],
    ]


@pytest.fixture
def sample_large_dataset() -> list[list]:
    """Generate a larger dataset for performance testing."""
    headers = ["ID", "Value1", "Value2", "Value3", "Computed"]
    data = [headers]
    for i in range(1, 101):  # 100 rows
        data.append([i, i * 10, i * 20, i * 30, f"=B{i+1}+C{i+1}+D{i+1}"])
    return data

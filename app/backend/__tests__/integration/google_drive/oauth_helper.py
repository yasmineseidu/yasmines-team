"""OAuth helper for Google Drive integration tests.

Handles OAuth 2.0 flow to obtain access tokens for live API testing.
"""

import asyncio
import json
import os

import httpx


class GoogleOAuthHelper:
    """Helper to obtain Google OAuth access token for testing."""

    OAUTH_TOKEN_URL = "https://oauth2.googleapis.com/token"
    OAUTH_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str = "http://localhost:8000/api/google/callback",
    ):
        """Initialize OAuth helper.

        Args:
            client_id: Google OAuth client ID
            client_secret: Google OAuth client secret
            redirect_uri: Redirect URI (must match Google Cloud Console)
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.access_token: str | None = None
        self.refresh_token: str | None = None

    async def get_access_token_from_refresh_token(self, refresh_token: str) -> str:
        """Get new access token using refresh token.

        Args:
            refresh_token: Valid Google refresh token

        Returns:
            New access token

        Raises:
            Exception: If token refresh fails
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.OAUTH_TOKEN_URL,
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token",
                },
            )

            if response.status_code != 200:
                raise Exception(f"Failed to refresh token: {response.text}")

            data = response.json()
            self.access_token = data["access_token"]
            return self.access_token

    async def get_access_token_from_code(self, authorization_code: str) -> tuple[str, str | None]:
        """Get access token from authorization code.

        Args:
            authorization_code: Code from OAuth consent screen

        Returns:
            Tuple of (access_token, refresh_token)

        Raises:
            Exception: If token exchange fails
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.OAUTH_TOKEN_URL,
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "code": authorization_code,
                    "grant_type": "authorization_code",
                    "redirect_uri": self.redirect_uri,
                },
            )

            if response.status_code != 200:
                raise Exception(f"Failed to exchange code for token: {response.text}")

            data = response.json()
            self.access_token = data["access_token"]
            self.refresh_token = data.get("refresh_token")
            return self.access_token, self.refresh_token

    def get_auth_url(self, scopes: list[str] | None = None) -> str:
        """Get authorization URL for user to visit.

        Args:
            scopes: List of OAuth scopes (default: Drive scopes)

        Returns:
            Full authorization URL
        """
        if scopes is None:
            scopes = [
                "https://www.googleapis.com/auth/drive",
                "https://www.googleapis.com/auth/drive.file",
            ]

        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": " ".join(scopes),
            "access_type": "offline",
        }

        query_string = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{self.OAUTH_AUTH_URL}?{query_string}"

    @staticmethod
    def load_token_from_file(token_file: str = ".google_drive_token.json") -> str:
        """Load saved access token from file.

        Args:
            token_file: Path to token file

        Returns:
            Access token

        Raises:
            FileNotFoundError: If token file doesn't exist
        """
        with open(token_file) as f:
            data = json.load(f)
            return data["access_token"]

    def save_token_to_file(self, token_file: str = ".google_drive_token.json") -> None:
        """Save access token to file.

        Args:
            token_file: Path to save token file
        """
        with open(token_file, "w") as f:
            json.dump(
                {
                    "access_token": self.access_token,
                    "refresh_token": self.refresh_token,
                },
                f,
            )


async def get_access_token_for_testing() -> str:
    """Get access token for integration tests.

    Strategy:
    1. Check for saved token in .google_drive_token.json
    2. If found and valid, use it
    3. If expired or not found, try to refresh using refresh_token
    4. If no refresh token, provide instructions for manual authorization

    Returns:
        Valid Google access token

    Raises:
        Exception: If cannot obtain valid token
    """
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    redirect_uri = os.getenv(
        "GOOGLE_REDIRECT_URI",
        "http://localhost:8000/api/google/callback",
    )

    if not client_id or not client_secret:
        raise Exception("Missing GOOGLE_CLIENT_ID or GOOGLE_CLIENT_SECRET in environment")

    oauth = GoogleOAuthHelper(client_id, client_secret, redirect_uri)

    # Try to load saved token
    token_file = ".google_drive_token.json"
    if os.path.exists(token_file):
        try:
            access_token = oauth.load_token_from_file(token_file)
            print(f"✅ Loaded saved token from {token_file}")
            return access_token
        except Exception as e:
            print(f"⚠️  Failed to load saved token: {e}")

    # Try to refresh token if refresh_token is saved
    if os.path.exists(token_file):
        try:
            with open(token_file) as f:
                data = json.load(f)
                if refresh_token := data.get("refresh_token"):
                    access_token = await oauth.get_access_token_from_refresh_token(refresh_token)
                    oauth.save_token_to_file(token_file)
                    print("✅ Refreshed token using refresh token")
                    return access_token
        except Exception as e:
            print(f"⚠️  Failed to refresh token: {e}")

    # No token available - provide instructions
    raise Exception(
        f"""
❌ No valid Google access token found.

To run live API integration tests, you need:

1. Visit this authorization URL in your browser:
   {oauth.get_auth_url()}

2. Grant permission and copy the authorization code

3. Create a .google_drive_token.json file with:
   {json.dumps({{
       "access_token": "YOUR_ACCESS_TOKEN",
       "refresh_token": "YOUR_REFRESH_TOKEN"
   }}, indent=2)}

4. Or set GOOGLE_DRIVE_ACCESS_TOKEN environment variable

5. Then run tests again:
   pytest app/backend/__tests__/integration/google_drive/test_live_api.py -v
"""
    )


if __name__ == "__main__":
    # Test token loading
    try:
        token = asyncio.run(get_access_token_for_testing())
        print(f"✅ Token: {token[:20]}...")
    except Exception as e:
        print(f"Error: {e}")

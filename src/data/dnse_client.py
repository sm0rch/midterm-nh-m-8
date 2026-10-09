"""
dnse_client.py — DNSE LightSpeed API Client
Handles authentication and provides a base HTTP session
with the JWT token automatically attached to every request.
"""

import requests
import time
from config import DNSE_USERNAME, DNSE_PASSWORD

# ── Endpoints ──────────────────────────────────────────────────────────────
LOGIN_URL = "https://services.entrade.com.vn/dnse-user-service/api/auth"
USER_INFO_URL = "https://services.entrade.com.vn/dnse-user-service/api/me"

# JWT token is valid for 8 hours — we refresh 30 minutes before expiry
TOKEN_TTL_SECONDS = 8 * 3600
REFRESH_MARGIN_SECONDS = 30 * 60


class DNSEClient:
    """
    A simple DNSE API client that:
    - Logs in with username/password to obtain a JWT token
    - Attaches the token to every API request via Authorization header
    - Auto-refreshes the token before it expires
    """

    def __init__(self):
        self._token: str = ""
        self._token_obtained_at: float = 0.0
        self._session = requests.Session()
        self._session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json",
        })

    # ── Authentication ──────────────────────────────────────────────────────

    def login(self) -> None:
        """
        Step 1: POST username/password → receive JWT token.
        The token is valid for 8 hours and is used for all data requests.
        """
        print("🔐 Logging in to DNSE...")
        response = self._session.post(
            LOGIN_URL,
            json={"username": DNSE_USERNAME, "password": DNSE_PASSWORD},
        )

        if response.status_code != 200:
            raise ConnectionError(
                f"❌ Login failed (HTTP {response.status_code}): {response.text}"
            )

        data = response.json()
        self._token = data.get("token") or data.get("jwt") or data.get("access_token", "")

        if not self._token:
            raise ValueError(
                f"❌ No token found in login response. Response was: {data}"
            )

        self._token_obtained_at = time.time()
        self._session.headers.update({"Authorization": f"Bearer {self._token}"})
        print("✅ Login successful! JWT token obtained.")

    def _ensure_token(self) -> None:
        """Auto-refresh the token if it's about to expire or missing."""
        elapsed = time.time() - self._token_obtained_at
        if not self._token or elapsed >= (TOKEN_TTL_SECONDS - REFRESH_MARGIN_SECONDS):
            print("🔄 Token expired or missing — refreshing...")
            self.login()

    # ── Helper: make authenticated requests ────────────────────────────────

    def get(self, url: str, params: dict = None) -> dict:
        """Send an authenticated GET request and return JSON response."""
        self._ensure_token()
        response = self._session.get(url, params=params)
        response.raise_for_status()
        return response.json()

    def post(self, url: str, payload: dict = None) -> dict:
        """Send an authenticated POST request and return JSON response."""
        self._ensure_token()
        response = self._session.post(url, json=payload)
        response.raise_for_status()
        return response.json()

    # ── Convenience Methods ─────────────────────────────────────────────────

    def get_user_info(self) -> dict:
        """Fetch the logged-in user's account information."""
        return self.get(USER_INFO_URL)

    @property
    def token(self) -> str:
        """Read-only access to the current JWT token."""
        return self._token


# ── Quick Test ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    client = DNSEClient()
    client.login()

    print("\n📋 Fetching user info...")
    info = client.get_user_info()
    print(f"   Name    : {info.get('name') or info.get('fullName', 'N/A')}")
    print(f"   Email   : {info.get('email', 'N/A')}")
    print(f"   User ID : {info.get('id') or info.get('userId', 'N/A')}")
    print("\n🎉 DNSE authentication is working correctly!")

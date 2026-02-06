"""Google OAuth2 provider implementation.

This module provides OAuth2 authentication for Google services including
Gmail, Calendar, Drive, Docs, and Sheets with PKCE support.
"""

import os
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import aiohttp

from claude_mpm.auth.models import OAuthToken
from claude_mpm.auth.providers.base import OAuthProvider


class OAuthError(Exception):
    """Exception raised for OAuth-related errors."""

    def __init__(self, message: str, error_code: str | None = None) -> None:
        """Initialize OAuthError.

        Args:
            message: Human-readable error message.
            error_code: Optional OAuth error code from provider.
        """
        super().__init__(message)
        self.error_code = error_code


class GoogleOAuthProvider(OAuthProvider):
    """Google OAuth2 provider with PKCE support.

    Implements OAuth2 authentication for Google services with support
    for offline access (refresh tokens) and PKCE security.

    Attributes:
        AUTHORIZATION_ENDPOINT: Google OAuth2 authorization URL.
        TOKEN_ENDPOINT: Google OAuth2 token exchange URL.
        REVOKE_ENDPOINT: Google OAuth2 token revocation URL.
        DEFAULT_SCOPES: Default OAuth scopes for common Google services.

    Environment Variables:
        GOOGLE_OAUTH_CLIENT_ID: Google OAuth client ID (required).
        GOOGLE_OAUTH_CLIENT_SECRET: Google OAuth client secret (required).
    """

    AUTHORIZATION_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
    TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"  # nosec B105 - public OAuth2 endpoint
    REVOKE_ENDPOINT = "https://oauth2.googleapis.com/revoke"

    DEFAULT_SCOPES: list[str] = [
        "https://www.googleapis.com/auth/gmail.modify",
        "https://www.googleapis.com/auth/calendar",
        "https://www.googleapis.com/auth/drive",
        "https://www.googleapis.com/auth/documents",
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/tasks",
    ]

    def __init__(
        self,
        client_id: str | None = None,
        client_secret: str | None = None,
    ) -> None:
        """Initialize Google OAuth provider.

        Args:
            client_id: Google OAuth client ID. Defaults to GOOGLE_OAUTH_CLIENT_ID env var.
            client_secret: Google OAuth client secret. Defaults to GOOGLE_OAUTH_CLIENT_SECRET env var.

        Raises:
            ValueError: If client ID or secret is not provided and not in environment.
        """
        self._client_id = client_id or os.environ.get("GOOGLE_OAUTH_CLIENT_ID")
        self._client_secret = client_secret or os.environ.get(
            "GOOGLE_OAUTH_CLIENT_SECRET"
        )

        if not self._client_id:
            raise ValueError(
                "Google OAuth client ID is required. "
                "Set GOOGLE_OAUTH_CLIENT_ID environment variable or pass client_id parameter."
            )
        if not self._client_secret:
            raise ValueError(
                "Google OAuth client secret is required. "
                "Set GOOGLE_OAUTH_CLIENT_SECRET environment variable or pass client_secret parameter."
            )

    @property
    def name(self) -> str:
        """Human-readable name of the OAuth provider."""
        return "Google"

    @property
    def authorization_url(self) -> str:
        """URL for initiating user authorization."""
        return self.AUTHORIZATION_ENDPOINT

    @property
    def token_url(self) -> str:
        """URL for exchanging authorization code for tokens."""
        return self.TOKEN_ENDPOINT

    def get_authorization_url(
        self,
        redirect_uri: str,
        scopes: list[str],
        state: str,
        code_challenge: str,
    ) -> str:
        """Build the Google authorization URL with PKCE support.

        Constructs the authorization URL with offline access and consent
        prompt to ensure a refresh token is issued.

        Args:
            redirect_uri: URL to redirect to after authorization.
            scopes: List of OAuth scopes to request.
            state: Random state string for CSRF protection.
            code_challenge: PKCE code challenge (S256 hash of verifier).

        Returns:
            Complete authorization URL for user redirect.
        """
        params = {
            "client_id": self._client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": " ".join(scopes),
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            "access_type": "offline",
            "prompt": "consent",
        }
        return f"{self.AUTHORIZATION_ENDPOINT}?{urlencode(params)}"

    async def exchange_code(
        self,
        code: str,
        redirect_uri: str,
        code_verifier: str,
    ) -> OAuthToken:
        """Exchange authorization code for Google tokens.

        Args:
            code: Authorization code received from Google.
            redirect_uri: Same redirect URI used in authorization.
            code_verifier: PKCE code verifier used to generate the challenge.

        Returns:
            OAuthToken containing access token and refresh token.

        Raises:
            OAuthError: If token exchange fails.
        """
        data = {
            "client_id": self._client_id,
            "client_secret": self._client_secret,
            "code": code,
            "code_verifier": code_verifier,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.TOKEN_ENDPOINT,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            ) as response:
                result = await response.json()

                if response.status != 200:
                    error_msg = result.get(
                        "error_description", result.get("error", "Unknown error")
                    )
                    raise OAuthError(
                        f"Token exchange failed: {error_msg}",
                        error_code=result.get("error"),
                    )

                # Calculate expiration time
                expires_in = result.get("expires_in", 3600)
                expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

                return OAuthToken(
                    access_token=result["access_token"],
                    refresh_token=result.get("refresh_token"),
                    expires_at=expires_at,
                    scopes=result.get("scope", "").split(),
                    token_type=result.get("token_type", "Bearer"),
                )

    async def refresh_token(self, refresh_token: str) -> OAuthToken:
        """Refresh an expired Google access token.

        Args:
            refresh_token: Valid refresh token from previous authentication.

        Returns:
            OAuthToken with new access token.

        Raises:
            OAuthError: If token refresh fails.
        """
        data = {
            "client_id": self._client_id,
            "client_secret": self._client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.TOKEN_ENDPOINT,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            ) as response:
                result = await response.json()

                if response.status != 200:
                    error_msg = result.get(
                        "error_description", result.get("error", "Unknown error")
                    )
                    raise OAuthError(
                        f"Token refresh failed: {error_msg}",
                        error_code=result.get("error"),
                    )

                # Calculate expiration time
                expires_in = result.get("expires_in", 3600)
                expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

                return OAuthToken(
                    access_token=result["access_token"],
                    # Google may or may not return a new refresh token
                    refresh_token=result.get("refresh_token", refresh_token),
                    expires_at=expires_at,
                    scopes=result.get("scope", "").split(),
                    token_type=result.get("token_type", "Bearer"),
                )

    async def revoke_token(self, token: str) -> bool:
        """Revoke a Google access or refresh token.

        Args:
            token: Access token or refresh token to revoke.

        Returns:
            True if revocation succeeded, False otherwise.
        """
        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.REVOKE_ENDPOINT,
                data={"token": token},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            ) as response:
                # Google returns 200 on success, various error codes on failure
                return response.status == 200

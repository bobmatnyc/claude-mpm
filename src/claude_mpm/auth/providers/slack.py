"""Slack OAuth2 provider implementation.

This module provides OAuth2 authentication for Slack services enabling
user token-based access to channels, messages, and workspace features.
"""

import os
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import aiohttp

from claude_mpm.auth.models import OAuthToken
from claude_mpm.auth.providers.base import OAuthProvider
from claude_mpm.auth.providers.google import OAuthError


class SlackOAuthProvider(OAuthProvider):
    """Slack OAuth2 provider with PKCE support.

    Implements OAuth2 authentication for Slack using user tokens,
    which act on behalf of the authenticated user rather than a bot.

    Attributes:
        AUTHORIZATION_ENDPOINT: Slack OAuth2 authorization URL.
        TOKEN_ENDPOINT: Slack OAuth2 token exchange URL.
        REVOKE_ENDPOINT: Slack OAuth2 token revocation URL.
        DEFAULT_SCOPES: Default OAuth user scopes for proxy functionality.

    Environment Variables:
        SLACK_OAUTH_CLIENT_ID: Slack OAuth client ID (required).
        SLACK_OAUTH_CLIENT_SECRET: Slack OAuth client secret (required).

    Note:
        Slack uses `user_scope` parameter instead of `scope` for user tokens.
        The token response returns the user token in `authed_user.access_token`.
        Slack tokens do not typically include refresh tokens - they are
        long-lived until explicitly revoked.
    """

    AUTHORIZATION_ENDPOINT = "https://slack.com/oauth/v2/authorize"
    TOKEN_ENDPOINT = "https://slack.com/api/oauth.v2.access"  # nosec B105 - public OAuth2 endpoint
    REVOKE_ENDPOINT = "https://slack.com/api/auth.revoke"

    DEFAULT_SCOPES: list[str] = [
        # Channel access
        "channels:read",  # List public channels
        "channels:history",  # Read public channel messages
        "groups:read",  # List private channels
        "groups:history",  # Read private channel messages
        # Direct messages
        "im:read",  # List DMs
        "im:history",  # Read DM messages
        "mpim:read",  # List group DMs
        "mpim:history",  # Read group DM messages
        # Messaging
        "chat:write",  # Send messages as user
        # User and workspace info
        "users:read",  # Get user info
        "users:read.email",  # Get user emails
        "team:read",  # Get workspace info
        # Search
        "search:read",  # Search messages
    ]

    def __init__(
        self,
        client_id: str | None = None,
        client_secret: str | None = None,
    ) -> None:
        """Initialize Slack OAuth provider.

        Args:
            client_id: Slack OAuth client ID. Defaults to SLACK_OAUTH_CLIENT_ID env var.
            client_secret: Slack OAuth client secret. Defaults to SLACK_OAUTH_CLIENT_SECRET env var.

        Raises:
            ValueError: If client ID or secret is not provided and not in environment.
        """
        self._client_id = client_id or os.environ.get("SLACK_OAUTH_CLIENT_ID")
        self._client_secret = client_secret or os.environ.get(
            "SLACK_OAUTH_CLIENT_SECRET"
        )

        if not self._client_id:
            raise ValueError(
                "Slack OAuth client ID is required. "
                "Set SLACK_OAUTH_CLIENT_ID environment variable or pass client_id parameter."
            )
        if not self._client_secret:
            raise ValueError(
                "Slack OAuth client secret is required. "
                "Set SLACK_OAUTH_CLIENT_SECRET environment variable or pass client_secret parameter."
            )

    @property
    def name(self) -> str:
        """Human-readable name of the OAuth provider."""
        return "Slack"

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
        """Build the Slack authorization URL with PKCE support.

        Constructs the authorization URL for Slack user token authentication.
        Note that Slack uses `user_scope` instead of `scope` for user tokens.

        Args:
            redirect_uri: URL to redirect to after authorization.
            scopes: List of OAuth user scopes to request.
            state: Random state string for CSRF protection.
            code_challenge: PKCE code challenge (S256 hash of verifier).

        Returns:
            Complete authorization URL for user redirect.
        """
        params = {
            "client_id": self._client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            # Slack uses user_scope for user tokens (not scope)
            "user_scope": " ".join(scopes),
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
        return f"{self.AUTHORIZATION_ENDPOINT}?{urlencode(params)}"

    async def exchange_code(
        self,
        code: str,
        redirect_uri: str,
        code_verifier: str,
    ) -> OAuthToken:
        """Exchange authorization code for Slack user tokens.

        Slack's token response structure differs from standard OAuth2:
        - User tokens are in `authed_user.access_token`
        - Refresh tokens may not be provided (tokens are long-lived)

        Args:
            code: Authorization code received from Slack.
            redirect_uri: Same redirect URI used in authorization.
            code_verifier: PKCE code verifier used to generate the challenge.

        Returns:
            OAuthToken containing access token (refresh token may be None).

        Raises:
            OAuthError: If token exchange fails.
        """
        data = {
            "client_id": self._client_id,
            "client_secret": self._client_secret,
            "code": code,
            "code_verifier": code_verifier,
            "redirect_uri": redirect_uri,
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.TOKEN_ENDPOINT,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            ) as response:
                result = await response.json()

                # Slack returns ok: false on error, not HTTP status codes
                if not result.get("ok", False):
                    error_msg = result.get("error", "Unknown error")
                    raise OAuthError(
                        f"Token exchange failed: {error_msg}",
                        error_code=error_msg,
                    )

                # Slack returns user token in authed_user.access_token
                authed_user = result.get("authed_user", {})
                access_token = authed_user.get("access_token")

                if not access_token:
                    raise OAuthError(
                        "No user access token in response. "
                        "Ensure user_scope was requested in authorization.",
                        error_code="missing_user_token",
                    )

                # Slack user tokens are long-lived (no expiration by default)
                # We set a far-future expiration as they don't expire unless revoked
                # Using 1 year as a reasonable "long-lived" indicator
                expires_at = datetime.now(timezone.utc) + timedelta(days=365)

                # Extract scopes from authed_user
                scopes_str = authed_user.get("scope", "")
                scopes = scopes_str.split(",") if scopes_str else []

                # Slack may provide a refresh token, but typically doesn't for user tokens
                refresh_token = authed_user.get("refresh_token")

                return OAuthToken(
                    access_token=access_token,
                    refresh_token=refresh_token,
                    expires_at=expires_at,
                    scopes=scopes,
                    token_type=authed_user.get("token_type", "Bearer"),
                )

    async def refresh_token(self, refresh_token: str) -> OAuthToken:
        """Refresh a Slack access token.

        Note: Slack user tokens are typically long-lived and don't require
        refresh. This method is provided for completeness and for cases
        where token rotation is configured.

        Args:
            refresh_token: Valid refresh token from previous authentication.

        Returns:
            OAuthToken with new access token.

        Raises:
            OAuthError: If token refresh fails or refresh tokens are not supported.
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

                # Slack returns ok: false on error
                if not result.get("ok", False):
                    error_msg = result.get("error", "Unknown error")
                    # Provide helpful message for common case
                    if error_msg == "invalid_grant":
                        raise OAuthError(
                            "Token refresh failed: Slack user tokens are typically "
                            "long-lived and may not support refresh. "
                            "Re-authentication may be required.",
                            error_code=error_msg,
                        )
                    raise OAuthError(
                        f"Token refresh failed: {error_msg}",
                        error_code=error_msg,
                    )

                # Handle both standard response and authed_user response formats
                access_token = result.get("access_token")
                authed_user = result.get("authed_user", {})

                if not access_token and authed_user:
                    access_token = authed_user.get("access_token")

                if not access_token:
                    raise OAuthError(
                        "No access token in refresh response",
                        error_code="missing_token",
                    )

                # Calculate expiration
                expires_in = result.get("expires_in")
                if expires_in:
                    expires_at = datetime.now(timezone.utc) + timedelta(
                        seconds=expires_in
                    )
                else:
                    # Default to 1 year for long-lived tokens
                    expires_at = datetime.now(timezone.utc) + timedelta(days=365)

                # Extract scopes
                scopes_str = result.get("scope", authed_user.get("scope", ""))
                scopes = scopes_str.split(",") if scopes_str else []

                return OAuthToken(
                    access_token=access_token,
                    # Use new refresh token if provided, otherwise keep existing
                    refresh_token=result.get("refresh_token", refresh_token),
                    expires_at=expires_at,
                    scopes=scopes,
                    token_type=result.get("token_type", "Bearer"),
                )

    async def revoke_token(self, token: str) -> bool:
        """Revoke a Slack access token.

        Args:
            token: Access token to revoke.

        Returns:
            True if revocation succeeded, False otherwise.
        """
        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.REVOKE_ENDPOINT,
                data={"token": token},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            ) as response:
                result = await response.json()
                # Slack returns ok: true on success
                return bool(result.get("ok", False))

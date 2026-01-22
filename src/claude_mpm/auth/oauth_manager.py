"""OAuth manager for orchestrating complete OAuth2 authentication flows.

This module provides a high-level interface for OAuth authentication,
coordinating providers, callback servers, and token storage.
"""

import webbrowser
from typing import Optional

from claude_mpm.auth.callback_server import OAuthCallbackServer
from claude_mpm.auth.models import OAuthToken, StoredToken, TokenMetadata, TokenStatus
from claude_mpm.auth.providers.base import OAuthProvider
from claude_mpm.auth.providers.google import GoogleOAuthProvider, OAuthError
from claude_mpm.auth.token_storage import TokenStorage

# Mapping of provider names to provider classes
PROVIDERS: dict[str, type[OAuthProvider]] = {
    "google": GoogleOAuthProvider,
}


class OAuthManager:
    """High-level OAuth authentication manager.

    Orchestrates the complete OAuth2 flow including authorization,
    token exchange, storage, refresh, and revocation.

    Attributes:
        storage: Token storage instance for persisting credentials.

    Example:
        ```python
        manager = OAuthManager()

        # Authenticate with Google
        token = await manager.authenticate(
            service_name="gmail-mcp",
            provider_name="google",
            scopes=["https://www.googleapis.com/auth/gmail.readonly"],
        )

        # Check token status
        status, stored = manager.get_status("gmail-mcp")
        if status == TokenStatus.EXPIRED:
            token = await manager.refresh_if_needed("gmail-mcp")

        # Revoke when done
        await manager.revoke("gmail-mcp")
        ```
    """

    def __init__(self, storage: Optional[TokenStorage] = None) -> None:
        """Initialize OAuth manager.

        Args:
            storage: Token storage instance. Creates default if not provided.
        """
        self.storage = storage or TokenStorage()

    def get_provider(self, provider_name: str) -> OAuthProvider:
        """Get an OAuth provider instance by name.

        Args:
            provider_name: Name of the provider (e.g., "google").

        Returns:
            Configured provider instance.

        Raises:
            ValueError: If provider name is not recognized.
        """
        provider_class = PROVIDERS.get(provider_name.lower())
        if provider_class is None:
            available = ", ".join(PROVIDERS.keys())
            raise ValueError(
                f"Unknown provider: {provider_name}. Available providers: {available}"
            )
        return provider_class()

    async def authenticate(
        self,
        service_name: str,
        provider_name: str,
        scopes: Optional[list[str]] = None,
        open_browser: bool = True,
    ) -> OAuthToken:
        """Perform complete OAuth2 authentication flow.

        This method orchestrates the full OAuth flow:
        1. Start callback server
        2. Generate PKCE and state
        3. Build authorization URL
        4. Open browser for user authorization
        5. Wait for callback with authorization code
        6. Exchange code for tokens
        7. Store tokens securely

        Args:
            service_name: Unique identifier for this service/credential.
            provider_name: Name of the OAuth provider (e.g., "google").
            scopes: OAuth scopes to request. Uses provider defaults if not specified.
            open_browser: Whether to automatically open the authorization URL.

        Returns:
            OAuthToken containing access and refresh tokens.

        Raises:
            ValueError: If provider is not recognized.
            OAuthError: If authentication fails at any step.
        """
        # Get provider instance
        provider = self.get_provider(provider_name)

        # Use provider's default scopes if none specified
        if scopes is None:
            if hasattr(provider, "DEFAULT_SCOPES"):
                scopes = provider.DEFAULT_SCOPES
            else:
                scopes = []

        # Step 1: Start callback server
        callback_server = OAuthCallbackServer()

        # Step 2: Generate PKCE and state
        pkce = OAuthProvider.generate_pkce()
        state = callback_server.generate_state()

        # Step 3: Build authorization URL
        auth_url = provider.get_authorization_url(
            redirect_uri=callback_server.callback_url,
            scopes=scopes,
            state=state,
            code_challenge=pkce.code_challenge,
        )

        # Step 4: Open browser for user authorization
        if open_browser:
            webbrowser.open(auth_url)

        # Step 5: Wait for callback
        result = await callback_server.wait_for_callback(
            expected_state=state,
            timeout=300.0,
        )

        if not result.success:
            raise OAuthError(
                f"Authorization failed: {result.error_description or result.error}",
                error_code=result.error,
            )

        if result.code is None:
            raise OAuthError("No authorization code received")

        # Step 6: Exchange code for tokens
        token = await provider.exchange_code(
            code=result.code,
            redirect_uri=callback_server.callback_url,
            code_verifier=pkce.code_verifier,
        )

        # Step 7: Store tokens
        metadata = TokenMetadata(
            service_name=service_name,
            provider=provider_name,
        )
        self.storage.store(service_name, token, metadata)

        return token

    async def refresh_if_needed(self, service_name: str) -> Optional[OAuthToken]:
        """Refresh token if expired or about to expire.

        Checks if the stored token is expired and refreshes it using
        the refresh token if available.

        Args:
            service_name: Unique identifier for the service.

        Returns:
            New OAuthToken if refreshed, existing token if still valid,
            None if no token exists or refresh failed.

        Raises:
            OAuthError: If token refresh fails.
        """
        stored = self.storage.retrieve(service_name)
        if stored is None:
            return None

        # Check if token is still valid (with 60 second buffer)
        if not stored.token.is_expired():
            return stored.token

        # Need to refresh
        if stored.token.refresh_token is None:
            return None

        # Get provider and refresh
        provider = self.get_provider(stored.metadata.provider)
        new_token = await provider.refresh_token(stored.token.refresh_token)

        # Update stored token
        self.storage.store(service_name, new_token, stored.metadata)

        return new_token

    async def revoke(self, service_name: str) -> bool:
        """Revoke tokens and delete stored credentials.

        Revokes the token with the OAuth provider and removes
        the stored credentials.

        Args:
            service_name: Unique identifier for the service.

        Returns:
            True if revocation and deletion succeeded, False otherwise.
        """
        stored = self.storage.retrieve(service_name)
        if stored is None:
            return False

        # Get provider and revoke
        provider = self.get_provider(stored.metadata.provider)

        # Try to revoke the refresh token first (more thorough)
        revoked = False
        if stored.token.refresh_token:
            revoked = await provider.revoke_token(stored.token.refresh_token)

        # If no refresh token or revocation failed, try access token
        if not revoked:
            revoked = await provider.revoke_token(stored.token.access_token)

        # Delete stored credentials regardless of revocation result
        self.storage.delete(service_name)

        return revoked

    def get_status(
        self, service_name: str
    ) -> tuple[TokenStatus, Optional[StoredToken]]:
        """Get the status of a stored token.

        Args:
            service_name: Unique identifier for the service.

        Returns:
            Tuple of (TokenStatus, StoredToken or None).
        """
        status = self.storage.get_status(service_name)
        stored = (
            self.storage.retrieve(service_name)
            if status != TokenStatus.MISSING
            else None
        )
        return (status, stored)

    def list_authenticated_services(self) -> list[str]:
        """List all services with stored tokens.

        Returns:
            List of service names that have stored credentials.
        """
        return self.storage.list_services()

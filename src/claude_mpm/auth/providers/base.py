"""Abstract base class for OAuth providers.

This module defines the interface that all OAuth providers must implement,
providing a consistent API for OAuth2 authentication flows with PKCE support.
"""

import base64
import hashlib
import secrets
from abc import ABC, abstractmethod
from dataclasses import dataclass

from claude_mpm.auth.models import OAuthToken


@dataclass(frozen=True)
class PKCEChallenge:
    """PKCE code verifier and challenge pair.

    Attributes:
        code_verifier: Random string used to generate the challenge.
        code_challenge: SHA256 hash of the verifier, base64url encoded.
    """

    code_verifier: str
    code_challenge: str


class OAuthProvider(ABC):
    """Abstract base class for OAuth2 providers.

    Defines the interface for OAuth authentication flows including
    authorization URL generation, token exchange, refresh, and revocation.
    All implementations should support PKCE (Proof Key for Code Exchange).

    Attributes:
        name: Human-readable name of the OAuth provider.
        authorization_url: URL for user authorization.
        token_url: URL for token exchange.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name of the OAuth provider."""
        ...

    @property
    @abstractmethod
    def authorization_url(self) -> str:
        """URL for initiating user authorization."""
        ...

    @property
    @abstractmethod
    def token_url(self) -> str:
        """URL for exchanging authorization code for tokens."""
        ...

    @abstractmethod
    def get_authorization_url(
        self,
        redirect_uri: str,
        scopes: list[str],
        state: str,
        code_challenge: str,
    ) -> str:
        """Build the authorization URL with PKCE support.

        Constructs the full authorization URL including all required
        parameters for the OAuth2 flow with PKCE.

        Args:
            redirect_uri: URL to redirect to after authorization.
            scopes: List of OAuth scopes to request.
            state: Random state string for CSRF protection.
            code_challenge: PKCE code challenge (S256 hash of verifier).

        Returns:
            Complete authorization URL for user redirect.
        """
        ...

    @abstractmethod
    async def exchange_code(
        self,
        code: str,
        redirect_uri: str,
        code_verifier: str,
    ) -> OAuthToken:
        """Exchange authorization code for tokens.

        Completes the OAuth2 flow by exchanging the authorization code
        for access and refresh tokens.

        Args:
            code: Authorization code received from the provider.
            redirect_uri: Same redirect URI used in authorization.
            code_verifier: PKCE code verifier used to generate the challenge.

        Returns:
            OAuthToken containing access token and optional refresh token.

        Raises:
            OAuthError: If token exchange fails.
        """
        ...

    @abstractmethod
    async def refresh_token(self, refresh_token: str) -> OAuthToken:
        """Refresh an expired access token.

        Uses the refresh token to obtain a new access token without
        requiring user interaction.

        Args:
            refresh_token: Valid refresh token from previous authentication.

        Returns:
            OAuthToken with new access token (may include new refresh token).

        Raises:
            OAuthError: If token refresh fails or refresh token is invalid.
        """
        ...

    @abstractmethod
    async def revoke_token(self, token: str) -> bool:
        """Revoke an access or refresh token.

        Invalidates the token with the OAuth provider, preventing
        further use.

        Args:
            token: Access token or refresh token to revoke.

        Returns:
            True if revocation succeeded, False otherwise.
        """
        ...

    @staticmethod
    def generate_pkce() -> PKCEChallenge:
        """Generate PKCE code verifier and challenge.

        Creates a cryptographically secure code verifier and derives
        the S256 challenge from it per RFC 7636.

        Returns:
            PKCEChallenge containing verifier and challenge strings.
        """
        # Generate 32 bytes of random data (256 bits)
        code_verifier_bytes = secrets.token_bytes(32)
        # Base64url encode without padding
        code_verifier = (
            base64.urlsafe_b64encode(code_verifier_bytes).rstrip(b"=").decode("ascii")
        )

        # Create S256 challenge: BASE64URL(SHA256(code_verifier))
        challenge_digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
        code_challenge = (
            base64.urlsafe_b64encode(challenge_digest).rstrip(b"=").decode("ascii")
        )

        return PKCEChallenge(code_verifier=code_verifier, code_challenge=code_challenge)

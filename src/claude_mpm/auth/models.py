"""OAuth data models for token management.

This module defines Pydantic models for OAuth tokens and their metadata,
providing type-safe token handling with automatic validation.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class TokenStatus(str, Enum):
    """Status of an OAuth token."""

    VALID = "valid"
    EXPIRED = "expired"
    MISSING = "missing"
    INVALID = "invalid"


class OAuthToken(BaseModel):
    """OAuth2 token data.

    Represents the token response from an OAuth provider with
    expiration tracking and scope management.

    Attributes:
        access_token: The access token string for API authentication.
        refresh_token: Optional refresh token for token renewal.
        expires_at: UTC timestamp when the access token expires.
        scopes: List of granted OAuth scopes.
        token_type: Token type, typically "Bearer".
    """

    access_token: str = Field(..., description="OAuth access token")
    refresh_token: Optional[str] = Field(
        default=None, description="OAuth refresh token for renewal"
    )
    expires_at: datetime = Field(..., description="Token expiration timestamp (UTC)")
    scopes: list[str] = Field(default_factory=list, description="Granted OAuth scopes")
    token_type: str = Field(default="Bearer", description="Token type")

    def is_expired(self, buffer_seconds: int = 60) -> bool:
        """Check if the token is expired or about to expire.

        Args:
            buffer_seconds: Number of seconds before actual expiration
                to consider the token expired. Defaults to 60 seconds
                to allow time for token refresh.

        Returns:
            True if the token is expired or will expire within the buffer period.
        """
        now = datetime.now(timezone.utc)
        # Ensure expires_at is timezone-aware
        expires_at = self.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        from datetime import timedelta

        return now >= (expires_at - timedelta(seconds=buffer_seconds))


class TokenMetadata(BaseModel):
    """Metadata about a stored OAuth token.

    Tracks service information and timestamps for token lifecycle management.

    Attributes:
        service_name: Name of the MCP service this token authenticates.
        provider: OAuth provider identifier (e.g., "github", "google").
        created_at: When the token was first stored.
        last_refreshed: When the token was last refreshed, if applicable.
    """

    service_name: str = Field(..., description="MCP service name")
    provider: str = Field(..., description="OAuth provider identifier")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Token creation timestamp",
    )
    last_refreshed: Optional[datetime] = Field(
        default=None, description="Last token refresh timestamp"
    )


class StoredToken(BaseModel):
    """Complete stored token with metadata and versioning.

    This is the top-level structure persisted to storage, containing
    both the token data and metadata needed for management.

    Attributes:
        version: Schema version for future migration support.
        metadata: Token metadata including service and provider info.
        token: The actual OAuth token data.
    """

    version: int = Field(default=1, description="Schema version for migrations")
    metadata: TokenMetadata = Field(..., description="Token metadata")
    token: OAuthToken = Field(..., description="OAuth token data")

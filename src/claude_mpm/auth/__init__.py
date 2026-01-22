"""OAuth authentication module for MCP services.

This module provides secure OAuth token management and callback handling
for authenticating with MCP services that require OAuth2 flows.

Core Components:
    - OAuthToken: Token data model with expiration handling
    - TokenStorage: Secure encrypted token persistence
    - OAuthCallbackServer: Local HTTP server for OAuth callbacks
    - OAuthProvider: Abstract base class for OAuth providers
    - GoogleOAuthProvider: Google OAuth2 implementation
"""

from claude_mpm.auth.callback_server import OAuthCallbackServer
from claude_mpm.auth.models import (
    OAuthToken,
    StoredToken,
    TokenMetadata,
    TokenStatus,
)
from claude_mpm.auth.oauth_manager import OAuthManager
from claude_mpm.auth.providers import GoogleOAuthProvider, OAuthProvider
from claude_mpm.auth.token_storage import TokenStorage

__all__ = [
    "GoogleOAuthProvider",
    "OAuthCallbackServer",
    "OAuthManager",
    "OAuthProvider",
    "OAuthToken",
    "StoredToken",
    "TokenMetadata",
    "TokenStatus",
    "TokenStorage",
]

"""OAuth providers for authentication.

This module exports OAuth provider implementations for various services.
"""

from claude_mpm.auth.providers.base import OAuthProvider
from claude_mpm.auth.providers.google import GoogleOAuthProvider
from claude_mpm.auth.providers.slack import SlackOAuthProvider

__all__ = [
    "GoogleOAuthProvider",
    "OAuthProvider",
    "SlackOAuthProvider",
]

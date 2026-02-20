"""
GitHub Integration Services Package
====================================

Provides GitHub CLI integration for PR workflow automation.
Used by agent-improver and skills-manager agents.

Also includes multi-account management for projects requiring
different GitHub credentials.
"""

from .github_account_manager import GitHubAccountManager
from .github_cli_service import (
    GitHubAuthenticationError,
    GitHubCLIError,
    GitHubCLINotInstalledError,
    GitHubCLIService,
)

__all__ = [
    "GitHubAccountManager",
    "GitHubAuthenticationError",
    "GitHubCLIError",
    "GitHubCLINotInstalledError",
    "GitHubCLIService",
]

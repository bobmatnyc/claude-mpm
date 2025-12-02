"""
GitHub Integration Services Package
====================================

Provides GitHub CLI integration for PR workflow automation.
Used by agent-improver and skills-manager agents.
"""

from .github_cli_service import (
    GitHubAuthenticationError,
    GitHubCLIError,
    GitHubCLINotInstalledError,
    GitHubCLIService,
)

__all__ = [
    "GitHubAuthenticationError",
    "GitHubCLIError",
    "GitHubCLINotInstalledError",
    "GitHubCLIService",
]

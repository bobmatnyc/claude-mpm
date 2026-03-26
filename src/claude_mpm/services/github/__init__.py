"""
GitHub Integration Services Package
====================================

Provides GitHub CLI integration for PR workflow automation.
Used by agent-improver and skills-manager agents.

Also includes multi-account management for projects requiring
different GitHub credentials.

Phase 4 additions: identity manager, repo context detection,
MCP probe, and system prompt injector for GitHub-first sessions.
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
    "GitHubIdentityManager",
    "GitHubRepoContext",
    "GitHubSystemPromptInjector",
    "probe_github_mcp",
]

# Lazy exports — guarded with try/except to allow partial installs
try:
    from .identity_manager import GitHubIdentityManager
except ImportError:  # pragma: no cover
    GitHubIdentityManager = None  # type: ignore[assignment,misc]

try:
    from .repo_context import GitHubRepoContext
except ImportError:  # pragma: no cover
    GitHubRepoContext = None  # type: ignore[assignment,misc]

try:
    from .mcp_probe import probe_github_mcp
except ImportError:  # pragma: no cover
    probe_github_mcp = None  # type: ignore[assignment]

try:
    from .system_prompt_injector import GitHubSystemPromptInjector
except ImportError:  # pragma: no cover
    GitHubSystemPromptInjector = None  # type: ignore[assignment,misc]

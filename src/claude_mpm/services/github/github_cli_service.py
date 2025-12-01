"""
GitHub CLI Service
==================

Provides GitHub CLI (gh) integration for PR creation and management.

Design Decisions:
- Uses gh CLI as primary method (best UX, inherits authentication)
- Provides helpful installation prompts if gh CLI not found
- Validates authentication before operations
- Supports environment variable fallback for CI/CD

Example:
    >>> service = GitHubCLIService()
    >>> if service.is_gh_installed():
    ...     if service.is_authenticated():
    ...         pr_url = service.create_pr(
    ...             repo="bobmatnyc/claude-mpm-agents",
    ...             title="feat(agent): improve research agent",
    ...             body="## Problem\\n...",
    ...             base="main"
    ...         )
"""

import shutil
import subprocess
from typing import Optional, Tuple


# Custom Exceptions
class GitHubCLIError(Exception):
    """Base exception for GitHub CLI errors."""


class GitHubCLINotInstalledError(GitHubCLIError):
    """Raised when gh CLI is not installed."""


class GitHubAuthenticationError(GitHubCLIError):
    """Raised when gh CLI authentication fails."""


class GitHubCLIService:
    """
    Service for GitHub CLI operations.

    Provides abstraction over gh CLI for PR creation and management.
    Validates installation and authentication state before operations.
    """

    def __init__(self, timeout: int = 30):
        """
        Initialize GitHub CLI service.

        Args:
            timeout: Command timeout in seconds (default: 30)
        """
        self.timeout = timeout

    def is_gh_installed(self) -> bool:
        """
        Check if gh CLI is installed.

        Returns:
            True if gh CLI is available in PATH

        Example:
            >>> service = GitHubCLIService()
            >>> if not service.is_gh_installed():
            ...     print(service.get_installation_instructions())
        """
        return shutil.which("gh") is not None

    def is_authenticated(self) -> bool:
        """
        Check if gh CLI is authenticated.

        Returns:
            True if gh CLI is authenticated with GitHub

        Raises:
            GitHubCLINotInstalledError: If gh CLI is not installed
        """
        if not self.is_gh_installed():
            raise GitHubCLINotInstalledError(
                "GitHub CLI (gh) is not installed. "
                + self.get_installation_instructions()
            )

        try:
            returncode, _stdout, _stderr = self._run_gh_command(
                ["gh", "auth", "status"]
            )

            # gh auth status returns 0 if authenticated
            return returncode == 0

        except Exception:
            return False

    def get_installation_instructions(self) -> str:
        """
        Get platform-specific installation instructions for gh CLI.

        Returns:
            Installation instructions as formatted string

        Example:
            >>> service = GitHubCLIService()
            >>> print(service.get_installation_instructions())
            GitHub CLI not detected. Please install it to enable PR creation:

            macOS: brew install gh
            Linux: See https://github.com/cli/cli#installation

            After installation, authenticate with: gh auth login
        """
        return """
GitHub CLI not detected. Please install it to enable PR creation:

macOS:
  brew install gh

Linux:
  # Debian/Ubuntu
  curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null
  sudo apt update
  sudo apt install gh

  # Fedora/CentOS/RHEL
  sudo dnf install gh

  # For other distributions, see: https://github.com/cli/cli#installation

Windows:
  winget install --id GitHub.cli

After installation, authenticate with:
  gh auth login

For more information, visit: https://cli.github.com/
""".strip()

    def get_authentication_instructions(self) -> str:
        """
        Get authentication instructions for gh CLI.

        Returns:
            Authentication instructions as formatted string
        """
        return """
GitHub CLI is installed but not authenticated.

To authenticate, run:
  gh auth login

This will guide you through the authentication process.
You can authenticate via:
- Browser (recommended)
- Personal access token

After authentication, you'll be able to create PRs directly.
""".strip()

    def create_pr(
        self,
        repo: str,
        title: str,
        body: str,
        base: str = "main",
        head: Optional[str] = None,
        draft: bool = False,
    ) -> str:
        """
        Create a pull request using gh CLI.

        Args:
            repo: Repository in format "owner/repo" (e.g., "bobmatnyc/claude-mpm-agents")
            title: PR title
            body: PR description (markdown)
            base: Base branch (default: "main")
            head: Head branch (optional, uses current branch if not specified)
            draft: Create as draft PR (default: False)

        Returns:
            PR URL

        Raises:
            GitHubCLINotInstalledError: If gh CLI not installed
            GitHubAuthenticationError: If not authenticated
            GitHubCLIError: If PR creation fails

        Example:
            >>> service = GitHubCLIService()
            >>> pr_url = service.create_pr(
            ...     repo="bobmatnyc/claude-mpm-agents",
            ...     title="feat(agent): improve research agent",
            ...     body="## Problem\\nMemory exhaustion...",
            ...     base="main"
            ... )
            >>> print(f"PR created: {pr_url}")
        """
        # Validate installation
        if not self.is_gh_installed():
            raise GitHubCLINotInstalledError(
                "GitHub CLI (gh) is not installed. "
                + self.get_installation_instructions()
            )

        # Validate authentication
        if not self.is_authenticated():
            raise GitHubAuthenticationError(
                "GitHub CLI is not authenticated. "
                + self.get_authentication_instructions()
            )

        # Build command
        cmd = [
            "gh",
            "pr",
            "create",
            "--repo",
            repo,
            "--title",
            title,
            "--body",
            body,
            "--base",
            base,
        ]

        if head:
            cmd.extend(["--head", head])

        if draft:
            cmd.append("--draft")

        # Execute command
        try:
            returncode, stdout, stderr = self._run_gh_command(cmd)

            if returncode != 0:
                raise GitHubCLIError(f"Failed to create PR: {stderr}")

            # Extract PR URL from output (gh outputs the URL)
            return stdout.strip().split("\n")[-1]

        except subprocess.TimeoutExpired as e:
            raise GitHubCLIError(
                f"PR creation timed out after {self.timeout} seconds"
            ) from e
        except Exception as e:
            raise GitHubCLIError(f"Failed to create PR: {e}") from e

    def check_pr_exists(
        self, repo: str, head: str, base: str = "main"
    ) -> Optional[str]:
        """
        Check if a PR already exists for the given head branch.

        Args:
            repo: Repository in format "owner/repo"
            head: Head branch name
            base: Base branch (default: "main")

        Returns:
            PR URL if exists, None otherwise

        Raises:
            GitHubCLINotInstalledError: If gh CLI not installed
            GitHubCLIError: If command fails
        """
        if not self.is_gh_installed():
            raise GitHubCLINotInstalledError(self.get_installation_instructions())

        try:
            cmd = [
                "gh",
                "pr",
                "list",
                "--repo",
                repo,
                "--head",
                head,
                "--base",
                base,
                "--json",
                "url",
                "--jq",
                ".[0].url",
            ]

            returncode, stdout, _stderr = self._run_gh_command(cmd)

            if returncode != 0:
                return None

            pr_url = stdout.strip()
            return pr_url if pr_url else None

        except Exception:
            return None

    def get_pr_status(self, pr_url: str) -> Optional[dict]:
        """
        Get PR status information.

        Args:
            pr_url: PR URL

        Returns:
            Dictionary with PR status or None if failed

        Raises:
            GitHubCLINotInstalledError: If gh CLI not installed
        """
        if not self.is_gh_installed():
            raise GitHubCLINotInstalledError(self.get_installation_instructions())

        try:
            cmd = [
                "gh",
                "pr",
                "view",
                pr_url,
                "--json",
                "title,state,url,number",
            ]

            returncode, stdout, _stderr = self._run_gh_command(cmd)

            if returncode != 0:
                return None

            import json

            return json.loads(stdout)

        except Exception:
            return None

    def _run_gh_command(self, command: list) -> Tuple[int, str, str]:
        """
        Run gh command and return result.

        Args:
            command: Command and arguments

        Returns:
            Tuple of (returncode, stdout, stderr)

        Raises:
            subprocess.TimeoutExpired: If command times out
        """
        try:
            result = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )

            return result.returncode, result.stdout, result.stderr

        except subprocess.TimeoutExpired:
            raise
        except Exception as e:
            raise GitHubCLIError(f"Failed to run gh command: {e}") from e

    def validate_environment(self) -> Tuple[bool, str]:
        """
        Validate GitHub CLI environment is ready for operations.

        Returns:
            Tuple of (is_valid, message)

        Example:
            >>> service = GitHubCLIService()
            >>> valid, msg = service.validate_environment()
            >>> if not valid:
            ...     print(f"GitHub CLI not ready: {msg}")
            ...     print(service.get_installation_instructions())
        """
        # Check installation
        if not self.is_gh_installed():
            return False, "GitHub CLI (gh) is not installed"

        # Check authentication
        try:
            if not self.is_authenticated():
                return False, "GitHub CLI is not authenticated"
        except Exception as e:
            return False, f"Failed to check authentication: {e}"

        return True, "GitHub CLI is ready"

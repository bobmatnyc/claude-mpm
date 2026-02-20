"""
GitHub Multi-Account Management Service.

WHY: Manages GitHub account switching and verification for projects with multi-account setups.
Provides automated account switching based on .gh-account file markers.

DESIGN DECISIONS:
- Uses .gh-account file as project marker (simple, git-ignored)
- Integrates with gh CLI (industry standard GitHub CLI tool)
- Provides both switching and verification functionality
- Returns structured results for CLI formatting
"""

import subprocess  # nosec B404
from pathlib import Path
from typing import Optional

from ...core.logging_utils import get_logger

logger = get_logger(__name__)


class GitHubAccountManager:
    """Manages GitHub account switching and verification."""

    def __init__(self, project_dir: Optional[Path] = None):
        """
        Initialize GitHub account manager.

        Args:
            project_dir: Project directory (defaults to current directory)
        """
        self.project_dir = project_dir or Path.cwd()

    def find_project_root(self) -> Optional[Path]:
        """
        Find project root by looking for .gh-account file.

        Returns:
            Path to project root, or None if not found
        """
        current = self.project_dir.resolve()

        while current != current.parent:
            gh_account_file = current / ".gh-account"
            if gh_account_file.exists():
                return current
            current = current.parent

        return None

    def get_required_account(self) -> Optional[str]:
        """
        Get required GitHub account from .gh-account file.

        Returns:
            GitHub username, or None if file not found
        """
        project_root = self.find_project_root()
        if not project_root:
            return None

        gh_account_file = project_root / ".gh-account"
        try:
            account = gh_account_file.read_text().strip()
            return account if account else None
        except Exception as e:
            logger.error(f"Failed to read .gh-account file: {e}")
            return None

    def get_current_gh_account(self) -> Optional[str]:
        """
        Get current active gh CLI account.

        Returns:
            Current GitHub username, or None if not authenticated
        """
        try:
            result = subprocess.run(  # nosec B603 B607
                ["gh", "api", "user", "--jq", ".login"],
                check=False,
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                return result.stdout.strip()
            return None
        except Exception as e:
            logger.error(f"Failed to get current gh account: {e}")
            return None

    def switch_account(self, account: str) -> bool:
        """
        Switch gh CLI to specified account.

        Args:
            account: GitHub username to switch to

        Returns:
            True if successful, False otherwise
        """
        try:
            result = subprocess.run(  # nosec B603 B607
                ["gh", "auth", "switch", "--user", account],
                check=False,
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Failed to switch gh account: {e}")
            return False

    def verify_git_config(self, expected_user: Optional[str] = None) -> dict:
        """
        Verify git configuration.

        Args:
            expected_user: Expected GitHub username (if None, uses .gh-account)

        Returns:
            Dictionary with verification results
        """
        if expected_user is None:
            expected_user = self.get_required_account()

        results = {
            "email": {"value": None, "valid": False},
            "name": {"value": None, "valid": False},
            "github_user": {"value": None, "valid": False},
        }

        try:
            # Get git config values
            email_result = subprocess.run(  # nosec B603 B607
                ["git", "config", "user.email"],
                check=False,
                capture_output=True,
                text=True,
                timeout=5,
            )
            if email_result.returncode == 0:
                results["email"]["value"] = email_result.stdout.strip()
                results["email"]["valid"] = bool(results["email"]["value"])

            name_result = subprocess.run(  # nosec B603 B607
                ["git", "config", "user.name"],
                check=False,
                capture_output=True,
                text=True,
                timeout=5,
            )
            if name_result.returncode == 0:
                results["name"]["value"] = name_result.stdout.strip()
                results["name"]["valid"] = bool(results["name"]["value"])

            github_user_result = subprocess.run(  # nosec B603 B607
                ["git", "config", "github.user"],
                check=False,
                capture_output=True,
                text=True,
                timeout=5,
            )
            if github_user_result.returncode == 0:
                github_user = github_user_result.stdout.strip()
                results["github_user"]["value"] = github_user
                if expected_user:
                    results["github_user"]["valid"] = github_user == expected_user
                else:
                    results["github_user"]["valid"] = bool(github_user)

        except Exception as e:
            logger.error(f"Failed to verify git config: {e}")

        return results

    def verify_ssh_connection(self, expected_user: Optional[str] = None) -> dict:
        """
        Verify SSH connection to GitHub.

        Args:
            expected_user: Expected GitHub username

        Returns:
            Dictionary with verification results
        """
        result = {"authenticated": False, "user": None, "valid": False}

        try:
            ssh_result = subprocess.run(  # nosec B603 B607
                ["ssh", "-T", "git@github.com"],
                check=False,
                capture_output=True,
                text=True,
                timeout=10,
            )

            # SSH returns exit code 1 for successful auth with message
            output = ssh_result.stderr + ssh_result.stdout
            if "Hi " in output:
                result["authenticated"] = True
                # Extract username from "Hi <username>!"
                user_start = output.find("Hi ") + 3
                user_end = output.find("!", user_start)
                if user_end > user_start:
                    result["user"] = output[user_start:user_end]

                    if expected_user:
                        result["valid"] = result["user"] == expected_user
                    else:
                        result["valid"] = True

        except Exception as e:
            logger.error(f"Failed to verify SSH connection: {e}")

        return result

    def verify_gh_cli(self, expected_user: Optional[str] = None) -> dict:
        """
        Verify gh CLI authentication.

        Args:
            expected_user: Expected GitHub username

        Returns:
            Dictionary with verification results
        """
        result = {"authenticated": False, "user": None, "valid": False}

        try:
            gh_user = self.get_current_gh_account()
            if gh_user:
                result["authenticated"] = True
                result["user"] = gh_user

                if expected_user:
                    result["valid"] = gh_user == expected_user
                else:
                    result["valid"] = True

        except Exception as e:
            logger.error(f"Failed to verify gh CLI: {e}")

        return result

    def verify_setup(self) -> dict:
        """
        Run comprehensive setup verification.

        Returns:
            Dictionary with all verification results
        """
        expected_user = self.get_required_account()
        project_root = self.find_project_root()

        return {
            "project_root": str(project_root) if project_root else None,
            "expected_user": expected_user,
            "git_config": self.verify_git_config(expected_user),
            "ssh": self.verify_ssh_connection(expected_user),
            "gh_cli": self.verify_gh_cli(expected_user),
            "has_gh_account_file": project_root is not None,
        }

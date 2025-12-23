"""
Git Operations Service
======================

Abstraction layer for Git operations used in PR workflow automation.

Design Decisions:
- Uses subprocess for git commands (not gitpython) for simplicity and reliability
- Provides rollback mechanism on failures
- Validates repo state before operations
- Clear error messages for debugging

Example:
    >>> service = GitOperationsService()
    >>> success = service.create_branch(Path("~/.claude-mpm/cache/agents"), "improve/research-memory")
    >>> if success:
    ...     service.stage_files(Path("~/.claude-mpm/cache/agents"), ["agents/research.md"])
    ...     service.commit(Path("~/.claude-mpm/cache/agents"), "feat: improve research agent memory handling")
"""

import logging
import subprocess
from pathlib import Path
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)


# Custom Exceptions
class GitOperationError(Exception):
    """Base exception for git operation failures."""


class GitConflictError(GitOperationError):
    """Raised when git detects merge conflicts."""


class GitAuthenticationError(GitOperationError):
    """Raised when git authentication fails."""


class GitOperationsService:
    """
    Service for Git repository operations.

    Provides abstraction over git commands for PR workflow automation.
    All operations validate repository state and provide clear error messages.
    """

    def __init__(self, timeout: int = 30):
        """
        Initialize git operations service.

        Args:
            timeout: Command timeout in seconds (default: 30)
        """
        self.timeout = timeout

    def is_git_repo(self, repo_path: Path) -> bool:
        """
        Check if directory is a git repository.

        Args:
            repo_path: Path to check

        Returns:
            True if directory is a git repo, False otherwise

        Example:
            >>> service = GitOperationsService()
            >>> service.is_git_repo(Path("~/.claude-mpm/cache/agents"))
            True
        """
        try:
            result = self._run_git_command(
                ["git", "rev-parse", "--git-dir"], cwd=repo_path
            )
            return result[0] == 0
        except Exception:
            return False

    def get_current_branch(self, repo_path: Path) -> str:
        """
        Get current branch name.

        Args:
            repo_path: Repository path

        Returns:
            Current branch name

        Raises:
            GitOperationError: If not in a git repo or command fails
        """
        self._validate_repo(repo_path)

        returncode, stdout, stderr = self._run_git_command(
            ["git", "branch", "--show-current"], cwd=repo_path
        )

        if returncode != 0:
            raise GitOperationError(f"Failed to get current branch: {stderr}")

        return stdout.strip()

    def has_uncommitted_changes(self, repo_path: Path) -> bool:
        """
        Check if repository has uncommitted changes.

        Args:
            repo_path: Repository path

        Returns:
            True if there are uncommitted changes

        Raises:
            GitOperationError: If command fails
        """
        self._validate_repo(repo_path)

        returncode, stdout, stderr = self._run_git_command(
            ["git", "status", "--porcelain"], cwd=repo_path
        )

        if returncode != 0:
            raise GitOperationError(f"Failed to check git status: {stderr}")

        return bool(stdout.strip())

    def create_and_checkout_branch(
        self, repo_path: Path, branch_name: str, base_branch: str = "main"
    ) -> bool:
        """
        Create and checkout a new branch from base branch.

        Pulls latest from remote before creating branch to avoid conflicts.

        Args:
            repo_path: Repository path
            branch_name: New branch name (e.g., "improve/research-memory")
            base_branch: Base branch to branch from (default: "main")

        Returns:
            True if successful

        Raises:
            GitOperationError: If operation fails
            GitConflictError: If merge conflicts detected

        Example:
            >>> service = GitOperationsService()
            >>> service.create_and_checkout_branch(
            ...     Path("~/.claude-mpm/cache/agents"),
            ...     "improve/research-memory",
            ...     "main"
            ... )
            True
        """
        self._validate_repo(repo_path)

        # Store current branch for rollback
        original_branch = self.get_current_branch(repo_path)

        try:
            # Checkout base branch
            returncode, _stdout, stderr = self._run_git_command(
                ["git", "checkout", base_branch], cwd=repo_path
            )
            if returncode != 0:
                raise GitOperationError(f"Failed to checkout {base_branch}: {stderr}")

            # Pull latest from remote
            returncode, _stdout, stderr = self._run_git_command(
                ["git", "pull", "origin", base_branch], cwd=repo_path
            )
            if returncode != 0:
                # Non-blocking if pull fails (might not have remote configured)
                pass

            # Create and checkout new branch
            returncode, _stdout, stderr = self._run_git_command(
                ["git", "checkout", "-b", branch_name], cwd=repo_path
            )
            if returncode != 0:
                raise GitOperationError(
                    f"Failed to create branch {branch_name}: {stderr}"
                )

            return True

        except Exception as e:
            # Rollback to original branch on failure
            try:
                self._run_git_command(
                    ["git", "checkout", original_branch], cwd=repo_path
                )
            except Exception:
                pass  # Best effort rollback

            raise GitOperationError(f"Failed to create branch: {e}") from e

    def stage_files(self, repo_path: Path, files: List[str]) -> bool:
        """
        Stage files for commit.

        Args:
            repo_path: Repository path
            files: List of file paths relative to repo root

        Returns:
            True if successful

        Raises:
            GitOperationError: If staging fails
        """
        self._validate_repo(repo_path)

        if not files:
            raise GitOperationError("No files specified for staging")

        returncode, _stdout, stderr = self._run_git_command(
            ["git", "add"] + files, cwd=repo_path
        )

        if returncode != 0:
            raise GitOperationError(f"Failed to stage files: {stderr}")

        return True

    def commit(self, repo_path: Path, message: str, allow_empty: bool = False) -> bool:
        """
        Commit staged changes.

        Args:
            repo_path: Repository path
            message: Commit message (should follow conventional commits format)
            allow_empty: Allow empty commits

        Returns:
            True if successful

        Raises:
            GitOperationError: If commit fails

        Example:
            >>> service = GitOperationsService()
            >>> service.commit(
            ...     Path("~/.claude-mpm/cache/agents"),
            ...     "feat(agent): improve research agent memory handling\\n\\n- Add hard limit of 5 files"
            ... )
            True
        """
        self._validate_repo(repo_path)

        if not message:
            raise GitOperationError("Commit message cannot be empty")

        cmd = ["git", "commit", "-m", message]
        if allow_empty:
            cmd.append("--allow-empty")

        returncode, _stdout, stderr = self._run_git_command(cmd, cwd=repo_path)

        if returncode != 0:
            # Check if it's just "nothing to commit"
            if "nothing to commit" in stderr.lower() and not allow_empty:
                raise GitOperationError("No changes to commit")
            raise GitOperationError(f"Failed to commit: {stderr}")

        return True

    def push(
        self, repo_path: Path, branch_name: str, set_upstream: bool = True
    ) -> bool:
        """
        Push branch to remote.

        Args:
            repo_path: Repository path
            branch_name: Branch name to push
            set_upstream: Set upstream tracking (default: True)

        Returns:
            True if successful

        Raises:
            GitOperationError: If push fails
            GitAuthenticationError: If authentication fails

        Example:
            >>> service = GitOperationsService()
            >>> service.push(Path("~/.claude-mpm/cache/agents"), "improve/research-memory")
            True
        """
        self._validate_repo(repo_path)

        cmd = ["git", "push"]
        if set_upstream:
            cmd.extend(["-u", "origin", branch_name])
        else:
            cmd.extend(["origin", branch_name])

        returncode, _stdout, stderr = self._run_git_command(cmd, cwd=repo_path)

        if returncode != 0:
            # Check for authentication errors
            if any(
                keyword in stderr.lower()
                for keyword in ["authentication", "permission denied", "403"]
            ):
                raise GitAuthenticationError(
                    f"Git authentication failed. Please configure SSH keys or credentials: {stderr}"
                )
            raise GitOperationError(f"Failed to push branch: {stderr}")

        return True

    def pull(self, repo_path: Path, branch: str = "main") -> bool:
        """
        Pull latest changes from remote with automatic divergent branch recovery.

        For cache/sync repositories, automatically handles divergent branches by:
        1. First attempting git pull --rebase (cleaner history)
        2. If rebase fails or conflicts exist, hard reset to match remote exactly
           (cache repos should mirror remote state, local changes are discarded)

        Args:
            repo_path: Repository path
            branch: Branch name to pull

        Returns:
            True if successful

        Raises:
            GitOperationError: If pull fails
            GitConflictError: If merge conflicts detected and cannot be auto-resolved
        """
        self._validate_repo(repo_path)

        # First, try standard pull
        returncode, _stdout, stderr = self._run_git_command(
            ["git", "pull", "origin", branch], cwd=repo_path
        )

        if returncode == 0:
            return True

        # Check if this is a divergent branch situation
        is_divergent = any(
            phrase in stderr.lower()
            for phrase in [
                "divergent branches",
                "need to specify how to reconcile",
                "have diverged",
            ]
        )

        if is_divergent:
            logger.warning(
                f"Divergent branches detected in cache repository at {repo_path}. "
                "Attempting automatic recovery with rebase..."
            )

            # Strategy 1: Try rebase for cleaner history
            returncode, _stdout, stderr = self._run_git_command(
                ["git", "pull", "--rebase", "origin", branch], cwd=repo_path
            )

            if returncode == 0:
                logger.info(
                    f"Successfully resolved divergent branches with rebase for {branch}"
                )
                return True

            # Check if rebase had conflicts
            has_rebase_conflict = any(
                phrase in stderr.lower()
                for phrase in ["conflict", "rebase in progress"]
            )

            if has_rebase_conflict:
                logger.warning(
                    "Rebase conflicts detected. Aborting rebase and resetting to remote state..."
                )
                # Abort the rebase
                self._run_git_command(["git", "rebase", "--abort"], cwd=repo_path)

            # Strategy 2: Hard reset to match remote exactly (cache repos should mirror remote)
            logger.warning(
                f"Discarding local changes and resetting to origin/{branch} "
                "(cache repositories should match remote exactly)"
            )

            # Fetch latest to ensure we have the remote state
            returncode, _stdout, stderr = self._run_git_command(
                ["git", "fetch", "origin", branch], cwd=repo_path
            )

            if returncode != 0:
                raise GitOperationError(
                    f"Failed to fetch from remote during divergent branch recovery: {stderr}"
                )

            # Hard reset to remote branch
            returncode, _stdout, stderr = self._run_git_command(
                ["git", "reset", "--hard", f"origin/{branch}"], cwd=repo_path
            )

            if returncode != 0:
                raise GitOperationError(
                    f"Failed to reset to origin/{branch} during divergent branch recovery: {stderr}"
                )

            logger.info(
                f"Successfully reset cache repository to origin/{branch} "
                "(local changes discarded)"
            )
            return True

        # Check for merge conflicts (non-divergent case)
        if "conflict" in stderr.lower():
            raise GitConflictError(
                f"Merge conflicts detected when pulling {branch}: {stderr}"
            )

        # Other pull errors
        raise GitOperationError(f"Failed to pull {branch}: {stderr}")

        return True

    def checkout_branch(self, repo_path: Path, branch_name: str) -> bool:
        """
        Checkout existing branch.

        Args:
            repo_path: Repository path
            branch_name: Branch name to checkout

        Returns:
            True if successful

        Raises:
            GitOperationError: If checkout fails
        """
        self._validate_repo(repo_path)

        returncode, _stdout, stderr = self._run_git_command(
            ["git", "checkout", branch_name], cwd=repo_path
        )

        if returncode != 0:
            raise GitOperationError(f"Failed to checkout {branch_name}: {stderr}")

        return True

    def get_remote_url(self, repo_path: Path) -> Optional[str]:
        """
        Get remote origin URL.

        Args:
            repo_path: Repository path

        Returns:
            Remote URL or None if not configured

        Raises:
            GitOperationError: If command fails
        """
        self._validate_repo(repo_path)

        returncode, stdout, _stderr = self._run_git_command(
            ["git", "config", "--get", "remote.origin.url"], cwd=repo_path
        )

        if returncode != 0:
            return None

        return stdout.strip()

    def validate_repo(self, repo_path: Path) -> Tuple[bool, str]:
        """
        Validate repository configuration.

        Args:
            repo_path: Repository path

        Returns:
            Tuple of (is_valid, message)

        Example:
            >>> service = GitOperationsService()
            >>> valid, msg = service.validate_repo(Path("~/.claude-mpm/cache/agents"))
            >>> if not valid:
            ...     print(f"Repository invalid: {msg}")
        """
        try:
            if not repo_path.exists():
                return False, f"Path does not exist: {repo_path}"

            if not self.is_git_repo(repo_path):
                return False, f"Not a git repository: {repo_path}"

            remote_url = self.get_remote_url(repo_path)
            if not remote_url:
                return False, "No remote origin configured"

            return True, "Repository is valid"

        except Exception as e:
            return False, f"Validation failed: {e}"

    def rollback_changes(self, repo_path: Path, original_branch: str) -> bool:
        """
        Rollback uncommitted changes and return to original branch.

        Args:
            repo_path: Repository path
            original_branch: Branch to return to

        Returns:
            True if successful (best effort)
        """
        try:
            # Discard uncommitted changes
            self._run_git_command(["git", "reset", "--hard"], cwd=repo_path)

            # Checkout original branch
            self._run_git_command(["git", "checkout", original_branch], cwd=repo_path)

            return True

        except Exception:
            return False

    def _validate_repo(self, repo_path: Path) -> None:
        """
        Validate repository exists and is a git repo.

        Args:
            repo_path: Repository path

        Raises:
            GitOperationError: If validation fails
        """
        if not repo_path.exists():
            raise GitOperationError(f"Repository path does not exist: {repo_path}")

        if not self.is_git_repo(repo_path):
            raise GitOperationError(f"Not a git repository: {repo_path}")

    def _run_git_command(self, command: List[str], cwd: Path) -> Tuple[int, str, str]:
        """
        Run git command and return result.

        Args:
            command: Command and arguments
            cwd: Working directory

        Returns:
            Tuple of (returncode, stdout, stderr)
        """
        try:
            result = subprocess.run(
                command,
                check=False,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )

            return result.returncode, result.stdout, result.stderr

        except subprocess.TimeoutExpired as e:
            raise GitOperationError(
                f"Git command timed out after {self.timeout} seconds: {' '.join(command)}"
            ) from e
        except Exception as e:
            raise GitOperationError(f"Failed to run git command: {e}") from e

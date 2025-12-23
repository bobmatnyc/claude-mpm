"""
Cache Git Manager - Git workflow integration for agent cache management.

Design Decision: Wrap existing GitOperationsService instead of duplicating code

Rationale: GitOperationsService already provides all necessary git operations
(status, pull, commit, push) with proper error handling. This wrapper adapts
it specifically for cache directory operations without code duplication.

Trade-offs:
- Code Reuse: Leverages 90% of existing GitOperationsService (~400 lines)
- Maintainability: Changes to git operations benefit all users
- Specificity: Adds cache-specific behavior (status reporting, sync workflow)
- Simplicity: Net new code ~150 lines vs ~400 for complete reimplementation

Performance:
- Time Complexity: O(1) for status checks, O(n) for file operations where n = number of changed files
- Expected Performance:
  * Status check: ~100-200ms (git status + rev-list)
  * Pull latest: ~1-2s (git pull from GitHub)
  * Commit + push: ~2-3s (git commit + push)

Error Handling:
- Network unavailable: Warns user, continues with cached version
- Merge conflicts: Detects, displays files, guides user to manual resolution
- Detached HEAD: Warns user, provides recovery instructions
- Push rejected: Informs about remote changes, suggests pull first
- Uncommitted changes: Warns before pull, offers to continue or abort

Example:
    >>> from pathlib import Path
    >>> manager = CacheGitManager(Path.home() / ".claude-mpm/cache/agents")
    >>> if manager.is_git_repo():
    ...     status = manager.get_status()
    ...     print(f"Branch: {status['branch']}, Uncommitted: {len(status['uncommitted'])}")
    ...     success, msg = manager.pull_latest()
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from claude_mpm.services.git.git_operations_service import (
    GitAuthenticationError,
    GitConflictError,
    GitOperationError,
    GitOperationsService,
)

logger = logging.getLogger(__name__)


class CacheGitManager:
    """
    Git operations wrapper for agent cache directory.

    Design Decision: Composition over inheritance

    Rationale: Wraps GitOperationsService instead of inheriting to maintain
    separation of concerns. Cache-specific logic (sync workflow, status
    reporting) is independent from core git operations.

    Provides high-level git workflows specifically for cache management:
    - Pre-deploy git pull (sync latest agents)
    - Status reporting with uncommitted/unpushed detection
    - Full sync workflow (pull, handle conflicts, push)
    - User-friendly error messages for cache context
    """

    def __init__(self, cache_path: Path, timeout: int = 30):
        """
        Initialize cache git manager.

        Args:
            cache_path: Path to cache directory (should contain .git)
            timeout: Git command timeout in seconds (default: 30)

        Example:
            >>> cache_dir = Path.home() / ".claude-mpm/cache/agents"
            >>> manager = CacheGitManager(cache_dir)
        """
        self.cache_path = Path(cache_path)
        self.git_ops = GitOperationsService(timeout=timeout)

        # Find git repository root (cache_path or parent)
        self.repo_path = self._find_git_root()

        if self.repo_path:
            logger.debug(f"Initialized CacheGitManager for repo: {self.repo_path}")
        else:
            logger.warning(f"Cache path is not a git repository: {cache_path}")

    def _find_git_root(self) -> Optional[Path]:
        """
        Find git repository root starting from cache_path.

        Searches cache_path and up to 3 parent directories for .git directory.
        If not found upward, searches one level down into subdirectories.
        This handles both cases:
        - cache_path is inside repo (search upward)
        - repo is nested in cache_path (search downward)

        Returns:
            Path to repository root, or None if not a git repo

        Example:
            >>> # Case 1: cache_path inside repo (searches upward)
            >>> # cache_path: ~/.claude-mpm/cache/agents/bobmatnyc/claude-mpm-agents/agents
            >>> # Found at: ~/.claude-mpm/cache/agents/bobmatnyc/claude-mpm-agents

            >>> # Case 2: repo nested in cache_path (searches downward)
            >>> # cache_path: ~/.claude-mpm/cache/agents
            >>> # Found at: ~/.claude-mpm/cache/agents/bobmatnyc/claude-mpm-agents
        """
        # Strategy 1: Search upward (cache_path is inside repo)
        current = self.cache_path
        max_depth = 3

        for _ in range(max_depth):
            if self.git_ops.is_git_repo(current):
                return current
            parent = current.parent
            if parent == current:  # Reached filesystem root
                break
            current = parent

        # Strategy 2: Search downward one level (repo nested in cache_path)
        # Check immediate subdirectories for git repos
        if self.cache_path.is_dir():
            try:
                for subdir in self.cache_path.iterdir():
                    if subdir.is_dir():
                        # Check if subdir itself is a git repo
                        if self.git_ops.is_git_repo(subdir):
                            return subdir

                        # Check one level deeper (handle org/repo structure)
                        try:
                            for nested_dir in subdir.iterdir():
                                if nested_dir.is_dir() and self.git_ops.is_git_repo(
                                    nested_dir
                                ):
                                    return nested_dir
                        except (OSError, PermissionError):
                            # Skip subdirectories we can't read
                            continue
            except (OSError, PermissionError) as e:
                logger.debug(f"Could not scan cache directory for git repos: {e}")

        return None

    def is_git_repo(self) -> bool:
        """
        Check if cache is a git repository.

        Returns:
            True if cache contains a valid git repository, False otherwise

        Example:
            >>> if not manager.is_git_repo():
            ...     print("Cache is not a git repo. Falling back to HTTP sync.")
        """
        return self.repo_path is not None

    def get_status(self) -> Dict[str, Any]:
        """
        Get comprehensive git status for cache.

        Returns dictionary with current branch, uncommitted changes, and
        unpushed commits. Useful for warning users before destructive operations.

        Returns:
            Dictionary with status information:
            {
                "branch": "main",
                "uncommitted": ["agents/engineer.md", "agents/research.md"],
                "uncommitted_count": 2,
                "unpushed": 3,
                "is_clean": False,
                "remote_url": "https://github.com/owner/repo",
                "ahead": 3,
                "behind": 0
            }

        Error Handling:
        - Not a git repo: Returns error dict with "error" key
        - Git command failure: Logs error, returns partial status

        Example:
            >>> status = manager.get_status()
            >>> if status.get("uncommitted_count", 0) > 0:
            ...     print(f"Warning: {status['uncommitted_count']} uncommitted changes")
            ...     for file in status["uncommitted"]:
            ...         print(f"  - {file}")
        """
        if not self.is_git_repo():
            return {"error": "Not a git repository", "is_clean": True}

        try:
            # Get current branch
            branch = self.git_ops.get_current_branch(self.repo_path)

            # Get uncommitted changes
            has_changes = self.git_ops.has_uncommitted_changes(self.repo_path)
            uncommitted_files: List[str] = []

            if has_changes:
                # Parse git status --porcelain for file list
                returncode, stdout, _stderr = self.git_ops._run_git_command(
                    ["git", "status", "--porcelain"], cwd=self.repo_path
                )
                if returncode == 0:
                    # Split without stripping first to preserve format
                    for line in stdout.split("\n"):
                        if line.strip():
                            # Extract filename from git status output (format: "XY filename")
                            # Skip first 3 characters (2 status + 1 space)
                            filename = (
                                line[3:].strip() if len(line) > 3 else line.strip()
                            )
                            if filename:
                                uncommitted_files.append(filename)

            # Get unpushed commits (commits ahead of remote)
            ahead = 0
            behind = 0
            try:
                returncode, stdout, _stderr = self.git_ops._run_git_command(
                    [
                        "git",
                        "rev-list",
                        "--left-right",
                        "--count",
                        f"origin/{branch}...HEAD",
                    ],
                    cwd=self.repo_path,
                )
                if returncode == 0 and stdout.strip():
                    parts = stdout.strip().split()
                    if len(parts) == 2:
                        try:
                            behind, ahead = map(int, parts)
                        except ValueError:
                            # Parsing error, skip ahead/behind count
                            logger.debug(
                                f"Could not parse rev-list output: {stdout.strip()}"
                            )
            except (GitOperationError, Exception) as e:
                # No remote tracking branch configured or other error
                logger.debug(f"Could not get ahead/behind count: {e}")

            # Get remote URL
            remote_url = self.git_ops.get_remote_url(self.repo_path)

            return {
                "branch": branch,
                "uncommitted": uncommitted_files,
                "uncommitted_count": len(uncommitted_files),
                "unpushed": ahead,
                "is_clean": not has_changes and ahead == 0,
                "remote_url": remote_url,
                "ahead": ahead,
                "behind": behind,
            }

        except GitOperationError as e:
            logger.error(f"Error getting git status: {e}")
            return {
                "error": str(e),
                "is_clean": False,
            }

    def pull_latest(self, branch: str = "main") -> Tuple[bool, str]:
        """
        Pull latest changes from remote.

        Design Decision: Non-blocking pull with informative messages

        Rationale: Pull failures shouldn't stop deployment. Cache may be
        outdated but still usable. HTTP sync provides fallback mechanism.

        Args:
            branch: Branch to pull (default: "main")

        Returns:
            Tuple of (success, message) where:
            - success: True if pull succeeded, False if failed
            - message: Human-readable status message

        Error Handling:
        - Merge conflicts: Returns (False, detailed conflict message)
        - Network errors: Returns (False, network error message)
        - Detached HEAD: Returns (False, recovery instructions)
        - Success: Returns (True, summary of changes)

        Example:
            >>> success, msg = manager.pull_latest()
            >>> if not success:
            ...     logger.warning(f"Pull failed: {msg}")
            ...     logger.info("Continuing with cached version")
        """
        if not self.is_git_repo():
            return False, "Not a git repository"

        try:
            # Check for uncommitted changes first
            if self.git_ops.has_uncommitted_changes(self.repo_path):
                uncommitted_count = len(self.get_status().get("uncommitted", []))
                logger.warning(
                    f"Cache has {uncommitted_count} uncommitted change(s). "
                    "Pull may fail or create merge conflicts."
                )

            # Perform pull
            self.git_ops.pull(self.repo_path, branch)

            logger.info(f"Successfully pulled latest changes from {branch}")
            return True, f"Successfully pulled latest changes from {branch}"

        except GitConflictError:
            # Parse conflict details from error message
            conflict_msg = (
                f"Merge conflicts detected when pulling {branch}. "
                "Manual resolution required.\n\n"
                "To resolve:\n"
                f"  1. cd {self.repo_path}\n"
                "  2. Resolve conflicts in affected files\n"
                "  3. git add <resolved-files>\n"
                "  4. git commit\n"
                "  5. Run sync again"
            )
            logger.error(conflict_msg)
            return False, conflict_msg

        except GitOperationError as e:
            error_msg = f"Failed to pull {branch}: {e!s}"
            logger.error(error_msg)
            return False, error_msg

    def commit_changes(
        self, message: str, files: Optional[List[Path]] = None
    ) -> Tuple[bool, str]:
        """
        Commit changes to cache.

        Args:
            message: Commit message (should follow conventional commits format)
            files: Specific files to commit (None = all modified files)

        Returns:
            Tuple of (success, message)

        Error Handling:
        - No changes to commit: Returns (False, informative message)
        - Git commit failure: Returns (False, error details)
        - File staging error: Returns (False, staging error message)

        Example:
            >>> success, msg = manager.commit_changes(
            ...     "feat: update agents from local development",
            ...     files=[Path("agents/engineer.md")]
            ... )
            >>> if success:
            ...     print(f"Committed: {msg}")
        """
        if not self.is_git_repo():
            return False, "Not a git repository"

        try:
            # Stage files
            if files:
                # Convert Path objects to strings relative to repo root
                file_strs = [str(f.relative_to(self.repo_path)) for f in files]
                self.git_ops.stage_files(self.repo_path, file_strs)
            else:
                # Stage all changes
                self.git_ops.stage_files(self.repo_path, ["."])

            # Commit
            self.git_ops.commit(self.repo_path, message)

            logger.info(f"Committed changes: {message[:50]}")
            return True, "Successfully committed changes"

        except GitOperationError as e:
            error_msg = f"Failed to commit: {e!s}"
            logger.error(error_msg)
            return False, error_msg

    def push_changes(self, branch: str = "main") -> Tuple[bool, str]:
        """
        Push committed changes to remote.

        Args:
            branch: Branch to push (default: "main")

        Returns:
            Tuple of (success, message)

        Error Handling:
        - Authentication failure: Returns (False, auth error with instructions)
        - Push rejected: Returns (False, suggests pull first)
        - Network error: Returns (False, network error message)

        Example:
            >>> success, msg = manager.push_changes()
            >>> if not success:
            ...     if "authentication" in msg.lower():
            ...         print("Configure SSH keys or GitHub token")
        """
        if not self.is_git_repo():
            return False, "Not a git repository"

        try:
            self.git_ops.push(self.repo_path, branch, set_upstream=True)

            logger.info(f"Successfully pushed changes to {branch}")
            return True, f"Successfully pushed changes to {branch}"

        except GitAuthenticationError as e:
            error_msg = (
                f"Authentication failed: {e!s}\n\n"
                "To fix:\n"
                "  1. Configure SSH keys: ssh-keygen -t ed25519\n"
                "  2. Add to GitHub: https://github.com/settings/keys\n"
                "  OR\n"
                "  3. Use HTTPS with token: git remote set-url origin https://TOKEN@github.com/owner/repo"
            )
            logger.error(error_msg)
            return False, error_msg

        except GitOperationError as e:
            # Check if push was rejected due to remote changes
            if "rejected" in str(e).lower() or "non-fast-forward" in str(e).lower():
                error_msg = (
                    "Push rejected: Remote has changes you don't have locally.\n\n"
                    "To fix:\n"
                    "  1. Pull latest changes: git pull origin main\n"
                    "  2. Resolve any conflicts\n"
                    "  3. Push again"
                )
            else:
                error_msg = f"Failed to push: {e!s}"

            logger.error(error_msg)
            return False, error_msg

    def has_uncommitted_changes(self) -> bool:
        """
        Check for uncommitted changes in cache.

        Returns:
            True if there are uncommitted changes, False otherwise

        Example:
            >>> if manager.has_uncommitted_changes():
            ...     print("⚠️  Uncommitted changes detected")
            ...     print("Commit changes before pushing")
        """
        if not self.is_git_repo():
            return False

        try:
            return self.git_ops.has_uncommitted_changes(self.repo_path)
        except GitOperationError:
            return False

    def has_unpushed_commits(self) -> bool:
        """
        Check for commits not pushed to remote.

        Returns:
            True if there are unpushed commits, False otherwise

        Example:
            >>> if manager.has_unpushed_commits():
            ...     print("📤 You have local commits not pushed to remote")
            ...     print("Run: claude-mpm agents cache-push")
        """
        status = self.get_status()
        return status.get("unpushed", 0) > 0

    def check_conflicts(self) -> List[Path]:
        """
        Check for merge conflicts after pull.

        Scans working directory for Git conflict markers (<<<<<<, ======, >>>>>>).

        Returns:
            List of file paths with unresolved conflicts

        Algorithm:
        1. Run git status --porcelain to find files with merge conflicts
        2. Look for "UU" status (both modified - conflict)
        3. Return relative paths for user-friendly display

        Example:
            >>> conflicts = manager.check_conflicts()
            >>> if conflicts:
            ...     print("⚠️  Merge conflicts detected:")
            ...     for file in conflicts:
            ...         print(f"  - {file}")
        """
        if not self.is_git_repo():
            return []

        try:
            returncode, stdout, _stderr = self.git_ops._run_git_command(
                ["git", "status", "--porcelain"], cwd=self.repo_path
            )

            if returncode != 0:
                return []

            # Parse git status output for conflict markers
            conflicted_files: List[Path] = []
            for line in stdout.strip().split("\n"):
                if line.strip():
                    status = line[:2]
                    # "UU" means both modified (merge conflict)
                    # "AA" means both added
                    # "DD" means both deleted
                    if status in ["UU", "AA", "DD", "AU", "UA", "DU", "UD"]:
                        filename = line[3:].strip()
                        conflicted_files.append(Path(filename))

            return conflicted_files

        except GitOperationError as e:
            logger.error(f"Error checking conflicts: {e}")
            return []

    def sync_with_remote(self) -> Tuple[bool, str]:
        """
        Full sync workflow: pull, handle conflicts, push if needed.

        Design Decision: Three-phase sync with conflict detection

        Rationale: Provides complete sync automation while protecting against
        data loss. Detects issues (uncommitted changes, conflicts) and guides
        user through resolution rather than silently failing.

        Workflow:
        1. Check for uncommitted changes (warn user but continue)
        2. Pull latest from remote
        3. Detect and report conflicts (stops if found)
        4. Push local commits if any exist and no conflicts

        Returns:
            Tuple of (success, detailed_message)

        Error Handling:
        - Uncommitted changes: Warns user, continues with pull
        - Conflicts: Stops sync, provides resolution instructions
        - Network errors: Reports error, doesn't attempt push
        - Push failures: Reports error with recovery instructions

        Example:
            >>> success, msg = manager.sync_with_remote()
            >>> print(msg)  # Detailed breakdown of sync process
            >>> if not success:
            ...     logger.error("Sync failed, investigate manually")
        """
        if not self.is_git_repo():
            return False, "Not a git repository"

        status_log = []

        # Phase 1: Check for uncommitted changes
        status_log.append("Phase 1: Checking local changes...")
        if self.has_uncommitted_changes():
            uncommitted_count = self.get_status().get("uncommitted_count", 0)
            warning = (
                f"⚠️  Warning: {uncommitted_count} uncommitted change(s) detected.\n"
                "   Sync will continue, but you should commit these changes."
            )
            status_log.append(warning)
            logger.warning(warning)

        # Phase 2: Pull latest
        status_log.append("\nPhase 2: Pulling latest changes...")
        pull_success, pull_msg = self.pull_latest()

        if not pull_success:
            status_log.append(f"❌ Pull failed: {pull_msg}")
            return False, "\n".join(status_log)

        status_log.append(f"✅ {pull_msg}")

        # Phase 3: Check for conflicts
        status_log.append("\nPhase 3: Checking for conflicts...")
        conflicts = self.check_conflicts()

        if conflicts:
            conflict_msg = (
                f"❌ {len(conflicts)} merge conflict(s) detected:\n"
                + "\n".join(f"  - {file}" for file in conflicts)
                + "\n\nResolve conflicts manually before continuing."
            )
            status_log.append(conflict_msg)
            return False, "\n".join(status_log)

        status_log.append("✅ No conflicts detected")

        # Phase 4: Push if we have local commits
        status_log.append("\nPhase 4: Checking for local commits...")
        if self.has_unpushed_commits():
            unpushed = self.get_status().get("unpushed", 0)
            status_log.append(f"📤 Pushing {unpushed} local commit(s)...")

            push_success, push_msg = self.push_changes()
            if not push_success:
                status_log.append(f"❌ Push failed: {push_msg}")
                return False, "\n".join(status_log)

            status_log.append(f"✅ {push_msg}")
        else:
            status_log.append("✅ No local commits to push")

        status_log.append("\n✅ Sync complete!")
        return True, "\n".join(status_log)

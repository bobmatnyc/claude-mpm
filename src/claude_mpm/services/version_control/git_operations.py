from pathlib import Path

"""
Git Operations Manager - Core Git operation automation for Version Control Agent.

This module provides comprehensive Git operation management including:
1. Branch creation and management
2. Merge operations and conflict resolution
3. Remote operations and synchronization
4. Quality gate integration
5. Automatic branch lifecycle management
"""

import logging
import os
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class GitBranchInfo:
    """Information about a Git branch."""

    name: str
    current: bool
    remote: Optional[str] = None
    upstream: Optional[str] = None
    last_commit: Optional[str] = None
    last_commit_message: Optional[str] = None
    ahead: int = 0
    behind: int = 0
    modified_files: List[str] = field(default_factory=list)


@dataclass
class GitOperationResult:
    """Result of a Git operation."""

    success: bool
    operation: str
    message: str
    output: str = ""
    error: str = ""
    branch_before: Optional[str] = None
    branch_after: Optional[str] = None
    files_changed: List[str] = field(default_factory=list)
    execution_time: float = 0.0


class GitOperationError(Exception):
    """Exception raised for Git operation errors."""

    def __init__(
        self, message: str, command: str = "", output: str = "", error: str = ""
    ):
        super().__init__(message)
        self.command = command
        self.output = output
        self.error = error


class GitOperationsManager:
    """
    Manages Git operations for the Version Control Agent.

    Provides comprehensive Git operation automation including branch management,
    merging, remote operations, and integration with quality gates.
    """

    def __init__(self, project_root: str, logger: logging.Logger):
        """
        Initialize Git Operations Manager.

        Args:
            project_root: Root directory of the Git repository
            logger: Logger instance
        """
        self.project_root = Path(project_root)
        self.logger = logger
        self.git_dir = self.project_root / ".git"

        # Branch naming conventions
        self.branch_prefixes = {
            "issue": "issue/",
            "feature": "feature/",
            "enhancement": "enhancement/",
            "hotfix": "hotfix/",
            "epic": "epic/",
        }

        # Merge strategies
        self.merge_strategies = {
            "merge": "--no-ff",
            "squash": "--squash",
            "rebase": "--rebase",
        }

        # Validate Git repository
        if not self._is_git_repository():
            raise GitOperationError(f"Not a Git repository: {project_root}")

    def _is_git_repository(self) -> bool:
        """Check if the directory is a Git repository."""
        return self.git_dir.exists() and self.git_dir.is_dir()

    def _run_git_command(
        self,
        args: List[str],
        check: bool = True,
        capture_output: bool = True,
        cwd: Optional[str] = None,
    ) -> subprocess.CompletedProcess:
        """
        Run a Git command and return the result.

        Args:
            args: Git command arguments
            check: Whether to raise exception on non-zero exit
            capture_output: Whether to capture stdout/stderr
            cwd: Working directory (defaults to project_root)

        Returns:
            CompletedProcess result

        Raises:
            GitOperationError: If command fails and check=True
        """
        cmd = ["git", *args]
        cwd = cwd or str(self.project_root)

        try:
            self.logger.debug(f"Running Git command: {' '.join(cmd)}")

            result = subprocess.run(
                cmd, cwd=cwd, capture_output=capture_output, text=True, check=False
            )

            if check and result.returncode != 0:
                raise GitOperationError(
                    f"Git command failed: {' '.join(cmd)}",
                    command=" ".join(cmd),
                    output=result.stdout,
                    error=result.stderr,
                )

            return result

        except FileNotFoundError:
            raise GitOperationError("Git is not installed or not in PATH")
        except Exception as e:
            raise GitOperationError(f"Error running Git command: {e}")

    def get_current_branch(self) -> str:
        """Get the current Git branch name."""
        try:
            result = self._run_git_command(["branch", "--show-current"])
            return result.stdout.strip()
        except GitOperationError:
            # Fallback for older Git versions
            result = self._run_git_command(["rev-parse", "--abbrev-ref", "HEAD"])
            return result.stdout.strip()

    def get_branch_info(self, branch_name: Optional[str] = None) -> GitBranchInfo:
        """
        Get detailed information about a branch.

        Args:
            branch_name: Branch name (defaults to current branch)

        Returns:
            GitBranchInfo object with branch details
        """
        if not branch_name:
            branch_name = self.get_current_branch()

        # Get basic branch info
        current_branch = self.get_current_branch()
        is_current = branch_name == current_branch

        # Get remote tracking info
        remote = None
        upstream = None
        ahead = 0
        behind = 0

        try:
            # Get remote tracking branch
            result = self._run_git_command(
                ["rev-parse", "--abbrev-ref", f"{branch_name}@{{upstream}}"],
                check=False,
            )

            if result.returncode == 0:
                upstream = result.stdout.strip()
                remote = upstream.split("/")[0] if "/" in upstream else None

                # Get ahead/behind info
                result = self._run_git_command(
                    [
                        "rev-list",
                        "--left-right",
                        "--count",
                        f"{upstream}...{branch_name}",
                    ],
                    check=False,
                )

                if result.returncode == 0:
                    parts = result.stdout.strip().split()
                    if len(parts) == 2:
                        behind, ahead = map(int, parts)

        except GitOperationError:
            pass

        # Get last commit info
        last_commit = None
        last_commit_message = None

        try:
            result = self._run_git_command(
                ["log", "-1", "--format=%H", branch_name], check=False
            )

            if result.returncode == 0:
                last_commit = result.stdout.strip()

                result = self._run_git_command(
                    ["log", "-1", "--format=%s", branch_name], check=False
                )

                if result.returncode == 0:
                    last_commit_message = result.stdout.strip()

        except GitOperationError:
            pass

        # Get modified files if current branch
        modified_files = []
        if is_current:
            modified_files = self.get_modified_files()

        return GitBranchInfo(
            name=branch_name,
            current=is_current,
            remote=remote,
            upstream=upstream,
            last_commit=last_commit,
            last_commit_message=last_commit_message,
            ahead=ahead,
            behind=behind,
            modified_files=modified_files,
        )

    def get_all_branches(self, include_remotes: bool = False) -> List[GitBranchInfo]:
        """
        Get information about all branches.

        Args:
            include_remotes: Whether to include remote branches

        Returns:
            List of GitBranchInfo objects
        """
        branches = []

        # Get local branches
        result = self._run_git_command(["branch", "--list"])
        for line in result.stdout.strip().split("\n"):
            if line.strip():
                branch_name = line.strip().lstrip("* ").strip()
                if branch_name:
                    branches.append(self.get_branch_info(branch_name))

        # Get remote branches if requested
        if include_remotes:
            result = self._run_git_command(["branch", "-r"], check=False)
            if result.returncode == 0:
                for line in result.stdout.strip().split("\n"):
                    if line.strip() and not line.strip().endswith("/HEAD"):
                        remote_branch = line.strip()
                        # Create simplified info for remote branches
                        branches.append(
                            GitBranchInfo(
                                name=remote_branch,
                                current=False,
                                remote=(
                                    remote_branch.split("/")[0]
                                    if "/" in remote_branch
                                    else None
                                ),
                            )
                        )

        return branches

    def get_modified_files(self) -> List[str]:
        """Get list of modified files in working directory."""
        try:
            result = self._run_git_command(["status", "--porcelain"])
            modified_files = []

            for line in result.stdout.strip().split("\n"):
                if line.strip():
                    # Extract filename from git status output
                    filename = line[3:].strip()
                    modified_files.append(filename)

            return modified_files

        except GitOperationError:
            return []

    def is_working_directory_clean(self) -> bool:
        """Check if working directory is clean (no uncommitted changes)."""
        try:
            result = self._run_git_command(["status", "--porcelain"])
            return not result.stdout.strip()
        except GitOperationError:
            return False

    def is_file_tracked(self, file_path: str) -> bool:
        """
        Check if a file is tracked by git.

        Args:
            file_path: Path to the file to check (can be absolute or relative)

        Returns:
            bool: True if file is tracked, False otherwise
        """
        try:
            # Convert to relative path if absolute
            if os.path.isabs(file_path):
                try:
                    file_path = os.path.relpath(file_path, self.project_root)
                except ValueError:
                    # If file is outside project root, it's not tracked
                    return False

            # Use git ls-files to check if file is tracked
            result = self._run_git_command(["ls-files", "--", file_path])
            return bool(result.stdout.strip())

        except GitOperationError:
            return False

    def create_branch(
        self,
        branch_name: str,
        branch_type: str = "issue",
        base_branch: str = "main",
        switch_to_branch: bool = True,
    ) -> GitOperationResult:
        """
        Create a new Git branch with proper naming conventions.

        Args:
            branch_name: Base name for the branch
            branch_type: Type of branch (issue, feature, enhancement, hotfix, epic)
            base_branch: Base branch to create from
            switch_to_branch: Whether to switch to the new branch

        Returns:
            GitOperationResult with operation details
        """
        start_time = datetime.now()
        current_branch = self.get_current_branch()

        # Generate full branch name with prefix
        prefix = self.branch_prefixes.get(branch_type, "")
        full_branch_name = f"{prefix}{branch_name}"

        try:
            # Ensure we're on the base branch
            if current_branch != base_branch:
                self._run_git_command(["checkout", base_branch])

                # Pull latest changes from base branch
                self._run_git_command(["pull", "origin", base_branch], check=False)

            # Create the new branch
            create_args = ["checkout", "-b", full_branch_name]
            if not switch_to_branch:
                create_args = ["branch", full_branch_name]

            result = self._run_git_command(create_args)

            # Set up remote tracking if creating a new branch
            if switch_to_branch:
                try:
                    self._run_git_command(
                        ["push", "-u", "origin", full_branch_name], check=False
                    )
                except GitOperationError:
                    # Remote push failed, continue without remote tracking
                    pass

            execution_time = (datetime.now() - start_time).total_seconds()

            return GitOperationResult(
                success=True,
                operation="create_branch",
                message=f"Successfully created branch: {full_branch_name}",
                output=result.stdout,
                branch_before=current_branch,
                branch_after=full_branch_name if switch_to_branch else current_branch,
                execution_time=execution_time,
            )

        except GitOperationError as e:
            execution_time = (datetime.now() - start_time).total_seconds()

            return GitOperationResult(
                success=False,
                operation="create_branch",
                message=f"Failed to create branch: {full_branch_name}",
                error=str(e),
                branch_before=current_branch,
                branch_after=current_branch,
                execution_time=execution_time,
            )

    def switch_branch(self, branch_name: str) -> GitOperationResult:
        """
        Switch to an existing branch.

        Args:
            branch_name: Name of branch to switch to

        Returns:
            GitOperationResult with operation details
        """
        start_time = datetime.now()
        current_branch = self.get_current_branch()

        try:
            # Check if working directory is clean
            if not self.is_working_directory_clean():
                modified_files = self.get_modified_files()
                return GitOperationResult(
                    success=False,
                    operation="switch_branch",
                    message="Cannot switch branch: uncommitted changes exist",
                    error=f"Modified files: {', '.join(modified_files)}",
                    branch_before=current_branch,
                    branch_after=current_branch,
                    files_changed=modified_files,
                    execution_time=(datetime.now() - start_time).total_seconds(),
                )

            # Switch to the branch
            result = self._run_git_command(["checkout", branch_name])

            execution_time = (datetime.now() - start_time).total_seconds()

            return GitOperationResult(
                success=True,
                operation="switch_branch",
                message=f"Successfully switched to branch: {branch_name}",
                output=result.stdout,
                branch_before=current_branch,
                branch_after=branch_name,
                execution_time=execution_time,
            )

        except GitOperationError as e:
            execution_time = (datetime.now() - start_time).total_seconds()

            return GitOperationResult(
                success=False,
                operation="switch_branch",
                message=f"Failed to switch to branch: {branch_name}",
                error=str(e),
                branch_before=current_branch,
                branch_after=current_branch,
                execution_time=execution_time,
            )

    def merge_branch(
        self,
        source_branch: str,
        target_branch: str = "main",
        merge_strategy: str = "merge",
        delete_source: bool = True,
    ) -> GitOperationResult:
        """
        Merge a source branch into target branch.

        Args:
            source_branch: Branch to merge from
            target_branch: Branch to merge into
            merge_strategy: Merge strategy (merge, squash, rebase)
            delete_source: Whether to delete source branch after merge

        Returns:
            GitOperationResult with operation details
        """
        start_time = datetime.now()
        current_branch = self.get_current_branch()

        try:
            # Switch to target branch
            if current_branch != target_branch:
                switch_result = self.switch_branch(target_branch)
                if not switch_result.success:
                    return switch_result

            # Pull latest changes
            self._run_git_command(["pull", "origin", target_branch], check=False)

            # Perform merge based on strategy
            strategy_arg = self.merge_strategies.get(merge_strategy, "--no-ff")

            if merge_strategy == "rebase":
                # Rebase strategy
                result = self._run_git_command(["rebase", source_branch])
            else:
                # Merge strategy
                merge_args = ["merge", strategy_arg, source_branch]
                if merge_strategy == "merge":
                    # Add merge commit message
                    merge_args.extend(
                        ["-m", f"Merge {source_branch} into {target_branch}"]
                    )

                result = self._run_git_command(merge_args)

            # Delete source branch if requested
            if delete_source and source_branch != target_branch:
                try:
                    # Delete local branch
                    self._run_git_command(["branch", "-d", source_branch], check=False)

                    # Delete remote branch
                    self._run_git_command(
                        ["push", "origin", "--delete", source_branch], check=False
                    )
                except GitOperationError:
                    # Branch deletion failed, but merge was successful
                    pass

            execution_time = (datetime.now() - start_time).total_seconds()

            return GitOperationResult(
                success=True,
                operation="merge_branch",
                message=f"Successfully merged {source_branch} into {target_branch}",
                output=result.stdout,
                branch_before=current_branch,
                branch_after=target_branch,
                execution_time=execution_time,
            )

        except GitOperationError as e:
            execution_time = (datetime.now() - start_time).total_seconds()

            return GitOperationResult(
                success=False,
                operation="merge_branch",
                message=f"Failed to merge {source_branch} into {target_branch}",
                error=str(e),
                branch_before=current_branch,
                branch_after=current_branch,
                execution_time=execution_time,
            )

    def detect_merge_conflicts(
        self, source_branch: str, target_branch: str
    ) -> Dict[str, Any]:
        """
        Detect potential merge conflicts between branches.

        Args:
            source_branch: Source branch
            target_branch: Target branch

        Returns:
            Dictionary with conflict information
        """
        try:
            # Perform a dry-run merge to detect conflicts
            result = self._run_git_command(
                [
                    "merge-tree",
                    f"$(git merge-base {target_branch} {source_branch})",
                    target_branch,
                    source_branch,
                ],
                check=False,
            )

            has_conflicts = result.returncode != 0 or "<<<<<<< " in result.stdout

            # Parse conflicted files
            conflicted_files = []
            if has_conflicts:
                lines = result.stdout.split("\n")

                for line in lines:
                    if line.startswith(("+++", "---")):
                        # Extract filename
                        parts = line.split("\t")
                        if len(parts) > 1:
                            filename = parts[1].strip()
                            if (
                                filename != "/dev/null"
                                and filename not in conflicted_files
                            ):
                                conflicted_files.append(filename)

            return {
                "has_conflicts": has_conflicts,
                "conflicted_files": conflicted_files,
                "can_auto_merge": not has_conflicts,
                "merge_base": self._get_merge_base(source_branch, target_branch),
            }

        except GitOperationError:
            return {
                "has_conflicts": True,
                "conflicted_files": [],
                "can_auto_merge": False,
                "error": "Could not detect conflicts",
            }

    def _get_merge_base(self, branch1: str, branch2: str) -> Optional[str]:
        """Get the merge base commit between two branches."""
        try:
            result = self._run_git_command(["merge-base", branch1, branch2])
            return result.stdout.strip()
        except GitOperationError:
            return None

    def push_to_remote(
        self,
        branch_name: Optional[str] = None,
        remote: str = "origin",
        set_upstream: bool = False,
    ) -> GitOperationResult:
        """
        Push branch to remote repository.

        Args:
            branch_name: Branch to push (defaults to current branch)
            remote: Remote name
            set_upstream: Whether to set upstream tracking

        Returns:
            GitOperationResult with operation details
        """
        start_time = datetime.now()
        current_branch = self.get_current_branch()

        if not branch_name:
            branch_name = current_branch

        try:
            # Build push command
            push_args = ["push"]

            if set_upstream:
                push_args.extend(["-u", remote, branch_name])
            else:
                push_args.extend([remote, branch_name])

            result = self._run_git_command(push_args)

            execution_time = (datetime.now() - start_time).total_seconds()

            return GitOperationResult(
                success=True,
                operation="push_to_remote",
                message=f"Successfully pushed {branch_name} to {remote}",
                output=result.stdout,
                branch_before=current_branch,
                branch_after=current_branch,
                execution_time=execution_time,
            )

        except GitOperationError as e:
            execution_time = (datetime.now() - start_time).total_seconds()

            return GitOperationResult(
                success=False,
                operation="push_to_remote",
                message=f"Failed to push {branch_name} to {remote}",
                error=str(e),
                branch_before=current_branch,
                branch_after=current_branch,
                execution_time=execution_time,
            )

    def sync_with_remote(
        self, branch_name: Optional[str] = None, remote: str = "origin"
    ) -> GitOperationResult:
        """
        Sync local branch with remote (fetch + pull).

        Args:
            branch_name: Branch to sync (defaults to current branch)
            remote: Remote name

        Returns:
            GitOperationResult with operation details
        """
        start_time = datetime.now()
        current_branch = self.get_current_branch()

        if not branch_name:
            branch_name = current_branch

        try:
            # Fetch latest changes
            self._run_git_command(["fetch", remote])

            # Pull changes if on the target branch
            if current_branch == branch_name:
                result = self._run_git_command(["pull", remote, branch_name])
            else:
                # Switch to branch, pull, then switch back
                self._run_git_command(["checkout", branch_name])
                result = self._run_git_command(["pull", remote, branch_name])
                self._run_git_command(["checkout", current_branch])

            execution_time = (datetime.now() - start_time).total_seconds()

            return GitOperationResult(
                success=True,
                operation="sync_with_remote",
                message=f"Successfully synced {branch_name} with {remote}",
                output=result.stdout,
                branch_before=current_branch,
                branch_after=current_branch,
                execution_time=execution_time,
            )

        except GitOperationError as e:
            execution_time = (datetime.now() - start_time).total_seconds()

            return GitOperationResult(
                success=False,
                operation="sync_with_remote",
                message=f"Failed to sync {branch_name} with {remote}",
                error=str(e),
                branch_before=current_branch,
                branch_after=current_branch,
                execution_time=execution_time,
            )

    def cleanup_merged_branches(
        self, target_branch: str = "main"
    ) -> GitOperationResult:
        """
        Clean up branches that have been merged into target branch.

        Args:
            target_branch: Target branch to check for merged branches

        Returns:
            GitOperationResult with cleanup details
        """
        start_time = datetime.now()
        current_branch = self.get_current_branch()

        try:
            # Get merged branches
            result = self._run_git_command(["branch", "--merged", target_branch])

            merged_branches = []
            for line in result.stdout.strip().split("\n"):
                branch = line.strip().lstrip("* ").strip()
                # Skip target branch and current branch
                if branch and branch not in (target_branch, current_branch):
                    merged_branches.append(branch)

            # Delete merged branches
            deleted_branches = []
            for branch in merged_branches:
                try:
                    self._run_git_command(["branch", "-d", branch])
                    deleted_branches.append(branch)
                except GitOperationError:
                    # Skip branches that can't be deleted
                    pass

            # Clean up remote tracking branches
            self._run_git_command(["remote", "prune", "origin"], check=False)

            execution_time = (datetime.now() - start_time).total_seconds()

            return GitOperationResult(
                success=True,
                operation="cleanup_merged_branches",
                message=f"Cleaned up {len(deleted_branches)} merged branches",
                output=f"Deleted branches: {', '.join(deleted_branches)}",
                branch_before=current_branch,
                branch_after=current_branch,
                execution_time=execution_time,
            )

        except GitOperationError as e:
            execution_time = (datetime.now() - start_time).total_seconds()

            return GitOperationResult(
                success=False,
                operation="cleanup_merged_branches",
                message="Failed to cleanup merged branches",
                error=str(e),
                branch_before=current_branch,
                branch_after=current_branch,
                execution_time=execution_time,
            )

    def get_repository_status(self) -> Dict[str, Any]:
        """Get comprehensive repository status."""
        try:
            current_branch = self.get_current_branch()
            branch_info = self.get_branch_info(current_branch)
            all_branches = self.get_all_branches()

            return {
                "current_branch": current_branch,
                "branch_info": branch_info,
                "total_branches": len(all_branches),
                "working_directory_clean": self.is_working_directory_clean(),
                "modified_files": self.get_modified_files(),
                "repository_root": str(self.project_root),
                "is_git_repository": self._is_git_repository(),
            }

        except Exception as e:
            return {
                "error": str(e),
                "repository_root": str(self.project_root),
                "is_git_repository": self._is_git_repository(),
            }

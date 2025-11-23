"""Git operation event handlers for Socket.IO.

WHY: This module handles all git-related events including branch queries,
file tracking status, and git add operations. Isolating git operations
improves maintainability and makes it easier to extend git functionality.
"""

import asyncio
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from .base import BaseEventHandler


class GitEventHandler(BaseEventHandler):
    """Handles git-related Socket.IO events.

    WHY: Git operations are a distinct domain that benefits from focused
    handling. This includes checking branches, file tracking status,
    and adding files to git. Separating these improves code organization.
    """

    def register_events(self) -> None:
        """Register git-related event handlers."""

        @self.sio.event
        async def get_git_branch(sid, working_dir=None):
            """Get the current git branch for a directory.

            WHY: The dashboard needs to display the current git branch
            to provide context about which branch changes are being made on.
            """
            try:
                # Debug: get_git_branch called

                # Validate and sanitize working directory
                working_dir = self._sanitize_working_dir(working_dir, "get_git_branch")

                if not await self._validate_directory(
                    sid, working_dir, "git_branch_response"
                ):
                    return

                # Debug: Running git command

                # Run git command to get current branch
                result = subprocess.run(
                    ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                    cwd=working_dir,
                    capture_output=True,
                    text=True,
                    check=False,
                )

                # Debug: Git command completed

                if result.returncode == 0:
                    branch = result.stdout.strip()
                    # Debug: Successfully got git branch
                    await self.emit_to_client(
                        sid,
                        "git_branch_response",
                        {
                            "success": True,
                            "branch": branch,
                            "working_dir": working_dir,
                            "original_working_dir": working_dir,
                        },
                    )
                else:
                    self.logger.warning(f"Git command failed: {result.stderr}")
                    await self.emit_to_client(
                        sid,
                        "git_branch_response",
                        {
                            "success": False,
                            "error": "Not a git repository",
                            "working_dir": working_dir,
                            "original_working_dir": working_dir,
                            "git_error": result.stderr,
                        },
                    )

            except Exception as e:
                self.log_error("get_git_branch", e, {"working_dir": working_dir})
                await self.emit_to_client(
                    sid,
                    "git_branch_response",
                    {
                        "success": False,
                        "error": str(e),
                        "working_dir": working_dir,
                        "original_working_dir": working_dir,
                    },
                )

        @self.sio.event
        async def check_file_tracked(sid, data):
            """Check if a file is tracked by git.

            WHY: The dashboard needs to know if a file is tracked by git
            to determine whether to show git-related UI elements.
            """
            try:
                file_path = data.get("file_path")
                working_dir = data.get("working_dir", Path.cwd())

                if not file_path:
                    await self.emit_to_client(
                        sid,
                        "file_tracked_response",
                        {
                            "success": False,
                            "error": "file_path is required",
                            "file_path": file_path,
                        },
                    )
                    return

                # Use git ls-files to check if file is tracked
                result = subprocess.run(
                    ["git", "-C", working_dir, "ls-files", "--", file_path],
                    capture_output=True,
                    text=True,
                    check=False,
                )

                is_tracked = result.returncode == 0 and result.stdout.strip()

                await self.emit_to_client(
                    sid,
                    "file_tracked_response",
                    {
                        "success": True,
                        "file_path": file_path,
                        "working_dir": working_dir,
                        "is_tracked": bool(is_tracked),
                    },
                )

            except Exception as e:
                self.log_error("check_file_tracked", e, data)
                await self.emit_to_client(
                    sid,
                    "file_tracked_response",
                    {
                        "success": False,
                        "error": str(e),
                        "file_path": data.get("file_path", "unknown"),
                    },
                )

        @self.sio.event
        async def check_git_status(sid, data):
            """Check git status for a file to determine if git diff icons should be shown.

            WHY: The dashboard shows git diff icons for files that have changes.
            This checks if a file has git status to determine icon visibility.
            """
            try:
                file_path = data.get("file_path")
                working_dir = data.get("working_dir", Path.cwd())

                # Debug: check_git_status called

                if not file_path:
                    await self.emit_to_client(
                        sid,
                        "git_status_response",
                        {
                            "success": False,
                            "error": "file_path is required",
                            "file_path": file_path,
                        },
                    )
                    return

                # Validate and sanitize working_dir
                original_working_dir = working_dir
                working_dir = self._sanitize_working_dir(
                    working_dir, "check_git_status"
                )

                if not await self._validate_directory_for_status(
                    sid, working_dir, original_working_dir, file_path
                ):
                    return

                # Check if this is a git repository
                if not self._is_git_repository(working_dir):
                    await self.emit_to_client(
                        sid,
                        "git_status_response",
                        {
                            "success": False,
                            "error": "Not a git repository",
                            "file_path": file_path,
                            "working_dir": working_dir,
                            "original_working_dir": original_working_dir,
                        },
                    )
                    return

                # Check git status for the file
                file_path_for_git = self._make_path_relative_to_git(
                    file_path, working_dir
                )

                # Check if the file exists
                file_path_obj = Path(file_path)
                full_path = (
                    file_path_obj
                    if file_path_obj.is_absolute()
                    else Path(working_dir) / file_path
                )
                if not full_path.exists():
                    self.logger.warning(f"File does not exist: {full_path}")
                    await self.emit_to_client(
                        sid,
                        "git_status_response",
                        {
                            "success": False,
                            "error": f"File does not exist: {file_path}",
                            "file_path": file_path,
                            "working_dir": working_dir,
                            "original_working_dir": original_working_dir,
                        },
                    )
                    return

                # Check git status and tracking
                is_tracked, has_changes = self._check_file_git_status(
                    file_path_for_git, working_dir
                )

                if is_tracked or has_changes:
                    # Debug: Git status check successful
                    await self.emit_to_client(
                        sid,
                        "git_status_response",
                        {
                            "success": True,
                            "file_path": file_path,
                            "working_dir": working_dir,
                            "original_working_dir": original_working_dir,
                            "is_tracked": is_tracked,
                            "has_changes": has_changes,
                        },
                    )
                else:
                    # Debug: File is not tracked by git
                    await self.emit_to_client(
                        sid,
                        "git_status_response",
                        {
                            "success": False,
                            "error": "File is not tracked by git",
                            "file_path": file_path,
                            "working_dir": working_dir,
                            "original_working_dir": original_working_dir,
                            "is_tracked": False,
                        },
                    )

            except Exception as e:
                self.log_error("check_git_status", e, data)
                await self.emit_to_client(
                    sid,
                    "git_status_response",
                    {
                        "success": False,
                        "error": str(e),
                        "file_path": data.get("file_path", "unknown"),
                        "working_dir": data.get("working_dir", "unknown"),
                    },
                )

        @self.sio.event
        async def git_add_file(sid, data):
            """Add file to git tracking.

            WHY: Users can add untracked files to git directly from the dashboard,
            making it easier to manage version control without leaving the UI.
            """
            try:
                file_path = data.get("file_path")
                working_dir = data.get("working_dir", Path.cwd())

                # Debug: git_add_file called

                if not file_path:
                    await self.emit_to_client(
                        sid,
                        "git_add_response",
                        {
                            "success": False,
                            "error": "file_path is required",
                            "file_path": file_path,
                        },
                    )
                    return

                # Validate and sanitize working_dir
                original_working_dir = working_dir
                working_dir = self._sanitize_working_dir(working_dir, "git_add_file")

                if not await self._validate_directory_for_add(
                    sid, working_dir, original_working_dir, file_path
                ):
                    return

                # Debug: Running git add command

                # Use git add to track the file
                result = subprocess.run(
                    ["git", "-C", working_dir, "add", file_path],
                    capture_output=True,
                    text=True,
                    check=False,
                )

                # Debug: Git add completed

                if result.returncode == 0:
                    # Debug: Successfully added file to git
                    await self.emit_to_client(
                        sid,
                        "git_add_response",
                        {
                            "success": True,
                            "file_path": file_path,
                            "working_dir": working_dir,
                            "original_working_dir": original_working_dir,
                            "message": "File successfully added to git tracking",
                        },
                    )
                else:
                    error_message = result.stderr.strip() or "Unknown git error"
                    self.logger.warning(f"Git add failed: {error_message}")
                    await self.emit_to_client(
                        sid,
                        "git_add_response",
                        {
                            "success": False,
                            "error": f"Git add failed: {error_message}",
                            "file_path": file_path,
                            "working_dir": working_dir,
                            "original_working_dir": original_working_dir,
                        },
                    )

            except Exception as e:
                self.log_error("git_add_file", e, data)
                await self.emit_to_client(
                    sid,
                    "git_add_response",
                    {
                        "success": False,
                        "error": str(e),
                        "file_path": data.get("file_path", "unknown"),
                        "working_dir": data.get("working_dir", "unknown"),
                    },
                )

    def _sanitize_working_dir(self, working_dir: Optional[str], operation: str) -> str:
        """Sanitize and validate working directory input.

        WHY: Working directory input from clients can be invalid or malformed.
        This ensures we have a valid directory path to work with.
        """
        invalid_states = [
            None,
            "",
            "Unknown",
            "Loading...",
            "Loading",
            "undefined",
            "null",
            "Not Connected",
            "Invalid Directory",
            "No Directory",
            ".",
        ]

        original_working_dir = working_dir
        if working_dir in invalid_states or (
            isinstance(working_dir, str) and working_dir.strip() == ""
        ):
            working_dir = Path.cwd()
            self.logger.info(
                f"[{operation}] working_dir was invalid ({original_working_dir!r}), using cwd: {working_dir}"
            )
        else:
            self.logger.info(f"[{operation}] Using provided working_dir: {working_dir}")

        # Additional validation for obviously invalid paths
        if isinstance(working_dir, str):
            working_dir = working_dir.strip()
            # Check for null bytes or other invalid characters
            if "\x00" in working_dir:
                self.logger.warning(
                    f"[{operation}] working_dir contains null bytes, using cwd instead"
                )
                working_dir = Path.cwd()

        return working_dir

    async def _validate_directory(
        self, sid: str, working_dir: str, response_event: str
    ) -> bool:
        """Validate that a directory exists and is accessible.

        WHY: We need to ensure the directory exists and is a directory
        before attempting git operations on it.
        """
        working_dir_path = Path(working_dir)
        if not working_dir_path.exists():
            self.logger.info(
                f"Directory does not exist: {working_dir} - responding gracefully"
            )
            await self.emit_to_client(
                sid,
                response_event,
                {
                    "success": False,
                    "error": "Directory not found",
                    "working_dir": working_dir,
                    "detail": f"Path does not exist: {working_dir}",
                },
            )
            return False

        if not working_dir_path.is_dir():
            self.logger.info(
                f"Path is not a directory: {working_dir} - responding gracefully"
            )
            await self.emit_to_client(
                sid,
                response_event,
                {
                    "success": False,
                    "error": "Not a directory",
                    "working_dir": working_dir,
                    "detail": f"Path is not a directory: {working_dir}",
                },
            )
            return False

        return True

    async def _validate_directory_for_status(
        self, sid: str, working_dir: str, original_working_dir: str, file_path: str
    ) -> bool:
        """Validate directory for git status operations."""
        working_dir_path = Path(working_dir)
        if not working_dir_path.exists():
            self.logger.warning(f"Directory does not exist: {working_dir}")
            await self.emit_to_client(
                sid,
                "git_status_response",
                {
                    "success": False,
                    "error": f"Directory does not exist: {working_dir}",
                    "file_path": file_path,
                    "working_dir": working_dir,
                    "original_working_dir": original_working_dir,
                },
            )
            return False

        if not working_dir_path.is_dir():
            self.logger.warning(f"Path is not a directory: {working_dir}")
            await self.emit_to_client(
                sid,
                "git_status_response",
                {
                    "success": False,
                    "error": f"Path is not a directory: {working_dir}",
                    "file_path": file_path,
                    "working_dir": working_dir,
                    "original_working_dir": original_working_dir,
                },
            )
            return False

        return True

    async def _validate_directory_for_add(
        self, sid: str, working_dir: str, original_working_dir: str, file_path: str
    ) -> bool:
        """Validate directory for git add operations."""
        working_dir_path = Path(working_dir)
        if not working_dir_path.exists():
            self.logger.warning(f"Directory does not exist: {working_dir}")
            await self.emit_to_client(
                sid,
                "git_add_response",
                {
                    "success": False,
                    "error": f"Directory does not exist: {working_dir}",
                    "file_path": file_path,
                    "working_dir": working_dir,
                    "original_working_dir": original_working_dir,
                },
            )
            return False

        if not working_dir_path.is_dir():
            self.logger.warning(f"Path is not a directory: {working_dir}")
            await self.emit_to_client(
                sid,
                "git_add_response",
                {
                    "success": False,
                    "error": f"Path is not a directory: {working_dir}",
                    "file_path": file_path,
                    "working_dir": working_dir,
                    "original_working_dir": original_working_dir,
                },
            )
            return False

        return True

    def _is_git_repository(self, working_dir: str) -> bool:
        """Check if a directory is a git repository."""
        git_check = subprocess.run(
            ["git", "-C", working_dir, "rev-parse", "--git-dir"],
            capture_output=True,
            text=True,
            check=False,
        )
        return git_check.returncode == 0

    def _make_path_relative_to_git(self, file_path: str, working_dir: str) -> str:
        """Make an absolute path relative to the git root if needed."""
        file_path_obj = Path(file_path)
        if not file_path_obj.is_absolute():
            return file_path

        # Get git root to make path relative if needed
        git_root_result = subprocess.run(
            ["git", "-C", working_dir, "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=False,
        )

        if git_root_result.returncode == 0:
            git_root = Path(git_root_result.stdout.strip())
            try:
                relative_path = file_path_obj.relative_to(git_root)
                self.logger.info(
                    f"Made file path relative to git root: {relative_path}"
                )
                return str(relative_path)
            except ValueError:
                # File is not under git root - keep original path
                self.logger.info(
                    f"File not under git root, keeping original path: {file_path}"
                )

        return file_path

    def _check_file_git_status(
        self, file_path: str, working_dir: str
    ) -> tuple[bool, bool]:
        """Check if a file is tracked and has changes."""
        # Check git status for the file
        git_status_result = subprocess.run(
            ["git", "-C", working_dir, "status", "--porcelain", file_path],
            capture_output=True,
            text=True,
            check=False,
        )

        # Check if file is tracked by git
        ls_files_result = subprocess.run(
            ["git", "-C", working_dir, "ls-files", file_path],
            capture_output=True,
            text=True,
            check=False,
        )

        is_tracked = ls_files_result.returncode == 0 and ls_files_result.stdout.strip()
        has_changes = git_status_result.returncode == 0 and bool(
            git_status_result.stdout.strip()
        )

        self.logger.info(
            f"File tracking status: is_tracked={is_tracked}, has_changes={has_changes}"
        )

        return is_tracked, has_changes

    async def generate_git_diff(
        self,
        file_path: str,
        timestamp: Optional[str] = None,
        working_dir: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate git diff for a specific file operation.

        WHY: This method generates a git diff showing the changes made to a file
        during a specific write operation. It uses git log and show commands to
        find the most relevant commit around the specified timestamp.

        Args:
            file_path: Path to the file relative to the git repository
            timestamp: ISO timestamp of the file operation (optional)
            working_dir: Working directory containing the git repository

        Returns:
            dict: Contains diff content, metadata, and status information
        """
        try:
            # If file_path is absolute, determine its git repository
            file_path_obj = Path(file_path)
            if file_path_obj.is_absolute():
                # Find the directory containing the file
                file_dir = file_path_obj.parent
                if file_dir.exists():
                    # Try to find the git root from the file's directory
                    current_dir = file_dir
                    while current_dir != current_dir.parent:  # Stop at root
                        if (current_dir / ".git").exists():
                            working_dir = str(current_dir)
                            self.logger.info(f"Found git repository at: {working_dir}")
                            break
                        current_dir = current_dir.parent
                    else:
                        # If no git repo found, use the file's directory
                        working_dir = str(file_dir)
                        self.logger.info(
                            f"No git repo found, using file's directory: {working_dir}"
                        )

            # Handle case where working_dir is None, empty string, or 'Unknown'
            if not working_dir or working_dir == "Unknown" or working_dir.strip() == "":
                working_dir = Path.cwd()
                # Debug: working_dir was invalid, using cwd
            else:
                # Debug: Using provided working_dir
                pass

            # For read-only git operations, we can work from any directory
            # by passing the -C flag to git commands instead of changing directories
            original_cwd = Path.cwd()
            try:
                # We'll use git -C <working_dir> for all commands instead of chdir

                # Check if this is a git repository
                git_check = await asyncio.create_subprocess_exec(
                    "git",
                    "-C",
                    working_dir,
                    "rev-parse",
                    "--git-dir",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                await git_check.communicate()

                if git_check.returncode != 0:
                    return {
                        "success": False,
                        "error": "Not a git repository",
                        "file_path": file_path,
                        "working_dir": working_dir,
                    }

                # Get the absolute path of the file relative to git root
                git_root_proc = await asyncio.create_subprocess_exec(
                    "git",
                    "-C",
                    working_dir,
                    "rev-parse",
                    "--show-toplevel",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                git_root_output, _ = await git_root_proc.communicate()

                if git_root_proc.returncode != 0:
                    return {
                        "success": False,
                        "error": "Failed to determine git root directory",
                    }

                git_root = git_root_output.decode().strip()

                # Make file_path relative to git root if it's absolute
                file_path_obj = Path(file_path)
                if file_path_obj.is_absolute():
                    try:
                        file_path = str(file_path_obj.relative_to(Path(git_root)))
                    except ValueError:
                        # File is not under git root
                        pass

                # If timestamp is provided, try to find commits around that time
                if timestamp:
                    # Convert timestamp to git format
                    try:
                        dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                        git_since = dt.strftime("%Y-%m-%d %H:%M:%S")

                        # Find commits that modified this file around the timestamp
                        log_proc = await asyncio.create_subprocess_exec(
                            "git",
                            "-C",
                            working_dir,
                            "log",
                            "--oneline",
                            "--since",
                            git_since,
                            "--until",
                            f"{git_since} +1 hour",
                            "--",
                            file_path,
                            stdout=asyncio.subprocess.PIPE,
                            stderr=asyncio.subprocess.PIPE,
                        )
                        log_output, _ = await log_proc.communicate()

                        if log_proc.returncode == 0 and log_output:
                            # Get the most recent commit hash
                            commits = log_output.decode().strip().split("\n")
                            if commits and commits[0]:
                                commit_hash = commits[0].split()[0]

                                # Get the diff for this specific commit
                                diff_proc = await asyncio.create_subprocess_exec(
                                    "git",
                                    "-C",
                                    working_dir,
                                    "show",
                                    "--format=fuller",
                                    commit_hash,
                                    "--",
                                    file_path,
                                    stdout=asyncio.subprocess.PIPE,
                                    stderr=asyncio.subprocess.PIPE,
                                )
                                diff_output, _ = await diff_proc.communicate()

                                if diff_proc.returncode == 0:
                                    return {
                                        "success": True,
                                        "diff": diff_output.decode(),
                                        "commit_hash": commit_hash,
                                        "file_path": file_path,
                                        "method": "timestamp_based",
                                        "timestamp": timestamp,
                                    }
                    except Exception as e:
                        self.logger.warning(
                            f"Failed to parse timestamp or find commits: {e}"
                        )

                # Fallback: Get the most recent change to the file
                log_proc = await asyncio.create_subprocess_exec(
                    "git",
                    "-C",
                    working_dir,
                    "log",
                    "-1",
                    "--oneline",
                    "--",
                    file_path,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                log_output, _ = await log_proc.communicate()

                if log_proc.returncode == 0 and log_output:
                    commit_hash = log_output.decode().strip().split()[0]

                    # Get the diff for the most recent commit
                    diff_proc = await asyncio.create_subprocess_exec(
                        "git",
                        "-C",
                        working_dir,
                        "show",
                        "--format=fuller",
                        commit_hash,
                        "--",
                        file_path,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                    )
                    diff_output, _diff_error = await diff_proc.communicate()

                    if diff_proc.returncode == 0:
                        return {
                            "success": True,
                            "diff": diff_output.decode(),
                            "commit_hash": commit_hash,
                            "file_path": file_path,
                            "method": "latest_commit",
                            "timestamp": timestamp,
                        }

                # Try to show unstaged changes first
                diff_proc = await asyncio.create_subprocess_exec(
                    "git",
                    "-C",
                    working_dir,
                    "diff",
                    "--",
                    file_path,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                diff_output, _ = await diff_proc.communicate()

                if diff_proc.returncode == 0 and diff_output.decode().strip():
                    return {
                        "success": True,
                        "diff": diff_output.decode(),
                        "commit_hash": "unstaged_changes",
                        "file_path": file_path,
                        "method": "unstaged_changes",
                        "timestamp": timestamp,
                    }

                # Then try staged changes
                diff_proc = await asyncio.create_subprocess_exec(
                    "git",
                    "-C",
                    working_dir,
                    "diff",
                    "--cached",
                    "--",
                    file_path,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                diff_output, _ = await diff_proc.communicate()

                if diff_proc.returncode == 0 and diff_output.decode().strip():
                    return {
                        "success": True,
                        "diff": diff_output.decode(),
                        "commit_hash": "staged_changes",
                        "file_path": file_path,
                        "method": "staged_changes",
                        "timestamp": timestamp,
                    }

                # Final fallback: Show changes against HEAD
                diff_proc = await asyncio.create_subprocess_exec(
                    "git",
                    "-C",
                    working_dir,
                    "diff",
                    "HEAD",
                    "--",
                    file_path,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                diff_output, _ = await diff_proc.communicate()

                if diff_proc.returncode == 0:
                    working_diff = diff_output.decode()
                    if working_diff.strip():
                        return {
                            "success": True,
                            "diff": working_diff,
                            "commit_hash": "working_directory",
                            "file_path": file_path,
                            "method": "working_directory",
                            "timestamp": timestamp,
                        }

                # Check if file is tracked by git
                status_proc = await asyncio.create_subprocess_exec(
                    "git",
                    "-C",
                    working_dir,
                    "ls-files",
                    "--",
                    file_path,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                status_output, _ = await status_proc.communicate()

                is_tracked = (
                    status_proc.returncode == 0 and status_output.decode().strip()
                )

                if not is_tracked:
                    # File is not tracked by git
                    return {
                        "success": False,
                        "error": "This file is not tracked by git",
                        "file_path": file_path,
                        "working_dir": working_dir,
                        "suggestions": [
                            "This file has not been added to git yet",
                            "Use 'git add' to track this file before viewing its diff",
                            "Git diff can only show changes for files that are tracked by git",
                        ],
                    }

                # File is tracked but has no changes to show
                suggestions = [
                    "The file may not have any committed changes yet",
                    "The file may have been added but not committed",
                    "The timestamp may be outside the git history range",
                ]

                file_path_obj = Path(file_path)
                current_cwd = Path.cwd()
                if file_path_obj.is_absolute() and not str(file_path_obj).startswith(
                    str(current_cwd)
                ):
                    current_repo = current_cwd.name
                    file_repo = "unknown"
                    # Try to extract repository name from path
                    path_parts = file_path_obj.parts
                    if "Projects" in path_parts:
                        idx = path_parts.index("Projects")
                        if idx + 1 < len(path_parts):
                            file_repo = path_parts[idx + 1]

                    suggestions.clear()
                    suggestions.append(
                        f"This file is from the '{file_repo}' repository"
                    )
                    suggestions.append(
                        f"The git diff viewer is running from the '{current_repo}' repository"
                    )
                    suggestions.append(
                        "Git diff can only show changes for files in the current repository"
                    )
                    suggestions.append(
                        "To view changes for this file, run the monitoring dashboard from its repository"
                    )

                return {
                    "success": False,
                    "error": "No git history found for this file",
                    "file_path": file_path,
                    "suggestions": suggestions,
                }

            finally:
                os.chdir(original_cwd)

        except Exception as e:
            self.logger.error(f"Error in generate_git_diff: {e}")
            return {
                "success": False,
                "error": f"Git diff generation failed: {e!s}",
                "file_path": file_path,
            }

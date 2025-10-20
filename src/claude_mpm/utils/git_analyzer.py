"""
Git history analysis utilities for intelligent context reconstruction.

This module provides utilities to analyze git repository activity for
context reconstruction and project intelligence. Extracted from the
session management system to support git-based context approaches.
"""

import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from claude_mpm.core.logging_utils import get_logger

logger = get_logger(__name__)


def analyze_recent_activity(
    repo_path: str = ".", days: int = 7, max_commits: int = 50, min_commits: int = 25
) -> Dict[str, Any]:
    """
    Analyze recent git activity for context reconstruction with adaptive time window.

    Strategy:
    1. Try to get commits from last {days} days
    2. If fewer than {min_commits} found, expand window to get {min_commits}
    3. Never exceed {max_commits} total

    This ensures meaningful context for both high-velocity and low-velocity projects.

    Args:
        repo_path: Path to the git repository (default: current directory)
        days: Number of days to look back initially (default: 7)
        max_commits: Maximum number of commits to analyze (default: 50)
        min_commits: Minimum commits to retrieve, will expand window if needed (default: 25)

    Returns:
        Dict containing:
        - time_range: str - Description of analysis period
        - commits: List[Dict] - Recent commits with metadata
        - branches: List[str] - Active branches in the repository
        - contributors: Dict[str, Dict] - Contributor statistics
        - file_changes: Dict[str, Dict] - File change statistics
        - has_activity: bool - Whether any activity was found
        - adaptive_mode: bool - Whether time window was expanded
        - actual_time_span: Optional[str] - Actual time span if adaptive mode was used
        - reason: Optional[str] - Explanation for adaptive mode
        - error: Optional[str] - Error message if analysis failed
    """
    repo_path_obj = Path(repo_path)
    analysis = {
        "time_range": f"last {days} days",
        "commits": [],
        "branches": [],
        "contributors": {},
        "file_changes": {},
        "has_activity": False,
        "adaptive_mode": False,
        "min_commits_target": min_commits,
    }

    try:
        # Get all branches
        result = subprocess.run(
            ["git", "branch", "-a"],
            cwd=str(repo_path_obj),
            capture_output=True,
            text=True,
            check=True,
        )
        branches = [
            line.strip().replace("* ", "").replace("remotes/origin/", "")
            for line in result.stdout.strip().split("\n")
            if line.strip()
        ]
        analysis["branches"] = list(set(branches))

        # Step 1: Get commits from specified time window
        result = subprocess.run(
            [
                "git",
                "log",
                "--all",
                f"--since={days} days ago",
                f"--max-count={max_commits}",
                "--format=%h|%an|%ae|%ai|%s",
                "--name-status",
            ],
            cwd=str(repo_path_obj),
            capture_output=True,
            text=True,
            check=True,
        )

        if not result.stdout.strip():
            return analysis

        analysis["has_activity"] = True

        # Step 2: Count commit lines (lines with pipe separator) to determine if we need adaptive mode
        temp_commits = []
        for line in result.stdout.strip().split("\n"):
            if "|" in line:
                temp_commits.append(line)

        # Step 3: Check if we need adaptive mode
        if len(temp_commits) < min_commits:
            logger.info(
                f"Only {len(temp_commits)} commits found in last {days} days, "
                f"expanding to get at least {min_commits} commits"
            )

            # Get last N commits regardless of date
            expanded_result = subprocess.run(
                [
                    "git",
                    "log",
                    "--all",
                    f"-{min_commits}",
                    "--format=%h|%an|%ae|%ai|%s",
                    "--name-status",
                ],
                cwd=str(repo_path_obj),
                capture_output=True,
                text=True,
                check=True,
            )

            if expanded_result.stdout.strip():
                result = expanded_result
                analysis["adaptive_mode"] = True

                # Calculate actual time span
                from datetime import datetime

                commit_lines = [
                    line for line in result.stdout.strip().split("\n") if "|" in line
                ]
                if commit_lines:
                    # Parse first and last commit dates
                    try:
                        first_parts = commit_lines[0].split("|", 4)
                        last_parts = commit_lines[-1].split("|", 4)

                        if len(first_parts) >= 4 and len(last_parts) >= 4:
                            # Parse ISO format dates (e.g., "2025-10-20 11:38:20 -0700")
                            # Extract just the date portion before timezone
                            first_date_str = first_parts[3].strip()
                            last_date_str = last_parts[3].strip()

                            # Remove timezone info for parsing
                            first_date_clean = first_date_str.split(" +")[0].split(
                                " -"
                            )[0]
                            last_date_clean = last_date_str.split(" +")[0].split(" -")[
                                0
                            ]

                            # Parse as datetime
                            first_date = datetime.fromisoformat(
                                first_date_clean.replace(" ", "T")
                            )
                            last_date = datetime.fromisoformat(
                                last_date_clean.replace(" ", "T")
                            )

                            days_diff = (first_date - last_date).days
                            # Handle the case where days_diff might be 0 or 1
                            if days_diff <= 1:
                                days_diff = max(days_diff, 1)

                            analysis["actual_time_span"] = str(days_diff)

                            # Provide clear messaging based on the expansion
                            if days_diff > days:
                                analysis["reason"] = (
                                    f"Expanded from {days} days to {days_diff} days "
                                    f"to reach minimum {min_commits} commits for meaningful context"
                                )
                            else:
                                # High-velocity project: reached min_commits without expanding time window
                                analysis["reason"] = (
                                    f"Fetched last {min_commits} commits (spanning {days_diff} days) "
                                    f"to ensure meaningful context"
                                )
                    except Exception as e:
                        logger.warning(f"Could not calculate actual time span: {e}")
                        analysis["actual_time_span"] = f">{days} days"
                        analysis["reason"] = (
                            f"Expanded beyond {days} days to get minimum {min_commits} commits"
                        )

        # Parse commit log
        commits = []
        current_commit = None
        file_changes = {}

        for line in result.stdout.strip().split("\n"):
            if not line.strip():
                continue

            if "|" in line:
                # Commit line
                if current_commit:
                    commits.append(current_commit)

                parts = line.split("|", 4)
                if len(parts) == 5:
                    sha, author, email, timestamp, message = parts
                    current_commit = {
                        "sha": sha,
                        "author": author,
                        "email": email,
                        "timestamp": timestamp,
                        "message": message,
                        "files": [],
                    }

                    # Track contributors
                    if author not in analysis["contributors"]:
                        analysis["contributors"][author] = {
                            "email": email,
                            "commits": 0,
                        }
                    analysis["contributors"][author]["commits"] += 1
            # File change line
            elif current_commit and "\t" in line:
                parts = line.split("\t", 1)
                if len(parts) == 2:
                    status, file_path = parts
                    current_commit["files"].append(
                        {"status": status, "path": file_path}
                    )

                    # Track file changes
                    if file_path not in file_changes:
                        file_changes[file_path] = {
                            "modifications": 0,
                            "contributors": set(),
                        }
                    file_changes[file_path]["modifications"] += 1
                    file_changes[file_path]["contributors"].add(
                        current_commit["author"]
                    )

        # Add last commit
        if current_commit:
            commits.append(current_commit)

        analysis["commits"] = commits

        # Convert file changes to serializable format
        analysis["file_changes"] = {
            path: {
                "modifications": info["modifications"],
                "contributors": list(info["contributors"]),
            }
            for path, info in file_changes.items()
        }

    except subprocess.CalledProcessError as e:
        logger.warning(f"Git command failed: {e}")
        analysis["error"] = f"Git command failed: {e}"
    except Exception as e:
        logger.warning(f"Could not analyze recent activity: {e}")
        analysis["error"] = str(e)

    return analysis


def get_current_branch(repo_path: str = ".") -> Optional[str]:
    """
    Get the current git branch name.

    Args:
        repo_path: Path to the git repository (default: current directory)

    Returns:
        Current branch name or None if not in a git repository
    """
    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=str(Path(repo_path)),
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except Exception:
        return None


def get_commits_since(since_sha: str, repo_path: str = ".") -> List[Dict[str, str]]:
    """
    Get commits since a specific SHA.

    Args:
        since_sha: The SHA to get commits after
        repo_path: Path to the git repository (default: current directory)

    Returns:
        List of commit dicts with sha, author, timestamp, and message
    """
    try:
        result = subprocess.run(
            ["git", "log", f"{since_sha}..HEAD", "--format=%h|%an|%ai|%s"],
            cwd=str(Path(repo_path)),
            capture_output=True,
            text=True,
            check=True,
        )

        commits = []
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            parts = line.split("|", 3)
            if len(parts) == 4:
                sha, author, timestamp, message = parts
                commits.append(
                    {
                        "sha": sha,
                        "author": author,
                        "timestamp": timestamp,
                        "message": message,
                    }
                )

        return commits

    except Exception as e:
        logger.warning(f"Could not get commits: {e}")
        return []


def get_current_status(repo_path: str = ".") -> Dict[str, Any]:
    """
    Get current git status.

    Args:
        repo_path: Path to the git repository (default: current directory)

    Returns:
        Dict with:
        - clean: bool - Whether working directory is clean
        - modified_files: List[str] - Modified files
        - untracked_files: List[str] - Untracked files
    """
    status = {"clean": True, "modified_files": [], "untracked_files": []}

    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(Path(repo_path)),
            capture_output=True,
            text=True,
            check=True,
        )

        modified_files = []
        untracked_files = []

        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            status_code = line[:2]
            file_path = line[3:]

            if status_code.startswith("??"):
                untracked_files.append(file_path)
            else:
                modified_files.append(file_path)

        status = {
            "clean": len(modified_files) == 0 and len(untracked_files) == 0,
            "modified_files": modified_files,
            "untracked_files": untracked_files,
        }

    except Exception as e:
        logger.warning(f"Could not get status: {e}")

    return status


def is_git_repository(repo_path: str = ".") -> bool:
    """
    Check if the given path is a git repository.

    Args:
        repo_path: Path to check (default: current directory)

    Returns:
        True if the path is a git repository, False otherwise
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            cwd=str(Path(repo_path)),
            capture_output=True,
            text=True,
            check=False,
        )
        return result.returncode == 0
    except Exception:
        return False

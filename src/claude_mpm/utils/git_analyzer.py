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
    repo_path: str = ".", days: int = 7, max_commits: int = 50
) -> Dict[str, Any]:
    """
    Analyze recent git activity for context reconstruction.

    This function analyzes git history to provide comprehensive context about
    recent project activity including commits, contributors, file changes,
    and branch activity.

    Args:
        repo_path: Path to the git repository (default: current directory)
        days: Number of days to look back (default: 7)
        max_commits: Maximum number of commits to analyze (default: 50)

    Returns:
        Dict containing:
        - time_range: str - Description of analysis period
        - commits: List[Dict] - Recent commits with metadata
        - branches: List[str] - Active branches in the repository
        - contributors: Dict[str, Dict] - Contributor statistics
        - file_changes: Dict[str, Dict] - File change statistics
        - has_activity: bool - Whether any activity was found
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

        # Get recent commits from all branches
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

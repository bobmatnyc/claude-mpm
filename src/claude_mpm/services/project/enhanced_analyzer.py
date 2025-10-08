"""
Enhanced Project Analyzer with Git History Support
=================================================

This service extends project analysis with git history analysis,
recent changes tracking, and intelligent project state detection.

Key Features:
- Git history analysis and recent commits
- Change frequency detection
- Author contribution analysis
- File modification tracking
- Project lifecycle detection

Author: Claude MPM Development Team
Created: 2025-01-26
"""

import os
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional

from rich.console import Console

from claude_mpm.core.logging_utils import get_logger

logger = get_logger(__name__)
console = Console()


class EnhancedProjectAnalyzer:
    """Enhanced project analyzer with git history support."""

    def __init__(self, project_path: Optional[Path] = None):
        """
        Initialize the enhanced analyzer.

        Args:
            project_path: Path to the project. If None, uses CLAUDE_MPM_USER_PWD
                         environment variable or current working directory.
        """
        # Determine project path with proper priority
        if project_path is None:
            # Try environment variable first (user's project, not framework)
            env_path = os.getenv("CLAUDE_MPM_USER_PWD")
            if env_path:
                self.project_path = Path(env_path)
            else:
                self.project_path = Path.cwd()
        else:
            self.project_path = project_path

        # Ensure path is absolute
        if not self.project_path.is_absolute():
            self.project_path = self.project_path.resolve()

        # Check if it's a git repository
        git_dir = self.project_path / ".git"
        self.is_git_repo = git_dir.exists() and git_dir.is_dir()

        # Log warning if not a git repository
        if not self.is_git_repo:
            logger.debug(f"Directory is not a git repository: {self.project_path}")

    def analyze_git_history(self, days_back: int = 30) -> Dict:
        """Analyze git history for recent changes and patterns."""
        if not self.is_git_repo:
            return {"git_available": False, "message": "Not a git repository"}

        analysis = {
            "git_available": True,
            "recent_commits": self._get_recent_commits(days_back),
            "changed_files": self._get_changed_files(days_back),
            "authors": self._get_author_stats(days_back),
            "branch_info": self._get_branch_info(),
            "documentation_changes": self._get_documentation_changes(days_back),
        }

        # Analyze patterns
        analysis["patterns"] = self._analyze_commit_patterns(analysis["recent_commits"])
        analysis["hot_spots"] = self._identify_hot_spots(analysis["changed_files"])

        return analysis

    def _run_git_command(self, args: List[str]) -> Optional[str]:
        """Run a git command and return output."""
        try:
            result = subprocess.run(
                ["git", *args],
                cwd=self.project_path,
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            logger.debug(f"Git command failed: {e}")
            return None

    def _get_recent_commits(self, days: int) -> List[Dict]:
        """Get recent commits within specified days."""
        since_date = (datetime.now(timezone.utc) - timedelta(days=days)).strftime(
            "%Y-%m-%d"
        )

        # Get commit log with structured format
        output = self._run_git_command(
            [
                "log",
                f"--since={since_date}",
                "--pretty=format:%H|%an|%ae|%at|%s",
                "--no-merges",
            ]
        )

        if not output:
            return []

        commits = []
        for line in output.splitlines():
            parts = line.split("|", 4)
            if len(parts) == 5:
                commits.append(
                    {
                        "hash": parts[0][:8],
                        "author": parts[1],
                        "email": parts[2],
                        "timestamp": datetime.fromtimestamp(int(parts[3])).isoformat(),
                        "message": parts[4],
                    }
                )

        return commits[:50]  # Limit to 50 most recent

    def _get_changed_files(self, days: int) -> Dict:
        """Get files changed in recent commits."""
        since_date = (datetime.now(timezone.utc) - timedelta(days=days)).strftime(
            "%Y-%m-%d"
        )

        output = self._run_git_command(
            [
                "log",
                f"--since={since_date}",
                "--pretty=format:",
                "--name-only",
                "--no-merges",
            ]
        )

        if not output:
            return {}

        file_changes = {}
        for line in output.splitlines():
            if line:
                file_changes[line] = file_changes.get(line, 0) + 1

        # Sort by change frequency
        sorted_files = sorted(file_changes.items(), key=lambda x: x[1], reverse=True)

        return {
            "total_files": len(file_changes),
            "most_changed": dict(sorted_files[:20]),  # Top 20 most changed
            "recently_added": self._get_recently_added_files(days),
        }

    def _get_recently_added_files(self, days: int) -> List[str]:
        """Get files added in recent commits."""
        since_date = (datetime.now(timezone.utc) - timedelta(days=days)).strftime(
            "%Y-%m-%d"
        )

        output = self._run_git_command(
            [
                "log",
                f"--since={since_date}",
                "--pretty=format:",
                "--name-status",
                "--diff-filter=A",  # Added files only
            ]
        )

        if not output:
            return []

        added_files = []
        for line in output.splitlines():
            if line.startswith("A\t"):
                added_files.append(line[2:])

        return list(set(added_files))[:20]  # Unique files, max 20

    def _get_author_stats(self, days: int) -> Dict:
        """Get author contribution statistics."""
        since_date = (datetime.now(timezone.utc) - timedelta(days=days)).strftime(
            "%Y-%m-%d"
        )

        output = self._run_git_command(
            [
                "shortlog",
                "-sne",
                f"--since={since_date}",
                "--no-merges",
            ]
        )

        if not output:
            return {}

        authors = {}
        for line in output.splitlines():
            parts = line.strip().split("\t", 1)
            if len(parts) == 2:
                count = int(parts[0])
                author_info = parts[1]
                authors[author_info] = count

        return {
            "total_authors": len(authors),
            "contributors": dict(list(authors.items())[:10]),  # Top 10 contributors
        }

    def _get_branch_info(self) -> Dict:
        """Get current branch and remote information."""
        info = {}

        # Current branch
        branch = self._run_git_command(["branch", "--show-current"])
        info["current_branch"] = branch or "unknown"

        # All branches
        branches = self._run_git_command(["branch", "-a"])
        if branches:
            info["branches"] = [
                b.strip().replace("* ", "") for b in branches.splitlines()
            ]

        # Remote info
        remotes = self._run_git_command(["remote", "-v"])
        if remotes:
            info["remotes"] = []
            for line in remotes.splitlines():
                parts = line.split()
                if len(parts) >= 2:
                    info["remotes"].append(
                        {
                            "name": parts[0],
                            "url": parts[1],
                        }
                    )

        # Check for uncommitted changes
        status = self._run_git_command(["status", "--porcelain"])
        info["has_uncommitted_changes"] = bool(status)
        if status:
            info["uncommitted_files"] = len(status.splitlines())

        return info

    def _get_documentation_changes(self, days: int) -> Dict:
        """Track changes to documentation files."""
        since_date = (datetime.now(timezone.utc) - timedelta(days=days)).strftime(
            "%Y-%m-%d"
        )

        # Get changes to documentation files
        doc_patterns = ["*.md", "*.rst", "*.txt", "docs/*", "README*", "CLAUDE*"]

        doc_changes = {}
        for pattern in doc_patterns:
            output = self._run_git_command(
                [
                    "log",
                    f"--since={since_date}",
                    "--pretty=format:%H|%s",
                    "--",
                    pattern,
                ]
            )

            if output:
                for line in output.splitlines():
                    parts = line.split("|", 1)
                    if len(parts) == 2:
                        if pattern not in doc_changes:
                            doc_changes[pattern] = []
                        doc_changes[pattern].append(
                            {
                                "commit": parts[0][:8],
                                "message": parts[1],
                            }
                        )

        # Check CLAUDE.md specifically
        claude_history = self._run_git_command(
            [
                "log",
                f"--since={since_date}",
                "--pretty=format:%H|%at|%s",
                "--",
                "CLAUDE.md",
            ]
        )

        claude_updates = []
        if claude_history:
            for line in claude_history.splitlines():
                parts = line.split("|", 2)
                if len(parts) == 3:
                    claude_updates.append(
                        {
                            "commit": parts[0][:8],
                            "timestamp": datetime.fromtimestamp(
                                int(parts[1])
                            ).isoformat(),
                            "message": parts[2],
                        }
                    )

        return {
            "documentation_commits": doc_changes,
            "claude_md_updates": claude_updates,
            "has_recent_doc_changes": bool(doc_changes or claude_updates),
        }

    def _analyze_commit_patterns(self, commits: List[Dict]) -> Dict:
        """Analyze patterns in commit messages."""
        patterns = {
            "features": [],
            "fixes": [],
            "refactoring": [],
            "documentation": [],
            "tests": [],
            "chores": [],
        }

        for commit in commits:
            msg_lower = commit["message"].lower()

            if any(kw in msg_lower for kw in ["feat", "feature", "add", "implement"]):
                patterns["features"].append(commit["message"][:100])
            elif any(kw in msg_lower for kw in ["fix", "bug", "resolve", "patch"]):
                patterns["fixes"].append(commit["message"][:100])
            elif any(
                kw in msg_lower for kw in ["refactor", "restructure", "reorganize"]
            ):
                patterns["refactoring"].append(commit["message"][:100])
            elif any(kw in msg_lower for kw in ["doc", "readme", "comment"]):
                patterns["documentation"].append(commit["message"][:100])
            elif any(kw in msg_lower for kw in ["test", "spec", "coverage"]):
                patterns["tests"].append(commit["message"][:100])
            elif any(kw in msg_lower for kw in ["chore", "build", "ci", "deps"]):
                patterns["chores"].append(commit["message"][:100])

        # Limit each category to 5 items
        for key in patterns:
            patterns[key] = patterns[key][:5]

        # Add summary
        patterns["summary"] = {
            "total_commits": len(commits),
            "feature_commits": len(patterns["features"]),
            "bug_fixes": len(patterns["fixes"]),
            "most_active_type": max(
                patterns.keys(),
                key=lambda k: len(patterns[k]) if k != "summary" else 0,
            ),
        }

        return patterns

    def _identify_hot_spots(self, changed_files: Dict) -> List[Dict]:
        """Identify hot spots (frequently changed files)."""
        if not changed_files.get("most_changed"):
            return []

        hot_spots = []
        for file_path, change_count in list(changed_files["most_changed"].items())[:10]:
            file_type = Path(file_path).suffix
            hot_spots.append(
                {
                    "file": file_path,
                    "changes": change_count,
                    "type": file_type,
                    "category": self._categorize_file(file_path),
                }
            )

        return hot_spots

    def _categorize_file(self, file_path: str) -> str:
        """Categorize file based on path and extension."""
        path = Path(file_path)

        # Check directory
        if "test" in str(path).lower():
            return "test"
        if "docs" in str(path).lower():
            return "documentation"
        if "src" in str(path) or "lib" in str(path):
            return "source"
        if "scripts" in str(path):
            return "scripts"
        if path.suffix in [".yml", ".yaml", ".json", ".toml", ".ini"]:
            return "configuration"
        if path.suffix in [".md", ".rst", ".txt"]:
            return "documentation"
        return "other"

    def detect_project_state(self) -> Dict:
        """Detect the current state and lifecycle phase of the project."""
        state = {
            "phase": "unknown",
            "indicators": [],
            "recommendations": [],
        }

        # Check various indicators
        indicators = []

        # Check for version files
        version_files = ["VERSION", "version.txt", "package.json", "pyproject.toml"]
        for vf in version_files:
            if (self.project_path / vf).exists():
                indicators.append(f"Has {vf} file")

        # Check for CI/CD
        if (self.project_path / ".github" / "workflows").exists():
            indicators.append("Has GitHub Actions")
        if (self.project_path / ".gitlab-ci.yml").exists():
            indicators.append("Has GitLab CI")

        # Check for tests
        if (self.project_path / "tests").exists() or (
            self.project_path / "test"
        ).exists():
            indicators.append("Has test directory")

        # Check for documentation
        if (self.project_path / "docs").exists():
            indicators.append("Has documentation directory")
        if (self.project_path / "CLAUDE.md").exists():
            indicators.append("Has CLAUDE.md")

        # Check git history if available
        if self.is_git_repo:
            # Count total commits
            commit_count = self._run_git_command(["rev-list", "--count", "HEAD"])
            if commit_count:
                count = int(commit_count)
                indicators.append(f"{count} total commits")

                # Determine phase based on commit count
                if count < 10:
                    state["phase"] = "initial"
                    state["recommendations"].append(
                        "Focus on establishing core structure"
                    )
                elif count < 50:
                    state["phase"] = "early_development"
                    state["recommendations"].append(
                        "Consider adding tests and documentation"
                    )
                elif count < 200:
                    state["phase"] = "active_development"
                    state["recommendations"].append(
                        "Ensure CI/CD and testing are in place"
                    )
                elif count < 1000:
                    state["phase"] = "maturing"
                    state["recommendations"].append(
                        "Focus on optimization and documentation"
                    )
                else:
                    state["phase"] = "mature"
                    state["recommendations"].append("Maintain backward compatibility")

            # Check age
            first_commit = self._run_git_command(
                ["log", "--reverse", "--format=%at", "-1"]
            )
            if first_commit:
                age_days = (
                    datetime.now(timezone.utc)
                    - datetime.fromtimestamp(int(first_commit))
                ).days
                indicators.append(f"{age_days} days old")

        state["indicators"] = indicators

        # Add phase-specific recommendations
        if not (self.project_path / "CLAUDE.md").exists():
            state["recommendations"].append(
                "Create CLAUDE.md for AI agent documentation"
            )
        if not (self.project_path / "tests").exists():
            state["recommendations"].append("Add tests directory for test organization")
        if not (self.project_path / ".gitignore").exists():
            state["recommendations"].append("Create .gitignore file")

        return state

    def generate_analysis_report(self, include_git: bool = True) -> Dict:
        """Generate comprehensive project analysis report."""
        report = {
            "project_path": str(self.project_path),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # Basic project info
        report["project_info"] = {
            "name": self.project_path.name,
            "is_git_repo": self.is_git_repo,
        }

        # Project state
        report["state"] = self.detect_project_state()

        # Git analysis if available
        if include_git and self.is_git_repo:
            report["git_analysis"] = self.analyze_git_history()

        # File statistics
        report["statistics"] = self._get_project_statistics()

        return report

    def _get_project_statistics(self) -> Dict:
        """Get basic project statistics."""
        stats = {
            "total_files": 0,
            "total_directories": 0,
            "file_types": {},
            "largest_files": [],
        }

        # Count files and directories
        for path in self.project_path.rglob("*"):
            # Skip hidden and git files
            if any(part.startswith(".") for part in path.parts):
                continue

            if path.is_file():
                stats["total_files"] += 1
                ext = path.suffix or "no_extension"
                stats["file_types"][ext] = stats["file_types"].get(ext, 0) + 1

                # Track large files
                try:
                    size = path.stat().st_size
                    if size > 1024 * 1024:  # Files over 1MB
                        stats["largest_files"].append(
                            {
                                "path": str(path.relative_to(self.project_path)),
                                "size_mb": round(size / (1024 * 1024), 2),
                            }
                        )
                except (OSError, PermissionError):
                    pass

            elif path.is_dir():
                stats["total_directories"] += 1

        # Sort largest files
        stats["largest_files"].sort(key=lambda x: x["size_mb"], reverse=True)
        stats["largest_files"] = stats["largest_files"][:10]  # Top 10

        return stats

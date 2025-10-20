"""
Session Resume Manager - Loads and analyzes paused session state.

This module provides functionality to resume a paused Claude MPM session by:
- Loading the most recent (or specified) paused session
- Checking for changes since the pause
- Detecting potential conflicts
- Generating context summary for seamless resumption

The resume manager ensures users have full awareness of what changed during the pause.
"""

import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from claude_mpm.core.logging_utils import get_logger
from claude_mpm.storage.state_storage import StateStorage

logger = get_logger(__name__)
console = Console()


class SessionResumeManager:
    """Manages resuming paused sessions with change detection."""

    def __init__(self, project_path: Path):
        """Initialize Session Resume Manager.

        Args:
            project_path: Path to the project directory
        """
        self.project_path = project_path
        self.session_dir = project_path / ".claude-mpm" / "sessions" / "pause"
        self.storage = StateStorage()

    def resume_session(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Resume a paused session.

        Args:
            session_id: Optional specific session ID to resume (defaults to most recent)

        Returns:
            Dict containing resume context and warnings
        """
        try:
            # Load session state
            if session_id:
                session_state = self._load_session_by_id(session_id)
            else:
                session_state = self._load_latest_session()

            if not session_state:
                return {
                    "status": "error",
                    "message": (
                        "No paused sessions found"
                        if not session_id
                        else f"Session {session_id} not found"
                    ),
                }

            # Analyze changes since pause
            changes = self._analyze_changes_since_pause(session_state)

            # Generate resume context
            resume_context = self._generate_resume_context(session_state, changes)

            # Display resume information
            self._display_resume_info(session_state, changes)

            return {
                "status": "success",
                "session_state": session_state,
                "changes": changes,
                "resume_context": resume_context,
            }

        except Exception as e:
            logger.error(f"Failed to resume session: {e}")
            return {"status": "error", "message": str(e)}

    def _load_session_by_id(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Load a specific session by ID.

        Args:
            session_id: The session identifier

        Returns:
            Session state dict or None if not found
        """
        session_file = self.session_dir / f"{session_id}.json"
        if not session_file.exists():
            logger.warning(f"Session file not found: {session_file}")
            return None

        return self.storage.read_json(session_file)

    def _load_latest_session(self) -> Optional[Dict[str, Any]]:
        """Load the most recent paused session.

        Returns:
            Session state dict or None if no sessions found
        """
        if not self.session_dir.exists():
            return None

        session_files = sorted(self.session_dir.glob("session-*.json"))
        if not session_files:
            return None

        # Load the most recent session
        latest_file = session_files[-1]
        return self.storage.read_json(latest_file)

    def _analyze_changes_since_pause(
        self, session_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze what changed since session was paused.

        Args:
            session_state: The paused session state

        Returns:
            Dict containing change analysis
        """
        changes: Dict[str, Any] = {
            "branch_changed": False,
            "new_commits": [],
            "new_commits_count": 0,
            "working_directory_changes": {
                "new_modified": [],
                "new_untracked": [],
                "resolved_files": [],
            },
            "warnings": [],
        }

        try:
            git_context = session_state.get("git_context", {})

            if not git_context.get("is_git_repo"):
                return changes

            # Check if branch changed
            paused_branch = git_context.get("branch")
            current_branch = self._get_current_branch()

            if paused_branch and current_branch and paused_branch != current_branch:
                changes["branch_changed"] = True
                changes["warnings"].append(
                    f"Branch changed from '{paused_branch}' to '{current_branch}'"
                )

            # Check for new commits
            paused_commits = git_context.get("recent_commits", [])
            if paused_commits:
                latest_paused_sha = paused_commits[0]["sha"]
                new_commits = self._get_commits_since(latest_paused_sha)
                changes["new_commits"] = new_commits
                changes["new_commits_count"] = len(new_commits)

                if new_commits:
                    changes["warnings"].append(
                        f"{len(new_commits)} new commit(s) since pause"
                    )

            # Check working directory changes
            paused_status = git_context.get("status", {})
            current_status = self._get_current_status()

            paused_modified = set(paused_status.get("modified_files", []))
            current_modified = set(current_status.get("modified_files", []))
            paused_untracked = set(paused_status.get("untracked_files", []))
            current_untracked = set(current_status.get("untracked_files", []))

            # Files that are newly modified
            new_modified = list(current_modified - paused_modified)
            # Files that are newly untracked
            new_untracked = list(current_untracked - paused_untracked)
            # Files that were modified but are now clean
            resolved_files = list(paused_modified - current_modified)

            changes["working_directory_changes"] = {
                "new_modified": new_modified,
                "new_untracked": new_untracked,
                "resolved_files": resolved_files,
            }

            if new_modified:
                changes["warnings"].append(
                    f"{len(new_modified)} file(s) modified since pause"
                )
            if new_untracked:
                changes["warnings"].append(
                    f"{len(new_untracked)} new untracked file(s)"
                )

        except Exception as e:
            logger.warning(f"Could not analyze changes: {e}")
            changes["warnings"].append(f"Could not analyze changes: {e}")

        return changes

    def _get_current_branch(self) -> Optional[str]:
        """Get current git branch.

        Returns:
            Branch name or None
        """
        try:
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=str(self.project_path),
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip()
        except Exception:
            return None

    def _get_commits_since(self, since_sha: str) -> List[Dict[str, str]]:
        """Get commits since a specific SHA.

        Args:
            since_sha: The SHA to get commits after

        Returns:
            List of commit dicts
        """
        try:
            result = subprocess.run(
                ["git", "log", f"{since_sha}..HEAD", "--format=%h|%an|%ai|%s"],
                cwd=str(self.project_path),
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

    def _get_current_status(self) -> Dict[str, Any]:
        """Get current git status.

        Returns:
            Dict with status information
        """
        status = {"clean": True, "modified_files": [], "untracked_files": []}

        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=str(self.project_path),
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

    def _generate_resume_context(
        self, session_state: Dict[str, Any], changes: Dict[str, Any]
    ) -> str:
        """Generate formatted context summary for resuming.

        Args:
            session_state: The paused session state
            changes: Analysis of changes since pause

        Returns:
            Formatted context string
        """
        lines = []
        lines.append("=" * 80)
        lines.append("SESSION RESUME CONTEXT")
        lines.append("=" * 80)
        lines.append("")

        # Session info
        session_id = session_state.get("session_id", "unknown")
        paused_at = session_state.get("paused_at", "unknown")
        lines.append(f"Session ID: {session_id}")
        lines.append(f"Paused at: {paused_at}")
        lines.append("")

        # Previous context
        conversation = session_state.get("conversation", {})
        lines.append("PREVIOUS CONTEXT:")
        lines.append(f"  Summary: {conversation.get('summary', 'Not provided')}")
        lines.append("")

        # Accomplishments
        accomplishments = conversation.get("accomplishments", [])
        if accomplishments:
            lines.append("ACCOMPLISHMENTS:")
            for item in accomplishments:
                lines.append(f"  - {item}")
            lines.append("")

        # Next steps
        next_steps = conversation.get("next_steps", [])
        if next_steps:
            lines.append("PLANNED NEXT STEPS:")
            for item in next_steps:
                lines.append(f"  - {item}")
            lines.append("")

        # Changes since pause
        if changes.get("warnings"):
            lines.append("CHANGES SINCE PAUSE:")
            for warning in changes["warnings"]:
                lines.append(f"  ⚠️  {warning}")
            lines.append("")

        # New commits details
        if changes.get("new_commits"):
            lines.append("NEW COMMITS:")
            for commit in changes["new_commits"][:5]:
                lines.append(
                    f"  - {commit['sha']}: {commit['message']} ({commit['author']})"
                )
            if len(changes["new_commits"]) > 5:
                lines.append(f"  ... and {len(changes['new_commits']) - 5} more")
            lines.append("")

        # Working directory changes
        wd_changes = changes.get("working_directory_changes", {})
        if wd_changes.get("new_modified"):
            lines.append("NEWLY MODIFIED FILES:")
            for file_path in wd_changes["new_modified"][:10]:
                lines.append(f"  - {file_path}")
            if len(wd_changes["new_modified"]) > 10:
                lines.append(f"  ... and {len(wd_changes['new_modified']) - 10} more")
            lines.append("")

        # Todos
        todos = session_state.get("todos", {})
        active_todos = todos.get("active", [])
        if active_todos:
            lines.append("ACTIVE TODO ITEMS:")
            for todo in active_todos:
                status = todo.get("status", "unknown")
                content = todo.get("content", "unknown")
                lines.append(f"  [{status}] {content}")
            lines.append("")

        lines.append("=" * 80)
        lines.append("Ready to resume work!")
        lines.append("=" * 80)

        return "\n".join(lines)

    def _display_resume_info(
        self, session_state: Dict[str, Any], changes: Dict[str, Any]
    ) -> None:
        """Display resume information to console.

        Args:
            session_state: The paused session state
            changes: Analysis of changes since pause
        """
        console.print()

        # Session header
        session_id = session_state.get("session_id", "unknown")
        paused_at = session_state.get("paused_at", "unknown")

        # Parse timestamp for better display
        try:
            dt = datetime.fromisoformat(paused_at.replace("Z", "+00:00"))
            paused_display = dt.strftime("%Y-%m-%d %H:%M:%S UTC")
        except Exception:
            paused_display = paused_at

        console.print(
            Panel(
                f"[bold cyan]Resuming Session[/bold cyan]\n\n"
                f"[yellow]Session ID:[/yellow] {session_id}\n"
                f"[yellow]Paused at:[/yellow] {paused_display}",
                title="🟢 Session Resume",
                border_style="cyan",
            )
        )

        # Previous context
        conversation = session_state.get("conversation", {})
        console.print("\n[bold]Previous Context:[/bold]")
        console.print(f"  {conversation.get('summary', 'Not provided')}")

        # Accomplishments
        accomplishments = conversation.get("accomplishments", [])
        if accomplishments:
            console.print("\n[bold green]Accomplishments:[/bold green]")
            for item in accomplishments:
                console.print(f"  ✓ {item}")

        # Next steps
        next_steps = conversation.get("next_steps", [])
        if next_steps:
            console.print("\n[bold yellow]Planned Next Steps:[/bold yellow]")
            for idx, item in enumerate(next_steps, 1):
                console.print(f"  {idx}. {item}")

        # Changes/Warnings
        warnings = changes.get("warnings", [])
        if warnings:
            console.print("\n[bold red]⚠️  Changes Since Pause:[/bold red]")
            for warning in warnings:
                console.print(f"  • {warning}")

        # New commits table
        new_commits = changes.get("new_commits", [])
        if new_commits:
            console.print("\n[bold]New Commits:[/bold]")
            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("SHA", style="yellow", width=8)
            table.add_column("Author", style="green", width=20)
            table.add_column("Message", style="white")

            for commit in new_commits[:5]:
                msg = commit["message"]
                if len(msg) > 60:
                    msg = msg[:57] + "..."
                table.add_row(commit["sha"], commit["author"], msg)

            console.print(table)
            if len(new_commits) > 5:
                console.print(
                    f"  [dim]... and {len(new_commits) - 5} more commits[/dim]"
                )

        # Active todos
        todos = session_state.get("todos", {})
        active_todos = todos.get("active", [])
        if active_todos:
            console.print("\n[bold]Active Todo Items:[/bold]")
            for todo in active_todos:
                status = todo.get("status", "unknown")
                content = todo.get("content", "unknown")
                status_icon = {
                    "pending": "⏸️",
                    "in_progress": "🔄",
                    "completed": "✅",
                }.get(status, "❓")
                console.print(f"  {status_icon} [{status}] {content}")

        console.print()

    def list_available_sessions(self) -> List[Dict[str, Any]]:
        """List all available paused sessions.

        Returns:
            List of session information dicts
        """
        if not self.session_dir.exists():
            return []

        sessions = []
        for session_file in sorted(self.session_dir.glob("session-*.json")):
            try:
                state = self.storage.read_json(session_file)
                if state:
                    sessions.append(
                        {
                            "session_id": state.get("session_id"),
                            "paused_at": state.get("paused_at"),
                            "summary": state.get("conversation", {}).get("summary"),
                            "file_path": str(session_file),
                        }
                    )
            except Exception as e:
                logger.warning(f"Could not read session file {session_file}: {e}")

        return sessions

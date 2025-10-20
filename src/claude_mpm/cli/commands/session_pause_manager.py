"""
Session Pause Manager - Captures and saves session state for later resumption.

This module provides functionality to pause a Claude MPM session by capturing:
- Conversation context and progress
- Git repository state
- Todo list status
- Working directory changes

The saved state enables seamless session resumption with full context.
"""

import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from rich.console import Console
from rich.panel import Panel

from claude_mpm.core.logging_utils import get_logger
from claude_mpm.storage.state_storage import StateStorage

logger = get_logger(__name__)
console = Console()


class SessionPauseManager:
    """Manages pausing and saving session state."""

    def __init__(self, project_path: Path):
        """Initialize Session Pause Manager.

        Args:
            project_path: Path to the project directory
        """
        self.project_path = project_path
        self.session_dir = project_path / ".claude-mpm" / "sessions" / "pause"
        self.storage = StateStorage()

    def pause_session(
        self,
        conversation_summary: Optional[str] = None,
        accomplishments: Optional[List[str]] = None,
        next_steps: Optional[List[str]] = None,
        todos_active: Optional[List[Dict[str, str]]] = None,
        todos_completed: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """Pause the current session and save state.

        Args:
            conversation_summary: Summary of what was being worked on
            accomplishments: List of things accomplished in this session
            next_steps: List of next steps to continue work
            todos_active: Active todo items
            todos_completed: Completed todo items

        Returns:
            Dict containing pause result with session_file path
        """
        try:
            # Ensure session directory exists
            self.session_dir.mkdir(parents=True, exist_ok=True)

            # Generate session ID
            timestamp = datetime.now(timezone.utc)
            session_id = f"session-{timestamp.strftime('%Y%m%d-%H%M%S')}"

            # Capture git context
            git_context = self._capture_git_context()

            # Build session state
            session_state = {
                "session_id": session_id,
                "paused_at": timestamp.isoformat(),
                "conversation": {
                    "summary": conversation_summary
                    or "Session paused - context not provided",
                    "accomplishments": accomplishments or [],
                    "next_steps": next_steps or [],
                },
                "git_context": git_context,
                "todos": {
                    "active": todos_active or [],
                    "completed": todos_completed or [],
                },
                "version": self._get_version(),
                "build": self._get_build_number(),
                "project_path": str(self.project_path),
            }

            # Save session state to file
            session_file = self.session_dir / f"{session_id}.json"
            success = self.storage.write_json(
                session_state, session_file, atomic=True, compress=False
            )

            if not success:
                return {
                    "status": "error",
                    "message": "Failed to write session state file",
                }

            # Create git commit with session state
            commit_success = self._create_pause_commit(session_id, conversation_summary)

            # Display success message
            self._display_pause_success(session_id, session_file, commit_success)

            return {
                "status": "success",
                "session_id": session_id,
                "session_file": str(session_file),
                "git_commit_created": commit_success,
                "message": f"Session paused: {session_id}",
            }

        except Exception as e:
            logger.error(f"Failed to pause session: {e}")
            return {"status": "error", "message": str(e)}

    def _capture_git_context(self) -> Dict[str, Any]:
        """Capture current git repository state.

        Returns:
            Dict containing git context information
        """
        git_context: Dict[str, Any] = {
            "is_git_repo": False,
            "branch": None,
            "recent_commits": [],
            "status": {"clean": True, "modified_files": [], "untracked_files": []},
        }

        try:
            # Check if git repo
            result = subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                cwd=str(self.project_path),
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode != 0:
                return git_context

            git_context["is_git_repo"] = True

            # Get current branch
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=str(self.project_path),
                capture_output=True,
                text=True,
                check=True,
            )
            git_context["branch"] = result.stdout.strip()

            # Get recent commits (last 10)
            result = subprocess.run(
                ["git", "log", "--format=%h|%an|%ai|%s", "-10"],
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
                    sha, author, timestamp_str, message = parts
                    commits.append(
                        {
                            "sha": sha,
                            "author": author,
                            "timestamp": timestamp_str,
                            "message": message,
                        }
                    )
            git_context["recent_commits"] = commits

            # Get status
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

            git_context["status"] = {
                "clean": len(modified_files) == 0 and len(untracked_files) == 0,
                "modified_files": modified_files,
                "untracked_files": untracked_files,
            }

        except Exception as e:
            logger.warning(f"Could not capture git context: {e}")

        return git_context

    def _get_version(self) -> str:
        """Get Claude MPM version.

        Returns:
            Version string or "unknown"
        """
        try:
            version_file = Path(__file__).parent.parent.parent.parent.parent / "VERSION"
            if version_file.exists():
                return version_file.read_text().strip()
        except Exception:
            pass
        return "unknown"

    def _get_build_number(self) -> str:
        """Get Claude MPM build number.

        Returns:
            Build number string or "unknown"
        """
        try:
            build_file = (
                Path(__file__).parent.parent.parent.parent.parent / "BUILD_NUMBER"
            )
            if build_file.exists():
                return build_file.read_text().strip()
        except Exception:
            pass
        return "unknown"

    def _create_pause_commit(self, session_id: str, summary: Optional[str]) -> bool:
        """Create git commit with session pause information.

        Args:
            session_id: The session identifier
            summary: Optional summary of what was being worked on

        Returns:
            True if commit was created successfully
        """
        try:
            # Check if we're in a git repo
            result = subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                cwd=str(self.project_path),
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode != 0:
                logger.debug("Not a git repository, skipping commit")
                return False

            # Add session files to git
            subprocess.run(
                ["git", "add", ".claude-mpm/sessions/pause/"],
                cwd=str(self.project_path),
                capture_output=True,
                check=False,
            )

            # Check if there are changes to commit
            result = subprocess.run(
                ["git", "diff", "--cached", "--quiet"],
                cwd=str(self.project_path),
                check=False,
            )

            if result.returncode == 0:
                logger.debug("No changes to commit")
                return False

            # Build commit message
            timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            context = summary or "Session paused"

            commit_message = f"""session: pause at {timestamp}

Session ID: {session_id}
Context: {context}

🤖👥 Generated with [Claude MPM](https://github.com/bobmatnyc/claude-mpm)

Co-Authored-By: Claude <noreply@anthropic.com>"""

            # Create commit
            result = subprocess.run(
                ["git", "commit", "-m", commit_message],
                cwd=str(self.project_path),
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode == 0:
                logger.info(f"Created pause commit for session {session_id}")
                return True
            logger.warning(f"Could not create commit: {result.stderr}")
            return False

        except Exception as e:
            logger.warning(f"Could not create pause commit: {e}")
            return False

    def _display_pause_success(
        self, session_id: str, session_file: Path, commit_created: bool
    ) -> None:
        """Display success message for paused session.

        Args:
            session_id: The session identifier
            session_file: Path to the session state file
            commit_created: Whether git commit was created
        """
        console.print()
        console.print(
            Panel(
                f"[bold green]Session Paused Successfully[/bold green]\n\n"
                f"[cyan]Session ID:[/cyan] {session_id}\n"
                f"[cyan]State saved:[/cyan] {session_file}\n"
                f"[cyan]Git commit:[/cyan] {'✓ Created' if commit_created else '✗ Not created (no git repo or no changes)'}\n\n"
                f"[dim]To resume this session later, run:[/dim]\n"
                f"[yellow]  claude-mpm mpm-init pause resume[/yellow]",
                title="🔴 Session Pause",
                border_style="green",
            )
        )
        console.print()

    def list_paused_sessions(self) -> List[Dict[str, Any]]:
        """List all paused sessions.

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

    def get_latest_session(self) -> Optional[Dict[str, Any]]:
        """Get the most recent paused session.

        Returns:
            Session state dict or None if no sessions found
        """
        sessions = self.list_paused_sessions()
        if not sessions:
            return None

        # Return the most recent (last in sorted list)
        latest_file = Path(sessions[-1]["file_path"])
        return self.storage.read_json(latest_file)

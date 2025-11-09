"""Session Resume Helper Service.

WHY: This service provides automatic session resume detection and prompting for PM startup.
It detects paused sessions, calculates git changes since pause, and presents resumption
context to users.

DESIGN DECISIONS:
- Project-specific session storage (.claude-mpm/sessions/)
- Backward compatibility with legacy .claude-mpm/sessions/pause/ location
- Non-blocking detection with graceful degradation
- Git change detection for context updates
- User-friendly prompts with time elapsed information
- Integration with existing SessionManager infrastructure
"""

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from claude_mpm.core.logger import get_logger

logger = get_logger(__name__)


class SessionResumeHelper:
    """Helper for automatic session resume detection and prompting."""

    def __init__(self, project_path: Optional[Path] = None):
        """Initialize session resume helper.

        Args:
            project_path: Project root path (default: current directory)
        """
        self.project_path = project_path or Path.cwd()
        # Primary location: flattened structure
        self.pause_dir = self.project_path / ".claude-mpm" / "sessions"
        # Legacy location for backward compatibility
        self.legacy_pause_dir = self.project_path / ".claude-mpm" / "sessions" / "pause"

    def has_paused_sessions(self) -> bool:
        """Check if there are any paused sessions.

        Returns:
            True if paused sessions exist, False otherwise
        """
        # Check both primary and legacy locations
        session_files = []

        if self.pause_dir.exists():
            session_files.extend(list(self.pause_dir.glob("session-*.json")))

        if self.legacy_pause_dir.exists():
            session_files.extend(list(self.legacy_pause_dir.glob("session-*.json")))

        return len(session_files) > 0

    def get_most_recent_session(self) -> Optional[Dict[str, Any]]:
        """Get the most recent paused session.

        Returns:
            Session data dictionary or None if no sessions found
        """
        # Find all session files from both locations
        session_files = []

        if self.pause_dir.exists():
            session_files.extend(list(self.pause_dir.glob("session-*.json")))

        if self.legacy_pause_dir.exists():
            session_files.extend(list(self.legacy_pause_dir.glob("session-*.json")))

        if not session_files:
            return None

        # Sort by modification time (most recent first)
        session_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)

        # Load the most recent session
        try:
            with session_files[0].open("r") as f:
                session_data = json.load(f)
            session_data["file_path"] = session_files[0]
            return session_data
        except Exception as e:
            logger.error(f"Failed to load session file {session_files[0]}: {e}")
            return None

    def get_git_changes_since_pause(
        self, paused_at: str, recent_commits: List[Dict[str, str]]
    ) -> Tuple[int, List[Dict[str, str]]]:
        """Calculate git changes since session was paused.

        Args:
            paused_at: ISO-8601 timestamp when session was paused
            recent_commits: List of recent commits from session data

        Returns:
            Tuple of (new_commit_count, new_commits_list)
        """
        try:
            # Parse pause timestamp
            pause_time = datetime.fromisoformat(paused_at)

            # Get commits since pause time
            cmd = [
                "git",
                "log",
                f'--since="{pause_time.isoformat()}"',
                "--pretty=format:%h|%an|%ai|%s",
                "--all",
            ]

            result = subprocess.run(
                cmd,
                cwd=self.project_path,
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode != 0:
                logger.warning(f"Git log command failed: {result.stderr}")
                return 0, []

            # Parse commit output
            new_commits = []
            for line in result.stdout.strip().split("\n"):
                if line:
                    parts = line.split("|", 3)
                    if len(parts) == 4:
                        new_commits.append(
                            {
                                "sha": parts[0],
                                "author": parts[1],
                                "timestamp": parts[2],
                                "message": parts[3],
                            }
                        )

            return len(new_commits), new_commits

        except Exception as e:
            logger.error(f"Failed to get git changes: {e}")
            return 0, []

    def get_time_elapsed(self, paused_at: str) -> str:
        """Calculate human-readable time elapsed since pause.

        Args:
            paused_at: ISO-8601 timestamp when session was paused

        Returns:
            Human-readable time string (e.g., "2 hours ago", "3 days ago")
        """
        try:
            pause_time = datetime.fromisoformat(paused_at)
            now = datetime.now(timezone.utc)

            # Ensure pause_time is timezone-aware
            if pause_time.tzinfo is None:
                pause_time = pause_time.replace(tzinfo=timezone.utc)

            delta = now - pause_time

            # Calculate time components
            days = delta.days
            hours = delta.seconds // 3600
            minutes = (delta.seconds % 3600) // 60

            # Format human-readable string
            if days > 0:
                if days == 1:
                    return "1 day ago"
                return f"{days} days ago"
            if hours > 0:
                if hours == 1:
                    return "1 hour ago"
                return f"{hours} hours ago"
            if minutes > 0:
                if minutes == 1:
                    return "1 minute ago"
                return f"{minutes} minutes ago"
            return "just now"

        except Exception as e:
            logger.error(f"Failed to calculate time elapsed: {e}")
            return "unknown time ago"

    def format_resume_prompt(self, session_data: Dict[str, Any]) -> str:
        """Format a user-friendly resume prompt.

        Args:
            session_data: Session data dictionary

        Returns:
            Formatted prompt string for display
        """
        try:
            # Extract session information
            paused_at = session_data.get("paused_at", "")
            conversation = session_data.get("conversation", {})
            git_context = session_data.get("git_context", {})

            summary = conversation.get("summary", "No summary available")
            accomplishments = conversation.get("accomplishments", [])
            next_steps = conversation.get("next_steps", [])

            # Calculate time elapsed
            time_ago = self.get_time_elapsed(paused_at)

            # Get git changes
            recent_commits = git_context.get("recent_commits", [])
            new_commit_count, new_commits = self.get_git_changes_since_pause(
                paused_at, recent_commits
            )

            # Build prompt
            lines = []
            lines.append("\n" + "=" * 80)
            lines.append("📋 PAUSED SESSION FOUND")
            lines.append("=" * 80)
            lines.append(f"\nPaused: {time_ago}")
            lines.append(f"\nLast working on: {summary}")

            if accomplishments:
                lines.append("\nCompleted:")
                for item in accomplishments[:5]:  # Limit to first 5
                    lines.append(f"  ✓ {item}")
                if len(accomplishments) > 5:
                    lines.append(f"  ... and {len(accomplishments) - 5} more")

            if next_steps:
                lines.append("\nNext steps:")
                for item in next_steps[:5]:  # Limit to first 5
                    lines.append(f"  • {item}")
                if len(next_steps) > 5:
                    lines.append(f"  ... and {len(next_steps) - 5} more")

            # Git changes information
            if new_commit_count > 0:
                lines.append(f"\nGit changes since pause: {new_commit_count} commits")
                if new_commits:
                    lines.append("\nRecent commits:")
                    for commit in new_commits[:3]:  # Show first 3
                        lines.append(
                            f"  {commit['sha']} - {commit['message']} ({commit['author']})"
                        )
                    if len(new_commits) > 3:
                        lines.append(f"  ... and {len(new_commits) - 3} more")
            else:
                lines.append("\nNo git changes since pause")

            lines.append("\n" + "=" * 80)
            lines.append(
                "Use this context to resume work, or start fresh if not relevant."
            )
            lines.append("=" * 80 + "\n")

            return "\n".join(lines)

        except Exception as e:
            logger.error(f"Failed to format resume prompt: {e}")
            return "\n📋 Paused session found, but failed to format details.\n"

    def check_and_display_resume_prompt(self) -> Optional[Dict[str, Any]]:
        """Check for paused sessions and display resume prompt if found.

        This is the main entry point for PM startup integration.

        Returns:
            Session data if found and user should resume, None otherwise
        """
        if not self.has_paused_sessions():
            logger.debug("No paused sessions found")
            return None

        # Get most recent session
        session_data = self.get_most_recent_session()
        if not session_data:
            logger.debug("Failed to load paused session data")
            return None

        # Display resume prompt
        prompt_text = self.format_resume_prompt(session_data)
        print(prompt_text)

        # Return session data for PM to use
        return session_data

    def clear_session(self, session_data: Dict[str, Any]) -> bool:
        """Clear a paused session after successful resume.

        Args:
            session_data: Session data dictionary with 'file_path' key

        Returns:
            True if successfully cleared, False otherwise
        """
        try:
            file_path = session_data.get("file_path")
            if not file_path or not isinstance(file_path, Path):
                logger.error("Invalid session file path")
                return False

            if file_path.exists():
                file_path.unlink()
                logger.info(f"Cleared paused session: {file_path}")

                # Also remove SHA256 checksum file if exists
                sha_file = file_path.parent / f".{file_path.name}.sha256"
                if sha_file.exists():
                    sha_file.unlink()
                    logger.debug(f"Cleared session checksum: {sha_file}")

                return True
            logger.warning(f"Session file not found: {file_path}")
            return False

        except Exception as e:
            logger.error(f"Failed to clear session: {e}")
            return False

    def get_session_count(self) -> int:
        """Get count of paused sessions.

        Returns:
            Number of paused sessions
        """
        session_files = []

        if self.pause_dir.exists():
            session_files.extend(list(self.pause_dir.glob("session-*.json")))

        if self.legacy_pause_dir.exists():
            session_files.extend(list(self.legacy_pause_dir.glob("session-*.json")))

        return len(session_files)

    def list_all_sessions(self) -> List[Dict[str, Any]]:
        """List all paused sessions sorted by most recent.

        Returns:
            List of session data dictionaries
        """
        session_files = []

        if self.pause_dir.exists():
            session_files.extend(list(self.pause_dir.glob("session-*.json")))

        if self.legacy_pause_dir.exists():
            session_files.extend(list(self.legacy_pause_dir.glob("session-*.json")))

        if not session_files:
            return []

        # Sort by modification time (most recent first)
        session_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)

        sessions = []
        for session_file in session_files:
            try:
                with session_file.open("r") as f:
                    session_data = json.load(f)
                session_data["file_path"] = session_file
                sessions.append(session_data)
            except Exception as e:
                logger.error(f"Failed to load session {session_file}: {e}")
                continue

        return sessions

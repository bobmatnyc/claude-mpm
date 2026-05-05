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
import re
import subprocess  # nosec B404 - subprocess needed for git commands
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# Matches real timestamped session filenames: session-YYYYMMDD-HHMMSS.json
# Excludes test fixtures like session-test.json, session-valid.json, session-0.json
_TIMESTAMPED_SESSION_RE = re.compile(r"^session-\d{8}-\d{6}\.json$")

# Matches real timestamped .md-only session filenames: session-YYYYMMDD-HHMMSS.md
# These are sessions written by older code or interrupted writes that lack the
# authoritative .json sibling but still contain useful resume context.
_TIMESTAMPED_SESSION_MD_RE = re.compile(r"^session-\d{8}-\d{6}\.md$")

from claude_mpm.core.logger import get_logger

logger = get_logger(__name__)


class SessionResumeHelper:
    """Helper for automatic session resume detection and prompting."""

    def __init__(self, project_path: Path | None = None):
        """Initialize session resume helper.

        Args:
            project_path: Project root path (default: current directory)
        """
        self.project_path = (project_path or Path.cwd()).resolve()
        # Project-local path so sessions are scoped to their originating project
        self.pause_dir = self.project_path / ".claude-mpm" / "sessions"
        # Legacy location for backward compatibility (also project-local)
        self.legacy_pause_dir = self.project_path / ".claude-mpm" / "sessions" / "pause"

    def _find_md_only_sessions(self, directory: Path) -> list[Path]:
        """Find timestamped .md session files lacking a .json counterpart.

        Normal session pauses write three sibling files atomically (.json, .yaml,
        .md). If only the .md file exists, the session is from older code or an
        interrupted write — we still want users to be able to see and resume it.

        Args:
            directory: Directory to scan for .md-only sessions.

        Returns:
            List of Path objects for timestamped .md session files that have no
            corresponding .json file in the same directory.
        """
        if not directory.exists():
            return []

        md_only: list[Path] = []
        for md_path in directory.glob("session-*.md"):
            if not _TIMESTAMPED_SESSION_MD_RE.match(md_path.name):
                continue
            # Skip if a sibling .json exists — the .json is authoritative and
            # will be picked up by the regular .json scan.
            if md_path.with_suffix(".json").exists():
                continue
            md_only.append(md_path)

        if md_only:
            logger.warning(
                "Found .md-only session(s) with no .json counterpart "
                "(may be from older code or interrupted write): %s",
                ", ".join(p.name for p in md_only),
            )

        return md_only

    def _parse_md_session(self, path: Path) -> dict[str, Any] | None:
        """Parse a markdown session file into a session-data dictionary.

        Supports two markdown formats observed in the wild:

        1. Structured format (modern, written alongside .json):
           ``## Session Metadata`` section with ``**Session ID**: ...``,
           ``**Paused At**: ...``, ``**Project**: ...`` lines, plus a
           ``## What You Were Working On`` section with a ``**Summary**:``
           paragraph, and ``## Git Context`` with branch + recent commits.

        2. Legacy/freeform format (older, .md-only):
           ``# <Title>`` with ``**Paused**: <human-readable timestamp>``,
           ``## Accomplishments`` bullet list, etc. We extract whatever we can.

        Args:
            path: Absolute path to the .md session file.

        Returns:
            Session data dictionary compatible with the rest of the helper
            (keys: ``session_id``, ``paused_at``, ``project_path``,
            ``conversation`` with ``summary``/``accomplishments``/``next_steps``,
            and ``file_path``), or ``None`` if the file cannot be read.
        """
        try:
            content = path.read_text(encoding="utf-8")
        except Exception as e:
            logger.error(f"Failed to read .md session {path}: {e}")
            return None

        session_id = path.stem  # session-YYYYMMDD-HHMMSS
        data: dict[str, Any] = {
            "session_id": session_id,
            "paused_at": "",
            "project_path": "",
            "conversation": {
                "summary": "",
                "accomplishments": [],
                "next_steps": [],
            },
            "git_context": {},
            "_md_only": True,  # Marker so callers know this lacks full data
        }

        # Try structured format first: **Session ID**: `...`, **Paused At**: ...
        session_id_match = re.search(r"\*\*Session ID\*\*:\s*`?([^`\n]+)`?", content)
        if session_id_match:
            data["session_id"] = session_id_match.group(1).strip()

        paused_at_match = re.search(r"\*\*Paused At\*\*:\s*([^\n]+)", content)
        if paused_at_match:
            data["paused_at"] = paused_at_match.group(1).strip()
        else:
            # Legacy format: **Paused**: <human-readable date>
            paused_match = re.search(r"\*\*Paused\*\*:\s*([^\n]+)", content)
            if paused_match:
                data["paused_at"] = paused_match.group(1).strip()

        project_match = re.search(r"\*\*Project\*\*:\s*`?([^`\n]+)`?", content)
        if project_match:
            data["project_path"] = project_match.group(1).strip()

        # Summary: paragraph following "**Summary**:" line under any heading
        summary_match = re.search(
            r"\*\*Summary\*\*:\s*\n+([^\n][^\n]*(?:\n(?!\n)[^\n]+)*)",
            content,
        )
        if summary_match:
            data["conversation"]["summary"] = summary_match.group(1).strip()
        else:
            # Legacy: take the first non-empty paragraph after the title line
            # if no summary section exists. This is best-effort.
            lines = [line.strip() for line in content.splitlines()]
            for line in lines:
                if line.startswith("# ") and not line.startswith("## "):
                    # Title line — use it as a fallback summary
                    data["conversation"]["summary"] = line.lstrip("# ").strip()
                    break

        # Accomplishments: bullet list under ## Accomplishments (any suffix)
        accomp_section = re.search(
            r"##\s+Accomplishments[^\n]*\n+((?:.*?\n)*?)(?=\n##\s|\Z)",
            content,
            re.DOTALL,
        )
        if accomp_section:
            bullets = re.findall(
                r"^\s*[-*]\s+(.+)$", accomp_section.group(1), re.MULTILINE
            )
            data["conversation"]["accomplishments"] = [b.strip() for b in bullets]

        # Next steps: bullet list under common section names
        next_section = re.search(
            r"##\s+(?:Next Steps|To Resume|Remaining Work|To Verify[^\n]*)\n+"
            r"((?:.*?\n)*?)(?=\n##\s|\Z)",
            content,
            re.DOTALL,
        )
        if next_section:
            bullets = re.findall(
                r"^\s*(?:[-*]|\d+\.)\s+(?:\[[ x]\]\s+)?(.+)$",
                next_section.group(1),
                re.MULTILINE,
            )
            data["conversation"]["next_steps"] = [b.strip() for b in bullets]

        data["file_path"] = path
        return data

    def has_paused_sessions(self) -> bool:
        """Check if there are any paused sessions.

        Filters to real timestamped session files only (excludes test fixtures
        like ``session-test.json``, ``session-valid.json``, ``session-0.json``)
        to prevent test fixture pollution from triggering false-positive resume
        prompts in production. See ``_TIMESTAMPED_SESSION_RE`` for the regex.

        Returns:
            True if paused sessions exist, False otherwise
        """
        # Check both primary and legacy locations, filtering to real
        # timestamped sessions only (matches session-YYYYMMDD-HHMMSS.json)
        session_files = []

        if self.pause_dir.exists():
            session_files.extend(
                p
                for p in self.pause_dir.glob("session-*.json")
                if _TIMESTAMPED_SESSION_RE.match(p.name)
            )

        if self.legacy_pause_dir.exists():
            session_files.extend(
                p
                for p in self.legacy_pause_dir.glob("session-*.json")
                if _TIMESTAMPED_SESSION_RE.match(p.name)
            )

        if session_files:
            return True

        # No .json sessions — fall back to .md-only sessions so users still
        # see legacy/interrupted sessions in resume prompts and listings.
        md_only = self._find_md_only_sessions(
            self.pause_dir
        ) + self._find_md_only_sessions(self.legacy_pause_dir)
        return len(md_only) > 0

    def get_most_recent_session(self) -> dict[str, Any] | None:
        """Get the most recent paused session.

        Returns:
            Session data dictionary or None if no sessions found
        """
        # Only glob JSON files for loading — .md files cannot be json.load()'d
        session_files = []

        if self.pause_dir.exists():
            session_files.extend(list(self.pause_dir.glob("session-*.json")))

        if self.legacy_pause_dir.exists():
            session_files.extend(list(self.legacy_pause_dir.glob("session-*.json")))

        # Filter to only real timestamped session files (exclude test fixtures
        # like session-test.json, session-valid.json, session-0.json, etc.)
        session_files = [
            p for p in session_files if _TIMESTAMPED_SESSION_RE.match(p.name)
        ]

        # Also include .md-only sessions (legacy or interrupted writes).
        md_only_files = self._find_md_only_sessions(
            self.pause_dir
        ) + self._find_md_only_sessions(self.legacy_pause_dir)

        all_files: list[tuple[Path, str]] = [(p, "json") for p in session_files]
        all_files.extend((p, "md") for p in md_only_files)

        if not all_files:
            return None

        # Sort by modification time (most recent first)
        all_files.sort(key=lambda item: item[0].stat().st_mtime, reverse=True)

        # Load the most recent session belonging to the current project
        current_project = str(self.project_path.resolve())
        for session_file, kind in all_files:
            if kind == "json":
                try:
                    with session_file.open("r") as f:
                        session_data = json.load(f)
                except Exception as e:
                    logger.error(f"Failed to load session file {session_file}: {e}")
                    continue
            else:
                session_data = self._parse_md_session(session_file)
                if session_data is None:
                    continue

            # Validate the session belongs to the current project. This protects
            # against cross-project contamination (e.g. legacy global sessions
            # or sessions copied between projects). For .md-only sessions the
            # project_path may be missing — accept those rather than discard,
            # since they originated in this project's session directory.
            session_project = session_data.get("project_path", "")
            if session_project:
                try:
                    if str(Path(session_project).resolve()) != current_project:
                        continue
                except Exception:
                    # If the stored path is unresolvable, skip defensively
                    continue

            session_data["file_path"] = session_file
            return session_data

        return None

    def get_git_changes_since_pause(
        self, paused_at: str, _: list[dict[str, str]]
    ) -> tuple[int, list[dict[str, str]]]:
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

            result = subprocess.run(  # nosec B603 - git command with safe args
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
            now = datetime.now(UTC)

            # Ensure pause_time is timezone-aware
            if pause_time.tzinfo is None:
                pause_time = pause_time.replace(tzinfo=UTC)

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

    def format_resume_prompt(self, session_data: dict[str, Any]) -> str:
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

    def check_and_display_resume_prompt(self) -> dict[str, Any] | None:
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

    def clear_session(self, session_data: dict[str, Any]) -> bool:
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

        Filters to real timestamped session files only (excludes test fixtures)
        to prevent test fixture pollution. See ``_TIMESTAMPED_SESSION_RE``.

        Returns:
            Number of paused sessions
        """
        session_files = []

        if self.pause_dir.exists():
            session_files.extend(
                p
                for p in self.pause_dir.glob("session-*.json")
                if _TIMESTAMPED_SESSION_RE.match(p.name)
            )

        if self.legacy_pause_dir.exists():
            session_files.extend(
                p
                for p in self.legacy_pause_dir.glob("session-*.json")
                if _TIMESTAMPED_SESSION_RE.match(p.name)
            )

        # Include .md-only sessions (legacy or interrupted writes).
        session_files.extend(self._find_md_only_sessions(self.pause_dir))
        session_files.extend(self._find_md_only_sessions(self.legacy_pause_dir))

        return len(session_files)

    def list_all_sessions(self) -> list[dict[str, Any]]:
        """List all paused sessions sorted by most recent.

        Filters to real timestamped session files only (excludes test fixtures)
        to prevent test fixture pollution. See ``_TIMESTAMPED_SESSION_RE``.

        Returns:
            List of session data dictionaries
        """
        session_files = []

        if self.pause_dir.exists():
            session_files.extend(
                p
                for p in self.pause_dir.glob("session-*.json")
                if _TIMESTAMPED_SESSION_RE.match(p.name)
            )

        if self.legacy_pause_dir.exists():
            session_files.extend(
                p
                for p in self.legacy_pause_dir.glob("session-*.json")
                if _TIMESTAMPED_SESSION_RE.match(p.name)
            )

        # Also include .md-only sessions so they appear in listings.
        md_only_files = self._find_md_only_sessions(
            self.pause_dir
        ) + self._find_md_only_sessions(self.legacy_pause_dir)

        all_files: list[tuple[Path, str]] = [(p, "json") for p in session_files]
        all_files.extend((p, "md") for p in md_only_files)

        if not all_files:
            return []

        # Sort by modification time (most recent first)
        all_files.sort(key=lambda item: item[0].stat().st_mtime, reverse=True)

        sessions = []
        for session_file, kind in all_files:
            if kind == "json":
                try:
                    with session_file.open("r") as f:
                        session_data = json.load(f)
                    session_data["file_path"] = session_file
                    sessions.append(session_data)
                except Exception as e:
                    logger.error(f"Failed to load session {session_file}: {e}")
                    continue
            else:
                session_data = self._parse_md_session(session_file)
                if session_data is not None:
                    sessions.append(session_data)

        return sessions

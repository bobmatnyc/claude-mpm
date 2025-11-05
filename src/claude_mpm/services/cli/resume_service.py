"""Resume Service - Intelligent session resume from stop event logs.

WHY: This service provides resume capabilities by reading stop event logs from
.claude-mpm/responses/ and .claude-mpm/resume-logs/ to help users continue work.

DESIGN DECISIONS:
- Two-tier strategy: prefer resume logs, fallback to response logs
- Read JSON stop events from response logs
- Parse PM responses for context (tasks, files, next steps)
- Group by session_id for session-based resume
- Calculate time elapsed and display comprehensive context
- Non-blocking with graceful degradation

INTEGRATION:
- Used by /mpm-init resume command
- Complements SessionResumeHelper (pause-based) with log-based approach
"""

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from claude_mpm.core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class SessionSummary:
    """Summary of a session from logs."""

    session_id: str
    timestamp: datetime
    agent_count: int
    stop_reason: str
    token_usage: int
    last_agent: str
    working_directory: str
    git_branch: str


@dataclass
class SessionContext:
    """Full context for resuming a session."""

    session_id: str
    timestamp: datetime
    time_ago: str
    request: str
    response: str

    # Metadata
    stop_reason: str
    token_usage: int
    working_directory: str
    git_branch: str

    # PM-specific data
    tasks_completed: List[str]
    files_affected: List[str]
    next_steps: List[str]
    context_management: Optional[str]
    delegation_compliance: Optional[str]

    # Response logs used
    response_files: List[str]


class ResumeService:
    """Service for reading and parsing stop event logs for resume functionality."""

    def __init__(self, project_path: Optional[Path] = None):
        """Initialize resume service.

        Args:
            project_path: Project root path (default: current directory)
        """
        self.project_path = project_path or Path.cwd()
        self.responses_dir = self.project_path / ".claude-mpm" / "responses"
        self.resume_logs_dir = self.project_path / ".claude-mpm" / "resume-logs"

    def list_sessions(self) -> List[SessionSummary]:
        """List all available sessions from response logs.

        Returns:
            List of SessionSummary objects sorted by most recent first
        """
        if not self.responses_dir.exists():
            logger.debug("No responses directory found")
            return []

        # Group response files by session_id
        sessions_map: Dict[str, List[Path]] = {}

        for response_file in self.responses_dir.glob("*.json"):
            try:
                with response_file.open("r") as f:
                    data = json.load(f)

                session_id = data.get("session_id", "unknown")
                if session_id not in sessions_map:
                    sessions_map[session_id] = []
                sessions_map[session_id].append(response_file)

            except Exception as e:
                logger.warning(f"Failed to read {response_file}: {e}")
                continue

        # Create summaries
        summaries = []
        for session_id, files in sessions_map.items():
            try:
                # Use the most recent file for this session
                files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
                latest_file = files[0]

                with latest_file.open("r") as f:
                    data = json.load(f)

                metadata = data.get("metadata", {})
                timestamp_str = data.get("timestamp") or metadata.get("timestamp")
                timestamp = self._parse_timestamp(timestamp_str)

                summary = SessionSummary(
                    session_id=session_id,
                    timestamp=timestamp,
                    agent_count=len(files),
                    stop_reason=metadata.get("stop_reason", "unknown"),
                    token_usage=metadata.get("usage", {}).get("total_tokens", 0),
                    last_agent=data.get("agent", "unknown"),
                    working_directory=metadata.get("working_directory", ""),
                    git_branch=metadata.get("git_branch", "unknown"),
                )
                summaries.append(summary)

            except Exception as e:
                logger.warning(
                    f"Failed to create summary for session {session_id}: {e}"
                )
                continue

        # Sort by most recent first
        summaries.sort(key=lambda s: s.timestamp, reverse=True)
        return summaries

    def get_session_context(self, session_id: str) -> Optional[SessionContext]:
        """Get full context for a specific session.

        Args:
            session_id: Session ID to retrieve context for

        Returns:
            SessionContext object or None if not found
        """
        # Try resume log first
        resume_context = self._get_context_from_resume_log(session_id)
        if resume_context:
            return resume_context

        # Fallback to response logs
        return self._get_context_from_response_logs(session_id)

    def get_latest_session(self) -> Optional[SessionContext]:
        """Get context from most recent session.

        Returns:
            SessionContext object or None if no sessions found
        """
        sessions = self.list_sessions()
        if not sessions:
            logger.debug("No sessions found")
            return None

        latest = sessions[0]
        return self.get_session_context(latest.session_id)

    def _get_context_from_resume_log(self, session_id: str) -> Optional[SessionContext]:
        """Try to get context from structured resume log.

        Args:
            session_id: Session ID

        Returns:
            SessionContext or None if not found
        """
        if not self.resume_logs_dir.exists():
            return None

        # Find resume log for this session
        for resume_log in self.resume_logs_dir.glob(f"*{session_id}*.md"):
            try:
                content = resume_log.read_text(encoding="utf-8")
                return self._parse_resume_log(session_id, content)
            except Exception as e:
                logger.warning(f"Failed to parse resume log {resume_log}: {e}")
                continue

        return None

    def _get_context_from_response_logs(
        self, session_id: str
    ) -> Optional[SessionContext]:
        """Get context from response logs for a session.

        Args:
            session_id: Session ID

        Returns:
            SessionContext or None if not found
        """
        if not self.responses_dir.exists():
            return None

        # Find all response files for this session
        response_files = []
        for response_file in self.responses_dir.glob("*.json"):
            try:
                with response_file.open("r") as f:
                    data = json.load(f)
                if data.get("session_id") == session_id:
                    response_files.append(response_file)
            except Exception as e:
                logger.warning(f"Failed to read {response_file}: {e}")
                continue

        if not response_files:
            logger.debug(f"No response files found for session {session_id}")
            return None

        # Sort by timestamp (most recent last)
        response_files.sort(key=lambda p: p.stat().st_mtime)

        # Parse the files to build context
        return self._build_context_from_files(session_id, response_files)

    def _build_context_from_files(
        self, session_id: str, response_files: List[Path]
    ) -> Optional[SessionContext]:
        """Build SessionContext from multiple response files.

        Args:
            session_id: Session ID
            response_files: List of response file paths

        Returns:
            SessionContext or None if parsing fails
        """
        try:
            # Use the last (most recent) file for primary data
            latest_file = response_files[-1]

            with latest_file.open("r") as f:
                latest_data = json.load(f)

            metadata = latest_data.get("metadata", {})
            timestamp_str = latest_data.get("timestamp") or metadata.get("timestamp")
            timestamp = self._parse_timestamp(timestamp_str)

            # Extract basic info
            request = latest_data.get("request", "Unknown request")
            response = latest_data.get("response", "")

            # Parse PM response if available
            pm_data = self.parse_pm_response(latest_data)

            # Calculate time elapsed
            time_ago = self._calculate_time_ago(timestamp)

            return SessionContext(
                session_id=session_id,
                timestamp=timestamp,
                time_ago=time_ago,
                request=request,
                response=response,
                stop_reason=metadata.get("stop_reason", "unknown"),
                token_usage=metadata.get("usage", {}).get("total_tokens", 0),
                working_directory=metadata.get("working_directory", ""),
                git_branch=metadata.get("git_branch", "unknown"),
                tasks_completed=pm_data.get("tasks_completed", []),
                files_affected=pm_data.get("files_affected", []),
                next_steps=pm_data.get("next_steps", []),
                context_management=pm_data.get("context_management"),
                delegation_compliance=pm_data.get("delegation_compliance"),
                response_files=[str(f) for f in response_files],
            )

        except Exception as e:
            logger.error(f"Failed to build context from files: {e}")
            return None

    def parse_pm_response(self, response_json: dict) -> dict:
        """Extract key info from PM response JSON.

        Parses the PM's response text looking for JSON blocks with pm_summary,
        TodoWrite mentions, tasks, files, etc.

        Args:
            response_json: Full response JSON from log file

        Returns:
            Dict with extracted PM data
        """
        result = {
            "tasks_completed": [],
            "files_affected": [],
            "next_steps": [],
            "context_management": None,
            "delegation_compliance": None,
        }

        response_text = response_json.get("response", "")
        if not response_text:
            return result

        # Try to find JSON block in response
        json_blocks = re.findall(r"```json\s*(\{.*?\})\s*```", response_text, re.DOTALL)

        for json_str in json_blocks:
            try:
                data = json.loads(json_str)

                # Look for PM summary data
                if data.get("pm_summary"):
                    # Extract tasks from various PM fields
                    result["tasks_completed"] = (
                        data.get("tasks_completed", [])
                        or data.get("measurable_outcomes", [])
                        or []
                    )

                    # Extract files
                    result["files_affected"] = data.get("files_affected", [])

                    # Extract next steps from various fields
                    result["next_steps"] = (
                        data.get("next_steps", [])
                        or data.get("next_actions", [])
                        or data.get("unresolved_requirements", [])
                        or []
                    )

                    result["context_management"] = data.get("context_management")
                    result["delegation_compliance"] = data.get("delegation_compliance")
                    return result  # Found PM summary, use it

            except json.JSONDecodeError:
                continue

        # Fallback: parse response text for common patterns
        result["tasks_completed"] = self._extract_completed_tasks(response_text)
        result["files_affected"] = self._extract_files(response_text)
        result["next_steps"] = self._extract_next_steps(response_text)

        return result

    def _extract_completed_tasks(self, text: str) -> List[str]:
        """Extract completed tasks from response text."""
        tasks = []

        # Look for bullet lists with checkmarks
        for line in text.split("\n"):
            if re.search(r"[✓✅☑]\s*(.+)", line):
                match = re.search(r"[✓✅☑]\s*(.+)", line)
                if match:
                    tasks.append(match.group(1).strip())

        return tasks[:10]  # Limit to 10

    def _extract_files(self, text: str) -> List[str]:
        """Extract file paths from response text."""
        files = []

        # Look for file paths (common patterns)
        patterns = [
            r"`([^`]+\.(py|js|ts|md|json|yaml|yml|txt|sh))`",
            r"File:\s*([^\s]+)",
            r"Modified:\s*([^\s]+)",
        ]

        for pattern in patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                file_path = match[0] if isinstance(match, tuple) else match
                if file_path and file_path not in files:
                    files.append(file_path)

        return files[:20]  # Limit to 20

    def _extract_next_steps(self, text: str) -> List[str]:
        """Extract next steps from response text."""
        steps = []

        # Look for "Next steps" section
        next_steps_section = re.search(
            r"(?:Next [Ss]teps?|TODO|To [Dd]o):?\s*(.*?)(?:\n\n|\Z)", text, re.DOTALL
        )

        if next_steps_section:
            section_text = next_steps_section.group(1)
            for line in section_text.split("\n"):
                # Look for bullet points or numbered items
                if re.match(r"^\s*[-*•]\s*(.+)", line):
                    match = re.match(r"^\s*[-*•]\s*(.+)", line)
                    if match:
                        steps.append(match.group(1).strip())
                elif re.match(r"^\s*\d+[\.)]\s*(.+)", line):
                    match = re.match(r"^\s*\d+[\.)]\s*(.+)", line)
                    if match:
                        steps.append(match.group(1).strip())

        return steps[:10]  # Limit to 10

    def _parse_resume_log(
        self, session_id: str, content: str
    ) -> Optional[SessionContext]:
        """Parse structured resume log markdown file.

        Args:
            session_id: Session ID
            content: Markdown content of resume log

        Returns:
            SessionContext or None if parsing fails
        """
        try:
            # Extract sections using markdown headers
            mission = self._extract_section(content, "Mission")
            accomplishments = self._extract_list_items(content, "Accomplishments")
            findings = self._extract_section(content, "Key Findings")
            next_steps = self._extract_list_items(content, "Next Steps")

            # Extract timestamp from header
            timestamp_match = re.search(r"Session Resume:\s*(.+)", content)
            timestamp_str = timestamp_match.group(1) if timestamp_match else None
            timestamp = self._parse_timestamp(timestamp_str)

            time_ago = self._calculate_time_ago(timestamp)

            return SessionContext(
                session_id=session_id,
                timestamp=timestamp,
                time_ago=time_ago,
                request=mission or "Unknown",
                response=findings or "",
                stop_reason="resume_log",
                token_usage=0,
                working_directory="",
                git_branch="unknown",
                tasks_completed=accomplishments,
                files_affected=[],
                next_steps=next_steps,
                context_management=None,
                delegation_compliance=None,
                response_files=[],
            )

        except Exception as e:
            logger.error(f"Failed to parse resume log: {e}")
            return None

    def _extract_section(self, content: str, header: str) -> Optional[str]:
        """Extract content from a markdown section."""
        pattern = rf"##\s+{header}\s*\n(.+?)(?=\n##|\Z)"
        match = re.search(pattern, content, re.DOTALL)
        return match.group(1).strip() if match else None

    def _extract_list_items(self, content: str, header: str) -> List[str]:
        """Extract list items from a markdown section."""
        section = self._extract_section(content, header)
        if not section:
            return []

        items = []
        for line in section.split("\n"):
            if re.match(r"^\s*[-*•]\s*(.+)", line):
                match = re.match(r"^\s*[-*•]\s*(.+)", line)
                if match:
                    items.append(match.group(1).strip())

        return items

    def _parse_timestamp(self, timestamp_str: Optional[str]) -> datetime:
        """Parse timestamp string to datetime object.

        Args:
            timestamp_str: ISO-8601 timestamp string

        Returns:
            datetime object (defaults to epoch if parsing fails)
        """
        if not timestamp_str:
            return datetime.fromtimestamp(0, tz=timezone.utc)

        try:
            # Try ISO format
            dt = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except Exception:
            # Fallback to epoch
            logger.warning(f"Failed to parse timestamp: {timestamp_str}")
            return datetime.fromtimestamp(0, tz=timezone.utc)

    def _calculate_time_ago(self, timestamp: datetime) -> str:
        """Calculate human-readable time elapsed.

        Args:
            timestamp: Timestamp to calculate from

        Returns:
            Human-readable string like "2 hours ago"
        """
        now = datetime.now(timezone.utc)
        delta = now - timestamp

        days = delta.days
        hours = delta.seconds // 3600
        minutes = (delta.seconds % 3600) // 60

        if days > 0:
            return f"{days} day{'s' if days != 1 else ''} ago"
        if hours > 0:
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        if minutes > 0:
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        return "just now"

    def format_resume_display(self, context: SessionContext) -> str:
        """Format context for user display.

        Args:
            context: SessionContext to format

        Returns:
            Formatted string for console display
        """
        lines = []
        lines.append("\n" + "=" * 80)
        lines.append(f"📋 Resume Context - Session from {context.time_ago}")
        lines.append("=" * 80)
        lines.append("")

        lines.append(f"Session ID: {context.session_id}")
        lines.append(
            f"Ended: {context.timestamp.strftime('%Y-%m-%d %H:%M')} ({context.time_ago})"
        )
        lines.append(f"Stop Reason: {self._format_stop_reason(context.stop_reason)}")

        if context.token_usage > 0:
            usage_pct = (context.token_usage / 200000) * 100
            lines.append(
                f"Token Usage: {context.token_usage:,} / 200,000 ({usage_pct:.0f}%)"
            )

        lines.append("")
        lines.append("Working on:")
        lines.append(f'  "{context.request}"')

        if context.tasks_completed:
            lines.append("")
            lines.append("✅ Completed:")
            for task in context.tasks_completed[:10]:
                lines.append(f"  • {task}")
            if len(context.tasks_completed) > 10:
                lines.append(f"  ... and {len(context.tasks_completed) - 10} more")

        if context.files_affected:
            lines.append("")
            lines.append("📝 Files Modified:")
            for file_path in context.files_affected[:15]:
                lines.append(f"  • {file_path}")
            if len(context.files_affected) > 15:
                lines.append(f"  ... and {len(context.files_affected) - 15} more")

        if context.next_steps:
            lines.append("")
            lines.append("🎯 Next Steps:")
            for step in context.next_steps[:10]:
                lines.append(f"  • {step}")
            if len(context.next_steps) > 10:
                lines.append(f"  ... and {len(context.next_steps) - 10} more")

        if context.working_directory or context.git_branch != "unknown":
            lines.append("")
            lines.append("Git Context:")
            if context.git_branch != "unknown":
                lines.append(f"  Branch: {context.git_branch}")
            if context.working_directory:
                lines.append(f"  Working Directory: {context.working_directory}")

        lines.append("")
        lines.append("=" * 80)
        lines.append("")

        return "\n".join(lines)

    def _format_stop_reason(self, reason: str) -> str:
        """Format stop reason for display."""
        reason_map = {
            "end_turn": "Natural completion",
            "max_tokens": "Context limit reached",
            "stop_sequence": "Stop sequence detected",
            "tool_use": "Tool interaction completed",
            "completed": "Task completed",
            "resume_log": "From resume log",
            "unknown": "Unknown",
        }

        # Check for context threshold
        if "context" in reason.lower() and "threshold" in reason.lower():
            return "Context threshold reached"

        return reason_map.get(reason, reason.capitalize())

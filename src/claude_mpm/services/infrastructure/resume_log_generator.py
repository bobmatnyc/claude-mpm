"""Resume Log Generator Service.

Automatically generates session resume logs when approaching or hitting token limits.
Integrates with session management and response tracking infrastructure.

Triggers:
- model_context_window_exceeded (stop_reason)
- Manual pause command
- 95% token threshold reached
- Session end with high token usage (>85%)

Design Principles:
- Atomic file operations (via state_storage)
- Non-blocking generation
- Graceful degradation if generation fails
- Integration with existing session state
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from claude_mpm.core.logging_utils import get_logger
from claude_mpm.models.resume_log import ContextMetrics, ResumeLog
from claude_mpm.storage.state_storage import StateStorage

logger = get_logger(__name__)


class ResumeLogGenerator:
    """Service for generating session resume logs."""

    def __init__(
        self,
        storage_dir: Optional[Path] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        """Initialize resume log generator.

        Args:
            storage_dir: Directory for resume logs (default: .claude-mpm/resume-logs)
            config: Configuration dictionary
        """
        self.storage_dir = storage_dir or Path.home() / ".claude-mpm" / "resume-logs"
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        # State storage for atomic writes
        self.state_storage = StateStorage(
            storage_dir=self.storage_dir.parent / "storage"
        )

        # Configuration
        self.config = config or {}
        self.enabled = (
            self.config.get("context_management", {})
            .get("resume_logs", {})
            .get("enabled", True)
        )
        self.auto_generate = (
            self.config.get("context_management", {})
            .get("resume_logs", {})
            .get("auto_generate", True)
        )
        self.max_tokens = (
            self.config.get("context_management", {})
            .get("resume_logs", {})
            .get("max_tokens", 10000)
        )

        # Trigger thresholds
        thresholds = self.config.get("context_management", {}).get("thresholds", {})
        self.threshold_caution = thresholds.get("caution", 0.70)
        self.threshold_warning = thresholds.get("warning", 0.85)
        self.threshold_critical = thresholds.get("critical", 0.95)

        logger.info(
            f"ResumeLogGenerator initialized (enabled={self.enabled}, auto_generate={self.auto_generate})"
        )

    def should_generate(
        self,
        stop_reason: Optional[str] = None,
        token_usage_pct: Optional[float] = None,
        manual_trigger: bool = False,
    ) -> bool:
        """Determine if resume log should be generated.

        Args:
            stop_reason: Claude API stop_reason
            token_usage_pct: Current token usage percentage (0.0-1.0)
            manual_trigger: Manual pause/stop command

        Returns:
            True if resume log should be generated
        """
        if not self.enabled or not self.auto_generate:
            return manual_trigger  # Only generate on manual trigger if auto is disabled

        # Trigger conditions
        triggers = [
            stop_reason == "max_tokens",
            stop_reason == "model_context_window_exceeded",
            manual_trigger,
            token_usage_pct and token_usage_pct >= self.threshold_critical,
            token_usage_pct
            and token_usage_pct >= self.threshold_warning,  # Generate at 85% too
        ]

        should_gen = any(triggers)

        if should_gen:
            reason = "unknown"
            if stop_reason:
                reason = f"stop_reason={stop_reason}"
            elif manual_trigger:
                reason = "manual_trigger"
            elif token_usage_pct:
                reason = f"token_usage={token_usage_pct:.1%}"

            logger.info(f"Resume log generation triggered: {reason}")

        return should_gen

    def generate_from_session_state(
        self,
        session_id: str,
        session_state: Dict[str, Any],
        stop_reason: Optional[str] = None,
    ) -> Optional[ResumeLog]:
        """Generate resume log from session state data.

        Args:
            session_id: Current session ID
            session_state: Session state dictionary
            stop_reason: Claude API stop_reason

        Returns:
            Generated ResumeLog or None if generation failed
        """
        try:
            # Extract context metrics
            context_data = session_state.get("context_metrics", {})
            context_metrics = ContextMetrics(
                total_budget=context_data.get("total_budget", 200000),
                used_tokens=context_data.get("used_tokens", 0),
                remaining_tokens=context_data.get("remaining_tokens", 0),
                percentage_used=context_data.get("percentage_used", 0.0),
                stop_reason=stop_reason or context_data.get("stop_reason"),
                model=context_data.get("model", "claude-sonnet-4.5"),
                session_id=session_id,
            )

            # Extract content from session state
            mission_summary = session_state.get("mission_summary", "")
            accomplishments = session_state.get("accomplishments", [])
            key_findings = session_state.get("key_findings", [])
            decisions_made = session_state.get("decisions_made", [])
            next_steps = session_state.get("next_steps", [])
            critical_context = session_state.get("critical_context", {})

            # Extract metadata
            files_modified = session_state.get("files_modified", [])
            agents_used = session_state.get("agents_used", {})
            errors_encountered = session_state.get("errors_encountered", [])
            warnings = session_state.get("warnings", [])

            # Create resume log
            resume_log = ResumeLog(
                session_id=session_id,
                previous_session_id=session_state.get("previous_session_id"),
                context_metrics=context_metrics,
                mission_summary=mission_summary,
                accomplishments=accomplishments,
                key_findings=key_findings,
                decisions_made=decisions_made,
                next_steps=next_steps,
                critical_context=critical_context,
                files_modified=files_modified,
                agents_used=agents_used,
                errors_encountered=errors_encountered,
                warnings=warnings,
            )

            logger.info(f"Generated resume log for session {session_id}")
            return resume_log

        except Exception as e:
            logger.error(
                f"Failed to generate resume log from session state: {e}", exc_info=True
            )
            return None

    def generate_from_todo_list(
        self,
        session_id: str,
        todos: List[Dict[str, Any]],
        context_metrics: Optional[ContextMetrics] = None,
    ) -> Optional[ResumeLog]:
        """Generate resume log from TODO list.

        Useful when session state is minimal but TODO list has rich information.

        Args:
            session_id: Current session ID
            todos: TODO list items
            context_metrics: Context metrics (optional)

        Returns:
            Generated ResumeLog or None if generation failed
        """
        try:
            # Categorize todos
            completed = [t for t in todos if t.get("status") == "completed"]
            in_progress = [t for t in todos if t.get("status") == "in_progress"]
            pending = [t for t in todos if t.get("status") == "pending"]

            # Build accomplishments from completed tasks
            accomplishments = [f"✓ {task['content']}" for task in completed]

            # Build next steps from in-progress and pending
            next_steps = []
            for task in in_progress:
                next_steps.append(f"[IN PROGRESS] {task['content']}")
            for task in pending:
                next_steps.append(f"[PENDING] {task['content']}")

            # Create mission summary
            mission_summary = f"Working on {len(todos)} tasks: {len(completed)} completed, {len(in_progress)} in progress, {len(pending)} pending."

            # Use provided context metrics or create default
            if context_metrics is None:
                context_metrics = ContextMetrics(session_id=session_id)

            # Create resume log
            resume_log = ResumeLog(
                session_id=session_id,
                context_metrics=context_metrics,
                mission_summary=mission_summary,
                accomplishments=accomplishments,
                next_steps=next_steps,
                critical_context={
                    "total_tasks": len(todos),
                    "completed_tasks": len(completed),
                    "in_progress_tasks": len(in_progress),
                    "pending_tasks": len(pending),
                },
            )

            logger.info(f"Generated resume log from TODO list for session {session_id}")
            return resume_log

        except Exception as e:
            logger.error(
                f"Failed to generate resume log from TODO list: {e}", exc_info=True
            )
            return None

    def save_resume_log(self, resume_log: ResumeLog) -> Optional[Path]:
        """Save resume log to storage.

        Args:
            resume_log: ResumeLog instance to save

        Returns:
            Path to saved file or None if save failed
        """
        try:
            # Save as markdown (primary format)
            md_path = resume_log.save(storage_dir=self.storage_dir)

            # Also save as JSON for programmatic access
            json_path = self.storage_dir / f"session-{resume_log.session_id}.json"
            self.state_storage.write_json(
                data=resume_log.to_dict(),
                file_path=json_path,
                atomic=True,
            )

            logger.info(f"Resume log saved: {md_path}")
            return md_path

        except Exception as e:
            logger.error(f"Failed to save resume log: {e}", exc_info=True)
            return None

    def load_resume_log(self, session_id: str) -> Optional[str]:
        """Load resume log markdown content.

        Args:
            session_id: Session ID to load

        Returns:
            Markdown content or None if not found
        """
        try:
            md_path = self.storage_dir / f"session-{session_id}.md"

            if not md_path.exists():
                logger.debug(f"Resume log not found for session {session_id}")
                return None

            content = md_path.read_text(encoding="utf-8")
            logger.info(f"Loaded resume log for session {session_id}")
            return content

        except Exception as e:
            logger.error(f"Failed to load resume log: {e}", exc_info=True)
            return None

    def list_resume_logs(self) -> List[Dict[str, Any]]:
        """List all available resume logs.

        Returns:
            List of resume log metadata
        """
        try:
            logs = []

            for md_file in self.storage_dir.glob("session-*.md"):
                # Extract session ID from filename
                session_id = md_file.stem.replace("session-", "")

                # Check if JSON metadata exists
                json_file = md_file.with_suffix(".json")
                metadata = {}
                if json_file.exists():
                    json_data = self.state_storage.read_json(json_file)
                    if json_data:
                        metadata = {
                            "session_id": session_id,
                            "created_at": json_data.get("created_at"),
                            "previous_session_id": json_data.get("previous_session_id"),
                            "context_metrics": json_data.get("context_metrics", {}),
                            "file_path": str(md_file),
                        }

                if metadata:
                    logs.append(metadata)
                else:
                    # Fallback to file metadata
                    logs.append(
                        {
                            "session_id": session_id,
                            "file_path": str(md_file),
                            "modified_at": datetime.fromtimestamp(
                                md_file.stat().st_mtime, tz=timezone.utc
                            ).isoformat(),
                        }
                    )

            # Sort by creation time (newest first)
            logs.sort(
                key=lambda x: x.get("created_at", x.get("modified_at", "")),
                reverse=True,
            )

            logger.debug(f"Found {len(logs)} resume logs")
            return logs

        except Exception as e:
            logger.error(f"Failed to list resume logs: {e}", exc_info=True)
            return []

    def cleanup_old_logs(self, keep_count: int = 10) -> int:
        """Clean up old resume logs, keeping only the most recent.

        Args:
            keep_count: Number of logs to keep

        Returns:
            Number of logs deleted
        """
        try:
            logs = self.list_resume_logs()

            if len(logs) <= keep_count:
                logger.debug(
                    f"No cleanup needed ({len(logs)} logs <= {keep_count} keep)"
                )
                return 0

            # Delete old logs
            deleted = 0
            for log in logs[keep_count:]:
                try:
                    md_path = Path(log["file_path"])
                    json_path = md_path.with_suffix(".json")

                    if md_path.exists():
                        md_path.unlink()
                        deleted += 1

                    if json_path.exists():
                        json_path.unlink()

                except Exception as e:
                    logger.warning(f"Failed to delete log {log['session_id']}: {e}")

            logger.info(f"Cleaned up {deleted} old resume logs (kept {keep_count})")
            return deleted

        except Exception as e:
            logger.error(f"Failed to cleanup old logs: {e}", exc_info=True)
            return 0

    def get_stats(self) -> Dict[str, Any]:
        """Get resume log statistics.

        Returns:
            Dictionary with statistics
        """
        try:
            logs = self.list_resume_logs()

            total_size = 0
            for log in logs:
                path = Path(log["file_path"])
                if path.exists():
                    total_size += path.stat().st_size

            return {
                "enabled": self.enabled,
                "auto_generate": self.auto_generate,
                "total_logs": len(logs),
                "storage_dir": str(self.storage_dir),
                "total_size_kb": round(total_size / 1024, 2),
                "thresholds": {
                    "caution": f"{self.threshold_caution:.0%}",
                    "warning": f"{self.threshold_warning:.0%}",
                    "critical": f"{self.threshold_critical:.0%}",
                },
            }

        except Exception as e:
            logger.error(f"Failed to get stats: {e}", exc_info=True)
            return {
                "enabled": self.enabled,
                "error": str(e),
            }

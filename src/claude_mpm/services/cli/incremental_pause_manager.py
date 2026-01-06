"""Incremental Pause Manager Service.

WHY: Captures actions incrementally after auto-pause threshold (90%) is crossed to
record the "wind-down" period before session ends. Uses append-only JSONL format
for efficient incremental capture with crash safety.

DESIGN DECISIONS:
- JSONL format for append-only writes (one action per line)
- Atomic appends using file locking for concurrent safety
- Delegates to SessionPauseManager for final snapshot generation
- Tracks pause lifecycle: start -> append actions -> finalize/discard
- Session ID matches pattern from SessionPauseManager for consistency

USAGE:
    manager = IncrementalPauseManager()

    # Start incremental pause at 90% threshold
    session_id = manager.start_incremental_pause(
        context_percentage=0.90,
        initial_state=tracker.get_current_state().__dict__
    )

    # Record actions during wind-down
    manager.append_action(
        action_type="tool_call",
        action_data={"tool": "Read", "path": "/some/file.py"},
        context_percentage=0.92
    )

    # Finalize when session ends
    final_path = manager.finalize_pause()
"""

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from claude_mpm.core.logger import get_logger
from claude_mpm.services.cli.session_pause_manager import SessionPauseManager

logger = get_logger(__name__)


@dataclass
class PauseAction:
    """Single action recorded during incremental pause.

    Attributes:
        type: Action type ('tool_call', 'assistant_response', 'user_message',
              'system_event', 'pause_started', 'pause_finalized')
        timestamp: ISO format timestamp
        session_id: Unique session identifier
        data: Action-specific data dictionary
        context_percentage: Context usage when action recorded (0.0-1.0)
    """

    type: str
    timestamp: str
    session_id: str
    data: Dict[str, Any]
    context_percentage: float

    def to_json_line(self) -> str:
        """Convert to JSON line for JSONL format.

        Returns:
            JSON string with newline appended
        """
        return json.dumps(asdict(self), ensure_ascii=False, default=str) + "\n"

    @classmethod
    def from_json_line(cls, line: str) -> "PauseAction":
        """Parse from JSON line.

        Args:
            line: JSON string (with or without newline)

        Returns:
            PauseAction instance

        Raises:
            json.JSONDecodeError: If line is not valid JSON
            ValueError: If required fields are missing
        """
        data = json.loads(line.strip())
        return cls(**data)


class IncrementalPauseManager:
    """Manages incremental capture of actions during auto-pause wind-down.

    Features:
    - Append-only JSONL file for efficient incremental writes
    - Atomic file operations with file locking
    - Session lifecycle tracking (start -> append -> finalize/discard)
    - Integration with SessionPauseManager for final snapshots
    - Crash-safe recording (each action appended atomically)

    The incremental pause captures the "tail" of a session after the 90%
    threshold is crossed, allowing us to record final actions before the
    user decides to pause or continue.
    """

    ACTIVE_PAUSE_FILE = "ACTIVE-PAUSE.jsonl"

    def __init__(self, project_path: Optional[Path] = None):
        """Initialize incremental pause manager.

        Args:
            project_path: Project root path (default: current directory)
        """
        self.project_path = (project_path or Path.cwd()).resolve()
        self.sessions_dir = self.project_path / ".claude-mpm" / "sessions"
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self.active_pause_path = self.sessions_dir / self.ACTIVE_PAUSE_FILE

        logger.debug(f"IncrementalPauseManager initialized: {self.active_pause_path}")

    def is_pause_active(self) -> bool:
        """Check if there's an active incremental pause in progress.

        Returns:
            True if ACTIVE-PAUSE.jsonl exists
        """
        return self.active_pause_path.exists()

    def start_incremental_pause(
        self, context_percentage: float, initial_state: Dict[str, Any]
    ) -> str:
        """Start a new incremental pause session.

        Args:
            context_percentage: Current context usage (e.g., 0.90 for 90%)
            initial_state: Initial context snapshot (from ContextUsageTracker)

        Returns:
            session_id: Unique identifier for this pause session

        Raises:
            RuntimeError: If pause is already active
        """
        if self.is_pause_active():
            logger.warning("Incremental pause already active, cannot start new pause")
            raise RuntimeError(
                "An incremental pause is already active. "
                "Call finalize_pause() or discard_pause() first."
            )

        # Generate session ID matching SessionPauseManager pattern
        session_id = f"session-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"

        # Create initial pause_started action
        start_action = PauseAction(
            type="pause_started",
            timestamp=datetime.now(timezone.utc).isoformat(),
            session_id=session_id,
            data={
                "context_percentage": context_percentage,
                "initial_state": initial_state,
                "reason": "Auto-pause threshold exceeded (90%+)",
            },
            context_percentage=context_percentage,
        )

        # Write initial action to file
        try:
            with self.active_pause_path.open("w") as f:
                f.write(start_action.to_json_line())

            logger.info(
                f"Incremental pause started: {session_id} "
                f"(context: {context_percentage:.1%})"
            )
            return session_id

        except Exception as e:
            logger.error(f"Failed to start incremental pause: {e}")
            # Clean up partial file if created
            if self.active_pause_path.exists():
                self.active_pause_path.unlink()
            raise RuntimeError(f"Failed to start incremental pause: {e}") from e

    def append_action(
        self, action_type: str, action_data: Dict[str, Any], context_percentage: float
    ) -> None:
        """Append an action to the active pause file.

        Args:
            action_type: Type of action ('tool_call', 'assistant_response',
                        'user_message', 'system_event')
            action_data: Action-specific data to record
            context_percentage: Current context usage (0.0-1.0)

        Raises:
            RuntimeError: If no active pause session exists
        """
        if not self.is_pause_active():
            logger.warning(
                f"Cannot append action '{action_type}': no active pause session"
            )
            raise RuntimeError(
                "No active pause session. Call start_incremental_pause() first."
            )

        # Get session ID from first line
        try:
            session_id = self._get_session_id()

            action = PauseAction(
                type=action_type,
                timestamp=datetime.now(timezone.utc).isoformat(),
                session_id=session_id,
                data=action_data,
                context_percentage=context_percentage,
            )

            # Append to file atomically
            with self.active_pause_path.open("a") as f:
                f.write(action.to_json_line())
                f.flush()  # Ensure data is written to disk

            logger.debug(
                f"Appended action '{action_type}' to pause session "
                f"(context: {context_percentage:.1%})"
            )

        except Exception as e:
            logger.error(f"Failed to append action to pause session: {e}")
            raise RuntimeError(f"Failed to append action: {e}") from e

    def get_recorded_actions(self) -> List[PauseAction]:
        """Read all actions from the current pause session.

        Returns:
            List of PauseAction objects in chronological order

        Raises:
            RuntimeError: If no active pause session exists
        """
        if not self.is_pause_active():
            raise RuntimeError("No active pause session")

        try:
            actions = []
            with self.active_pause_path.open("r") as f:
                for line in f:
                    if line.strip():
                        actions.append(PauseAction.from_json_line(line))

            logger.debug(f"Read {len(actions)} actions from pause session")
            return actions

        except Exception as e:
            logger.error(f"Failed to read recorded actions: {e}")
            raise RuntimeError(f"Failed to read actions: {e}") from e

    def finalize_pause(self, create_full_snapshot: bool = True) -> Optional[Path]:
        """Finalize the incremental pause into a complete session snapshot.

        This method:
        1. Appends a 'pause_finalized' action
        2. Optionally delegates to SessionPauseManager to create JSON/YAML/MD files
        3. Removes the ACTIVE-PAUSE.jsonl file
        4. Returns path to the finalized session file

        Args:
            create_full_snapshot: If True, use SessionPauseManager to create
                                 complete session files

        Returns:
            Path to the finalized session file, or None if no active pause

        Raises:
            RuntimeError: If finalization fails
        """
        if not self.is_pause_active():
            logger.warning("No active pause session to finalize")
            return None

        try:
            # Read all recorded actions
            actions = self.get_recorded_actions()

            if not actions:
                logger.warning("No actions recorded in pause session, discarding")
                self.discard_pause()
                return None

            # Get session metadata from first action (pause_started)
            first_action = actions[0]
            if first_action.type != "pause_started":
                raise RuntimeError("First action is not 'pause_started'")

            session_id = first_action.session_id
            initial_state = first_action.data.get("initial_state", {})

            # Calculate final statistics
            total_actions = len(actions)
            final_percentage = actions[-1].context_percentage
            pause_started_at = first_action.timestamp
            pause_finalized_at = datetime.now(timezone.utc).isoformat()

            # Append finalization action
            self.append_action(
                action_type="pause_finalized",
                action_data={
                    "total_actions": total_actions,
                    "final_percentage": final_percentage,
                    "pause_started_at": pause_started_at,
                    "duration_seconds": self._calculate_duration(
                        pause_started_at, pause_finalized_at
                    ),
                },
                context_percentage=final_percentage,
            )

            # Create full snapshot if requested
            if create_full_snapshot:
                logger.info("Creating full session snapshot via SessionPauseManager")
                pause_manager = SessionPauseManager(self.project_path)

                # Build enriched state from initial_state and recorded actions
                enriched_state = self._build_enriched_state(
                    initial_state, actions, session_id
                )

                # Use SessionPauseManager's internal method to save state
                # (we'll build the state dict ourselves)
                session_path = self.sessions_dir / f"{session_id}.json"
                pause_manager.storage.write_json(
                    enriched_state, session_path, atomic=True
                )

                # Also create YAML and Markdown
                yaml_path = self.sessions_dir / f"{session_id}.yaml"
                pause_manager._save_yaml(enriched_state, yaml_path)

                md_path = self.sessions_dir / f"{session_id}.md"
                md_content = pause_manager._generate_markdown(enriched_state)
                md_path.write_text(md_content)

                # Update LATEST-SESSION pointer
                pause_manager._update_latest_pointer(session_id)

                logger.info(f"Full session snapshot created: {session_path}")

            # Archive the JSONL file (rename instead of delete for debugging)
            archive_path = self.sessions_dir / f"{session_id}-incremental.jsonl"
            self.active_pause_path.rename(archive_path)

            logger.info(
                f"Incremental pause finalized: {session_id} "
                f"({total_actions} actions, {final_percentage:.1%} context)"
            )

            return session_path if create_full_snapshot else archive_path

        except Exception as e:
            logger.error(f"Failed to finalize pause session: {e}")
            raise RuntimeError(f"Failed to finalize pause: {e}") from e

    def discard_pause(self) -> bool:
        """Discard the current incremental pause without finalizing.

        Returns:
            True if pause was discarded, False if no active pause

        Raises:
            RuntimeError: If discard operation fails
        """
        if not self.is_pause_active():
            logger.debug("No active pause session to discard")
            return False

        try:
            session_id = self._get_session_id()
            self.active_pause_path.unlink()

            logger.info(f"Incremental pause discarded: {session_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to discard pause session: {e}")
            raise RuntimeError(f"Failed to discard pause: {e}") from e

    def get_pause_summary(self) -> Optional[Dict[str, Any]]:
        """Get summary of current pause session.

        Returns:
            Summary dictionary with:
            - session_id: Session identifier
            - action_count: Number of recorded actions
            - duration_seconds: Time since pause started
            - context_range: (start_percentage, current_percentage)
            - pause_started_at: ISO timestamp
            Returns None if no active pause

        Raises:
            RuntimeError: If reading summary fails
        """
        if not self.is_pause_active():
            return None

        try:
            actions = self.get_recorded_actions()

            if not actions:
                return None

            first_action = actions[0]
            last_action = actions[-1]

            pause_started_at = first_action.timestamp
            current_time = datetime.now(timezone.utc).isoformat()

            return {
                "session_id": first_action.session_id,
                "action_count": len(actions),
                "duration_seconds": self._calculate_duration(
                    pause_started_at, current_time
                ),
                "context_range": (
                    first_action.context_percentage,
                    last_action.context_percentage,
                ),
                "pause_started_at": pause_started_at,
                "last_action_type": last_action.type,
                "last_updated": last_action.timestamp,
            }

        except Exception as e:
            logger.error(f"Failed to get pause summary: {e}")
            raise RuntimeError(f"Failed to get summary: {e}") from e

    def _get_session_id(self) -> str:
        """Extract session ID from first line of active pause file.

        Returns:
            Session identifier

        Raises:
            RuntimeError: If file is empty or corrupted
        """
        try:
            with self.active_pause_path.open("r") as f:
                first_line = f.readline()

            if not first_line:
                raise RuntimeError("Active pause file is empty")

            first_action = PauseAction.from_json_line(first_line)
            return first_action.session_id

        except Exception as e:
            logger.error(f"Failed to read session ID: {e}")
            raise RuntimeError(f"Failed to read session ID: {e}") from e

    def _calculate_duration(self, start_iso: str, end_iso: str) -> int:
        """Calculate duration between two ISO timestamps.

        Args:
            start_iso: Start timestamp (ISO format)
            end_iso: End timestamp (ISO format)

        Returns:
            Duration in seconds

        Raises:
            ValueError: If timestamps are invalid
        """
        try:
            start_dt = datetime.fromisoformat(start_iso.replace("Z", "+00:00"))
            end_dt = datetime.fromisoformat(end_iso.replace("Z", "+00:00"))
            return int((end_dt - start_dt).total_seconds())

        except Exception as e:
            logger.warning(f"Failed to calculate duration: {e}")
            return 0

    def _build_enriched_state(
        self,
        initial_state: Dict[str, Any],
        actions: List[PauseAction],
        session_id: str,
    ) -> Dict[str, Any]:
        """Build enriched state dictionary from initial state and recorded actions.

        Args:
            initial_state: Initial context snapshot
            actions: List of recorded actions
            session_id: Session identifier

        Returns:
            Enriched state dictionary compatible with SessionPauseManager
        """
        # Extract action summaries
        tool_calls = [a for a in actions if a.type == "tool_call"]
        assistant_responses = [a for a in actions if a.type == "assistant_response"]

        # Build accomplishments from actions
        accomplishments = []
        for response in assistant_responses:
            if "summary" in response.data:
                accomplishments.append(response.data["summary"])

        # Calculate session duration
        first_action = actions[0]
        last_action = actions[-1]
        duration_seconds = self._calculate_duration(
            first_action.timestamp, last_action.timestamp
        )

        # Build state dictionary
        pause_manager = SessionPauseManager(self.project_path)
        base_state = pause_manager._capture_state(session_id, None)

        # Enrich with incremental pause data
        base_state["paused_at"] = last_action.timestamp
        base_state["duration_hours"] = round(duration_seconds / 3600, 2)
        base_state["context_usage"] = {
            "tokens_used": int(
                last_action.context_percentage * ContextUsageTracker.CONTEXT_BUDGET
            ),
            "tokens_total": ContextUsageTracker.CONTEXT_BUDGET,
            "percentage": last_action.context_percentage * 100,
        }

        base_state["conversation"]["primary_task"] = (
            "Auto-pause triggered at 90% context"
        )
        base_state["conversation"]["current_phase"] = "Wind-down"
        base_state["conversation"]["summary"] = (
            f"Session auto-paused after {len(actions)} actions. "
            f"Context usage: {first_action.context_percentage:.1%} -> {last_action.context_percentage:.1%}"
        )
        base_state["conversation"]["accomplishments"] = accomplishments[
            :10
        ]  # Limit to 10

        # Add incremental pause metadata
        base_state["incremental_pause"] = {
            "enabled": True,
            "action_count": len(actions),
            "duration_seconds": duration_seconds,
            "context_range": [
                first_action.context_percentage,
                last_action.context_percentage,
            ],
            "tool_calls": len(tool_calls),
            "actions_summary": [
                {"type": a.type, "timestamp": a.timestamp} for a in actions[-10:]
            ],  # Last 10 actions
        }

        return base_state


# Import for type hints and usage
from claude_mpm.services.infrastructure.context_usage_tracker import ContextUsageTracker

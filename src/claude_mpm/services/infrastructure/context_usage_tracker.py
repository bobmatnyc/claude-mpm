"""Context Usage Tracker Service.

WHY: Track cumulative token usage across Claude Code hook invocations to prevent
context window exhaustion and enable intelligent auto-pause behavior.

DESIGN DECISIONS:
- File-based persistence (hooks run in separate processes)
- Atomic file operations using StateStorage
- Threshold detection at 70% (caution), 85% (warning), 90% (auto_pause), 95% (critical)
- Session-scoped tracking with reset capability
- Compatible with 200k context budget for Claude Sonnet 4.5

USAGE:
    tracker = ContextUsageTracker()
    state = tracker.update_usage(input_tokens=15000, output_tokens=2000)
    if tracker.should_auto_pause():
        # Trigger auto-pause workflow
        pass
"""

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from claude_mpm.core.logger import get_logger
from claude_mpm.storage.state_storage import StateStorage

logger = get_logger(__name__)


@dataclass
class ContextUsageState:
    """State tracking for cumulative context/token usage.

    Attributes:
        session_id: Unique session identifier
        cumulative_input_tokens: Total input tokens across all hook invocations
        cumulative_output_tokens: Total output tokens across all hook invocations
        cache_creation_tokens: Total tokens spent creating prompt cache
        cache_read_tokens: Total tokens read from prompt cache
        percentage_used: Percentage of 200k context budget used (0.0-100.0)
        threshold_reached: Highest threshold crossed ('caution', 'warning', 'auto_pause', 'critical')
        auto_pause_active: Whether auto-pause has been triggered
        last_updated: ISO timestamp of last update
    """

    session_id: str
    cumulative_input_tokens: int = 0
    cumulative_output_tokens: int = 0
    cache_creation_tokens: int = 0
    cache_read_tokens: int = 0
    percentage_used: float = 0.0
    threshold_reached: Optional[str] = None
    auto_pause_active: bool = False
    last_updated: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class ContextUsageTracker:
    """Track cumulative context/token usage across hook invocations.

    Features:
    - Cumulative tracking across multiple API calls
    - File-based persistence for cross-process state sharing
    - Atomic file operations for concurrent safety
    - Threshold detection (70%, 85%, 90%, 95%)
    - Auto-pause triggering at 90%+ usage
    - Session management with reset capability
    """

    # Claude Sonnet 4.5 context window
    CONTEXT_BUDGET = 200000

    # Threshold levels for warnings and auto-pause
    THRESHOLDS = {
        "caution": 0.70,  # Yellow warning
        "warning": 0.85,  # Orange warning
        "auto_pause": 0.90,  # Trigger auto-pause
        "critical": 0.95,  # Red critical alert
    }

    def __init__(self, project_path: Optional[Path] = None):
        """Initialize context usage tracker.

        Args:
            project_path: Project root path (default: current directory)
        """
        self.project_path = (project_path or Path.cwd()).resolve()
        self.state_dir = self.project_path / ".claude-mpm" / "state"
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.state_file = self.state_dir / "context-usage.json"

        # Use StateStorage for atomic operations
        self.storage = StateStorage(self.state_dir)

        logger.debug(f"ContextUsageTracker initialized: {self.state_file}")

    def update_usage(
        self,
        input_tokens: int,
        output_tokens: int,
        cache_creation: int = 0,
        cache_read: int = 0,
    ) -> ContextUsageState:
        """Update cumulative usage from API response.

        Args:
            input_tokens: Input tokens from this API call
            output_tokens: Output tokens from this API call
            cache_creation: Cache creation tokens (optional)
            cache_read: Cache read tokens (optional)

        Returns:
            Updated context usage state

        Raises:
            ValueError: If token counts are negative
        """
        if any(
            t < 0 for t in [input_tokens, output_tokens, cache_creation, cache_read]
        ):
            raise ValueError("Token counts cannot be negative")

        # Load current state
        state = self._load_state()

        # Update cumulative counters
        state.cumulative_input_tokens += input_tokens
        state.cumulative_output_tokens += output_tokens
        state.cache_creation_tokens += cache_creation
        state.cache_read_tokens += cache_read

        # Calculate total effective tokens (input + output, cache read is "free")
        total_tokens = state.cumulative_input_tokens + state.cumulative_output_tokens
        state.percentage_used = (total_tokens / self.CONTEXT_BUDGET) * 100

        # Check thresholds
        state.threshold_reached = self.check_thresholds(state)

        # Activate auto-pause if threshold reached
        if state.threshold_reached in {"auto_pause", "critical"}:
            state.auto_pause_active = True

        # Update timestamp
        state.last_updated = datetime.now(timezone.utc).isoformat()

        # Persist state atomically
        self._save_state(state)

        logger.debug(
            f"Usage updated: {total_tokens}/{self.CONTEXT_BUDGET} tokens "
            f"({state.percentage_used:.1f}%), threshold: {state.threshold_reached}"
        )

        return state

    def check_thresholds(
        self, state: Optional[ContextUsageState] = None
    ) -> Optional[str]:
        """Check which threshold (if any) has been exceeded.

        Args:
            state: Optional state to check (uses current state if None)

        Returns:
            Highest threshold exceeded ('caution', 'warning', 'auto_pause', 'critical')
            or None if no thresholds exceeded
        """
        if state is None:
            state = self.get_current_state()

        percentage = state.percentage_used / 100  # Convert to 0.0-1.0

        # Check thresholds in descending order (highest first)
        for threshold_name in ["critical", "auto_pause", "warning", "caution"]:
            if percentage >= self.THRESHOLDS[threshold_name]:
                return threshold_name

        return None

    def should_auto_pause(self) -> bool:
        """Check if auto-pause should be triggered.

        Returns:
            True if 90%+ context budget used
        """
        state = self.get_current_state()
        return state.percentage_used >= (self.THRESHOLDS["auto_pause"] * 100)

    def get_current_state(self) -> ContextUsageState:
        """Get current usage state without modifying.

        Returns:
            Current context usage state
        """
        return self._load_state()

    def reset_session(self, new_session_id: str) -> None:
        """Reset tracking for a new session.

        Args:
            new_session_id: New session identifier
        """
        state = ContextUsageState(session_id=new_session_id)
        self._save_state(state)
        logger.info(f"Context usage reset for new session: {new_session_id}")

    def _load_state(self) -> ContextUsageState:
        """Load state from persistence file.

        Returns:
            Loaded state or default state if file doesn't exist/is corrupted
        """
        try:
            if not self.state_file.exists():
                # Generate initial session ID
                session_id = (
                    f"session-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
                )
                logger.debug("No state file found, creating default state")
                return ContextUsageState(session_id=session_id)

            # Load JSON state
            data = self.storage.read_json(self.state_file)

            if data is None:
                logger.warning("Failed to read state file, using default state")
                session_id = (
                    f"session-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
                )
                return ContextUsageState(session_id=session_id)

            # Reconstruct ContextUsageState from dict
            return ContextUsageState(**data)

        except Exception as e:
            logger.error(f"Error loading state, using default: {e}")
            session_id = (
                f"session-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
            )
            return ContextUsageState(session_id=session_id)

    def _save_state(self, state: ContextUsageState) -> None:
        """Save state to persistence file atomically.

        Args:
            state: Context usage state to persist

        Raises:
            RuntimeError: If atomic write fails
        """
        try:
            # Convert dataclass to dict
            state_dict = asdict(state)

            # Atomic write using StateStorage
            if not self.storage.write_json(state_dict, self.state_file, atomic=True):
                raise RuntimeError(f"Failed to write state to {self.state_file}")

            logger.debug(f"State saved: {self.state_file}")

        except Exception as e:
            logger.error(f"Error saving state: {e}")
            raise RuntimeError(f"Failed to persist context usage state: {e}") from e

    def get_usage_summary(self) -> dict:
        """Get human-readable usage summary.

        Returns:
            Dictionary with usage statistics
        """
        state = self.get_current_state()
        total_tokens = state.cumulative_input_tokens + state.cumulative_output_tokens

        return {
            "session_id": state.session_id,
            "total_tokens": total_tokens,
            "budget": self.CONTEXT_BUDGET,
            "percentage_used": round(state.percentage_used, 2),
            "threshold_reached": state.threshold_reached,
            "auto_pause_active": state.auto_pause_active,
            "breakdown": {
                "input_tokens": state.cumulative_input_tokens,
                "output_tokens": state.cumulative_output_tokens,
                "cache_creation_tokens": state.cache_creation_tokens,
                "cache_read_tokens": state.cache_read_tokens,
            },
            "last_updated": state.last_updated,
        }

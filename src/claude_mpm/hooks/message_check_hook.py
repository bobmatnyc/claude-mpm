"""
Message Check Hook - Periodically checks for incoming messages.

WHY: Enables asynchronous cross-project communication by checking inbox on
predictable intervals without being intrusive.

TRIGGERS:
- Session start (always)
- Every 10 commands (command counter)
- Every 30 minutes (time-based)

DESIGN:
- Maintains state in .claude-mpm/message_check_state.json
- Injects message notifications into PM context
- Respects user configuration for thresholds
"""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Optional, Tuple

from ..core.logging_utils import get_logger
from ..services.communication.message_service import MessageService
from ..services.communication.task_injector import TaskInjector

logger = get_logger(__name__)


class MessageCheckState:
    """Manages state for message check hook."""

    def __init__(self, state_file: Path):
        """
        Initialize message check state.

        Args:
            state_file: Path to state JSON file
        """
        self.state_file = state_file
        self.state_file.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> Dict:
        """
        Load state from file.

        Returns:
            State dictionary with defaults if file doesn't exist
        """
        if not self.state_file.exists():
            return {
                "last_check": None,
                "command_count": 0,
                "session_start": datetime.now(timezone.utc).isoformat(),
            }

        try:
            return json.loads(self.state_file.read_text())
        except Exception as e:
            logger.warning(f"Failed to load message check state: {e}")
            return {
                "last_check": None,
                "command_count": 0,
                "session_start": datetime.now(timezone.utc).isoformat(),
            }

    def save(self, state: Dict) -> None:
        """
        Save state to file.

        Args:
            state: State dictionary to save
        """
        try:
            self.state_file.write_text(json.dumps(state, indent=2))
        except Exception as e:
            logger.warning(f"Failed to save message check state: {e}")

    def increment_command_count(self) -> int:
        """
        Increment command counter and save.

        Returns:
            New command count
        """
        state = self.load()
        state["command_count"] = state.get("command_count", 0) + 1
        self.save(state)
        return state["command_count"]

    def reset(self) -> None:
        """Reset state after check."""
        state = self.load()
        state["last_check"] = datetime.now(timezone.utc).isoformat()
        state["command_count"] = 0
        self.save(state)


def should_check_messages(
    state: Dict, command_threshold: int = 10, time_threshold_minutes: int = 30
) -> Tuple[bool, Optional[str]]:
    """
    Determine if we should check messages now.

    Args:
        state: Current state dictionary
        command_threshold: Check every N commands
        time_threshold_minutes: Check every N minutes

    Returns:
        (should_check, reason)
    """
    # Always check on session start (no last_check)
    if state.get("last_check") is None:
        return (True, "session_start")

    # Check command counter
    command_count = state.get("command_count", 0)
    if command_count >= command_threshold:
        return (True, "command_threshold")

    # Check time elapsed
    try:
        last_check = datetime.fromisoformat(state["last_check"])
        if datetime.now(timezone.utc) - last_check > timedelta(
            minutes=time_threshold_minutes
        ):
            return (True, "time_threshold")
    except (ValueError, KeyError) as e:
        logger.warning(f"Invalid last_check timestamp: {e}")
        return (True, "invalid_state")

    return (False, None)


def format_message_for_pm(msg) -> Dict:
    """
    Format a message for PM context.

    Args:
        msg: Message object

    Returns:
        Formatted message dict
    """
    from_project_name = Path(msg.from_project).name

    return {
        "id": msg.id,
        "from_agent": msg.from_agent,
        "from_project": from_project_name,
        "from_project_path": msg.from_project,
        "to_agent": msg.to_agent,
        "subject": msg.subject,
        "type": msg.type,
        "priority": msg.priority,
        "created_at": msg.created_at.isoformat(),
        "body_preview": msg.body[:200] + "..." if len(msg.body) > 200 else msg.body,
    }


def get_config() -> Dict:
    """
    Get messaging configuration from config.

    Returns:
        Configuration dict with defaults
    """
    try:
        from ..core.config import Config

        config = Config()
        messaging_config = config.data.get("messaging", {})

        return {
            "enabled": messaging_config.get("enabled", True),
            "check_on_startup": messaging_config.get("check_on_startup", True),
            "command_threshold": messaging_config.get("command_threshold", 10),
            "time_threshold": messaging_config.get("time_threshold", 30),
            "auto_create_tasks": messaging_config.get("auto_create_tasks", False),
            "notify_priority": messaging_config.get(
                "notify_priority", ["high", "urgent"]
            ),
        }
    except Exception as e:
        logger.warning(f"Failed to load messaging config, using defaults: {e}")
        return {
            "enabled": True,
            "check_on_startup": True,
            "command_threshold": 10,
            "time_threshold": 30,
            "auto_create_tasks": False,
            "notify_priority": ["high", "urgent"],
        }


def get_message_check_hook():
    """Factory function to get message check hook."""
    return message_check_hook


def message_check_hook() -> Optional[str]:
    """
    Hook that checks for unread messages and injects into PM context.

    Returns:
        Formatted message notification for PM, or None if no messages
    """
    try:
        # Get configuration
        config = get_config()

        if not config["enabled"]:
            return None

        # Get project root
        from ..core.unified_paths import UnifiedPathManager

        project_root = UnifiedPathManager().project_root

        # Initialize state
        state_file = project_root / ".claude-mpm" / "message_check_state.json"
        state_manager = MessageCheckState(state_file)

        # Load current state
        state = state_manager.load()

        # Determine if we should check
        should_check, reason = should_check_messages(
            state,
            command_threshold=config["command_threshold"],
            time_threshold_minutes=config["time_threshold"],
        )

        if not should_check:
            # Just increment counter
            state_manager.increment_command_count()
            return None

        logger.debug(f"Checking messages (reason: {reason})")

        # Reset state
        state_manager.reset()

        # Check for messages
        service = MessageService(project_root)
        unread = service.list_messages(status="unread")

        if not unread:
            return None

        # Task injection (if enabled)
        injected_count = 0
        if config.get("auto_create_tasks", False):
            injector = TaskInjector()
            task_priority_filter = set(
                config.get("notify_priority", ["high", "urgent"])
            )

            for msg in unread:
                # Skip if task already exists
                if injector.task_exists(msg.id):
                    continue

                # Check priority filter
                if msg.priority in task_priority_filter:
                    injector.inject_message_task(
                        message_id=msg.id,
                        from_project=msg.from_project,
                        subject=msg.subject,
                        body=msg.body,
                        priority=msg.priority,
                        from_agent=msg.from_agent,
                        message_type=msg.type,
                    )
                    injected_count += 1

        # Filter by priority if configured
        notify_priorities = set(config["notify_priority"])
        high_priority = [msg for msg in unread if msg.priority in notify_priorities]

        # Format notification
        notification_lines = []
        notification_lines.append("## 📬 Incoming Messages\n")

        if high_priority:
            notification_lines.append(
                f"**You have {len(unread)} unread message(s) ({len(high_priority)} high priority)**\n"
            )
        else:
            notification_lines.append(f"You have {len(unread)} unread message(s)\n")

        # Show details for high priority or all if few messages
        messages_to_show = high_priority if high_priority else unread[:3]

        for i, msg in enumerate(messages_to_show, 1):
            priority_emoji = {
                "urgent": "🔴",
                "high": "🟠",
                "normal": "🟡",
                "low": "🟢",
            }.get(msg.priority, "⚪")

            type_emoji = {
                "task": "📋",
                "request": "❓",
                "notification": "🔔",
                "reply": "💬",
            }.get(msg.type, "📨")

            from_project = Path(msg.from_project).name

            notification_lines.append(
                f"{i}. {priority_emoji} {type_emoji} **{msg.subject}** "
                f"from `{from_project}` ({msg.from_agent})\n"
            )
            notification_lines.append(f"   - To: {msg.to_agent}\n")
            notification_lines.append(f"   - Type: {msg.type}\n")
            notification_lines.append(f"   - Priority: {msg.priority}\n")
            notification_lines.append(f"   - ID: `{msg.id}`\n")

            # Show body preview for tasks
            if msg.type == "task":
                preview = msg.body[:150] + "..." if len(msg.body) > 150 else msg.body
                notification_lines.append(f"   - Preview: {preview}\n")

            notification_lines.append("\n")

        # Add action guidance
        notification_lines.append("**How to handle messages:**\n")
        notification_lines.append(
            "- Use `MessageService` from `claude_mpm.services.communication.message_service`\n"
        )
        notification_lines.append("- `read_message(message_id)` - Read full message\n")
        notification_lines.append(
            "- `reply_to_message(message_id, body)` - Send reply\n"
        )

        if injected_count > 0:
            notification_lines.append(
                f"\n**✅ {injected_count} message(s) added to task list.**\n"
            )
            notification_lines.append("Check with `TaskList` or `/tasks` command.\n")

        return "".join(notification_lines)

    except Exception as e:
        logger.error(f"Message check hook failed: {e}", exc_info=True)
        return None

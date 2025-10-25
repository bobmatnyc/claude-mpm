"""Instruction Reinforcement Hook for PM instruction drift prevention.

This module implements a hook that intercepts TodoWrite calls and injects
reminder messages at configurable intervals to combat PM instruction drift
during long conversations.

WHY this is needed:
- PM agents can drift from their original instructions during long sessions
- Direct tool usage (Edit, Write, Bash) is a common drift pattern
- Reminder injection via TodoWrite is a non-intrusive way to reinforce instructions
- Configurable intervals and message rotation provide flexibility

The hook works by:
1. Tracking TodoWrite call count
2. Injecting reminders at configured intervals (default: every 5 calls)
3. Rotating through multiple reminder messages
4. Providing metrics for monitoring effectiveness
"""

import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ..core.enums import OperationResult
from ..core.logger import get_logger


class InstructionReinforcementHook:
    """Hook for injecting instruction reminders into TodoWrite calls.

    This class intercepts TodoWrite operations and periodically injects
    reminder messages to help prevent PM instruction drift.

    Key features:
    - Configurable injection intervals
    - Message rotation for variety
    - Thread-safe operation
    - Metrics tracking
    - Test mode support
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the instruction reinforcement hook.

        Args:
            config: Configuration dictionary with optional keys:
                - enabled: Whether the hook is enabled (default: True)
                - test_mode: Whether to use test messages (default: True)
                - injection_interval: Calls between injections (default: 5)
                - test_messages: List of test messages to rotate through
        """
        self.logger = get_logger("instruction_reinforcement_hook")

        # Initialize configuration
        config = config or {}
        self.enabled = config.get("enabled", True)
        self.test_mode = config.get("test_mode", True)
        self.injection_interval = config.get("injection_interval", 5)

        # Thread-safe counters
        self._lock = threading.Lock()
        self.call_count = 0
        self.injection_count = 0
        self.message_index = 0

        # Default test messages (will be used in test_mode)
        self.test_messages = config.get(
            "test_messages",
            [
                "[TEST-REMINDER] This is an injected instruction reminder",
                "[PM-INSTRUCTION] Remember to delegate all work to agents",
                "[PM-INSTRUCTION] Do not use Edit, Write, or Bash tools directly",
                "[PM-INSTRUCTION] Your role is orchestration and coordination",
            ],
        )

        # Production messages (used when test_mode=False)
        self.production_messages = [
            "[STOP] Are you about to use Edit/Write/Bash? Delegate to Engineer instead!",
            "[DELEGATE] Your job is coordination, not implementation - pass this to an agent",
            "[REMINDER] PM = Project Manager, not Project Implementer - delegate this work",
            "[CHECK] If you're reading code files, stop and delegate to Research Agent",
            "[WARNING] Direct implementation detected - use 'do this yourself' to override",
        ]

        self.logger.info(
            f"InstructionReinforcementHook initialized: "
            f"enabled={self.enabled}, test_mode={self.test_mode}, "
            f"interval={self.injection_interval}"
        )

    def intercept_todowrite(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Intercept TodoWrite parameters and potentially inject reminders.

        Args:
            params: TodoWrite parameters dictionary containing 'todos' list

        Returns:
            Modified parameters with potentially injected reminders
        """
        if not self.enabled:
            return params

        try:
            # Extract todos safely
            todos = params.get("todos", [])
            if not isinstance(todos, list):
                self.logger.warning("Invalid todos format - skipping injection")
                return params

            with self._lock:
                self.call_count += 1

                # Check if we should inject
                if self.should_inject():
                    modified_todos = self.inject_reminders(todos)
                    params = params.copy()  # Don't modify original
                    params["todos"] = modified_todos
                    self.injection_count += 1

                    self.logger.info(
                        f"Injected reminder #{self.injection_count} at call #{self.call_count}"
                    )

            return params

        except Exception as e:
            self.logger.error(f"Error in TodoWrite interception: {e}")
            # Return original params on error to avoid breaking functionality
            return params

    def should_inject(self) -> bool:
        """Determine if a reminder should be injected.

        Returns:
            True if injection should occur
        """
        if not self.enabled:
            return False

        return self.call_count % self.injection_interval == 0

    def inject_reminders(self, todos: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Inject reminder message into todos list.

        Args:
            todos: Original todos list

        Returns:
            Modified todos list with reminder injected at the beginning
        """
        # Choose message set based on mode
        messages = self.test_messages if self.test_mode else self.production_messages

        # Get next message (rotate through available messages)
        message = messages[self.message_index % len(messages)]
        self.message_index += 1

        # Create reminder todo
        reminder_todo = {
            "content": message,
            "status": OperationResult.PENDING,
            "activeForm": "Processing instruction reminder",
        }

        # Insert at beginning of todos list
        modified_todos = todos.copy()
        modified_todos.insert(0, reminder_todo)

        self.logger.debug(f"Injected reminder: {message}")

        return modified_todos

    def get_metrics(self) -> Dict[str, Any]:
        """Get current hook metrics.

        Returns:
            Dictionary containing metrics:
            - call_count: Total TodoWrite calls processed
            - injection_count: Total reminders injected
            - injection_rate: Ratio of injections to calls
            - next_injection_in: Calls until next injection
            - enabled: Whether hook is enabled
            - test_mode: Whether using test messages
        """
        with self._lock:
            next_injection = self.injection_interval - (
                self.call_count % self.injection_interval
            )
            if next_injection == self.injection_interval:
                next_injection = 0  # Next call will trigger injection

            return {
                "call_count": self.call_count,
                "injection_count": self.injection_count,
                "injection_rate": self.injection_count / max(self.call_count, 1),
                "next_injection_in": next_injection,
                "enabled": self.enabled,
                "test_mode": self.test_mode,
                "injection_interval": self.injection_interval,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    def reset_counters(self):
        """Reset all counters to zero.

        Useful for testing or starting fresh tracking.
        """
        with self._lock:
            self.call_count = 0
            self.injection_count = 0
            self.message_index = 0

        self.logger.info("Reset instruction reinforcement counters")

    def update_config(self, config: Dict[str, Any]):
        """Update hook configuration.

        Args:
            config: New configuration values
        """
        if "enabled" in config:
            self.enabled = config["enabled"]
        if "test_mode" in config:
            self.test_mode = config["test_mode"]
        if "injection_interval" in config:
            self.injection_interval = max(1, config["injection_interval"])  # Minimum 1
        if "test_messages" in config:
            self.test_messages = config["test_messages"]

        self.logger.info(f"Updated configuration: {config}")


# Global instance for singleton pattern
_instruction_reinforcement_hook: Optional[InstructionReinforcementHook] = None
_hook_lock = threading.Lock()


def get_instruction_reinforcement_hook(
    config: Optional[Dict[str, Any]] = None,
) -> InstructionReinforcementHook:
    """Get the global instruction reinforcement hook instance.

    Args:
        config: Configuration for first-time initialization

    Returns:
        InstructionReinforcementHook instance
    """
    global _instruction_reinforcement_hook

    with _hook_lock:
        if _instruction_reinforcement_hook is None:
            _instruction_reinforcement_hook = InstructionReinforcementHook(config)

    return _instruction_reinforcement_hook


def reset_instruction_reinforcement_hook():
    """Reset the global hook instance.

    Primarily used for testing to ensure clean state.
    """
    global _instruction_reinforcement_hook

    with _hook_lock:
        _instruction_reinforcement_hook = None

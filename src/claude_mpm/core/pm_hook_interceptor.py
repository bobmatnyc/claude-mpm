"""PM Hook Interceptor for TodoWrite operations.

This module intercepts TodoWrite operations from the PM agent and ensures
that the appropriate hook events are triggered, making PM operations
consistent with regular agent operations in terms of event streaming.

WHY this is needed:
- PM agent runs directly in Python, bypassing Claude Code's hook system
- TodoWrite calls from PM should trigger the same hooks as agent TodoWrite calls
- Ensures consistent event streaming to Socket.IO dashboard
- Maintains compatibility with existing hook-based monitoring systems
"""

import functools
import threading
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ..core.hook_manager import get_hook_manager
from ..core.logger import get_logger
from .instruction_reinforcement_hook import get_instruction_reinforcement_hook


class PMHookInterceptor:
    """Interceptor for PM operations that ensures hook events are triggered.

    WHY this design:
    - Acts as a transparent proxy for tool operations
    - Automatically triggers pre/post hook events
    - Maintains session consistency with regular Claude Code operations
    - Provides real-time event streaming for PM operations
    """

    def __init__(self, instruction_reinforcement_config=None):
        self.logger = get_logger("pm_hook_interceptor")
        self.hook_manager = get_hook_manager()
        self._in_intercept = threading.local()  # Prevent recursion

        # Initialize instruction reinforcement hook
        self.instruction_reinforcement_hook = get_instruction_reinforcement_hook(
            instruction_reinforcement_config
        )

    def intercept_todowrite(self, original_function):
        """Decorator to intercept TodoWrite calls and trigger hooks.

        Args:
            original_function: The original TodoWrite function

        Returns:
            Wrapped function that triggers hooks
        """

        @functools.wraps(original_function)
        def wrapper(*args, **kwargs):
            # Prevent recursive interception
            if getattr(self._in_intercept, "active", False):
                return original_function(*args, **kwargs)

            self._in_intercept.active = True

            try:
                # Extract todos from arguments
                todos = self._extract_todos_from_args(args, kwargs)

                # Apply instruction reinforcement hook (modify parameters if needed)
                params = {"todos": todos}
                modified_params = (
                    self.instruction_reinforcement_hook.intercept_todowrite(params)
                )
                modified_todos = modified_params.get("todos", todos)

                # Update args/kwargs with potentially modified todos
                if modified_todos != todos:
                    args, kwargs = self._update_args_with_todos(
                        args, kwargs, modified_todos
                    )
                    self.logger.debug(
                        f"Applied instruction reinforcement: {len(modified_todos)} todos"
                    )

                # Trigger pre-tool hook
                self.hook_manager.trigger_pre_tool_hook(
                    "TodoWrite",
                    {"todos": modified_todos, "source": "PM", "intercepted": True},
                )

                # Call the original function with potentially modified arguments
                result = original_function(*args, **kwargs)

                # Trigger post-tool hook
                self.hook_manager.trigger_post_tool_hook(
                    "TodoWrite",
                    0,
                    {
                        "todos_count": len(modified_todos) if modified_todos else 0,
                        "original_todos_count": len(todos) if todos else 0,
                        "source": "PM",
                        "success": True,
                        "instruction_reinforcement_applied": len(modified_todos)
                        != len(todos),
                    },
                )

                self.logger.debug(
                    f"Successfully intercepted TodoWrite with {len(modified_todos) if modified_todos else 0} todos "
                    f"(original: {len(todos) if todos else 0})"
                )

                return result

            except Exception as e:
                # Trigger post-tool hook with error
                self.hook_manager.trigger_post_tool_hook(
                    "TodoWrite", 1, {"error": str(e), "source": "PM", "success": False}
                )

                self.logger.error(f"Error in TodoWrite interception: {e}")
                raise
            finally:
                self._in_intercept.active = False

        return wrapper

    def _extract_todos_from_args(self, args, kwargs) -> List[Dict[str, Any]]:
        """Extract todos from function arguments.

        Args:
            args: Positional arguments
            kwargs: Keyword arguments

        Returns:
            List of todo dictionaries
        """
        # Look for todos in kwargs first
        if "todos" in kwargs:
            return kwargs["todos"]

        # Look for todos in positional args
        for arg in args:
            if (
                isinstance(arg, list)
                and arg
                and isinstance(arg[0], dict)
                and ("content" in arg[0] or "id" in arg[0])
            ):
                return arg

        return []

    def _update_args_with_todos(
        self, args, kwargs, modified_todos: List[Dict[str, Any]]
    ):
        """Update function arguments with modified todos list.

        Args:
            args: Original positional arguments
            kwargs: Original keyword arguments
            modified_todos: Modified todos list to inject

        Returns:
            Tuple of (updated_args, updated_kwargs)
        """
        # Update kwargs if todos was passed as keyword argument
        if "todos" in kwargs:
            kwargs = kwargs.copy()
            kwargs["todos"] = modified_todos
            return args, kwargs

        # Update positional args if todos was passed positionally
        args_list = list(args)
        for i, arg in enumerate(args_list):
            if (
                isinstance(arg, list)
                and arg
                and isinstance(arg[0], dict)
                and ("content" in arg[0] or "id" in arg[0])
            ):
                args_list[i] = modified_todos
                return tuple(args_list), kwargs

        # If we can't find where todos was passed, add as keyword argument
        kwargs = kwargs.copy()
        kwargs["todos"] = modified_todos
        return args, kwargs

    def trigger_manual_todowrite_hooks(self, todos: List[Dict[str, Any]]):
        """Manually trigger TodoWrite hooks for given todos.

        This method can be called directly when TodoWrite operations
        are detected outside of function interception.

        Args:
            todos: List of todo dictionaries
        """
        try:
            # Trigger pre-tool hook
            success1 = self.hook_manager.trigger_pre_tool_hook(
                "TodoWrite",
                {
                    "todos": todos,
                    "source": "PM_Manual",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )

            # Small delay to ensure proper event ordering
            time.sleep(0.1)

            # Trigger post-tool hook
            success2 = self.hook_manager.trigger_post_tool_hook(
                "TodoWrite",
                0,
                {
                    "todos_count": len(todos),
                    "source": "PM_Manual",
                    "success": True,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )

            if success1 and success2:
                self.logger.info(
                    f"Manually triggered TodoWrite hooks for {len(todos)} todos"
                )
            else:
                self.logger.warning(
                    f"Hook triggering partially failed: pre={success1}, post={success2}"
                )

            return success1 and success2

        except Exception as e:
            self.logger.error(f"Error manually triggering TodoWrite hooks: {e}")
            return False

    def get_instruction_reinforcement_metrics(self) -> Dict[str, Any]:
        """Get metrics from the instruction reinforcement hook.

        Returns:
            Dictionary containing reinforcement metrics
        """
        return self.instruction_reinforcement_hook.get_metrics()

    def reset_instruction_reinforcement_counters(self):
        """Reset instruction reinforcement counters."""
        self.instruction_reinforcement_hook.reset_counters()
        self.logger.info("Reset instruction reinforcement counters via PM interceptor")


# Global instance
_pm_hook_interceptor: Optional[PMHookInterceptor] = None


def get_pm_hook_interceptor(instruction_reinforcement_config=None) -> PMHookInterceptor:
    """Get the global PM hook interceptor instance.

    Args:
        instruction_reinforcement_config: Configuration for instruction reinforcement hook
                                        (only used on first initialization)

    Returns:
        PMHookInterceptor instance
    """
    global _pm_hook_interceptor
    if _pm_hook_interceptor is None:
        _pm_hook_interceptor = PMHookInterceptor(instruction_reinforcement_config)
    return _pm_hook_interceptor


def trigger_pm_todowrite_hooks(todos: List[Dict[str, Any]]) -> bool:
    """Convenience function to trigger PM TodoWrite hooks.

    Args:
        todos: List of todo dictionaries

    Returns:
        bool: True if hooks were triggered successfully
    """
    interceptor = get_pm_hook_interceptor()
    return interceptor.trigger_manual_todowrite_hooks(todos)


def simulate_pm_todowrite_operation(todos: List[Dict[str, Any]]):
    """Simulate a PM TodoWrite operation with proper hook triggering.

    This function is useful for testing and for cases where we want to
    simulate a TodoWrite operation from the PM agent.

    Args:
        todos: List of todo dictionaries
    """
    interceptor = get_pm_hook_interceptor()

    # Log the operation
    logger = get_logger("pm_todowrite_simulation")
    logger.info(f"Simulating PM TodoWrite operation with {len(todos)} todos")

    # Trigger hooks
    interceptor.trigger_manual_todowrite_hooks(todos)

    # Log completion
    logger.info("PM TodoWrite simulation completed")


def get_instruction_reinforcement_metrics() -> Dict[str, Any]:
    """Get instruction reinforcement metrics from the global PM hook interceptor.

    Returns:
        Dictionary containing reinforcement metrics
    """
    interceptor = get_pm_hook_interceptor()
    return interceptor.get_instruction_reinforcement_metrics()


def reset_instruction_reinforcement_counters():
    """Reset instruction reinforcement counters in the global PM hook interceptor."""
    interceptor = get_pm_hook_interceptor()
    interceptor.reset_instruction_reinforcement_counters()

"""Hook service for managing pre and post delegation hooks.

WHY: The agent system needs a centralized way to manage hooks that can modify
behavior before and after agent delegation. This service provides a clean API
for registering, prioritizing, and executing hooks while handling errors gracefully.

DESIGN DECISION: We chose to have separate lists for pre/post delegation hooks
rather than a single list with type checking because:
- It's more performant (no filtering needed during execution)
- It's clearer in the API (register_pre_delegation_hook vs checking type)
- It prevents accidentally mixing hook types
"""

import time
from typing import Any, Dict, List, Optional

from claude_mpm.core.config import Config
from claude_mpm.core.interfaces import HookServiceInterface
from claude_mpm.core.logging_config import get_logger
from claude_mpm.hooks.base_hook import (
    BaseHook,
    HookContext,
    HookResult,
    PostDelegationHook,
    PreDelegationHook,
)


class HookService(HookServiceInterface):
    """Service for managing and executing hooks in the delegation workflow.

    WHY: Provides a centralized place to register and execute hooks, ensuring
    they run in the correct order and that failures in individual hooks don't
    break the entire delegation flow.

    DESIGN DECISION: We execute hooks even if previous ones fail because:
    - Hooks should be independent and not rely on each other
    - A logging hook failure shouldn't prevent memory hooks from running
    - We log all failures for debugging but keep the system resilient
    """

    def __init__(self, config: Optional[Config] = None):
        """Initialize the hook service.

        Args:
            config: Optional configuration object for controlling hook behavior
        """
        self.config = config or Config()
        self.logger = get_logger(__name__)

        # Separate lists for different hook types for performance
        self.pre_delegation_hooks: List[PreDelegationHook] = []
        self.post_delegation_hooks: List[PostDelegationHook] = []

        # Track execution statistics for monitoring
        self.stats = {
            "pre_delegation_executed": 0,
            "post_delegation_executed": 0,
            "errors": 0,
        }

    def register_hook(self, hook: BaseHook) -> bool:
        """Register a hook with the service.

        WHY: We need a way to add hooks dynamically, and we validate the hook
        type to ensure it goes into the correct execution list.

        Args:
            hook: The hook to register

        Returns:
            True if successfully registered, False otherwise
        """
        try:
            if isinstance(hook, PreDelegationHook):
                self.pre_delegation_hooks.append(hook)
                # Sort by priority (lower number = higher priority = executes first)
                self.pre_delegation_hooks.sort(key=lambda h: h.priority)
                self.logger.info(
                    f"Registered pre-delegation hook: {hook.name} (priority: {hook.priority})"
                )
                return True

            if isinstance(hook, PostDelegationHook):
                self.post_delegation_hooks.append(hook)
                # Sort by priority
                self.post_delegation_hooks.sort(key=lambda h: h.priority)
                self.logger.info(
                    f"Registered post-delegation hook: {hook.name} (priority: {hook.priority})"
                )
                return True

            self.logger.warning(
                f"Attempted to register unsupported hook type: {type(hook).__name__}"
            )
            return False

        except Exception as e:
            self.logger.error(f"Failed to register hook {hook.name}: {e}")
            return False

    def execute_pre_delegation_hooks(self, context: HookContext) -> HookResult:
        """Execute all pre-delegation hooks in priority order.

        WHY: Pre-delegation hooks need to modify the context before it's sent
        to the agent. Each hook can add or modify context data.

        DESIGN DECISION: We pass the context through all hooks sequentially,
        allowing each to modify it. This enables powerful composition patterns.

        Args:
            context: The HookContext to be processed by hooks

        Returns:
            HookResult containing the final processed data
        """
        # Check if hooks are enabled via config
        if not self._are_hooks_enabled("pre_delegation"):
            return HookResult(success=True, data=context.data, modified=False)

        # Create a working copy of the data to preserve original
        working_data = context.data.copy()

        executed_count = 0
        has_modifications = False

        for hook in self.pre_delegation_hooks:
            if not hook.enabled:
                self.logger.debug(f"Skipping disabled hook: {hook.name}")
                continue

            try:
                # Validate if hook should run
                if not hook.validate(context):
                    self.logger.debug(f"Hook {hook.name} validation failed, skipping")
                    continue

                # Create a hook context with the current working data
                hook_context = HookContext(
                    hook_type=context.hook_type,
                    data=working_data,
                    metadata=context.metadata,
                    timestamp=context.timestamp,
                    session_id=context.session_id,
                    user_id=context.user_id,
                )

                # Execute with timing
                start_time = time.time()
                result = hook.execute(hook_context)
                execution_time = (time.time() - start_time) * 1000  # ms

                if result.success:
                    if result.modified and result.data:
                        # Update working data with modified data
                        working_data.update(result.data)
                        has_modifications = True
                        self.logger.debug(f"Hook {hook.name} modified context")

                    self.logger.info(
                        f"Executed pre-delegation hook {hook.name} "
                        f"(took {execution_time:.2f}ms)"
                    )
                else:
                    self.logger.warning(f"Hook {hook.name} failed: {result.error}")
                    self.stats["errors"] += 1

                executed_count += 1

            except Exception as e:
                # Log error but continue with other hooks
                self.logger.error(f"Exception in hook {hook.name}: {e}", exc_info=True)
                self.stats["errors"] += 1

        self.stats["pre_delegation_executed"] += executed_count
        self.logger.info(f"Executed {executed_count} pre-delegation hooks")

        return HookResult(success=True, data=working_data, modified=has_modifications)

    def execute_post_delegation_hooks(self, context: HookContext) -> HookResult:
        """Execute all post-delegation hooks in priority order.

        WHY: Post-delegation hooks need to process agent results, extract learnings,
        log outcomes, or perform other post-processing tasks.

        Args:
            context: The HookContext containing delegation results

        Returns:
            HookResult containing the final processed data
        """
        # Check if hooks are enabled via config
        if not self._are_hooks_enabled("post_delegation"):
            return HookResult(success=True, data=context.data, modified=False)

        # Create a working copy of the data to preserve original
        working_data = context.data.copy()

        executed_count = 0
        has_modifications = False

        for hook in self.post_delegation_hooks:
            if not hook.enabled:
                self.logger.debug(f"Skipping disabled hook: {hook.name}")
                continue

            try:
                # Validate if hook should run
                if not hook.validate(context):
                    self.logger.debug(f"Hook {hook.name} validation failed, skipping")
                    continue

                # Create a hook context with the current working data
                hook_context = HookContext(
                    hook_type=context.hook_type,
                    data=working_data,
                    metadata=context.metadata,
                    timestamp=context.timestamp,
                    session_id=context.session_id,
                    user_id=context.user_id,
                )

                # Execute with timing
                start_time = time.time()
                result = hook.execute(hook_context)
                execution_time = (time.time() - start_time) * 1000  # ms

                if result.success:
                    if result.modified and result.data:
                        # Update working data with modified data
                        working_data.update(result.data)
                        has_modifications = True
                        self.logger.debug(f"Hook {hook.name} modified context")

                    self.logger.info(
                        f"Executed post-delegation hook {hook.name} "
                        f"(took {execution_time:.2f}ms)"
                    )
                else:
                    self.logger.warning(f"Hook {hook.name} failed: {result.error}")
                    self.stats["errors"] += 1

                executed_count += 1

            except Exception as e:
                # Log error but continue with other hooks
                self.logger.error(f"Exception in hook {hook.name}: {e}", exc_info=True)
                self.stats["errors"] += 1

        self.stats["post_delegation_executed"] += executed_count
        self.logger.info(f"Executed {executed_count} post-delegation hooks")

        return HookResult(success=True, data=working_data, modified=has_modifications)

    def _are_hooks_enabled(self, hook_type: str) -> bool:
        """Check if hooks are enabled in configuration.

        WHY: We need fine-grained control over hook execution. This allows
        disabling hooks for debugging or in specific environments.

        Args:
            hook_type: Type of hooks to check (pre_delegation, post_delegation)

        Returns:
            True if hooks are enabled
        """
        # Check global hook enable flag
        if not self.config.get("hooks.enabled", True):
            self.logger.debug("All hooks disabled via configuration")
            return False

        # Check specific hook type enable flag
        if not self.config.get(f"hooks.{hook_type}.enabled", True):
            self.logger.debug(f"{hook_type} hooks disabled via configuration")
            return False

        # Special check for memory hooks if they depend on memory system
        if hook_type in ["pre_delegation", "post_delegation"]:
            # If any registered hooks are memory-related, check memory.enabled
            for hook in getattr(self, f"{hook_type}_hooks", []):
                if "memory" in hook.name.lower():
                    if not self.config.get("memory.enabled", True):
                        self.logger.debug(
                            "Memory hooks disabled via memory.enabled config"
                        )
                        return False

        return True

    def get_stats(self) -> Dict[str, int]:
        """Get execution statistics.

        WHY: Monitoring hook execution helps identify performance issues
        and debug problems in production.

        Returns:
            Dictionary of execution statistics
        """
        return self.stats.copy()

    def reset_stats(self):
        """Reset execution statistics.

        WHY: Allows periodic cleanup of stats for long-running services.
        """
        self.stats = {
            "pre_delegation_executed": 0,
            "post_delegation_executed": 0,
            "errors": 0,
        }

    def list_hooks(self) -> Dict[str, List[str]]:
        """List all registered hooks by type.

        WHY: Useful for debugging and understanding what hooks are active.

        Returns:
            Dictionary mapping hook type to list of hook names
        """
        return {
            "pre_delegation": [h.name for h in self.pre_delegation_hooks],
            "post_delegation": [h.name for h in self.post_delegation_hooks],
        }

    def remove_hook(self, hook_name: str) -> bool:
        """Remove a hook by name.

        WHY: Allows dynamic hook management, useful for testing or
        conditional hook usage.

        Args:
            hook_name: Name of the hook to remove

        Returns:
            True if hook was found and removed
        """
        # Check pre-delegation hooks
        for i, hook in enumerate(self.pre_delegation_hooks):
            if hook.name == hook_name:
                self.pre_delegation_hooks.pop(i)
                self.logger.info(f"Removed pre-delegation hook: {hook_name}")
                return True

        # Check post-delegation hooks
        for i, hook in enumerate(self.post_delegation_hooks):
            if hook.name == hook_name:
                self.post_delegation_hooks.pop(i)
                self.logger.info(f"Removed post-delegation hook: {hook_name}")
                return True

        self.logger.warning(f"Hook not found: {hook_name}")
        return False

    # ================================================================================
    # Interface Adapter Methods
    # ================================================================================
    # These methods are added to comply with HookServiceInterface

    def get_registered_hooks(self) -> Dict[str, List[Any]]:
        """Get all registered hooks by type.

        WHY: This method provides interface compliance by exposing the
        registered hooks for inspection and debugging purposes.

        Returns:
            Dictionary mapping hook types to lists of hooks
        """
        return {
            "pre_delegation": [
                {
                    "name": hook.name,
                    "priority": hook.priority,
                    "enabled": hook.enabled,
                    "type": "pre_delegation",
                }
                for hook in self.pre_delegation_hooks
            ],
            "post_delegation": [
                {
                    "name": hook.name,
                    "priority": hook.priority,
                    "enabled": hook.enabled,
                    "type": "post_delegation",
                }
                for hook in self.post_delegation_hooks
            ],
        }

    def clear_hooks(self, hook_type: Optional[str] = None) -> None:
        """Clear registered hooks.

        WHY: This method provides interface compliance by allowing bulk
        removal of hooks, useful for testing and cleanup scenarios.

        Args:
            hook_type: Optional specific hook type to clear, or None for all
        """
        if hook_type is None or hook_type == "pre_delegation":
            count = len(self.pre_delegation_hooks)
            self.pre_delegation_hooks.clear()
            if count > 0:
                self.logger.info(f"Cleared {count} pre-delegation hooks")

        if hook_type is None or hook_type == "post_delegation":
            count = len(self.post_delegation_hooks)
            self.post_delegation_hooks.clear()
            if count > 0:
                self.logger.info(f"Cleared {count} post-delegation hooks")

        if hook_type and hook_type not in ["pre_delegation", "post_delegation"]:
            self.logger.warning(f"Unknown hook type: {hook_type}")

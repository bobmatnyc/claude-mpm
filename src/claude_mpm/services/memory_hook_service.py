"""Memory hook service for registering memory-related hooks.

This service handles:
1. Memory hook registration with the hook service
2. Memory management integration
3. Hook lifecycle management

Extracted from ClaudeRunner to follow Single Responsibility Principle.
"""

from typing import Any, Dict

from claude_mpm.core.base_service import BaseService
from claude_mpm.services.core.interfaces import MemoryHookInterface


class MemoryHookService(BaseService, MemoryHookInterface):
    """Service for managing memory-related hooks."""

    def __init__(self, hook_service=None):
        """Initialize the memory hook service.

        Args:
            hook_service: Hook service for registering hooks
        """
        super().__init__(name="memory_hook_service")
        self.hook_service = hook_service
        self.registered_hooks = []  # Track registered hook IDs

    async def _initialize(self) -> None:
        """Initialize the service. No special initialization needed."""

    async def _cleanup(self) -> None:
        """Cleanup service resources. No cleanup needed."""

    def register_memory_hooks(self):
        """Register memory-related hooks with the hook service.

        WHY: Memory management is a cross-cutting concern that needs to be
        integrated at various points in the Claude interaction lifecycle.
        These hooks ensure memory is properly managed and persisted.

        DESIGN DECISION: We register hooks for key lifecycle events:
        - Before Claude interaction: Load relevant memories
        - After Claude interaction: Save new memories
        - On error: Ensure memory state is preserved
        """
        if not self.hook_service:
            self.logger.debug(
                "Hook service not available, skipping memory hook registration"
            )
            return

        try:
            # Create hook objects for the actual HookService interface
            from claude_mpm.hooks.base_hook import (
                HookContext,
                HookResult,
                PostDelegationHook,
                PreDelegationHook,
            )

            # Create memory loading hook
            class MemoryLoadHook(PreDelegationHook):
                def __init__(self, memory_service):
                    super().__init__(name="memory_load", priority=10)
                    self.memory_service = memory_service

                def execute(self, context: HookContext) -> HookResult:
                    return self.memory_service._load_relevant_memories_hook(context)

            # Create memory saving hook
            class MemorySaveHook(PostDelegationHook):
                def __init__(self, memory_service):
                    super().__init__(name="memory_save", priority=90)
                    self.memory_service = memory_service

                def execute(self, context: HookContext) -> HookResult:
                    return self.memory_service._save_new_memories_hook(context)

            # Register the hook objects
            load_hook = MemoryLoadHook(self)
            save_hook = MemorySaveHook(self)

            success1 = self.hook_service.register_hook(load_hook)
            success2 = self.hook_service.register_hook(save_hook)

            if success1:
                self.registered_hooks.append("memory_load")
            if success2:
                self.registered_hooks.append("memory_save")

            self.logger.debug("Memory hooks registered successfully")

        except Exception as e:
            self.logger.warning(f"Failed to register memory hooks: {e}")

    def _load_relevant_memories_hook(self, context):
        """Hook function to load relevant memories before Claude interaction.

        Args:
            context: Hook context containing interaction details

        Returns:
            HookResult with success status and any modifications
        """
        try:
            # This would integrate with a memory service to load relevant memories
            # For now, this is a placeholder for future memory integration
            self.logger.debug("Loading relevant memories for interaction")

            # Example: Load memories based on context
            # if hasattr(context, 'prompt'):
            #     relevant_memories = memory_service.search_memories(context.prompt)
            #     context.memories = relevant_memories

            from claude_mpm.hooks.base_hook import HookResult

            return HookResult(success=True, data=context.data, modified=False)

        except Exception as e:
            self.logger.warning(f"Failed to load memories: {e}")
            from claude_mpm.hooks.base_hook import HookResult

            return HookResult(
                success=False, data=context.data, modified=False, error=str(e)
            )

    def _load_relevant_memories(self, context):
        """Legacy hook function for backward compatibility."""
        result = self._load_relevant_memories_hook(context)
        return result.data

    def _save_new_memories_hook(self, context):
        """Hook function to save new memories after Claude interaction.

        Args:
            context: Hook context containing interaction results

        Returns:
            HookResult with success status and any modifications
        """
        try:
            from claude_mpm.hooks.base_hook import HookResult

            # Extract agent_id and response from context
            agent_id = None
            response_text = None

            # Try to get agent_id from various possible locations in context
            if hasattr(context, "data") and context.data:
                data = context.data

                # Check for agent_id in various locations
                if isinstance(data, dict):
                    # Try direct agent_id field
                    agent_id = data.get("agent_id")

                    # Try agent_type field
                    if not agent_id:
                        agent_id = data.get("agent_type")

                    # Try subagent_type (for Task delegations)
                    if not agent_id:
                        agent_id = data.get("subagent_type")

                    # Try tool_parameters for Task delegations
                    if not agent_id and "tool_parameters" in data:
                        params = data.get("tool_parameters", {})
                        if isinstance(params, dict):
                            agent_id = params.get("subagent_type")

                    # Extract response text
                    response_text = (
                        data.get("response") or data.get("result") or data.get("output")
                    )

                    # If response_text is a dict, try to get text from it
                    if isinstance(response_text, dict):
                        response_text = (
                            response_text.get("text")
                            or response_text.get("content")
                            or str(response_text)
                        )

            # Default to PM if no agent_id found
            if not agent_id:
                agent_id = "PM"
                self.logger.debug("No agent_id found in context, defaulting to PM")

            # Only process if we have response text
            if response_text and isinstance(response_text, str):
                self.logger.debug(f"Processing memory extraction for agent: {agent_id}")

                # Import and use the memory manager
                from claude_mpm.services.agents.memory.agent_memory_manager import (
                    get_memory_manager,
                )

                try:
                    memory_manager = get_memory_manager()

                    # Extract and update memory
                    success = memory_manager.extract_and_update_memory(
                        agent_id, response_text
                    )

                    if success:
                        self.logger.info(
                            f"Successfully extracted and saved memories for {agent_id}"
                        )
                    else:
                        self.logger.debug(
                            f"No memories found to extract for {agent_id}"
                        )

                except Exception as mem_error:
                    self.logger.warning(
                        f"Failed to extract/save memories for {agent_id}: {mem_error}"
                    )
            else:
                self.logger.debug(
                    "No response text found in context for memory extraction"
                )

            return HookResult(success=True, data=context.data, modified=False)

        except Exception as e:
            self.logger.warning(f"Failed to save memories: {e}")
            from claude_mpm.hooks.base_hook import HookResult

            return HookResult(
                success=False, data=context.data, modified=False, error=str(e)
            )

    def _save_new_memories(self, context):
        """Legacy hook function for backward compatibility."""
        result = self._save_new_memories_hook(context)
        return result.data

    def _preserve_memory_state(self, context):
        """Hook function to preserve memory state on interaction error.

        Args:
            context: Hook context containing error details
        """
        try:
            # This would ensure memory state is preserved even if interaction fails
            self.logger.debug("Preserving memory state after error")

        except Exception as e:
            self.logger.warning(f"Failed to preserve memory state: {e}")

    def unregister_memory_hooks(self):
        """Unregister memory-related hooks from the hook service."""
        if not self.hook_service:
            return

        try:
            self.hook_service.unregister_hook(
                "before_claude_interaction", self._load_relevant_memories
            )
            self.hook_service.unregister_hook(
                "after_claude_interaction", self._save_new_memories
            )
            self.hook_service.unregister_hook(
                "on_interaction_error", self._preserve_memory_state
            )

            self.logger.debug("Memory hooks unregistered successfully")

        except Exception as e:
            self.logger.warning(f"Failed to unregister memory hooks: {e}")

    def is_memory_enabled(self) -> bool:
        """Check if memory functionality is enabled.

        Returns:
            bool: True if memory is enabled and available
        """
        # This would check if memory service is available and configured
        # For now, return False as memory is not yet implemented
        return False

    def get_memory_status(self) -> dict:
        """Get current memory system status.

        Returns:
            dict: Memory system status information
        """
        return {
            "enabled": self.is_memory_enabled(),
            "hooks_registered": self.hook_service is not None,
            "service_available": True,
        }

    def get_hook_status(self) -> Dict[str, Any]:
        """Get status of registered memory hooks.

        Returns:
            Dictionary with hook status information
        """
        return {
            "registered_hooks": self.registered_hooks,
            "hook_service_available": self.hook_service is not None,
            "memory_enabled": self.is_memory_enabled(),
            "total_hooks": len(self.registered_hooks),
            "status": "active" if self.registered_hooks else "inactive",
        }

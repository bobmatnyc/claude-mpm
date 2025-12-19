#!/usr/bin/env python3
"""Memory integration utilities for Claude Code hook handler.

This module provides utilities for integrating with the memory system,
including pre and post delegation hooks.
"""

import logging
import os
import sys

# Install-type-aware logging configuration BEFORE kuzu-memory imports
# This overrides kuzu-memory's WARNING-level basicConfig (fixes 1M-445)
# but respects production install silence
try:
    from claude_mpm.core.unified_paths import DeploymentContext, PathContext

    context = PathContext.detect_deployment_context()

    # Only configure verbose logging for development/editable installs
    # Production installs remain silent by default
    if context in (DeploymentContext.DEVELOPMENT, DeploymentContext.EDITABLE_INSTALL):
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            force=True,  # Python 3.8+ - reconfigures root logger
            stream=sys.stderr,
        )
except ImportError:
    # Fallback: if unified_paths not available, configure logging
    # This maintains backward compatibility
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        force=True,
        stream=sys.stderr,
    )
from datetime import datetime, timezone
from typing import Optional

# Debug mode
DEBUG = os.environ.get("CLAUDE_MPM_HOOK_DEBUG", "true").lower() != "false"

# Memory hooks integration
MEMORY_HOOKS_AVAILABLE = False
try:
    # Use centralized path management for adding src to path
    from claude_mpm.config.paths import paths

    paths.ensure_in_path()

    from claude_mpm.core.shared.config_loader import ConfigLoader
    from claude_mpm.hooks.base_hook import HookContext, HookType
    from claude_mpm.hooks.memory_integration_hook import (
        MemoryPostDelegationHook,
        MemoryPreDelegationHook,
    )

    MEMORY_HOOKS_AVAILABLE = True
except Exception as e:
    # Catch all exceptions to prevent any import errors from breaking the handler
    if DEBUG:
        print(f"Memory hooks not available: {e}", file=sys.stderr)
    MEMORY_HOOKS_AVAILABLE = False


class MemoryHookManager:
    """Manager for memory hook integration."""

    def __init__(self):
        self.memory_hooks_initialized = False
        self.pre_delegation_hook: Optional[MemoryPreDelegationHook] = None
        self.post_delegation_hook: Optional[MemoryPostDelegationHook] = None

        if MEMORY_HOOKS_AVAILABLE:
            self._initialize_memory_hooks()

    def _initialize_memory_hooks(self):
        """Initialize memory hooks for automatic agent memory management.

        WHY: This activates the memory system by connecting Claude Code hook events
        to our memory integration hooks. This enables automatic memory injection
        before delegations and learning extraction after delegations.

        DESIGN DECISION: We initialize hooks here in the Claude hook handler because
        this is where Claude Code events are processed. This ensures memory hooks
        are triggered at the right times during agent delegation.
        """
        try:
            # Create configuration using ConfigLoader
            config_loader = ConfigLoader()
            config = config_loader.load_main_config()

            # Only initialize if memory system is enabled
            if not config.get("memory.enabled", True):
                if DEBUG:
                    print(
                        "Memory system disabled - skipping hook initialization",
                        file=sys.stderr,
                    )
                return

            # Initialize pre-delegation hook for memory injection
            self.pre_delegation_hook = MemoryPreDelegationHook(config)

            # Initialize post-delegation hook if auto-learning is enabled
            if config.get("memory.auto_learning", True):  # Default to True now
                self.post_delegation_hook = MemoryPostDelegationHook(config)

            self.memory_hooks_initialized = True

            if DEBUG:
                hooks_info = []
                if self.pre_delegation_hook:
                    hooks_info.append("pre-delegation")
                if self.post_delegation_hook:
                    hooks_info.append("post-delegation")
                print(
                    f"✅ Memory hooks initialized: {', '.join(hooks_info)}",
                    file=sys.stderr,
                )

        except Exception as e:
            if DEBUG:
                print(f"❌ Failed to initialize memory hooks: {e}", file=sys.stderr)
            # Don't fail the entire handler - memory system is optional

    def trigger_pre_delegation_hook(
        self, agent_type: str, tool_input: dict, session_id: str
    ):
        """Trigger memory pre-delegation hook for agent memory injection.

        WHY: This connects Claude Code's Task delegation events to our memory system.
        When Claude is about to delegate to an agent, we inject the agent's memory
        into the delegation context so the agent has access to accumulated knowledge.

        DESIGN DECISION: We modify the tool_input in place to inject memory context.
        This ensures the agent receives the memory as part of their initial context.
        """
        if not self.memory_hooks_initialized or not self.pre_delegation_hook:
            return

        try:
            # Create hook context for memory injection
            hook_context = HookContext(
                hook_type=HookType.PRE_DELEGATION,
                data={
                    "agent": agent_type,
                    "context": tool_input,
                    "session_id": session_id,
                },
                metadata={"source": "claude_hook_handler", "tool_name": "Task"},
                timestamp=datetime.now(timezone.utc).isoformat(),
                session_id=session_id,
            )

            # Execute pre-delegation hook
            result = self.pre_delegation_hook.execute(hook_context)

            if result.success and result.modified and result.data:
                # Update tool_input with memory-enhanced context
                enhanced_context = result.data.get("context", {})
                if enhanced_context and "agent_memory" in enhanced_context:
                    # Inject memory into the task prompt/description
                    original_prompt = tool_input.get("prompt", "")
                    memory_section = enhanced_context["agent_memory"]

                    # Prepend memory to the original prompt
                    enhanced_prompt = f"{memory_section}\n\n{original_prompt}"
                    tool_input["prompt"] = enhanced_prompt

                    if DEBUG:
                        memory_size = len(memory_section.encode("utf-8"))
                        print(
                            f"✅ Injected {memory_size} bytes of memory for agent '{agent_type}'",
                            file=sys.stderr,
                        )

        except Exception as e:
            if DEBUG:
                print(f"❌ Memory pre-delegation hook failed: {e}", file=sys.stderr)
            # Don't fail the delegation - memory is optional

    def trigger_post_delegation_hook(
        self, agent_type: str, event: dict, session_id: str
    ):
        """Trigger memory post-delegation hook for learning extraction.

        WHY: This connects Claude Code's Task completion events to our memory system.
        When an agent completes a task, we extract learnings from the result and
        store them in the agent's memory for future use.

        DESIGN DECISION: We extract learnings from both the tool output and any
        error messages, providing comprehensive context for the memory system.
        """
        if not self.memory_hooks_initialized or not self.post_delegation_hook:
            return

        try:
            # Extract result content from the event
            result_content = ""
            output = event.get("output", "")
            error = event.get("error", "")
            exit_code = event.get("exit_code", 0)

            # Build result content
            if output:
                result_content = str(output)
            elif error:
                result_content = f"Error: {error!s}"
            else:
                result_content = f"Task completed with exit code: {exit_code}"

            # Create hook context for learning extraction
            hook_context = HookContext(
                hook_type=HookType.POST_DELEGATION,
                data={
                    "agent": agent_type,
                    "result": {
                        "content": result_content,
                        "success": exit_code == 0,
                        "exit_code": exit_code,
                    },
                    "session_id": session_id,
                },
                metadata={
                    "source": "claude_hook_handler",
                    "tool_name": "Task",
                    "duration_ms": event.get("duration_ms", 0),
                },
                timestamp=datetime.now(timezone.utc).isoformat(),
                session_id=session_id,
            )

            # Execute post-delegation hook
            result = self.post_delegation_hook.execute(hook_context)

            if result.success and result.metadata:
                learnings_extracted = result.metadata.get("learnings_extracted", 0)
                if learnings_extracted > 0 and DEBUG:
                    print(
                        f"✅ Extracted {learnings_extracted} learnings for agent '{agent_type}'",
                        file=sys.stderr,
                    )

        except Exception as e:
            if DEBUG:
                print(f"❌ Memory post-delegation hook failed: {e}", file=sys.stderr)
            # Don't fail the delegation result - memory is optional

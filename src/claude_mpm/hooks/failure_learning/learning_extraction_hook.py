#!/usr/bin/env python3
"""
Learning Extraction Hook
=========================

Synthesizes learnings from failure-fix pairs and writes them to agent memory.

WHY: The final step in the failure-learning cycle is extracting actionable
learnings and persisting them to agent memory files. This hook completes the
cycle by taking failure-fix pairs and creating formatted learning entries.

DESIGN DECISION: This hook runs last (priority=89) after both failure and fix
detection. It uses template-based synthesis for MVP (no AI) and integrates
with AgentMemoryManager to write learnings to the appropriate memory files.

Integration points:
- Monitors for fix_detected metadata from FixDetectionHook
- Extracts learnings using FailureTracker
- Formats learnings as markdown
- Writes to agent memory files via AgentMemoryManager
"""

import logging
from typing import Any

from claude_mpm.hooks.base_hook import BaseHook, HookContext, HookResult, HookType
from claude_mpm.services.memory.failure_tracker import get_failure_tracker

logger = logging.getLogger(__name__)


class LearningExtractionHook(BaseHook):
    """Hook that extracts and persists learnings from failure-fix pairs.

    WHY: Automatically converts failure-fix pairs into persistent learnings
    stored in agent memory files. This completes the failure-learning cycle
    without requiring manual intervention.

    DESIGN DECISION: Priority 89 ensures this runs last in the chain:
    1. Failure detection (85) - detects failures
    2. Fix detection (87) - matches fixes with failures
    3. Learning extraction (89) - creates and persists learnings

    MVP uses template-based learning synthesis. Future versions could use
    AI to analyze git diffs, code changes, and generate richer learnings.
    """

    def __init__(self):
        """Initialize the learning extraction hook."""
        super().__init__(
            name="learning_extraction",
            priority=89,  # Last in the chain, after fix detection
        )
        self.tracker = get_failure_tracker()
        self._memory_manager = None

    @property
    def memory_manager(self):
        """Lazy-load memory manager to avoid circular imports.

        WHY: AgentMemoryManager may import hooks, so we lazy-load to prevent
        circular dependency issues.

        Returns:
            AgentMemoryManager instance
        """
        if self._memory_manager is None:
            try:
                from claude_mpm.services.agents.memory.agent_memory_manager import (
                    get_memory_manager,
                )

                self._memory_manager = get_memory_manager()
            except ImportError as e:
                logger.error(f"Failed to import AgentMemoryManager: {e}")
                raise

        return self._memory_manager

    def execute(self, context: HookContext) -> HookResult:
        """Execute learning extraction from failure-fix pairs.

        WHY: When a fix is detected, we have everything needed to extract a
        learning: the original failure, the fix that resolved it, and the
        context. This method synthesizes a learning and writes it to memory.

        Args:
            context: Hook context containing fix detection metadata

        Returns:
            HookResult with extraction results
        """
        try:
            # Check if this is a fix detection event
            metadata = context.metadata or {}
            if not metadata.get("fix_detected"):
                # Not a fix event, skip
                return HookResult(success=True, modified=False)

            # Extract failure and fix events from metadata
            failure_event = metadata.get("failure_event")
            fix_event = metadata.get("fix_event")

            if not failure_event or not fix_event:
                logger.warning("Fix detected but failure/fix events not in metadata")
                return HookResult(success=True, modified=False)

            # Extract learning from failure-fix pair
            learning = self.tracker.extract_learning(
                fix_event=fix_event,
                failure_event=failure_event,
                target_agent=self._determine_target_agent(context, failure_event),
            )

            # Format learning as markdown
            learning_markdown = learning.to_markdown()

            # Write to agent memory
            success = self._write_to_memory(
                agent_id=learning.target_agent, learning_text=learning_markdown
            )

            if success:
                logger.info(
                    f"Learning extracted and saved for {learning.target_agent}: "
                    f"{learning.category}"
                )
                return HookResult(
                    success=True,
                    modified=False,
                    metadata={
                        "learning_extracted": True,
                        "target_agent": learning.target_agent,
                        "learning_category": learning.category,
                    },
                )
            logger.warning(
                f"Failed to write learning to memory for {learning.target_agent}"
            )
            return HookResult(
                success=True,  # Don't fail the hook, just log warning
                modified=False,
                metadata={"learning_extracted": False},
            )

        except Exception as e:
            logger.error(f"Error in learning extraction hook: {e}", exc_info=True)
            return HookResult(success=False, error=str(e), modified=False)

    def validate(self, context: HookContext) -> bool:
        """Validate if this hook should run for the given context.

        Args:
            context: Hook context to validate

        Returns:
            True if hook should execute
        """
        if not super().validate(context):
            return False

        # Run for POST_DELEGATION events (after tool execution)
        if context.hook_type != HookType.POST_DELEGATION:
            return False

        # Must have fix detection metadata
        metadata = context.metadata or {}
        return metadata.get("fix_detected", False)

    def _determine_target_agent(self, context: HookContext, failure_event: Any) -> str:
        """Determine which agent should receive the learning.

        WHY: Learnings should go to the agent most likely to benefit from them.
        This method applies routing logic to determine the best target.

        Args:
            context: Hook context
            failure_event: The failure event

        Returns:
            Agent identifier (PM, engineer, qa, etc.)
        """
        # Try to get agent from context first
        agent_type = (
            context.data.get("agent_type")
            or context.data.get("subagent_type")
            or context.metadata.get("agent_type")
        )
        if agent_type:
            return agent_type

        # Check failure event context
        if hasattr(failure_event, "context") and failure_event.context.get(
            "agent_type"
        ):
            return failure_event.context["agent_type"]

        # Fall back to task-based routing
        if hasattr(failure_event, "task_type"):
            task_type = failure_event.task_type
            if task_type in ("test", "lint"):
                return "qa"
            if task_type in ("build", "install", "script") or task_type == "git":
                return "engineer"

        # Default to PM
        return "PM"

    def _write_to_memory(self, agent_id: str, learning_text: str) -> bool:
        """Write learning to agent memory file.

        WHY: Learnings must be persisted to memory files so agents can access
        them in future sessions. This method uses AgentMemoryManager to handle
        the actual file operations.

        Args:
            agent_id: Agent identifier
            learning_text: Markdown-formatted learning

        Returns:
            True if write succeeded, False otherwise
        """
        try:
            # Parse learning sections from markdown
            learning_items = self._parse_learning_markdown(learning_text)

            if not learning_items:
                logger.warning(f"No learning items parsed from: {learning_text}")
                return False

            # Add to agent memory
            return self.memory_manager.update_agent_memory(
                agent_id=agent_id, new_items=learning_items
            )

        except Exception as e:
            logger.error(f"Failed to write learning to memory for {agent_id}: {e}")
            return False

    def _parse_learning_markdown(self, learning_markdown: str) -> list:
        """Parse learning markdown into list items for memory.

        WHY: AgentMemoryManager expects a list of learning items. We need to
        convert the markdown-formatted learning into individual list items.

        Args:
            learning_markdown: Markdown-formatted learning

        Returns:
            List of learning items
        """
        items = []

        # Split by lines and extract bullet points
        lines = learning_markdown.split("\n")

        for line in lines:
            line = line.strip()
            if line.startswith("- **"):
                # This is a learning item (e.g., "- **Problem**: ...")
                items.append(line)
            elif line.startswith("## "):
                # This is a category header, skip it
                continue

        # If no items found, return the whole thing as a single item
        if not items:
            items = [f"- {learning_markdown.strip()}"]

        return items


def get_learning_extraction_hook() -> LearningExtractionHook:
    """Factory function to create learning extraction hook.

    WHY: Provides consistent hook creation pattern used throughout the framework.

    Returns:
        Configured LearningExtractionHook instance
    """
    return LearningExtractionHook()

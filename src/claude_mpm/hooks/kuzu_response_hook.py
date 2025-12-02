"""
Kuzu-Memory Response Learning Hook
===================================

Captures assistant responses and extracts learnings to store in kuzu-memory.
This completes the bidirectional enrichment cycle:
- KuzuMemoryHook enriches prompts with memories (READ)
- KuzuResponseHook stores learnings from responses (WRITE)

WHY: To automatically capture and persist important information from agent
responses, enabling continuous learning across conversations.

DESIGN DECISIONS:
- Priority 80 to run late after main processing
- Reuses KuzuMemoryHook's storage methods for consistency
- Graceful degradation if kuzu-memory is not available
- Extracts structured learnings using patterns and AI
"""

import logging
from typing import Any, Optional

from claude_mpm.hooks.base_hook import HookContext, HookResult, PostDelegationHook
from claude_mpm.hooks.kuzu_memory_hook import get_kuzu_memory_hook

logger = logging.getLogger(__name__)


class KuzuResponseHook(PostDelegationHook):
    """
    Hook that captures agent responses and stores learnings in kuzu-memory.

    This hook:
    1. Processes agent responses after delegation completes
    2. Extracts important learnings and information
    3. Stores memories in kuzu-memory for future retrieval
    4. Tags memories for better categorization
    """

    def __init__(self):
        """Initialize the kuzu-memory response learning hook."""
        super().__init__(name="kuzu_response_learner", priority=80)

        # Reuse the kuzu-memory hook instance for storage
        self.kuzu_hook = get_kuzu_memory_hook()
        self.enabled = self.kuzu_hook.enabled

        if not self.enabled:
            logger.info(
                "Kuzu-memory response hook disabled (kuzu-memory not available)"
            )
        else:
            logger.info("Kuzu-memory response learning hook enabled")

    def validate(self, context: HookContext) -> bool:
        """
        Validate if hook should process this context.

        Args:
            context: Hook context to validate

        Returns:
            True if hook should execute
        """
        if not self.enabled:
            return False

        # Check base validation (enabled, correct hook type, has result)
        if not super().validate(context):
            return False

        # Must have result data to extract learnings from
        result_data = context.data.get("result")
        if not result_data:
            return False

        return True

    def execute(self, context: HookContext) -> HookResult:
        """
        Extract and store learnings from agent responses.

        Args:
            context: Hook context containing response data

        Returns:
            HookResult with success status and metadata
        """
        if not self.enabled:
            return HookResult(success=True, data=context.data, modified=False)

        try:
            # Extract response content from various possible formats
            result_data = context.data.get("result", {})
            response_content = self._extract_response_content(result_data)

            if not response_content:
                logger.debug("No response content found for learning extraction")
                return HookResult(success=True, data=context.data, modified=False)

            # Extract and store learnings
            count = self.kuzu_hook.extract_and_store_learnings(response_content)

            if count > 0:
                logger.info(f"Stored {count} learnings from agent response")
                return HookResult(
                    success=True,
                    data=context.data,
                    modified=False,
                    metadata={"learnings_stored": count, "memory_backend": "kuzu"},
                )

            return HookResult(success=True, data=context.data, modified=False)

        except Exception as e:
            logger.error(f"Error in kuzu response hook: {e}")
            # Don't fail the operation if learning extraction fails
            return HookResult(
                success=True,
                data=context.data,
                modified=False,
                error=f"Learning extraction failed: {e}",
            )

    def _extract_response_content(self, result_data: Any) -> Optional[str]:
        """
        Extract response content from various result formats.

        Args:
            result_data: Result data in various possible formats

        Returns:
            Extracted response content as string, or None
        """
        if not result_data:
            return None

        # Handle dict format
        if isinstance(result_data, dict):
            # Try common response fields
            for field in ["content", "text", "response", "output", "message"]:
                if field in result_data:
                    content = result_data[field]
                    if isinstance(content, str):
                        return content
                    if isinstance(content, dict):
                        # Recursively extract from nested dict
                        return self._extract_response_content(content)

            # If dict has no recognizable fields, try converting to string
            return str(result_data)

        # Handle string format
        if isinstance(result_data, str):
            return result_data

        # Handle list format (concatenate items)
        if isinstance(result_data, list):
            items = []
            for item in result_data:
                extracted = self._extract_response_content(item)
                if extracted:
                    items.append(extracted)
            return "\n\n".join(items) if items else None

        # Fallback to string conversion
        return str(result_data) if result_data else None


# Create a singleton instance
_kuzu_response_hook = None


def get_kuzu_response_hook() -> KuzuResponseHook:
    """Get the singleton kuzu-memory response hook instance."""
    global _kuzu_response_hook
    if _kuzu_response_hook is None:
        _kuzu_response_hook = KuzuResponseHook()
    return _kuzu_response_hook

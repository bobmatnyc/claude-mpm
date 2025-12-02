"""
Kuzu-Memory Pre-Delegation Enrichment Hook
==========================================

Enriches agent delegation context with relevant memories from kuzu-memory
before the agent receives the task. This is the READ side of bidirectional
enrichment.

WHY: Agents need access to relevant historical knowledge when performing tasks.
This hook retrieves memories from kuzu-memory and injects them into the
delegation context.

DESIGN DECISIONS:
- Priority 10 to run early, before other context modifications
- Reuses KuzuMemoryHook's retrieval methods for consistency
- Injects memories as a dedicated section in agent context
- Falls back gracefully if kuzu-memory is not available
"""

import logging
from typing import Any, Dict, Optional

from claude_mpm.hooks.base_hook import HookContext, HookResult, PreDelegationHook
from claude_mpm.hooks.kuzu_memory_hook import get_kuzu_memory_hook

logger = logging.getLogger(__name__)


class KuzuEnrichmentHook(PreDelegationHook):
    """
    Hook that enriches agent delegation context with kuzu-memory.

    This hook:
    1. Extracts the task/prompt from delegation context
    2. Retrieves relevant memories from kuzu-memory
    3. Injects memories into agent context
    4. Formats memories for optimal agent understanding
    """

    def __init__(self):
        """Initialize the kuzu-memory enrichment hook."""
        super().__init__(name="kuzu_memory_enrichment", priority=10)

        # Reuse the kuzu-memory hook instance for retrieval
        self.kuzu_hook = get_kuzu_memory_hook()
        self.enabled = self.kuzu_hook.enabled

        if not self.enabled:
            logger.info(
                "Kuzu-memory enrichment hook disabled (kuzu-memory not available)"
            )
        else:
            logger.info("Kuzu-memory enrichment hook enabled")

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

        # Check base validation (enabled, correct hook type, has agent)
        if not super().validate(context):
            return False

        # Must have agent and context data
        if not context.data.get("agent"):
            return False

        return True

    def execute(self, context: HookContext) -> HookResult:
        """
        Enrich delegation context with relevant memories.

        Args:
            context: Hook context containing delegation data

        Returns:
            HookResult with enriched context
        """
        if not self.enabled:
            return HookResult(success=True, data=context.data, modified=False)

        try:
            # Extract query for memory retrieval
            query = self._extract_query_from_context(context.data)

            if not query:
                logger.debug("No query extracted from context for memory retrieval")
                return HookResult(success=True, data=context.data, modified=False)

            # Retrieve relevant memories
            memories = self.kuzu_hook._retrieve_memories(query)

            if not memories:
                logger.debug("No relevant memories found")
                return HookResult(success=True, data=context.data, modified=False)

            # Enrich context with memories
            enriched_data = self._enrich_delegation_context(
                context.data, memories, context.data.get("agent", "Agent")
            )

            logger.info(
                f"Enriched delegation context with {len(memories)} memories for {context.data.get('agent')}"
            )

            return HookResult(
                success=True,
                data=enriched_data,
                modified=True,
                metadata={
                    "memories_added": len(memories),
                    "memory_source": "kuzu",
                    "agent": context.data.get("agent"),
                },
            )

        except Exception as e:
            logger.error(f"Error in kuzu enrichment hook: {e}")
            # Don't fail the delegation if memory enrichment fails
            return HookResult(
                success=True,
                data=context.data,
                modified=False,
                error=f"Memory enrichment failed: {e}",
            )

    def _extract_query_from_context(self, data: Dict[str, Any]) -> Optional[str]:
        """
        Extract query text for memory retrieval.

        Args:
            data: Delegation context data

        Returns:
            Query string or None
        """
        # Try various context fields
        delegation_context = data.get("context", {})

        # Handle string context
        if isinstance(delegation_context, str):
            return delegation_context

        # Handle dict context
        if isinstance(delegation_context, dict):
            # Try common fields
            for field in ["prompt", "task", "query", "user_request", "description"]:
                if field in delegation_context:
                    value = delegation_context[field]
                    if isinstance(value, str):
                        return value

            # If no specific field, join all string values
            text_parts = [
                str(v) for v in delegation_context.values() if isinstance(v, str)
            ]
            if text_parts:
                return " ".join(text_parts)

        # Fallback: try to get task or instruction directly
        if "task" in data and isinstance(data["task"], str):
            return data["task"]

        if "instruction" in data and isinstance(data["instruction"], str):
            return data["instruction"]

        return None

    def _enrich_delegation_context(
        self, original_data: Dict[str, Any], memories: list, agent_name: str
    ) -> Dict[str, Any]:
        """
        Enrich delegation context with memories.

        Args:
            original_data: Original delegation data
            memories: Retrieved memories
            agent_name: Name of the agent

        Returns:
            Enriched delegation data
        """
        # Format memories
        memory_section = self._format_memory_section(memories, agent_name)

        # Create enriched data
        enriched_data = original_data.copy()

        # Get existing context
        delegation_context = enriched_data.get("context", {})
        if isinstance(delegation_context, str):
            delegation_context = {"prompt": delegation_context}

        # Add memory section
        if isinstance(delegation_context, dict):
            # Prepend memory section to context
            delegation_context["kuzu_memories"] = memory_section

            # If there's a main prompt/task, prepend memory note
            for field in ["prompt", "task", "instruction"]:
                if field in delegation_context and isinstance(
                    delegation_context[field], str
                ):
                    delegation_context[field] = (
                        f"{memory_section}\n\n{delegation_context[field]}"
                    )
                    break
        else:
            # If context is not dict, create new dict with memory
            delegation_context = {
                "kuzu_memories": memory_section,
                "original_context": delegation_context,
            }

        enriched_data["context"] = delegation_context
        enriched_data["_kuzu_enriched"] = True

        return enriched_data

    def _format_memory_section(self, memories: list, agent_name: str) -> str:
        """
        Format memories into a readable section.

        Args:
            memories: List of memory dictionaries
            agent_name: Name of the agent

        Returns:
            Formatted memory section
        """
        memory_text = self.kuzu_hook._format_memories(memories)

        return f"""
=== RELEVANT KNOWLEDGE FROM KUZU MEMORY ===
{agent_name}, you have access to these relevant memories from the knowledge graph:

{memory_text}

INSTRUCTIONS: Review these memories before proceeding. Apply learned patterns and avoid known mistakes.
Use this knowledge to provide more informed and contextual responses.
===========================================
"""


# Create a singleton instance
_kuzu_enrichment_hook = None


def get_kuzu_enrichment_hook() -> KuzuEnrichmentHook:
    """Get the singleton kuzu-memory enrichment hook instance."""
    global _kuzu_enrichment_hook
    if _kuzu_enrichment_hook is None:
        _kuzu_enrichment_hook = KuzuEnrichmentHook()
    return _kuzu_enrichment_hook

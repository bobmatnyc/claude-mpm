"""
Kuzu-Memory Integration Hook
============================

Integrates kuzu-memory knowledge graph with Claude MPM for persistent memory
across conversations. This hook intercepts user prompts to enrich them with
relevant memories and stores new learnings after responses.

WHY: Claude MPM needs a way to persistently remember information across
different conversations and sessions. Kuzu-memory provides a graph database
for structured memory storage with semantic search capabilities.

DESIGN DECISIONS:
- Priority 10 for early execution to enrich prompts before other hooks
- Uses subprocess to call kuzu-memory directly for maximum compatibility
- Graceful degradation if kuzu-memory is not installed
- Automatic extraction and storage of important information
- kuzu-memory is an OPTIONAL dependency (install with: pip install claude-mpm[memory])
"""

import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from claude_mpm.core.logging_utils import get_logger
from claude_mpm.hooks.base_hook import HookContext, HookResult, SubmitHook

logger = get_logger(__name__)


class KuzuMemoryHook(SubmitHook):
    """
    Hook that integrates kuzu-memory for persistent knowledge management.

    This hook:
    1. Checks if kuzu-memory is installed via pipx
    2. Enriches user prompts with relevant memories
    3. Stores important information from conversations
    4. Provides context-aware memory retrieval
    """

    def __init__(self):
        """Initialize the kuzu-memory integration hook."""
        super().__init__(name="kuzu_memory_integration", priority=10)

        # Check if kuzu-memory is available
        self.kuzu_memory_cmd = self._detect_kuzu_memory()
        self.enabled = self.kuzu_memory_cmd is not None

        if not self.enabled:
            logger.debug(
                "Kuzu-memory not found. Graph-based memory disabled. "
                "To enable: pip install claude-mpm[memory] (requires cmake)"
            )
        else:
            logger.info(f"Kuzu-memory integration enabled: {self.kuzu_memory_cmd}")

        # Use current project directory (kuzu-memory works with project-specific databases)
        self.project_path = Path.cwd()

        # Memory extraction patterns
        self.memory_patterns = [
            r"#\s*(?:Remember|Memorize|Store):\s*(.+?)(?:#|$)",
            r"(?:Important|Note|Key point):\s*(.+?)(?:\n|$)",
            r"(?:Learned|Discovered|Found that):\s*(.+?)(?:\n|$)",
        ]

    def _detect_kuzu_memory(self) -> Optional[str]:
        """
        Detect if kuzu-memory is installed and return its command path.

        Priority:
        1. Check pipx installation
        2. Check system PATH
        3. Return None if not found

        NOTE: As of v4.8.6, kuzu-memory is a required dependency and should be
        installed via pip. This method checks both pipx and system PATH for
        backward compatibility.
        """
        # Check pipx installation
        pipx_path = (
            Path.home()
            / ".local"
            / "pipx"
            / "venvs"
            / "kuzu-memory"
            / "bin"
            / "kuzu-memory"
        )
        if pipx_path.exists():
            return str(pipx_path)

        # Check system PATH
        kuzu_cmd = shutil.which("kuzu-memory")
        if kuzu_cmd:
            return kuzu_cmd

        return None

    def execute(self, context: HookContext) -> HookResult:
        """
        Process user prompts with kuzu-memory integration.

        This method:
        1. Retrieves relevant memories for the prompt
        2. Enriches the prompt with memory context
        3. Stores new memories after processing
        """
        if not self.enabled:
            return HookResult(success=True, data=context.data, modified=False)

        try:
            # Extract user prompt
            prompt = context.data.get("prompt", "")
            if not prompt:
                return HookResult(success=True, data=context.data, modified=False)

            # Retrieve relevant memories
            memories = self._retrieve_memories(prompt)

            if memories:
                # Enrich prompt with memories
                enriched_data = self._enrich_prompt(context.data, prompt, memories)

                logger.info(f"Enriched prompt with {len(memories)} memories")

                # Store the original prompt for later processing
                enriched_data["_original_prompt"] = prompt
                enriched_data["_memory_enriched"] = True

                return HookResult(
                    success=True,
                    data=enriched_data,
                    modified=True,
                    metadata={
                        "memories_added": len(memories),
                        "memory_source": "kuzu",
                    },
                )

            return HookResult(success=True, data=context.data, modified=False)

        except Exception as e:
            logger.error(f"Kuzu-memory hook failed: {e}")
            # Don't fail the request if memory integration fails
            return HookResult(
                success=True,
                data=context.data,
                modified=False,
                error=f"Memory integration failed: {e}",
            )

    def _retrieve_memories(self, query: str) -> List[Dict[str, Any]]:
        """
        Retrieve relevant memories for the given query.

        Args:
            query: The user prompt to find memories for

        Returns:
            List of relevant memory dictionaries
        """
        try:
            # Type narrowing: ensure kuzu_memory_cmd is not None before using
            if self.kuzu_memory_cmd is None:
                return []

            # Use kuzu-memory recall command (v1.2.7+ syntax)
            result = subprocess.run(
                [self.kuzu_memory_cmd, "memory", "recall", query, "--format", "json"],
                capture_output=True,
                text=True,
                timeout=5,
                cwd=str(self.project_path),
                check=False,
            )

            if result.returncode == 0 and result.stdout:
                try:
                    # Parse JSON with strict=False to handle control characters
                    data = json.loads(result.stdout, strict=False)
                    # v1.2.7 returns dict with 'memories' key, not array
                    if isinstance(data, dict):
                        memories = data.get("memories", [])
                    else:
                        memories = data if isinstance(data, list) else []
                    return memories
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse kuzu-memory JSON output: {e}")
                    logger.debug(f"Raw output: {result.stdout[:200]}")
                    return []  # Graceful fallback

        except (subprocess.TimeoutExpired, Exception) as e:
            logger.debug(f"Memory retrieval failed: {e}")

        return []

    def _enrich_prompt(
        self, original_data: Dict[str, Any], prompt: str, memories: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Enrich the user prompt with relevant memories.

        Args:
            original_data: Original hook context data
            prompt: User prompt
            memories: Retrieved memories

        Returns:
            Enriched context data
        """
        # Format memories for context
        memory_context = self._format_memories(memories)

        # Create enriched prompt
        enriched_prompt = f"""
## RELEVANT MEMORIES FROM KUZU KNOWLEDGE GRAPH

{memory_context}

## USER REQUEST

{prompt}

Note: Use the memories above to provide more informed and contextual responses.
"""

        # Create new data with enriched prompt
        enriched_data = original_data.copy()
        enriched_data["prompt"] = enriched_prompt

        return enriched_data

    def _format_memories(self, memories: List[Dict[str, Any]]) -> str:
        """
        Format memories into a readable context string.

        Args:
            memories: List of memory dictionaries

        Returns:
            Formatted memory context
        """
        if not memories:
            return "No relevant memories found."

        formatted = []
        for i, memory in enumerate(memories, 1):
            # Extract memory content and metadata
            content = memory.get("content", "")
            tags = memory.get("tags", [])
            memory.get("timestamp", "")
            relevance = memory.get("relevance", 0.0)

            # Format memory entry
            entry = f"{i}. {content}"
            if tags:
                entry += f" [Tags: {', '.join(tags)}]"
            if relevance > 0:
                entry += f" (Relevance: {relevance:.2f})"

            formatted.append(entry)

        return "\n".join(formatted)

    def store_memory(self, content: str, tags: Optional[List[str]] = None) -> bool:
        """
        Store a memory using kuzu-memory.

        Args:
            content: The memory content to store
            tags: Optional tags for categorization

        Returns:
            True if storage was successful
        """
        if not self.enabled or self.kuzu_memory_cmd is None:
            return False

        try:
            # Use kuzu-memory store command (v1.2.7+ syntax)
            cmd = [self.kuzu_memory_cmd, "memory", "store", content]

            # Execute store command in project directory
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=5,
                cwd=str(self.project_path),
                check=False,
            )

            if result.returncode == 0:
                logger.debug(f"Stored memory in kuzu: {content[:50]}...")
                return True
            logger.warning(f"Failed to store memory in kuzu: {result.stderr}")
            return False

        except Exception as e:
            logger.error(f"Failed to store memory: {e}")

        return False

    def extract_and_store_learnings(self, text: str) -> int:
        """
        Extract learnings from text and store them as memories.

        Args:
            text: Text to extract learnings from

        Returns:
            Number of learnings stored
        """
        if not self.enabled:
            return 0

        stored_count = 0

        # Extract learnings using patterns
        for pattern in self.memory_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                learning = match.group(1).strip()
                if learning and len(learning) > 10:  # Minimum length check
                    # Determine tags based on content
                    tags = self._infer_tags(learning)

                    # Store the learning
                    if self.store_memory(learning, tags):
                        stored_count += 1

        return stored_count

    def _infer_tags(self, content: str) -> List[str]:
        """
        Infer tags based on memory content.

        Args:
            content: Memory content

        Returns:
            List of inferred tags
        """
        tags = []
        content_lower = content.lower()

        # Technical tags
        if any(
            word in content_lower for word in ["code", "function", "class", "module"]
        ):
            tags.append("technical")
        if any(word in content_lower for word in ["bug", "error", "fix", "issue"]):
            tags.append("debugging")
        if any(word in content_lower for word in ["pattern", "architecture", "design"]):
            tags.append("architecture")
        if any(word in content_lower for word in ["performance", "optimize", "speed"]):
            tags.append("performance")

        # Project context tags
        if "claude-mpm" in content_lower or "mpm" in content_lower:
            tags.append("claude-mpm")
        if any(word in content_lower for word in ["hook", "agent", "service"]):
            tags.append("framework")

        # Default tag if no others found
        if not tags:
            tags.append("general")

        return tags


# Create a singleton instance
_kuzu_memory_hook = None


def get_kuzu_memory_hook() -> KuzuMemoryHook:
    """Get the singleton kuzu-memory hook instance."""
    global _kuzu_memory_hook
    if _kuzu_memory_hook is None:
        _kuzu_memory_hook = KuzuMemoryHook()
    return _kuzu_memory_hook

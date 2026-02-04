"""
PM Memory Manager - Persistent memory for PM-level orchestration.

Captures meta-level user conversations with the PM agent:
- User directives ("implement feature X", "work on @project")
- Project preferences ("always use PR model")
- Workflow patterns ("when deploying, run tests first")
- Architectural decisions
- Cross-project context

Does NOT capture:
- Code-level details (agents handle that)
- File contents
- Implementation specifics
"""

import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Pattern detection for automatic categorization
PREFERENCE_PATTERNS = [
    r"\b(always|prefer|never|don't|do not)\b",
    r"\b(use|avoid)\s+\w+\s+(for|with|when)",
    r"\b(default|standard)\s+(to|is)",
]

WORKFLOW_PATTERNS = [
    r"\b(when|before|after|if)\b.*\b(then|do|run|deploy|commit|push)",
    r"\b(first|then|finally|next)\b",
    r"\b(workflow|process|procedure)\b",
]

DIRECTIVE_PATTERNS = [
    r"^@\w+",  # @project commands
    r"\b(implement|build|create|add|fix|update|refactor)\b",
    r"\b(work on|focus on|start with)\b",
]


class PMMemoryManager:
    """Manages PM-level orchestration memory via kuzu-memory."""

    def __init__(self, project_path: Optional[str] = None, enabled: bool = True):
        """Initialize PM memory manager.

        Args:
            project_path: Path to project for context
            enabled: Whether memory capture is enabled
        """
        self.enabled = enabled
        self.project_path = project_path
        self._memory = None
        self._initialized = False

    def _init_memory(self) -> bool:
        """Lazy initialize kuzu-memory connection."""
        if self._initialized:
            return self._memory is not None

        self._initialized = True

        if not self.enabled:
            return False

        try:
            from kuzu_memory import KuzuMemory

            self._memory = KuzuMemory(
                agent_id="pm",  # Distinguish from agent-level memories
                auto_sync=False,  # Fast startup for hooks
            )
            logger.debug("PMMemoryManager initialized with kuzu-memory")
            return True
        except ImportError:
            logger.debug("kuzu-memory not installed, PM memory disabled")
            return False
        except Exception as e:
            logger.warning(f"Failed to initialize kuzu-memory: {e}")
            return False

    def enhance_prompt(self, prompt: str, limit: int = 5) -> str:
        """Enhance user prompt with relevant PM-level context.

        Args:
            prompt: Original user prompt
            limit: Max memories to include

        Returns:
            Enhanced prompt with PM context, or original if unavailable
        """
        if not self._init_memory() or not self._memory:
            return prompt

        try:
            # Get relevant PM memories
            return self._memory.attach_memories(
                prompt,
                max_memories=limit,
                memory_types=["preference", "procedural", "semantic"],
            )
        except Exception as e:
            logger.debug(f"Failed to enhance prompt: {e}")
            return prompt

    def capture_directive(
        self, prompt: str, project: Optional[str] = None
    ) -> Optional[str]:
        """Capture user directive from prompt.

        Automatically detects and stores:
        - Preferences (always/never patterns)
        - Workflows (when/before/after patterns)
        - General directives

        Args:
            prompt: User prompt to analyze
            project: Project context (@alias or path)

        Returns:
            Memory ID if stored, None otherwise
        """
        if not self._init_memory() or not self._memory:
            return None

        try:
            # Detect memory type
            memory_type = self._detect_memory_type(prompt)

            # Build content with context
            content = prompt
            if project:
                content = f"[Project: {project}] {prompt}"

            # Store memory
            memory_id = self._memory.remember(
                content=content,
                memory_type=memory_type,
                metadata={
                    "source": "pm_directive",
                    "project": project,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )
            logger.debug(f"Captured PM directive as {memory_type}: {memory_id}")
            return memory_id
        except Exception as e:
            logger.debug(f"Failed to capture directive: {e}")
            return None

    def capture_preference(
        self, preference: str, project: Optional[str] = None
    ) -> Optional[str]:
        """Explicitly store a user preference.

        Args:
            preference: The preference statement
            project: Optional project scope

        Returns:
            Memory ID if stored
        """
        if not self._init_memory() or not self._memory:
            return None

        try:
            content = preference
            if project:
                content = f"[Project: {project}] {preference}"

            return self._memory.remember(
                content=content,
                memory_type="preference",
                metadata={
                    "source": "pm_explicit_preference",
                    "project": project,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )
        except Exception as e:
            logger.debug(f"Failed to capture preference: {e}")
            return None

    def capture_workflow(
        self, workflow: str, project: Optional[str] = None
    ) -> Optional[str]:
        """Explicitly store a workflow pattern.

        Args:
            workflow: The workflow description
            project: Optional project scope

        Returns:
            Memory ID if stored
        """
        if not self._init_memory() or not self._memory:
            return None

        try:
            content = workflow
            if project:
                content = f"[Project: {project}] {workflow}"

            return self._memory.remember(
                content=content,
                memory_type="procedural",
                metadata={
                    "source": "pm_workflow",
                    "project": project,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )
        except Exception as e:
            logger.debug(f"Failed to capture workflow: {e}")
            return None

    def capture_delegation_outcome(
        self,
        task: str,
        agent: str,
        outcome: str,
        success: bool,
        project: Optional[str] = None,
    ) -> Optional[str]:
        """Capture outcome of an agent delegation for learning.

        Args:
            task: What was delegated
            agent: Which agent handled it
            outcome: Result summary
            success: Whether it succeeded
            project: Project context

        Returns:
            Memory ID if stored
        """
        if not self._init_memory() or not self._memory:
            return None

        try:
            status = "succeeded" if success else "failed"
            content = f"Delegated '{task}' to {agent} agent - {status}: {outcome}"
            if project:
                content = f"[Project: {project}] {content}"

            return self._memory.remember(
                content=content,
                memory_type="episodic",
                metadata={
                    "source": "pm_delegation",
                    "agent": agent,
                    "success": success,
                    "project": project,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )
        except Exception as e:
            logger.debug(f"Failed to capture delegation outcome: {e}")
            return None

    def recall(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Recall PM-level memories matching a query.

        Args:
            query: Search query
            limit: Max results

        Returns:
            List of matching memories
        """
        if not self._init_memory() or not self._memory:
            return []

        try:
            results = self._memory.recall(
                query=query,
                limit=limit,
                memory_types=["preference", "procedural", "semantic", "episodic"],
            )
            return results if results else []
        except Exception as e:
            logger.debug(f"Failed to recall memories: {e}")
            return []

    def _detect_memory_type(self, prompt: str) -> str:
        """Detect appropriate memory type from prompt patterns.

        Returns:
            Memory type: preference, procedural, semantic, or episodic
        """
        prompt_lower = prompt.lower()

        # Check for preference patterns
        for pattern in PREFERENCE_PATTERNS:
            if re.search(pattern, prompt_lower):
                return "preference"

        # Check for workflow patterns
        for pattern in WORKFLOW_PATTERNS:
            if re.search(pattern, prompt_lower):
                return "procedural"

        # Check for directive patterns (episodic by default)
        for pattern in DIRECTIVE_PATTERNS:
            if re.search(pattern, prompt_lower):
                return "episodic"

        # Default to episodic for general directives
        return "episodic"


# Global singleton for hook performance
_pm_memory: Optional[PMMemoryManager] = None


def get_pm_memory(enabled: bool = True) -> PMMemoryManager:
    """Get or create the global PM memory manager.

    Args:
        enabled: Whether memory is enabled

    Returns:
        PMMemoryManager singleton
    """
    global _pm_memory
    if _pm_memory is None:
        _pm_memory = PMMemoryManager(enabled=enabled)
    return _pm_memory

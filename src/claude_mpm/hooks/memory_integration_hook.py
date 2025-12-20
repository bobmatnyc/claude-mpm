"""Memory integration hooks for automatic agent memory management.

WHY: Agents need to accumulate project-specific knowledge over time. These hooks
automatically inject agent memory before delegation and extract learnings after,
enabling agents to become more effective through experience.

DESIGN DECISION: We use explicit markers to extract structured learnings from
agent outputs because:
- It gives agents explicit control over what gets memorized
- The format is clear and unambiguous
- It's more reliable than pattern matching
- Agents can add multiple learnings in a single response
"""

import re
from datetime import datetime
from typing import Dict, List

from claude_mpm.core.config import Config
from claude_mpm.core.logging_utils import get_logger
from claude_mpm.core.shared.config_loader import ConfigLoader
from claude_mpm.hooks.base_hook import (
    HookContext,
    HookResult,
    PostDelegationHook,
    PreDelegationHook,
)

logger = get_logger(__name__)

# Try to import memory manager with fallback handling
try:
    from claude_mpm.services.agents.memory import AgentMemoryManager

    MEMORY_MANAGER_AVAILABLE = True
except ImportError as e:
    logger.warning(f"AgentMemoryManager not available: {e}")
    MEMORY_MANAGER_AVAILABLE = False
    AgentMemoryManager = None

# Try to import socketio server with fallback handling
try:
    from claude_mpm.services.socketio_server import get_socketio_server

    SOCKETIO_AVAILABLE = True
except ImportError as e:
    logger.debug(f"SocketIO server not available: {e}")
    SOCKETIO_AVAILABLE = False
    get_socketio_server = None

# Try to import event bus with fallback handling
try:
    from claude_mpm.services.event_bus.event_bus import EventBus

    EVENT_BUS_AVAILABLE = True
except ImportError as e:
    logger.debug(f"EventBus not available: {e}")
    EVENT_BUS_AVAILABLE = False
    EventBus = None


class MemoryPreDelegationHook(PreDelegationHook):
    """Inject agent memory into delegation context.

    WHY: Agents perform better when they have access to accumulated project knowledge.
    This hook loads agent-specific memory and adds it to the delegation context,
    allowing agents to apply learned patterns and avoid known mistakes.

    DESIGN DECISION: Memory is injected as a clearly formatted section in the context
    to ensure agents understand it's their accumulated knowledge, not current task info.
    """

    def __init__(self, config: Config = None):
        """Initialize with optional config.

        Args:
            config: Optional Config object. If not provided, will create default Config.
        """
        super().__init__(name="memory_pre_delegation", priority=20)
        if config:
            self.config = config
        else:
            config_loader = ConfigLoader()
            self.config = config_loader.load_main_config()

        # Initialize memory manager only if available
        if MEMORY_MANAGER_AVAILABLE and AgentMemoryManager:
            try:
                self.memory_manager = AgentMemoryManager(self.config)
            except Exception as e:
                logger.error(f"Failed to initialize AgentMemoryManager: {e}")
                self.memory_manager = None
        else:
            logger.info("Memory manager not available - hook will be inactive")
            self.memory_manager = None

        # Initialize event bus for observability
        if EVENT_BUS_AVAILABLE and EventBus:
            try:
                self.event_bus = EventBus.get_instance()
            except Exception as e:
                logger.debug(f"Failed to get EventBus instance: {e}")
                self.event_bus = None
        else:
            self.event_bus = None

    def execute(self, context: HookContext) -> HookResult:
        """Add agent memory to delegation context.

        WHY: By loading memory before delegation, agents can reference their
        accumulated knowledge when performing tasks, leading to better outcomes.
        """
        # If memory manager is not available, skip memory injection
        if not self.memory_manager:
            logger.debug("Memory manager not available - skipping memory injection")
            return HookResult(success=True, data=context.data, modified=False)

        try:
            # Extract and normalize agent ID from context
            agent_name = context.data.get("agent", "")
            if not agent_name:
                return HookResult(success=True, data=context.data, modified=False)

            # Normalize agent ID (e.g., "Engineer Agent" -> "engineer")
            agent_id = (
                agent_name.lower()
                .replace(" ", "_")
                .replace("_agent", "")
                .replace("agent", "")
                .strip("_")
            )

            if agent_id:
                # Load agent memory
                memory_content = self.memory_manager.load_agent_memory(agent_id)

                if memory_content and memory_content.strip():
                    # Get existing context data
                    delegation_context = context.data.get("context", {})
                    if isinstance(delegation_context, str):
                        # If context is a string, convert to dict
                        delegation_context = {"prompt": delegation_context}

                    # Add memory with clear formatting
                    memory_section = f"""
AGENT MEMORY - PROJECT-SPECIFIC KNOWLEDGE:
{memory_content}

INSTRUCTIONS: Review your memory above before proceeding. Apply learned patterns and avoid known mistakes.
"""

                    # Add to context
                    delegation_context["agent_memory"] = memory_section

                    # Update the context data
                    updated_data = context.data.copy()
                    updated_data["context"] = delegation_context

                    logger.info(f"Injected memory for agent '{agent_id}'")

                    # Calculate memory size for observability
                    memory_size = len(memory_content)

                    # Emit event bus event for observability
                    if self.event_bus:
                        try:
                            # Determine memory source (project or user level)
                            # This is inferred from the memory manager's behavior
                            memory_source = (
                                "runtime"  # Runtime loading from memory manager
                            )

                            self.event_bus.publish(
                                "agent.memory.loaded",
                                {
                                    "agent_id": agent_id,
                                    "memory_source": memory_source,
                                    "memory_size": memory_size,
                                    "timestamp": datetime.now(datetime.UTC).isoformat(),
                                },
                            )
                        except Exception as event_error:
                            logger.debug(f"EventBus publish failed: {event_error}")

                    # Emit Socket.IO event for memory injected (legacy compatibility)
                    try:
                        socketio_server = get_socketio_server()
                        # Calculate size of injected content
                        injected_size = len(memory_section.encode("utf-8"))
                        socketio_server.memory_injected(agent_id, injected_size)
                    except Exception as ws_error:
                        logger.debug(f"Socket.IO notification failed: {ws_error}")

                    return HookResult(
                        success=True,
                        data=updated_data,
                        modified=True,
                        metadata={"memory_injected": True, "agent_id": agent_id},
                    )

            return HookResult(success=True, data=context.data, modified=False)

        except Exception as e:
            logger.error(f"Memory injection failed: {e}")
            # Don't fail the delegation if memory injection fails
            return HookResult(
                success=True,
                data=context.data,
                modified=False,
                error=f"Memory injection failed: {e!s}",
            )


class MemoryPostDelegationHook(PostDelegationHook):
    """Extract learnings from delegation results using explicit markers.

    WHY: Agents produce valuable insights during task execution. This hook
    extracts structured learnings from their outputs using explicit markers,
    building up project-specific knowledge over time.

    DESIGN DECISION: We use explicit markers to give agents full control over
    what gets memorized. This is more reliable than pattern matching and allows
    multiple learnings per response. Supports multiple trigger phrases for flexibility.

    Supported formats:
    # Add To Memory:
    Type: pattern
    Content: All services use dependency injection for flexibility
    #

    # Memorize:
    Type: guideline
    Content: Always validate input parameters before processing
    #

    # Remember:
    Type: mistake
    Content: Never hardcode configuration values
    #
    """

    def __init__(self, config: Config = None):
        """Initialize with optional config.

        Args:
            config: Optional Config object. If not provided, will create default Config.
        """
        super().__init__(name="memory_post_delegation", priority=80)
        if config:
            self.config = config
        else:
            config_loader = ConfigLoader()
            self.config = config_loader.load_main_config()

        # Initialize memory manager only if available
        if MEMORY_MANAGER_AVAILABLE and AgentMemoryManager:
            try:
                self.memory_manager = AgentMemoryManager(self.config)
            except Exception as e:
                logger.error(
                    f"Failed to initialize AgentMemoryManager in PostDelegationHook: {e}"
                )
                self.memory_manager = None
        else:
            logger.info(
                "Memory manager not available - post-delegation hook will be inactive"
            )
            self.memory_manager = None

        # Map of supported types to memory sections
        self.type_mapping = {
            "pattern": "pattern",  # Coding Patterns Learned
            "architecture": "architecture",  # Project Architecture
            "guideline": "guideline",  # Implementation Guidelines
            "mistake": "mistake",  # Common Mistakes to Avoid
            "strategy": "strategy",  # Effective Strategies
            "integration": "integration",  # Integration Points
            "performance": "performance",  # Performance Considerations
            "context": "context",  # Current Technical Context
        }

    def execute(self, context: HookContext) -> HookResult:
        """Extract and store learnings from delegation result.

        WHY: Capturing learnings immediately after task completion ensures we
        don't lose valuable insights that agents discover during execution.
        """
        # If memory manager is not available, skip learning extraction
        if not self.memory_manager:
            logger.debug("Memory manager not available - skipping learning extraction")
            return HookResult(success=True, data=context.data, modified=False)

        try:
            # Check if auto-learning is enabled
            if not self.config.get(
                "memory.auto_learning", True
            ):  # Changed default to True
                return HookResult(success=True, data=context.data, modified=False)

            # Extract agent ID
            agent_name = context.data.get("agent", "")
            if not agent_name:
                return HookResult(success=True, data=context.data, modified=False)

            # Normalize agent ID
            agent_id = (
                agent_name.lower()
                .replace(" ", "_")
                .replace("_agent", "")
                .replace("agent", "")
                .strip("_")
            )

            # Check if auto-learning is enabled for this specific agent
            agent_overrides = self.config.get("memory.agent_overrides", {})
            agent_config = agent_overrides.get(agent_id, {})
            if "auto_learning" in agent_config and not agent_config["auto_learning"]:
                return HookResult(success=True, data=context.data, modified=False)

            # Extract result content
            result = context.data.get("result", {})
            if isinstance(result, dict):
                result_text = result.get("content", "") or str(result)
            else:
                result_text = str(result)

            if agent_id and result_text:
                # Extract learnings using patterns
                learnings = self._extract_learnings(result_text)

                # Store each learning
                learnings_stored = 0
                for learning_type, items in learnings.items():
                    for item in items:
                        try:
                            self.memory_manager.add_learning(
                                agent_id, learning_type, item
                            )
                            learnings_stored += 1
                        except Exception as e:
                            logger.warning(f"Failed to store learning: {e}")

                if learnings_stored > 0:
                    logger.info(
                        f"Extracted {learnings_stored} learnings for agent '{agent_id}'"
                    )

                    return HookResult(
                        success=True,
                        data=context.data,
                        modified=False,
                        metadata={
                            "learnings_extracted": learnings_stored,
                            "agent_id": agent_id,
                        },
                    )

            return HookResult(success=True, data=context.data, modified=False)

        except Exception as e:
            logger.error(f"Learning extraction failed: {e}")
            # Don't fail the delegation result if learning extraction fails
            return HookResult(
                success=True,
                data=context.data,
                modified=False,
                error=f"Learning extraction failed: {e!s}",
            )

    def _extract_learnings(self, text: str) -> Dict[str, List[str]]:
        """Extract structured learnings from text using explicit markers.

        WHY: We limit learnings to 100 characters to keep memory entries
        concise and actionable. Longer entries tend to be less useful as
        quick reference points.

        DESIGN DECISION: Using explicit markers gives agents full control and makes
        extraction reliable. We support multiple memory additions in a single response
        and multiple trigger phrases (Add To Memory, Memorize, Remember) for flexibility.

        Args:
            text: The text to extract learnings from

        Returns:
            Dictionary mapping learning types to lists of extracted learnings
        """
        learnings = {learning_type: [] for learning_type in self.type_mapping}
        seen_learnings = set()  # Avoid duplicates

        # Pattern to find memory blocks with multiple trigger phrases
        # Matches: # Add To Memory: / # Memorize: / # Remember:\n...\n#
        # Only matches complete blocks with proper closing markers
        memory_pattern = r"#\s*(?:Add\s+To\s+Memory|Memorize|Remember):\s*\n((?:[^#](?:[^#]|#(?!\s*(?:Add\s+To\s+Memory|Memorize|Remember):))*?)?)\n\s*#\s*$"
        matches = re.finditer(
            memory_pattern, text, re.MULTILINE | re.DOTALL | re.IGNORECASE
        )

        for match in matches:
            block_content = match.group(1).strip()
            logger.debug(f"Found memory block: {block_content[:50]}...")

            # Extract type and content from the block
            type_match = re.search(r"Type:\s*(\w+)", block_content, re.IGNORECASE)
            content_match = re.search(
                r"Content:\s*(.+)", block_content, re.IGNORECASE | re.DOTALL
            )

            if type_match and content_match:
                learning_type = type_match.group(1).lower().strip()
                content = content_match.group(1).strip()

                # Clean up multi-line content - take first line if multiple
                if "\n" in content:
                    content = content.split("\n")[0].strip()

                # Remove trailing punctuation
                content = content.rstrip(".!?,;")

                # Validate type is supported
                if learning_type in self.type_mapping:
                    # Check content length (between 5 and 100 characters)
                    if content and 5 < len(content) <= 100:
                        # Normalize for duplicate detection
                        normalized = content.lower()
                        if normalized not in seen_learnings:
                            learnings[learning_type].append(content)
                            seen_learnings.add(normalized)
                            logger.debug(
                                f"Extracted learning - Type: {learning_type}, Content: {content}"
                            )
                        else:
                            logger.debug(f"Skipping duplicate learning: {content}")
                    else:
                        logger.debug(
                            f"Skipping learning - invalid length ({len(content)}): {content}"
                        )
                else:
                    logger.warning(
                        f"Unsupported learning type: {learning_type}. Supported types: {list(self.type_mapping.keys())}"
                    )
            else:
                logger.debug("Invalid memory block format - missing Type or Content")

        # Log summary of extracted learnings
        total_learnings = sum(len(items) for items in learnings.values())
        if total_learnings > 0:
            logger.info(f"Extracted {total_learnings} learnings from agent response")
            for learning_type, items in learnings.items():
                if items:
                    logger.debug(f"  {learning_type}: {len(items)} items")

        return learnings

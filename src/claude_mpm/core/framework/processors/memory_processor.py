"""Memory content processor for framework memory management."""

from pathlib import Path
from typing import Any, Dict, Set

from claude_mpm.core.logging_utils import get_logger


class MemoryProcessor:
    """Processes and manages memory content for agents."""

    def __init__(self):
        """Initialize the memory processor."""
        self.logger = get_logger("memory_processor")

    def load_pm_memories(self) -> Dict[str, str]:
        """Load PM memories from various locations.

        Returns:
            Dictionary with actual_memories content
        """
        memories = {}

        # Check for project-specific PM memories (highest priority)
        project_memory_file = Path.cwd() / ".claude-mpm" / "memories" / "PM_memories.md"
        if project_memory_file.exists():
            try:
                content = project_memory_file.read_text()
                memories["actual_memories"] = content
                memories["memory_source"] = "project"
                self.logger.info(
                    f"Loaded PM memories from project: {project_memory_file}"
                )
                return memories
            except Exception as e:
                self.logger.error(f"Failed to load project PM memories: {e}")

        # Check for user-specific PM memories (fallback)
        user_memory_file = Path.home() / ".claude-mpm" / "memories" / "PM_memories.md"
        if user_memory_file.exists():
            try:
                content = user_memory_file.read_text()
                memories["actual_memories"] = content
                memories["memory_source"] = "user"
                self.logger.info(f"Loaded PM memories from user: {user_memory_file}")
                return memories
            except Exception as e:
                self.logger.error(f"Failed to load user PM memories: {e}")

        return memories

    def load_agent_memories(self, deployed_agents: Set[str]) -> Dict[str, str]:
        """Load memories for deployed agents.

        Args:
            deployed_agents: Set of deployed agent names

        Returns:
            Dictionary mapping agent names to their memory content
        """
        agent_memories = {}

        # Define memory file search locations
        memory_locations = [
            Path.cwd() / ".claude-mpm" / "memories",  # Project memories
            Path.home() / ".claude-mpm" / "memories",  # User memories
        ]

        for agent_name in deployed_agents:
            memory_filename = f"{agent_name}_memories.md"

            # Search for memory file in each location (project takes precedence)
            for memory_dir in memory_locations:
                memory_file = memory_dir / memory_filename
                if memory_file.exists():
                    try:
                        content = memory_file.read_text()
                        agent_memories[agent_name] = content
                        self.logger.debug(
                            f"Loaded memories for {agent_name} from {memory_file}"
                        )
                        break  # Use first found (project > user)
                    except Exception as e:
                        self.logger.error(
                            f"Failed to load memories for {agent_name}: {e}"
                        )

        return agent_memories

    def aggregate_memories(
        self,
        pm_memories: Dict[str, str],
        agent_memories: Dict[str, str],
    ) -> Dict[str, Any]:
        """Aggregate all memories into a single structure.

        Args:
            pm_memories: PM memory content
            agent_memories: Agent-specific memories

        Returns:
            Aggregated memory structure
        """
        result = {}

        # Add PM memories
        if pm_memories.get("actual_memories"):
            result["actual_memories"] = pm_memories["actual_memories"]
            result["memory_source"] = pm_memories.get("memory_source", "unknown")

        # Add agent memories
        if agent_memories:
            result["agent_memories"] = agent_memories

        return result

    def format_memory_section(self, memories: Dict[str, Any]) -> str:
        """Format memories into a section for instructions.

        Args:
            memories: Memory content dictionary

        Returns:
            Formatted memory section
        """
        sections = []

        # Format PM memories
        if memories.get("actual_memories"):
            sections.append("\n\n## Current PM Memories\n\n")
            sections.append(
                "**The following are your accumulated memories and knowledge from this project:**\n\n"
            )
            sections.append(memories["actual_memories"])
            sections.append("\n")

        # Format agent memories
        if memories.get("agent_memories"):
            agent_memories = memories["agent_memories"]
            if agent_memories:
                sections.append("\n\n## Agent Memories\n\n")
                sections.append(
                    "**The following are accumulated memories from specialized agents:**\n\n"
                )

                for agent_name in sorted(agent_memories.keys()):
                    memory_content = agent_memories[agent_name]
                    if memory_content:
                        formatted_name = agent_name.replace("_", " ").title()
                        sections.append(f"### {formatted_name} Agent Memory\n\n")
                        sections.append(memory_content)
                        sections.append("\n\n")

        return "".join(sections)

    def deduplicate_memories(self, memories: Dict[str, str]) -> Dict[str, str]:
        """Remove duplicate entries from memories.

        Args:
            memories: Raw memory content

        Returns:
            Deduplicated memories
        """
        deduplicated = {}

        for key, content in memories.items():
            if not content:
                continue

            # Split into lines and remove duplicates while preserving order
            lines = content.split("\n")
            seen = set()
            unique_lines = []

            for line in lines:
                # Skip empty lines in deduplication
                if not line.strip():
                    unique_lines.append(line)
                    continue

                # Add non-duplicate lines
                if line not in seen:
                    seen.add(line)
                    unique_lines.append(line)

            deduplicated[key] = "\n".join(unique_lines)

        return deduplicated

    def migrate_legacy_memories(self) -> bool:
        """Migrate memories from old .claude/ locations to new .claude-mpm/ locations.

        Returns:
            True if any migrations were performed
        """
        migrated = False

        # Define migration paths
        migrations = [
            # Project memories
            (
                Path.cwd() / ".claude" / "memories" / "PM_memories.md",
                Path.cwd() / ".claude-mpm" / "memories" / "PM_memories.md",
            ),
            # User memories
            (
                Path.home() / ".claude" / "memories" / "PM_memories.md",
                Path.home() / ".claude-mpm" / "memories" / "PM_memories.md",
            ),
        ]

        for old_path, new_path in migrations:
            if old_path.exists() and not new_path.exists():
                try:
                    # Create new directory if needed
                    new_path.parent.mkdir(parents=True, exist_ok=True)

                    # Copy content
                    content = old_path.read_text()
                    new_path.write_text(content)

                    self.logger.info(f"Migrated memories from {old_path} to {new_path}")
                    migrated = True
                except Exception as e:
                    self.logger.error(
                        f"Failed to migrate memories from {old_path}: {e}"
                    )

        return migrated

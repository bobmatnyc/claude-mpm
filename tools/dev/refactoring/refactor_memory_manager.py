#!/usr/bin/env python3
"""
Refactoring script for agent_memory_manager.py using rope.

This script extracts focused services from the large agent_memory_manager.py file.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))


def create_memory_file_service():
    """Phase 1.1: Extract MemoryFileService class."""

    # Create the new service file first
    service_content = '''#!/usr/bin/env python3
"""Memory File Service - Handles file operations for agent memories."""

import logging
from pathlib import Path
from typing import Optional
from datetime import datetime


class MemoryFileService:
    """Service for handling memory file operations."""

    def __init__(self, memories_dir: Path):
        """Initialize the memory file service.

        Args:
            memories_dir: Directory where memory files are stored
        """
        self.memories_dir = memories_dir
        self.logger = logging.getLogger(__name__)

    def get_memory_file_with_migration(self, directory: Path, agent_id: str) -> Path:
        """Get memory file path with migration support.

        Migrates from old naming convention if needed.

        Args:
            directory: Directory to check for memory file
            agent_id: Agent identifier

        Returns:
            Path to the memory file
        """
        new_file = directory / f"{agent_id}_memories.md"
        old_file = directory / f"{agent_id}_memory.md"

        # Migrate from old naming convention if needed
        if old_file.exists() and not new_file.exists():
            try:
                old_file.rename(new_file)
                self.logger.info(f"Migrated memory file: {old_file} -> {new_file}")
            except Exception as e:
                self.logger.warning(f"Could not migrate memory file: {e}")
                return old_file

        return new_file

    def save_memory_file(self, file_path: Path, content: str) -> bool:
        """Save content to a memory file.

        Args:
            file_path: Path to the memory file
            content: Content to save

        Returns:
            True if saved successfully, False otherwise
        """
        try:
            # Ensure directory exists
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # Write content
            file_path.write_text(content)

            self.logger.debug(f"Saved memory file: {file_path}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to save memory file {file_path}: {e}")
            return False

    def ensure_memories_directory(self) -> None:
        """Ensure the memories directory exists with README."""
        try:
            # Create directory if it doesn't exist
            self.memories_dir.mkdir(parents=True, exist_ok=True)

            # Create README if it doesn't exist
            readme_path = self.memories_dir / "README.md"
            if not readme_path.exists():
                readme_content = """# Agent Memories Directory

This directory contains memory files for various agents used in the project.

## File Format

Memory files follow the naming convention: `{agent_id}_memories.md`

Each file contains:
- Agent metadata (name, type, version)
- Project-specific learnings organized by category
- Timestamps for tracking updates

## Auto-generated

These files are managed automatically by the agent memory system.
Manual edits should be done carefully to preserve the format.
"""
                readme_path.write_text(readme_content)
                self.logger.debug(f"Created README in memories directory: {readme_path}")

        except Exception as e:
            self.logger.error(f"Failed to ensure memories directory: {e}")
'''

    # Write the new service file
    service_path = (
        Path(project_root)
        / "src/claude_mpm/services/agents/memory/memory_file_service.py"
    )
    service_path.write_text(service_content)
    print(f"✓ Created MemoryFileService at {service_path}")
    return service_path


def create_memory_limits_service():
    """Phase 1.2: Extract MemoryLimitsService class."""

    service_content = '''#!/usr/bin/env python3
"""Memory Limits Service - Manages memory size limits and configuration."""

import logging
from typing import Any, Dict, Optional
from claude_mpm.core.config import Config


class MemoryLimitsService:
    """Service for managing memory limits and configuration."""

    # Default limits
    DEFAULT_MEMORY_LIMITS = {
        "max_file_size_kb": 80,  # 80KB (20k tokens)
        "max_items": 100,  # Maximum total memory items
        "max_line_length": 120,
    }

    def __init__(self, config: Optional[Config] = None):
        """Initialize the memory limits service.

        Args:
            config: Optional Config object for reading configuration
        """
        self.config = config or Config()
        self.logger = logging.getLogger(__name__)
        self.memory_limits = self._init_memory_limits()

    def _init_memory_limits(self) -> Dict[str, Any]:
        """Initialize memory limits from configuration.

        Returns:
            Dictionary of memory limits
        """
        try:
            limits = self.DEFAULT_MEMORY_LIMITS.copy()

            # Try to load from config
            if hasattr(self.config, 'agent_memory_limits'):
                config_limits = self.config.agent_memory_limits
                if isinstance(config_limits, dict):
                    limits.update(config_limits)

            self.logger.debug(f"Initialized memory limits: {limits}")
            return limits

        except Exception as e:
            self.logger.warning(f"Failed to load memory limits from config: {e}")
            return self.DEFAULT_MEMORY_LIMITS.copy()

    def get_agent_limits(self, agent_id: str) -> Dict[str, Any]:
        """Get memory limits for a specific agent.

        Args:
            agent_id: Agent identifier

        Returns:
            Dictionary of memory limits for the agent
        """
        # Start with default limits
        limits = self.memory_limits.copy()

        # Check for agent-specific overrides
        try:
            if hasattr(self.config, 'agents') and agent_id in self.config.agents:
                agent_config = self.config.agents[agent_id]
                if 'memory_limits' in agent_config:
                    limits.update(agent_config['memory_limits'])
        except Exception as e:
            self.logger.debug(f"No agent-specific limits for {agent_id}: {e}")

        return limits

    def get_agent_auto_learning(self, agent_id: str) -> bool:
        """Get auto-learning setting for a specific agent.

        Args:
            agent_id: Agent identifier

        Returns:
            True if auto-learning is enabled, False otherwise
        """
        try:
            # Check agent-specific config
            if hasattr(self.config, 'agents') and agent_id in self.config.agents:
                agent_config = self.config.agents[agent_id]
                if 'auto_learning' in agent_config:
                    return agent_config['auto_learning']

            # Check global config
            if hasattr(self.config, 'agent_auto_learning'):
                return self.config.agent_auto_learning

        except Exception as e:
            self.logger.debug(f"Error checking auto-learning for {agent_id}: {e}")

        # Default to True (auto-learning enabled)
        return True
'''

    # Write the new service file
    service_path = (
        Path(project_root)
        / "src/claude_mpm/services/agents/memory/memory_limits_service.py"
    )
    service_path.write_text(service_content)
    print(f"✓ Created MemoryLimitsService at {service_path}")
    return service_path


def update_agent_memory_manager():
    """Update agent_memory_manager.py to use the new services."""

    manager_path = (
        Path(project_root)
        / "src/claude_mpm/services/agents/memory/agent_memory_manager.py"
    )
    content = manager_path.read_text()

    # Read the full file to understand the structure better
    lines = content.splitlines()

    # Find where to add imports (after existing imports)
    import_line = -1
    for i, line in enumerate(lines):
        if line.startswith("from .template_generator"):
            import_line = i
            break

    if import_line == -1:
        print("Could not find import location")
        return

    # Add new imports
    new_imports = [
        "from .memory_file_service import MemoryFileService",
        "from .memory_limits_service import MemoryLimitsService",
    ]

    # Insert imports
    for imp in reversed(new_imports):
        lines.insert(import_line + 1, imp)

    # Now we need to update the __init__ method to use the services
    # and replace method calls

    # Find __init__ method
    init_start = -1
    init_end = -1

    for i, line in enumerate(lines):
        if "def __init__" in line and "self" in line:
            init_start = i
            # Find the end of __init__
            for j in range(i + 1, len(lines)):
                if lines[j].strip() and not lines[j].startswith(" "):
                    init_end = j
                    break
                if lines[j].strip().startswith("def "):
                    init_end = j
                    break
            break

    # Modify __init__ to instantiate services
    if init_start != -1:
        # Find where to add service initialization (after self.memories_dir)
        for i in range(init_start, init_end):
            if "self.memories_dir = self.project_memories_dir" in lines[i]:
                # Add service initialization after this line
                lines.insert(i + 1, "")
                lines.insert(i + 2, "        # Initialize services")
                lines.insert(
                    i + 3,
                    "        self.file_service = MemoryFileService(self.memories_dir)",
                )
                lines.insert(
                    i + 4,
                    "        self.limits_service = MemoryLimitsService(self.config)",
                )
                lines.insert(
                    i + 5,
                    "        self.memory_limits = self.limits_service.memory_limits",
                )
                break

    # Replace method calls throughout the file
    replacements = [
        (
            "self._get_memory_file_with_migration",
            "self.file_service.get_memory_file_with_migration",
        ),
        (
            "self._save_memory_file(",
            "self._save_memory_file_wrapper(",
        ),  # We'll keep a wrapper
        (
            "self._ensure_memories_directory()",
            "self.file_service.ensure_memories_directory()",
        ),
        ("self._init_memory_limits()", "self.limits_service._init_memory_limits()"),
        ("self._get_agent_limits", "self.limits_service.get_agent_limits"),
        (
            "self._get_agent_auto_learning",
            "self.limits_service.get_agent_auto_learning",
        ),
    ]

    for old, new in replacements:
        for i, line in enumerate(lines):
            if old in line and "def " not in line:  # Don't replace method definitions
                lines[i] = line.replace(old, new)

    # Now remove the extracted methods
    methods_to_remove = [
        "_get_memory_file_with_migration",
        "_ensure_memories_directory",
        "_init_memory_limits",
        "_get_agent_limits",
        "_get_agent_auto_learning",
    ]

    i = 0
    while i < len(lines):
        for method in methods_to_remove:
            if f"def {method}" in lines[i]:
                # Find the end of this method
                indent = len(lines[i]) - len(lines[i].lstrip())
                j = i + 1
                while j < len(lines) and (
                    not lines[j].strip() or lines[j].startswith(" " * (indent + 1))
                ):
                    j += 1
                # Remove the method
                del lines[i:j]
                i -= 1  # Adjust index after deletion
                break
        i += 1

    # Add a wrapper for _save_memory_file since it needs agent_id
    wrapper_code = '''
    def _save_memory_file_wrapper(self, agent_id: str, content: str) -> bool:
        """Wrapper for save_memory_file that handles agent_id.

        Args:
            agent_id: Agent identifier
            content: Content to save

        Returns:
            True if saved successfully
        """
        file_path = self.file_service.get_memory_file_with_migration(
            self.memories_dir, agent_id
        )
        return self.file_service.save_memory_file(file_path, content)
'''

    # Find a good place to add the wrapper (after __init__)
    for i, line in enumerate(lines):
        if "def __init__" in line:
            # Find end of __init__
            j = i + 1
            while j < len(lines) and (not lines[j].strip() or lines[j].startswith(" ")):
                j += 1
            # Insert wrapper
            for wrapper_line in reversed(wrapper_code.strip().split("\n")):
                lines.insert(j, wrapper_line)
            break

    # Remove the old _save_memory_file method
    i = 0
    while i < len(lines):
        if "def _save_memory_file" in lines[i] and "wrapper" not in lines[i]:
            # Find the end of this method
            indent = len(lines[i]) - len(lines[i].lstrip())
            j = i + 1
            while j < len(lines) and (
                not lines[j].strip() or lines[j].startswith(" " * (indent + 1))
            ):
                j += 1
            # Remove the method
            del lines[i:j]
            break
        i += 1

    # Write the updated file
    updated_content = "\n".join(lines)
    manager_path.write_text(updated_content)
    print("✓ Updated agent_memory_manager.py to use new services")


def main():
    """Main refactoring process."""
    print("Starting memory manager refactoring...")
    print("=" * 60)

    # Phase 1: Extract utility services
    print("\nPhase 1: Extracting Utility Services")
    print("-" * 40)

    # Create MemoryFileService
    create_memory_file_service()

    # Create MemoryLimitsService
    create_memory_limits_service()

    # Update agent_memory_manager.py
    update_agent_memory_manager()

    print("\n" + "=" * 60)
    print("Phase 1 Complete! Next steps:")
    print("1. Run tests to verify no regressions")
    print("2. Continue with Phase 2 if tests pass")


if __name__ == "__main__":
    main()

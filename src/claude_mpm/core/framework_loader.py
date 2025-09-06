"""Framework loader for Claude MPM."""

import getpass
import locale
import logging
import os
import platform
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

# Import resource handling for packaged installations
try:
    # Python 3.9+
    from importlib.resources import files
except ImportError:
    # Python 3.8 fallback
    try:
        from importlib_resources import files
    except ImportError:
        # Final fallback for development environments
        files = None

from ..utils.imports import safe_import

# Import with fallback support - using absolute imports as primary since we're at module level
get_logger = safe_import("claude_mpm.core.logger", "core.logger", ["get_logger"])
AgentRegistryAdapter = safe_import(
    "claude_mpm.core.agent_registry", "core.agent_registry", ["AgentRegistryAdapter"]
)

# Import the service container and interfaces
try:
    from claude_mpm.services.core.cache_manager import CacheManager
    from claude_mpm.services.core.memory_manager import MemoryManager
    from claude_mpm.services.core.path_resolver import PathResolver
    from claude_mpm.services.core.service_container import (
        ServiceContainer,
        get_global_container,
    )
    from claude_mpm.services.core.service_interfaces import (
        ICacheManager,
        IMemoryManager,
        IPathResolver,
    )
except ImportError:
    # Fallback for development environments
    from ..services.core.cache_manager import CacheManager
    from ..services.core.memory_manager import MemoryManager
    from ..services.core.path_resolver import PathResolver
    from ..services.core.service_container import ServiceContainer, get_global_container
    from ..services.core.service_interfaces import (
        ICacheManager,
        IMemoryManager,
        IPathResolver,
    )


class FrameworkLoader:
    """
    Load and prepare framework instructions for injection.

    This component handles:
    1. Finding the framework (claude-multiagent-pm)
    2. Loading custom instructions from .claude-mpm/ directories
    3. Preparing agent definitions
    4. Formatting for injection

    Custom Instructions Loading:
    The framework loader supports custom instructions through .claude-mpm/ directories.
    It NEVER reads from .claude/ directories to avoid conflicts with Claude Code.

    File Loading Precedence (highest to lowest):

    INSTRUCTIONS.md:
      1. Project: ./.claude-mpm/INSTRUCTIONS.md
      2. User: ~/.claude-mpm/INSTRUCTIONS.md
      3. System: (built-in framework instructions)

    WORKFLOW.md:
      1. Project: ./.claude-mpm/WORKFLOW.md
      2. User: ~/.claude-mpm/WORKFLOW.md
      3. System: src/claude_mpm/agents/WORKFLOW.md

    MEMORY.md:
      1. Project: ./.claude-mpm/MEMORY.md
      2. User: ~/.claude-mpm/MEMORY.md
      3. System: src/claude_mpm/agents/MEMORY.md

    Actual Memories:
      - User: ~/.claude-mpm/memories/PM_memories.md
      - Project: ./.claude-mpm/memories/PM_memories.md (overrides user)
      - Agent memories: *_memories.md files (only loaded if agent is deployed)

    Important Notes:
    - Project-level files always override user-level files
    - User-level files always override system defaults
    - The framework NEVER reads from .claude/ directories
    - Custom instructions are clearly labeled with their source level
    """

    def __init__(
        self,
        framework_path: Optional[Path] = None,
        agents_dir: Optional[Path] = None,
        service_container: Optional[ServiceContainer] = None,
    ):
        """
        Initialize framework loader.

        Args:
            framework_path: Explicit path to framework (auto-detected if None)
            agents_dir: Custom agents directory (overrides framework agents)
            service_container: Optional service container for dependency injection
        """
        self.logger = get_logger("framework_loader")
        self.agents_dir = agents_dir
        self.framework_version = None
        self.framework_last_modified = None

        # Use provided container or get global container
        self.container = service_container or get_global_container()

        # Register services if not already registered
        if not self.container.is_registered(ICacheManager):
            self.container.register(ICacheManager, CacheManager, True)  # singleton=True

        if not self.container.is_registered(IPathResolver):
            # PathResolver depends on CacheManager, so resolve it first
            cache_manager = self.container.resolve(ICacheManager)
            path_resolver = PathResolver(cache_manager=cache_manager)
            self.container.register_instance(IPathResolver, path_resolver)

        if not self.container.is_registered(IMemoryManager):
            # MemoryManager depends on both CacheManager and PathResolver
            cache_manager = self.container.resolve(ICacheManager)
            path_resolver = self.container.resolve(IPathResolver)
            memory_manager = MemoryManager(
                cache_manager=cache_manager, path_resolver=path_resolver
            )
            self.container.register_instance(IMemoryManager, memory_manager)

        # Resolve services from container
        self._cache_manager = self.container.resolve(ICacheManager)
        self._path_resolver = self.container.resolve(IPathResolver)
        self._memory_manager = self.container.resolve(IMemoryManager)

        # Initialize framework path using PathResolver
        self.framework_path = (
            framework_path or self._path_resolver.detect_framework_path()
        )

        # Keep TTL constants for backward compatibility
        # These are implementation-specific, so we use defaults if not available
        if hasattr(self._cache_manager, "capabilities_ttl"):
            self.CAPABILITIES_CACHE_TTL = self._cache_manager.capabilities_ttl
            self.DEPLOYED_AGENTS_CACHE_TTL = self._cache_manager.deployed_agents_ttl
            self.METADATA_CACHE_TTL = self._cache_manager.metadata_ttl
            self.MEMORIES_CACHE_TTL = self._cache_manager.memories_ttl
        else:
            # Default TTL values
            self.CAPABILITIES_CACHE_TTL = 60
            self.DEPLOYED_AGENTS_CACHE_TTL = 30
            self.METADATA_CACHE_TTL = 60
            self.MEMORIES_CACHE_TTL = 60

        self.framework_content = self._load_framework_content()

        # Initialize agent registry
        self.agent_registry = AgentRegistryAdapter(self.framework_path)

        # Initialize output style manager (must be after content is loaded)
        self.output_style_manager = None
        # Defer initialization until first use to ensure content is loaded

    def clear_all_caches(self) -> None:
        """Clear all caches to force reload on next access."""
        self._cache_manager.clear_all()

    def clear_agent_caches(self) -> None:
        """Clear agent-related caches (capabilities, deployed agents, metadata)."""
        self._cache_manager.clear_agent_caches()

    def clear_memory_caches(self) -> None:
        """Clear memory-related caches."""
        self._cache_manager.clear_memory_caches()

    def _initialize_output_style(self) -> None:
        """Initialize output style management and deploy if applicable."""
        try:
            from claude_mpm.core.output_style_manager import OutputStyleManager

            self.output_style_manager = OutputStyleManager()

            # Log detailed output style status
            self._log_output_style_status()

            # Extract and save output style content (pass self to reuse loaded content)
            output_style_content = (
                self.output_style_manager.extract_output_style_content(
                    framework_loader=self
                )
            )
            self.output_style_manager.save_output_style(output_style_content)

            # Deploy to Claude Code if supported
            deployed = self.output_style_manager.deploy_output_style(
                output_style_content
            )

            if deployed:
                self.logger.info("✅ Output style deployed to Claude Code >= 1.0.83")
            else:
                self.logger.info(
                    "📝 Output style will be injected into instructions for older Claude versions"
                )

        except Exception as e:
            self.logger.warning(f"❌ Failed to initialize output style manager: {e}")
            # Continue without output style management

    def _log_output_style_status(self) -> None:
        """Log comprehensive output style status information."""
        if not self.output_style_manager:
            return

        # Claude version detection
        claude_version = self.output_style_manager.claude_version
        if claude_version:
            self.logger.info(f"Claude Code version detected: {claude_version}")

            # Check if version supports output styles
            if self.output_style_manager.supports_output_styles():
                self.logger.info("✅ Claude Code supports output styles (>= 1.0.83)")

                # Check deployment status
                output_style_path = self.output_style_manager.output_style_path
                if output_style_path.exists():
                    self.logger.info(
                        f"📁 Output style file exists: {output_style_path}"
                    )
                else:
                    self.logger.info(
                        f"📝 Output style will be created at: {output_style_path}"
                    )

            else:
                self.logger.info(
                    f"⚠️ Claude Code {claude_version} does not support output styles (< 1.0.83)"
                )
                self.logger.info(
                    "📝 Output style content will be injected into framework instructions"
                )
        else:
            self.logger.info("⚠️ Claude Code not detected or version unknown")
            self.logger.info(
                "📝 Output style content will be injected into framework instructions as fallback"
            )

    def _try_load_file(self, file_path: Path, file_type: str) -> Optional[str]:
        """
        Try to load a file with error handling.

        Args:
            file_path: Path to the file to load
            file_type: Description of file type for logging

        Returns:
            File content if successful, None otherwise
        """
        try:
            content = file_path.read_text()
            if hasattr(self.logger, "level") and self.logger.level <= logging.INFO:
                self.logger.info(f"Loaded {file_type} from: {file_path}")

            # Extract metadata if present
            import re

            version_match = re.search(r"<!-- FRAMEWORK_VERSION: (\d+) -->", content)
            if version_match:
                version = version_match.group(
                    1
                )  # Keep as string to preserve leading zeros
                self.logger.info(f"Framework version: {version}")
                # Store framework version if this is the main INSTRUCTIONS.md
                if "INSTRUCTIONS.md" in str(file_path):
                    self.framework_version = version

            # Extract modification timestamp
            timestamp_match = re.search(r"<!-- LAST_MODIFIED: ([^>]+) -->", content)
            if timestamp_match:
                timestamp = timestamp_match.group(1).strip()
                self.logger.info(f"Last modified: {timestamp}")
                # Store timestamp if this is the main INSTRUCTIONS.md
                if "INSTRUCTIONS.md" in str(file_path):
                    self.framework_last_modified = timestamp

            return content
        except Exception as e:
            if hasattr(self.logger, "level") and self.logger.level <= logging.ERROR:
                self.logger.error(f"Failed to load {file_type}: {e}")
            return None

    def _load_instructions_file(self, content: Dict[str, Any]) -> None:
        """
        Load custom INSTRUCTIONS.md from .claude-mpm directories.

        Precedence (highest to lowest):
        1. Project-specific: ./.claude-mpm/INSTRUCTIONS.md
        2. User-specific: ~/.claude-mpm/INSTRUCTIONS.md

        NOTE: We do NOT load CLAUDE.md files since Claude Code already picks them up automatically.
        This prevents duplication of instructions.

        Args:
            content: Dictionary to update with loaded instructions
        """
        # Check for project-specific INSTRUCTIONS.md first
        project_instructions_path = Path.cwd() / ".claude-mpm" / "INSTRUCTIONS.md"
        if project_instructions_path.exists():
            loaded_content = self._try_load_file(
                project_instructions_path, "project-specific INSTRUCTIONS.md"
            )
            if loaded_content:
                content["custom_instructions"] = loaded_content
                content["custom_instructions_level"] = "project"
                self.logger.info(
                    "Using project-specific PM instructions from .claude-mpm/INSTRUCTIONS.md"
                )
                return

        # Check for user-specific INSTRUCTIONS.md
        user_instructions_path = Path.home() / ".claude-mpm" / "INSTRUCTIONS.md"
        if user_instructions_path.exists():
            loaded_content = self._try_load_file(
                user_instructions_path, "user-specific INSTRUCTIONS.md"
            )
            if loaded_content:
                content["custom_instructions"] = loaded_content
                content["custom_instructions_level"] = "user"
                self.logger.info(
                    "Using user-specific PM instructions from ~/.claude-mpm/INSTRUCTIONS.md"
                )
                return

    def _load_workflow_instructions(self, content: Dict[str, Any]) -> None:
        """
        Load WORKFLOW.md from .claude-mpm directories.

        Precedence (highest to lowest):
        1. Project-specific: ./.claude-mpm/WORKFLOW.md
        2. User-specific: ~/.claude-mpm/WORKFLOW.md
        3. System default: src/claude_mpm/agents/WORKFLOW.md or packaged

        NOTE: We do NOT load from .claude/ directories to avoid conflicts.

        Args:
            content: Dictionary to update with workflow instructions
        """
        # Check for project-specific WORKFLOW.md first (highest priority)
        project_workflow_path = Path.cwd() / ".claude-mpm" / "WORKFLOW.md"
        if project_workflow_path.exists():
            loaded_content = self._try_load_file(
                project_workflow_path, "project-specific WORKFLOW.md"
            )
            if loaded_content:
                content["workflow_instructions"] = loaded_content
                content["workflow_instructions_level"] = "project"
                self.logger.info(
                    "Using project-specific workflow instructions from .claude-mpm/WORKFLOW.md"
                )
                return

        # Check for user-specific WORKFLOW.md (medium priority)
        user_workflow_path = Path.home() / ".claude-mpm" / "WORKFLOW.md"
        if user_workflow_path.exists():
            loaded_content = self._try_load_file(
                user_workflow_path, "user-specific WORKFLOW.md"
            )
            if loaded_content:
                content["workflow_instructions"] = loaded_content
                content["workflow_instructions_level"] = "user"
                self.logger.info(
                    "Using user-specific workflow instructions from ~/.claude-mpm/WORKFLOW.md"
                )
                return

        # Fall back to system workflow (lowest priority)
        if self.framework_path and self.framework_path != Path("__PACKAGED__"):
            system_workflow_path = (
                self.framework_path / "src" / "claude_mpm" / "agents" / "WORKFLOW.md"
            )
            if system_workflow_path.exists():
                loaded_content = self._try_load_file(
                    system_workflow_path, "system WORKFLOW.md"
                )
                if loaded_content:
                    content["workflow_instructions"] = loaded_content
                    content["workflow_instructions_level"] = "system"
                    self.logger.info("Using system workflow instructions")

    def _load_memory_instructions(self, content: Dict[str, Any]) -> None:
        """
        Load MEMORY.md from .claude-mpm directories.

        Precedence (highest to lowest):
        1. Project-specific: ./.claude-mpm/MEMORY.md
        2. User-specific: ~/.claude-mpm/MEMORY.md
        3. System default: src/claude_mpm/agents/MEMORY.md or packaged

        NOTE: We do NOT load from .claude/ directories to avoid conflicts.

        Args:
            content: Dictionary to update with memory instructions
        """
        # Check for project-specific MEMORY.md first (highest priority)
        project_memory_path = Path.cwd() / ".claude-mpm" / "MEMORY.md"
        if project_memory_path.exists():
            loaded_content = self._try_load_file(
                project_memory_path, "project-specific MEMORY.md"
            )
            if loaded_content:
                content["memory_instructions"] = loaded_content
                content["memory_instructions_level"] = "project"
                self.logger.info(
                    "Using project-specific memory instructions from .claude-mpm/MEMORY.md"
                )
                return

        # Check for user-specific MEMORY.md (medium priority)
        user_memory_path = Path.home() / ".claude-mpm" / "MEMORY.md"
        if user_memory_path.exists():
            loaded_content = self._try_load_file(
                user_memory_path, "user-specific MEMORY.md"
            )
            if loaded_content:
                content["memory_instructions"] = loaded_content
                content["memory_instructions_level"] = "user"
                self.logger.info(
                    "Using user-specific memory instructions from ~/.claude-mpm/MEMORY.md"
                )
                return

        # Fall back to system memory instructions (lowest priority)
        if self.framework_path and self.framework_path != Path("__PACKAGED__"):
            system_memory_path = (
                self.framework_path / "src" / "claude_mpm" / "agents" / "MEMORY.md"
            )
            if system_memory_path.exists():
                loaded_content = self._try_load_file(
                    system_memory_path, "system MEMORY.md"
                )
                if loaded_content:
                    content["memory_instructions"] = loaded_content
                    content["memory_instructions_level"] = "system"
                    self.logger.info("Using system memory instructions")

    def _get_deployed_agents(self) -> set:
        """
        Get a set of deployed agent names from .claude/agents/ directories.
        Uses caching to avoid repeated filesystem scans.

        Returns:
            Set of agent names (file stems) that are deployed
        """
        # Try to get from cache first
        cached = self._cache_manager.get_deployed_agents()
        if cached is not None:
            return cached

        # Cache miss or expired - perform actual scan
        self.logger.debug("Scanning for deployed agents (cache miss or expired)")
        deployed = set()

        # Check multiple locations for deployed agents
        agents_dirs = [
            Path.cwd() / ".claude" / "agents",  # Project-specific agents
            Path.home() / ".claude" / "agents",  # User's system agents
        ]

        for agents_dir in agents_dirs:
            if agents_dir.exists():
                for agent_file in agents_dir.glob("*.md"):
                    if not agent_file.name.startswith("."):
                        # Use stem to get agent name without extension
                        deployed.add(agent_file.stem)
                        self.logger.debug(
                            f"Found deployed agent: {agent_file.stem} in {agents_dir}"
                        )

        self.logger.debug(f"Total deployed agents found: {len(deployed)}")

        # Update cache
        self._cache_manager.set_deployed_agents(deployed)

        return deployed

    def _load_actual_memories(self, content: Dict[str, Any]) -> None:
        """
        Load actual memories using the MemoryManager service.

        This method delegates all memory loading operations to the MemoryManager,
        which handles caching, aggregation, deduplication, and legacy format migration.

        Args:
            content: Dictionary to update with actual memories
        """
        # Use MemoryManager to load all memories
        memories = self._memory_manager.load_memories()

        # Apply loaded memories to content
        if "actual_memories" in memories:
            content["actual_memories"] = memories["actual_memories"]
        if "agent_memories" in memories:
            content["agent_memories"] = memories["agent_memories"]

    def _load_single_agent(
        self, agent_file: Path
    ) -> tuple[Optional[str], Optional[str]]:
        """
        Load a single agent file.

        Args:
            agent_file: Path to the agent file

        Returns:
            Tuple of (agent_name, agent_content) or (None, None) on failure
        """
        try:
            agent_name = agent_file.stem
            # Skip README files
            if agent_name.upper() == "README":
                return None, None
            content = agent_file.read_text()
            self.logger.debug(f"Loaded agent: {agent_name}")
            return agent_name, content
        except Exception as e:
            self.logger.error(f"Failed to load agent {agent_file}: {e}")
            return None, None

    def _load_base_agent_fallback(
        self, content: Dict[str, Any], main_dir: Optional[Path]
    ) -> None:
        """
        Load base_agent.md from main directory as fallback.

        Args:
            content: Dictionary to update with base agent
            main_dir: Main agents directory path
        """
        if main_dir and main_dir.exists() and "base_agent" not in content["agents"]:
            base_agent_file = main_dir / "base_agent.md"
            if base_agent_file.exists():
                agent_name, agent_content = self._load_single_agent(base_agent_file)
                if agent_name and agent_content:
                    content["agents"][agent_name] = agent_content

    def _load_agents_directory(
        self,
        content: Dict[str, Any],
        agents_dir: Optional[Path],
        templates_dir: Optional[Path],
        main_dir: Optional[Path],
    ) -> None:
        """
        Load agent definitions from the appropriate directory.

        Args:
            content: Dictionary to update with loaded agents
            agents_dir: Primary agents directory to load from
            templates_dir: Templates directory path
            main_dir: Main agents directory path
        """
        if not agents_dir or not agents_dir.exists():
            return

        content["loaded"] = True

        # Load all agent files
        for agent_file in agents_dir.glob("*.md"):
            agent_name, agent_content = self._load_single_agent(agent_file)
            if agent_name and agent_content:
                content["agents"][agent_name] = agent_content

        # If we used templates dir, also check main dir for base_agent.md
        if agents_dir == templates_dir:
            self._load_base_agent_fallback(content, main_dir)

    def _load_framework_content(self) -> Dict[str, Any]:
        """Load framework content."""
        content = {
            "claude_md": "",
            "agents": {},
            "version": "unknown",
            "loaded": False,
            "working_claude_md": "",
            "framework_instructions": "",
            "workflow_instructions": "",
            "workflow_instructions_level": "",  # Track source level
            "memory_instructions": "",
            "memory_instructions_level": "",  # Track source level
            "project_workflow": "",  # Deprecated, use workflow_instructions_level
            "project_memory": "",  # Deprecated, use memory_instructions_level
            "actual_memories": "",  # Add field for actual memories from PM_memories.md
        }

        # Load instructions file from working directory
        self._load_instructions_file(content)

        if not self.framework_path:
            return content

        # Check if this is a packaged installation
        if self.framework_path == Path("__PACKAGED__"):
            # Load files using importlib.resources for packaged installations
            self._load_packaged_framework_content(content)
        else:
            # Load from filesystem for development mode
            # Load framework's INSTRUCTIONS.md
            framework_instructions_path = (
                self.framework_path
                / "src"
                / "claude_mpm"
                / "agents"
                / "INSTRUCTIONS.md"
            )
            if framework_instructions_path.exists():
                loaded_content = self._try_load_file(
                    framework_instructions_path, "framework INSTRUCTIONS.md"
                )
                if loaded_content:
                    content["framework_instructions"] = loaded_content
                    content["loaded"] = True
                    # Add framework version to content
                    if self.framework_version:
                        content["instructions_version"] = self.framework_version
                        content["version"] = (
                            self.framework_version
                        )  # Update main version key
                    # Add modification timestamp to content
                    if self.framework_last_modified:
                        content["instructions_last_modified"] = (
                            self.framework_last_modified
                        )

            # Load BASE_PM.md for core framework requirements
            base_pm_path = (
                self.framework_path / "src" / "claude_mpm" / "agents" / "BASE_PM.md"
            )
            if base_pm_path.exists():
                base_pm_content = self._try_load_file(
                    base_pm_path, "BASE_PM framework requirements"
                )
                if base_pm_content:
                    content["base_pm_instructions"] = base_pm_content

        # Load WORKFLOW.md - check for project-specific first, then system
        self._load_workflow_instructions(content)

        # Load MEMORY.md - check for project-specific first, then system
        self._load_memory_instructions(content)

        # Load actual memories from .claude-mpm/memories/PM_memories.md
        self._load_actual_memories(content)

        # Discover agent directories using PathResolver
        agents_dir, templates_dir, main_dir = self._path_resolver.discover_agent_paths(
            agents_dir=self.agents_dir, framework_path=self.framework_path
        )

        # Load agents from discovered directory
        self._load_agents_directory(content, agents_dir, templates_dir, main_dir)

        return content

    def _load_packaged_framework_content(self, content: Dict[str, Any]) -> None:
        """Load framework content from packaged installation using importlib.resources."""
        if not files:
            self.logger.warning(
                "importlib.resources not available, cannot load packaged framework"
            )
            self.logger.debug(f"files variable is: {files}")
            # Try alternative import methods
            try:
                from importlib import resources

                self.logger.info("Using importlib.resources as fallback")
                self._load_packaged_framework_content_fallback(content, resources)
                return
            except ImportError:
                self.logger.error(
                    "No importlib.resources available, using minimal framework"
                )
                return

        try:
            # Load INSTRUCTIONS.md
            instructions_content = self._load_packaged_file("INSTRUCTIONS.md")
            if instructions_content:
                content["framework_instructions"] = instructions_content
                content["loaded"] = True
                # Extract and store version/timestamp metadata
                self._extract_metadata_from_content(
                    instructions_content, "INSTRUCTIONS.md"
                )
                if self.framework_version:
                    content["instructions_version"] = self.framework_version
                    content["version"] = self.framework_version
                if self.framework_last_modified:
                    content["instructions_last_modified"] = self.framework_last_modified

            # Load BASE_PM.md
            base_pm_content = self._load_packaged_file("BASE_PM.md")
            if base_pm_content:
                content["base_pm_instructions"] = base_pm_content

            # Load WORKFLOW.md
            workflow_content = self._load_packaged_file("WORKFLOW.md")
            if workflow_content:
                content["workflow_instructions"] = workflow_content
                content["project_workflow"] = "system"

            # Load MEMORY.md
            memory_content = self._load_packaged_file("MEMORY.md")
            if memory_content:
                content["memory_instructions"] = memory_content
                content["project_memory"] = "system"

        except Exception as e:
            self.logger.error(f"Failed to load packaged framework content: {e}")

    def _load_packaged_framework_content_fallback(
        self, content: Dict[str, Any], resources
    ) -> None:
        """Load framework content using importlib.resources fallback."""
        try:
            # Load INSTRUCTIONS.md
            instructions_content = self._load_packaged_file_fallback(
                "INSTRUCTIONS.md", resources
            )
            if instructions_content:
                content["framework_instructions"] = instructions_content
                content["loaded"] = True
                # Extract and store version/timestamp metadata
                self._extract_metadata_from_content(
                    instructions_content, "INSTRUCTIONS.md"
                )
                if self.framework_version:
                    content["instructions_version"] = self.framework_version
                    content["version"] = self.framework_version
                if self.framework_last_modified:
                    content["instructions_last_modified"] = self.framework_last_modified

            # Load BASE_PM.md
            base_pm_content = self._load_packaged_file_fallback("BASE_PM.md", resources)
            if base_pm_content:
                content["base_pm_instructions"] = base_pm_content

            # Load WORKFLOW.md
            workflow_content = self._load_packaged_file_fallback(
                "WORKFLOW.md", resources
            )
            if workflow_content:
                content["workflow_instructions"] = workflow_content
                content["project_workflow"] = "system"

            # Load MEMORY.md
            memory_content = self._load_packaged_file_fallback("MEMORY.md", resources)
            if memory_content:
                content["memory_instructions"] = memory_content
                content["project_memory"] = "system"

        except Exception as e:
            self.logger.error(
                f"Failed to load packaged framework content with fallback: {e}"
            )

    def _load_packaged_file_fallback(self, filename: str, resources) -> Optional[str]:
        """Load a file from the packaged installation using importlib.resources fallback."""
        try:
            # Try different resource loading methods
            try:
                # Method 1: resources.read_text (Python 3.9+)
                content = resources.read_text("claude_mpm.agents", filename)
                self.logger.info(f"Loaded {filename} from package using read_text")
                return content
            except AttributeError:
                # Method 2: resources.files (Python 3.9+)
                agents_files = resources.files("claude_mpm.agents")
                file_path = agents_files / filename
                if file_path.is_file():
                    content = file_path.read_text()
                    self.logger.info(f"Loaded {filename} from package using files")
                    return content
                self.logger.warning(f"File {filename} not found in package")
                return None
        except Exception as e:
            self.logger.error(
                f"Failed to load {filename} from package with fallback: {e}"
            )
            return None

    def _load_packaged_file(self, filename: str) -> Optional[str]:
        """Load a file from the packaged installation."""
        try:
            # Use importlib.resources to load file from package
            agents_package = files("claude_mpm.agents")
            file_path = agents_package / filename

            if file_path.is_file():
                content = file_path.read_text()
                self.logger.info(f"Loaded {filename} from package")
                return content
            self.logger.warning(f"File {filename} not found in package")
            return None
        except Exception as e:
            self.logger.error(f"Failed to load {filename} from package: {e}")
            return None

    def _extract_metadata_from_content(self, content: str, filename: str) -> None:
        """Extract metadata from content string."""
        import re

        # Extract version
        version_match = re.search(r"<!-- FRAMEWORK_VERSION: (\d+) -->", content)
        if version_match and "INSTRUCTIONS.md" in filename:
            self.framework_version = version_match.group(1)
            self.logger.info(f"Framework version: {self.framework_version}")

        # Extract timestamp
        timestamp_match = re.search(r"<!-- LAST_MODIFIED: ([^>]+) -->", content)
        if timestamp_match and "INSTRUCTIONS.md" in filename:
            self.framework_last_modified = timestamp_match.group(1).strip()
            self.logger.info(f"Last modified: {self.framework_last_modified}")

    def get_framework_instructions(self) -> str:
        """
        Get formatted framework instructions for injection.

        Returns:
            Complete framework instructions ready for injection
        """
        # Import LogManager for prompt logging
        try:
            from .log_manager import get_log_manager

            log_manager = get_log_manager()
        except ImportError:
            log_manager = None

        # Generate the instructions
        if self.framework_content["loaded"]:
            # Build framework from components
            instructions = self._format_full_framework()
        else:
            # Use minimal fallback
            instructions = self._format_minimal_framework()

        # Log the system prompt if LogManager is available
        if log_manager:
            try:
                import asyncio
                import os

                # Get or create event loop
                try:
                    loop = asyncio.get_running_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)

                # Prepare metadata
                metadata = {
                    "framework_version": self.framework_version,
                    "framework_loaded": self.framework_content.get("loaded", False),
                    "session_id": os.environ.get("CLAUDE_SESSION_ID", "unknown"),
                    "instructions_length": len(instructions),
                }

                # Log the prompt asynchronously
                if loop.is_running():
                    asyncio.create_task(
                        log_manager.log_prompt("system_prompt", instructions, metadata)
                    )
                else:
                    loop.run_until_complete(
                        log_manager.log_prompt("system_prompt", instructions, metadata)
                    )

                self.logger.debug("System prompt logged to prompts directory")
            except Exception as e:
                self.logger.debug(f"Could not log system prompt: {e}")

        return instructions

    def _strip_metadata_comments(self, content: str) -> str:
        """Strip metadata HTML comments from content.

        Removes comments like:
        <!-- FRAMEWORK_VERSION: 0010 -->
        <!-- LAST_MODIFIED: 2025-08-10T00:00:00Z -->
        """
        import re

        # Remove HTML comments that contain metadata
        cleaned = re.sub(
            r"<!--\s*(FRAMEWORK_VERSION|LAST_MODIFIED|WORKFLOW_VERSION|PROJECT_WORKFLOW_VERSION|CUSTOM_PROJECT_WORKFLOW)[^>]*-->\n?",
            "",
            content,
        )
        # Also remove any leading blank lines that might result
        return cleaned.lstrip("\n")

    def _format_full_framework(self) -> str:
        """Format full framework instructions."""

        # Initialize output style manager on first use (ensures content is loaded)
        if self.output_style_manager is None:
            self._initialize_output_style()

        # Check if we need to inject output style content for older Claude versions
        inject_output_style = False
        if self.output_style_manager:
            inject_output_style = self.output_style_manager.should_inject_content()
            if inject_output_style:
                self.logger.info(
                    "Injecting output style content into instructions for Claude < 1.0.83"
                )

        # If we have the full framework INSTRUCTIONS.md, use it
        if self.framework_content.get("framework_instructions"):
            instructions = self._strip_metadata_comments(
                self.framework_content["framework_instructions"]
            )

            # Note: We don't add working directory CLAUDE.md here since Claude Code
            # already picks it up automatically. This prevents duplication.

            # Add custom INSTRUCTIONS.md if present (overrides or extends framework instructions)
            if self.framework_content.get("custom_instructions"):
                level = self.framework_content.get(
                    "custom_instructions_level", "unknown"
                )
                instructions += f"\n\n## Custom PM Instructions ({level} level)\n\n"
                instructions += "**The following custom instructions override or extend the framework defaults:**\n\n"
                instructions += self._strip_metadata_comments(
                    self.framework_content["custom_instructions"]
                )
                instructions += "\n"

            # Add WORKFLOW.md after instructions
            if self.framework_content.get("workflow_instructions"):
                workflow_content = self._strip_metadata_comments(
                    self.framework_content["workflow_instructions"]
                )
                level = self.framework_content.get(
                    "workflow_instructions_level", "system"
                )
                if level != "system":
                    instructions += f"\n\n## Workflow Instructions ({level} level)\n\n"
                    instructions += "**The following workflow instructions override system defaults:**\n\n"
                instructions += f"{workflow_content}\n"

            # Add MEMORY.md after workflow instructions
            if self.framework_content.get("memory_instructions"):
                memory_content = self._strip_metadata_comments(
                    self.framework_content["memory_instructions"]
                )
                level = self.framework_content.get(
                    "memory_instructions_level", "system"
                )
                if level != "system":
                    instructions += f"\n\n## Memory Instructions ({level} level)\n\n"
                    instructions += "**The following memory instructions override system defaults:**\n\n"
                instructions += f"{memory_content}\n"

            # Add actual PM memories after memory instructions
            if self.framework_content.get("actual_memories"):
                instructions += "\n\n## Current PM Memories\n\n"
                instructions += "**The following are your accumulated memories and knowledge from this project:**\n\n"
                instructions += self.framework_content["actual_memories"]
                instructions += "\n"

            # Add agent memories if available
            if self.framework_content.get("agent_memories"):
                agent_memories = self.framework_content["agent_memories"]
                if agent_memories:
                    instructions += "\n\n## Agent Memories\n\n"
                    instructions += "**The following are accumulated memories from specialized agents:**\n\n"

                    for agent_name in sorted(agent_memories.keys()):
                        memory_content = agent_memories[agent_name]
                        if memory_content:
                            instructions += f"### {agent_name.replace('_', ' ').title()} Agent Memory\n\n"
                            instructions += memory_content
                            instructions += "\n\n"

            # Add dynamic agent capabilities section
            instructions += self._generate_agent_capabilities_section()

            # Add enhanced temporal and user context for better awareness
            instructions += self._generate_temporal_user_context()

            # Add BASE_PM.md framework requirements AFTER INSTRUCTIONS.md
            if self.framework_content.get("base_pm_instructions"):
                base_pm = self._strip_metadata_comments(
                    self.framework_content["base_pm_instructions"]
                )
                instructions += f"\n\n{base_pm}"

            # Inject output style content if needed (for Claude < 1.0.83)
            if inject_output_style and self.output_style_manager:
                output_style_content = self.output_style_manager.get_injectable_content(
                    framework_loader=self
                )
                if output_style_content:
                    instructions += "\n\n## Output Style Configuration\n"
                    instructions += "**Note: The following output style is injected for Claude < 1.0.83**\n\n"
                    instructions += output_style_content
                    instructions += "\n"

            # Clean up any trailing whitespace
            return instructions.rstrip() + "\n"

        # Otherwise fall back to generating framework
        instructions = """# Claude MPM Framework Instructions

You are operating within the Claude Multi-Agent Project Manager (MPM) framework.

## Core Role
You are a multi-agent orchestrator. Your primary responsibilities are:
- Delegate all implementation work to specialized agents via Task Tool
- Coordinate multi-agent workflows and cross-agent collaboration
- Extract and track TODO/BUG/FEATURE items for ticket creation
- Maintain project visibility and strategic oversight
- NEVER perform direct implementation work yourself

"""

        # Note: We don't add working directory CLAUDE.md here since Claude Code
        # already picks it up automatically. This prevents duplication.

        # Add agent definitions
        if self.framework_content["agents"]:
            instructions += "## Available Agents\n\n"
            instructions += "You have the following specialized agents available for delegation:\n\n"

            # List agents with brief descriptions and correct IDs
            agent_list = []
            for agent_name in sorted(self.framework_content["agents"].keys()):
                # Use the actual agent_name as the ID (it's the filename stem)
                agent_id = agent_name
                clean_name = agent_name.replace("-", " ").replace("_", " ").title()
                if (
                    "engineer" in agent_name.lower()
                    and "data" not in agent_name.lower()
                ):
                    agent_list.append(
                        f"- **Engineer Agent** (`{agent_id}`): Code implementation and development"
                    )
                elif "qa" in agent_name.lower():
                    agent_list.append(
                        f"- **QA Agent** (`{agent_id}`): Testing and quality assurance"
                    )
                elif "documentation" in agent_name.lower():
                    agent_list.append(
                        f"- **Documentation Agent** (`{agent_id}`): Documentation creation and maintenance"
                    )
                elif "research" in agent_name.lower():
                    agent_list.append(
                        f"- **Research Agent** (`{agent_id}`): Investigation and analysis"
                    )
                elif "security" in agent_name.lower():
                    agent_list.append(
                        f"- **Security Agent** (`{agent_id}`): Security analysis and protection"
                    )
                elif "version" in agent_name.lower():
                    agent_list.append(
                        f"- **Version Control Agent** (`{agent_id}`): Git operations and version management"
                    )
                elif "ops" in agent_name.lower():
                    agent_list.append(
                        f"- **Ops Agent** (`{agent_id}`): Deployment and operations"
                    )
                elif "data" in agent_name.lower():
                    agent_list.append(
                        f"- **Data Engineer Agent** (`{agent_id}`): Data management and AI API integration"
                    )
                else:
                    agent_list.append(
                        f"- **{clean_name}** (`{agent_id}`): Available for specialized tasks"
                    )

            instructions += "\n".join(agent_list) + "\n\n"

            # Add full agent details
            instructions += "### Agent Details\n\n"
            for agent_name, agent_content in sorted(
                self.framework_content["agents"].items()
            ):
                instructions += f"#### {agent_name.replace('-', ' ').title()}\n"
                instructions += agent_content + "\n\n"

        # Add orchestration principles
        instructions += """
## Orchestration Principles
1. **Always Delegate**: Never perform direct work - use Task Tool for all implementation
2. **Comprehensive Context**: Provide rich, filtered context to each agent
3. **Track Everything**: Extract all TODO/BUG/FEATURE items systematically
4. **Cross-Agent Coordination**: Orchestrate workflows spanning multiple agents
5. **Results Integration**: Actively receive and integrate agent results

## Task Tool Format
```
**[Agent Name]**: [Clear task description with deliverables]

TEMPORAL CONTEXT: Today is [date]. Apply date awareness to [specific considerations].

**Task**: [Detailed task breakdown]
1. [Specific action item 1]
2. [Specific action item 2]
3. [Specific action item 3]

**Context**: [Comprehensive filtered context for this agent]
**Authority**: [Agent's decision-making scope]
**Expected Results**: [Specific deliverables needed]
**Integration**: [How results integrate with other work]
```

## Ticket Extraction Patterns
Extract tickets from these patterns:
- TODO: [description] → TODO ticket
- BUG: [description] → BUG ticket
- FEATURE: [description] → FEATURE ticket
- ISSUE: [description] → ISSUE ticket
- FIXME: [description] → BUG ticket

---
"""

        return instructions

    def _generate_agent_capabilities_section(self) -> str:
        """Generate dynamic agent capabilities section from deployed agents.
        Uses caching to avoid repeated file I/O and parsing operations.

        Now includes support for local JSON templates with proper priority:
        1. Project local agents (.claude-mpm/agents/*.json) - highest priority
        2. Deployed project agents (.claude/agents/*.md)
        3. User local agents (~/.claude-mpm/agents/*.json)
        4. Deployed user agents (~/.claude/agents/*.md)
        5. System agents - lowest priority
        """

        # Try to get from cache first
        cached_capabilities = self._cache_manager.get_capabilities()
        if cached_capabilities is not None:
            return cached_capabilities

        # Will be used for updating cache later
        current_time = time.time()

        # Cache miss or expired - generate capabilities
        self.logger.debug("Generating agent capabilities (cache miss or expired)")

        try:
            from pathlib import Path

            # First check for local JSON templates (highest priority)
            local_agents = self._discover_local_json_templates()

            # Read directly from deployed agents in .claude/agents/
            # Check multiple locations for deployed agents
            # Priority order: local templates > project > user home > fallback
            agents_dirs = [
                Path.cwd() / ".claude" / "agents",  # Project-specific agents
                Path.home() / ".claude" / "agents",  # User's system agents
            ]

            # Collect agents from all directories with proper precedence
            # Local agents override deployed agents with the same name
            # Project agents override user agents with the same name
            all_agents = {}  # key: agent_id, value: (agent_data, priority)

            # Add local agents first (highest priority)
            for agent_id, agent_data in local_agents.items():
                all_agents[agent_id] = (agent_data, -1)  # Priority -1 for local agents

            for priority, potential_dir in enumerate(agents_dirs):
                if potential_dir.exists() and any(potential_dir.glob("*.md")):
                    self.logger.debug(f"Found agents directory at: {potential_dir}")

                    # Collect agents from this directory
                    for agent_file in potential_dir.glob("*.md"):
                        if agent_file.name.startswith("."):
                            continue

                        # Parse agent metadata (with caching)
                        agent_data = self._parse_agent_metadata(agent_file)
                        if agent_data:
                            agent_id = agent_data["id"]
                            # Only add if not already present (project has priority 0, user has priority 1)
                            # Lower priority number wins (project > user)
                            if (
                                agent_id not in all_agents
                                or priority < all_agents[agent_id][1]
                            ):
                                all_agents[agent_id] = (agent_data, priority)
                                self.logger.debug(
                                    f"Added/Updated agent {agent_id} from {potential_dir} (priority {priority})"
                                )

            if not all_agents:
                self.logger.warning(f"No agents found in any location: {agents_dirs}")
                result = self._get_fallback_capabilities()
                # Cache the fallback result too
                self._cache_manager.set_capabilities(result)
                return result

            # Log agent collection summary
            project_agents = [aid for aid, (_, pri) in all_agents.items() if pri == 0]
            user_agents = [aid for aid, (_, pri) in all_agents.items() if pri == 1]

            # Include local agents in logging
            local_json_agents = [
                aid for aid, (_, pri) in all_agents.items() if pri == -1
            ]
            if local_json_agents:
                self.logger.info(
                    f"Loaded {len(local_json_agents)} local JSON agents: {', '.join(sorted(local_json_agents))}"
                )
            if project_agents:
                self.logger.info(
                    f"Loaded {len(project_agents)} project agents: {', '.join(sorted(project_agents))}"
                )
            if user_agents:
                self.logger.info(
                    f"Loaded {len(user_agents)} user agents: {', '.join(sorted(user_agents))}"
                )

            # Build capabilities section
            section = "\n\n## Available Agent Capabilities\n\n"

            # Extract just the agent data (drop priority info) and sort
            deployed_agents = [agent_data for agent_data, _ in all_agents.values()]

            if not deployed_agents:
                result = self._get_fallback_capabilities()
                # Cache the fallback result
                self._cache_manager.set_capabilities(result)
                return result

            # Sort agents alphabetically by ID
            deployed_agents.sort(key=lambda x: x["id"])

            # Display all agents with their rich descriptions
            for agent in deployed_agents:
                # Clean up display name - handle common acronyms
                display_name = agent["display_name"]
                display_name = (
                    display_name.replace("Qa ", "QA ")
                    .replace("Ui ", "UI ")
                    .replace("Api ", "API ")
                )
                if display_name.lower() == "qa agent":
                    display_name = "QA Agent"

                # Add local indicator if this is a local agent
                if agent.get("is_local"):
                    tier_label = f" [LOCAL-{agent.get('tier', 'PROJECT').upper()}]"
                    section += f"\n### {display_name} (`{agent['id']}`) {tier_label}\n"
                else:
                    section += f"\n### {display_name} (`{agent['id']}`)\n"
                section += f"{agent['description']}\n"

                # Add routing information if available
                if agent.get("routing"):
                    routing = agent["routing"]

                    # Format routing hints for PM usage
                    routing_hints = []

                    if routing.get("keywords"):
                        # Show first 5 keywords for brevity
                        keywords = routing["keywords"][:5]
                        routing_hints.append(f"Keywords: {', '.join(keywords)}")

                    if routing.get("paths"):
                        # Show first 3 paths for brevity
                        paths = routing["paths"][:3]
                        routing_hints.append(f"Paths: {', '.join(paths)}")

                    if routing.get("priority"):
                        routing_hints.append(f"Priority: {routing['priority']}")

                    if routing_hints:
                        section += f"- **Routing**: {' | '.join(routing_hints)}\n"

                    # Add when_to_use if present
                    if routing.get("when_to_use"):
                        section += f"- **When to use**: {routing['when_to_use']}\n"

                # Add any additional metadata if present
                if agent.get("authority"):
                    section += f"- **Authority**: {agent['authority']}\n"
                if agent.get("primary_function"):
                    section += f"- **Primary Function**: {agent['primary_function']}\n"
                if agent.get("handoff_to"):
                    section += f"- **Handoff To**: {agent['handoff_to']}\n"
                if agent.get("tools") and agent["tools"] != "standard":
                    section += f"- **Tools**: {agent['tools']}\n"
                if agent.get("model") and agent["model"] != "opus":
                    section += f"- **Model**: {agent['model']}\n"

                # Add memory routing information if available
                if agent.get("memory_routing"):
                    memory_routing = agent["memory_routing"]
                    if memory_routing.get("description"):
                        section += (
                            f"- **Memory Routing**: {memory_routing['description']}\n"
                        )

            # Add simple Context-Aware Agent Selection
            section += "\n## Context-Aware Agent Selection\n\n"
            section += (
                "Select agents based on their descriptions above. Key principles:\n"
            )
            section += "- **PM questions** → Answer directly (only exception)\n"
            section += "- Match task requirements to agent descriptions and authority\n"
            section += "- Consider agent handoff recommendations\n"
            section += (
                "- Use the agent ID in parentheses when delegating via Task tool\n"
            )

            # Add summary
            section += f"\n**Total Available Agents**: {len(deployed_agents)}\n"

            # Cache the generated capabilities
            self._cache_manager.set_capabilities(section)
            self.logger.debug(
                f"Cached agent capabilities section ({len(section)} chars)"
            )

            return section

        except Exception as e:
            self.logger.warning(f"Could not generate dynamic agent capabilities: {e}")
            result = self._get_fallback_capabilities()
            # Cache even the fallback result
            self._agent_capabilities_cache = result
            self._agent_capabilities_cache_time = current_time
            return result

    def _generate_temporal_user_context(self) -> str:
        """Generate enhanced temporal and user context for better PM awareness.

        Returns:
            str: Formatted context string with datetime, user, and system information
        """
        context_lines = ["\n\n## Temporal & User Context\n"]

        try:
            # Get current datetime with timezone awareness
            now = datetime.now()

            # Try to get timezone info - fallback to UTC offset if timezone name not available
            try:
                import time as time_module

                if hasattr(time_module, "tzname"):
                    tz_name = time_module.tzname[time_module.daylight]
                    tz_offset = time_module.strftime("%z")
                    if tz_offset:
                        # Format UTC offset properly (e.g., -0800 to -08:00)
                        tz_offset = (
                            f"{tz_offset[:3]}:{tz_offset[3:]}"
                            if len(tz_offset) >= 4
                            else tz_offset
                        )
                        tz_info = f"{tz_name} (UTC{tz_offset})"
                    else:
                        tz_info = tz_name
                else:
                    tz_info = "Local Time"
            except Exception:
                tz_info = "Local Time"

            # Format datetime components
            date_str = now.strftime("%Y-%m-%d")
            time_str = now.strftime("%H:%M:%S")
            day_name = now.strftime("%A")

            context_lines.append(
                f"**Current DateTime**: {date_str} {time_str} {tz_info}\n"
            )
            context_lines.append(f"**Day**: {day_name}\n")

        except Exception as e:
            # Fallback to basic date if enhanced datetime fails
            self.logger.debug(f"Error generating enhanced datetime context: {e}")
            context_lines.append(
                f"**Today's Date**: {datetime.now().strftime('%Y-%m-%d')}\n"
            )

        try:
            # Get user information with safe fallbacks
            username = None

            # Try multiple methods to get username
            methods = [
                lambda: os.environ.get("USER"),
                lambda: os.environ.get("USERNAME"),  # Windows fallback
                lambda: getpass.getuser(),
            ]

            for method in methods:
                try:
                    username = method()
                    if username:
                        break
                except Exception:
                    continue

            if username:
                context_lines.append(f"**User**: {username}\n")

                # Add home directory if available
                try:
                    home_dir = os.path.expanduser("~")
                    if home_dir and home_dir != "~":
                        context_lines.append(f"**Home Directory**: {home_dir}\n")
                except Exception:
                    pass

        except Exception as e:
            # User detection is optional, don't fail
            self.logger.debug(f"Could not detect user information: {e}")

        try:
            # Get system information
            system_info = platform.system()
            if system_info:
                # Enhance system name for common platforms
                system_names = {
                    "Darwin": "Darwin (macOS)",
                    "Linux": "Linux",
                    "Windows": "Windows",
                }
                system_display = system_names.get(system_info, system_info)
                context_lines.append(f"**System**: {system_display}\n")

                # Add platform version if available
                try:
                    platform_version = platform.release()
                    if platform_version:
                        context_lines.append(
                            f"**System Version**: {platform_version}\n"
                        )
                except Exception:
                    pass

        except Exception as e:
            # System info is optional
            self.logger.debug(f"Could not detect system information: {e}")

        try:
            # Add current working directory
            cwd = os.getcwd()
            if cwd:
                context_lines.append(f"**Working Directory**: {cwd}\n")
        except Exception:
            pass

        try:
            # Add locale information if available
            current_locale = locale.getlocale()
            if current_locale and current_locale[0]:
                context_lines.append(f"**Locale**: {current_locale[0]}\n")
        except Exception:
            # Locale is optional
            pass

        # Add instruction for applying context
        context_lines.append(
            "\nApply temporal and user awareness to all tasks, "
            "decisions, and interactions.\n"
        )
        context_lines.append(
            "Use this context for personalized responses and "
            "time-sensitive operations.\n"
        )

        return "".join(context_lines)

    def _parse_agent_metadata(self, agent_file: Path) -> Optional[Dict[str, Any]]:
        """Parse agent metadata from deployed agent file.
        Uses caching based on file path and modification time.

        Returns:
            Dictionary with agent metadata directly from YAML frontmatter.
        """
        try:
            # Check cache based on file path and modification time
            cache_key = str(agent_file)
            file_mtime = agent_file.stat().st_mtime
            time.time()

            # Try to get from cache first
            cached_result = self._cache_manager.get_agent_metadata(cache_key)
            if cached_result is not None:
                cached_data, cached_mtime = cached_result
                # Use cache if file hasn't been modified and cache isn't too old
                if cached_mtime == file_mtime:
                    self.logger.debug(f"Using cached metadata for {agent_file.name}")
                    return cached_data

            # Cache miss or expired - parse the file
            self.logger.debug(
                f"Parsing metadata for {agent_file.name} (cache miss or expired)"
            )

            import yaml

            with open(agent_file) as f:
                content = f.read()

            # Default values
            agent_data = {
                "id": agent_file.stem,
                "display_name": agent_file.stem.replace("_", " ")
                .replace("-", " ")
                .title(),
                "description": "Specialized agent",
            }

            # Extract YAML frontmatter if present
            if content.startswith("---"):
                end_marker = content.find("---", 3)
                if end_marker > 0:
                    frontmatter = content[3:end_marker]
                    metadata = yaml.safe_load(frontmatter)
                    if metadata:
                        # Use name as ID for Task tool
                        agent_data["id"] = metadata.get("name", agent_data["id"])
                        agent_data["display_name"] = (
                            metadata.get("name", agent_data["display_name"])
                            .replace("-", " ")
                            .title()
                        )

                        # Copy all metadata fields directly
                        for key, value in metadata.items():
                            if key not in ["name"]:  # Skip already processed fields
                                agent_data[key] = value

                        # IMPORTANT: Do NOT add spaces to tools field - it breaks deployment!
                        # Tools must remain as comma-separated without spaces: "Read,Write,Edit"

            # Try to load routing metadata from JSON template if not in YAML frontmatter
            if "routing" not in agent_data:
                routing_data = self._load_routing_from_template(agent_file.stem)
                if routing_data:
                    agent_data["routing"] = routing_data

            # Try to load memory routing metadata from JSON template if not in YAML frontmatter
            if "memory_routing" not in agent_data:
                memory_routing_data = self._load_memory_routing_from_template(
                    agent_file.stem
                )
                if memory_routing_data:
                    agent_data["memory_routing"] = memory_routing_data

            # Cache the parsed metadata
            self._cache_manager.set_agent_metadata(cache_key, agent_data, file_mtime)

            return agent_data

        except Exception as e:
            self.logger.debug(f"Could not parse metadata from {agent_file}: {e}")
            return None

    def _load_memory_routing_from_template(
        self, agent_name: str
    ) -> Optional[Dict[str, Any]]:
        """Load memory routing metadata from agent JSON template.

        Args:
            agent_name: Name of the agent (stem of the file)

        Returns:
            Dictionary with memory routing metadata or None if not found
        """
        try:
            import json

            # Check if we have a framework path
            if not self.framework_path or self.framework_path == Path("__PACKAGED__"):
                # For packaged installations, try to load from package resources
                if files:
                    try:
                        templates_package = files("claude_mpm.agents.templates")
                        template_file = templates_package / f"{agent_name}.json"

                        if template_file.is_file():
                            template_content = template_file.read_text()
                            template_data = json.loads(template_content)
                            return template_data.get("memory_routing")
                    except Exception as e:
                        self.logger.debug(
                            f"Could not load memory routing from packaged template for {agent_name}: {e}"
                        )
                return None

            # For development mode, load from filesystem
            templates_dir = (
                self.framework_path / "src" / "claude_mpm" / "agents" / "templates"
            )
            template_file = templates_dir / f"{agent_name}.json"

            if template_file.exists():
                with open(template_file) as f:
                    template_data = json.load(f)
                    return template_data.get("memory_routing")

            # Also check for variations in naming (underscore vs dash)
            # Handle common naming variations between deployed .md files and .json templates
            # Remove duplicates by using a set
            alternative_names = list(
                {
                    agent_name.replace("-", "_"),  # api-qa -> api_qa
                    agent_name.replace("_", "-"),  # api_qa -> api-qa
                    agent_name.replace("-", ""),  # api-qa -> apiqa
                    agent_name.replace("_", ""),  # api_qa -> apiqa
                    agent_name.replace("-agent", ""),  # research-agent -> research
                    agent_name.replace("_agent", ""),  # research_agent -> research
                    agent_name + "_agent",  # research -> research_agent
                    agent_name + "-agent",  # research -> research-agent
                }
            )

            for alt_name in alternative_names:
                if alt_name != agent_name:  # Skip the original name we already tried
                    alt_file = templates_dir / f"{alt_name}.json"
                    if alt_file.exists():
                        with open(alt_file) as f:
                            template_data = json.load(f)
                            return template_data.get("memory_routing")

            return None

        except Exception as e:
            self.logger.debug(
                f"Could not load memory routing from template for {agent_name}: {e}"
            )
            return None

    def _discover_local_json_templates(self) -> Dict[str, Dict[str, Any]]:
        """Discover local JSON agent templates from .claude-mpm/agents/ directories.

        Returns:
            Dictionary mapping agent IDs to agent metadata
        """
        import json
        from pathlib import Path

        local_agents = {}

        # Check for local JSON templates in priority order
        template_dirs = [
            Path.cwd()
            / ".claude-mpm"
            / "agents",  # Project local agents (highest priority)
            Path.home() / ".claude-mpm" / "agents",  # User local agents
        ]

        for priority, template_dir in enumerate(template_dirs):
            if not template_dir.exists():
                continue

            for json_file in template_dir.glob("*.json"):
                try:
                    with open(json_file) as f:
                        template_data = json.load(f)

                    # Extract agent metadata
                    agent_id = template_data.get("agent_id", json_file.stem)

                    # Skip if already found at higher priority
                    if agent_id in local_agents:
                        continue

                    # Extract metadata
                    metadata = template_data.get("metadata", {})

                    # Build agent data in expected format
                    agent_data = {
                        "id": agent_id,
                        "display_name": metadata.get(
                            "name", agent_id.replace("_", " ").title()
                        ),
                        "description": metadata.get(
                            "description", f"Local {agent_id} agent"
                        ),
                        "tools": self._extract_tools_from_template(template_data),
                        "is_local": True,
                        "tier": "project" if priority == 0 else "user",
                        "author": template_data.get("author", "local"),
                        "version": template_data.get("agent_version", "1.0.0"),
                    }

                    local_agents[agent_id] = agent_data
                    self.logger.debug(
                        f"Discovered local JSON agent: {agent_id} from {template_dir}"
                    )

                except Exception as e:
                    self.logger.warning(
                        f"Failed to parse local JSON template {json_file}: {e}"
                    )

        return local_agents

    def _extract_tools_from_template(self, template_data: Dict[str, Any]) -> str:
        """Extract tools string from template data.

        Args:
            template_data: JSON template data

        Returns:
            Tools string for display
        """
        capabilities = template_data.get("capabilities", {})
        tools = capabilities.get("tools", "*")

        if tools == "*":
            return "All Tools"
        if isinstance(tools, list):
            return ", ".join(tools) if tools else "Standard Tools"
        if isinstance(tools, str):
            if "," in tools:
                return tools
            return tools
        return "Standard Tools"

    def _load_routing_from_template(self, agent_name: str) -> Optional[Dict[str, Any]]:
        """Load routing metadata from agent JSON template.

        Args:
            agent_name: Name of the agent (stem of the file)

        Returns:
            Dictionary with routing metadata or None if not found
        """
        try:
            import json

            # Check if we have a framework path
            if not self.framework_path or self.framework_path == Path("__PACKAGED__"):
                # For packaged installations, try to load from package resources
                if files:
                    try:
                        templates_package = files("claude_mpm.agents.templates")
                        template_file = templates_package / f"{agent_name}.json"

                        if template_file.is_file():
                            template_content = template_file.read_text()
                            template_data = json.loads(template_content)
                            return template_data.get("routing")
                    except Exception as e:
                        self.logger.debug(
                            f"Could not load routing from packaged template for {agent_name}: {e}"
                        )
                return None

            # For development mode, load from filesystem
            templates_dir = (
                self.framework_path / "src" / "claude_mpm" / "agents" / "templates"
            )
            template_file = templates_dir / f"{agent_name}.json"

            if template_file.exists():
                with open(template_file) as f:
                    template_data = json.load(f)
                    return template_data.get("routing")

            # Also check for variations in naming (underscore vs dash)
            # Handle common naming variations between deployed .md files and .json templates
            # Remove duplicates by using a set
            alternative_names = list(
                {
                    agent_name.replace("-", "_"),  # api-qa -> api_qa
                    agent_name.replace("_", "-"),  # api_qa -> api-qa
                    agent_name.replace("-", ""),  # api-qa -> apiqa
                    agent_name.replace("_", ""),  # api_qa -> apiqa
                }
            )

            for alt_name in alternative_names:
                if alt_name != agent_name:
                    alt_file = templates_dir / f"{alt_name}.json"
                    if alt_file.exists():
                        with open(alt_file) as f:
                            template_data = json.load(f)
                            return template_data.get("routing")

            self.logger.debug(f"No JSON template found for agent: {agent_name}")
            return None

        except Exception as e:
            self.logger.debug(f"Could not load routing metadata for {agent_name}: {e}")
            return None

    def _generate_agent_selection_guide(self, deployed_agents: list) -> str:
        """Generate Context-Aware Agent Selection guide from deployed agents.

        Creates a mapping of task types to appropriate agents based on their
        descriptions and capabilities.
        """
        guide = ""

        # Build selection mapping based on deployed agents
        selection_map = {}

        for agent in deployed_agents:
            agent_id = agent["id"]
            desc_lower = agent["description"].lower()

            # Map task types to agents based on their descriptions
            if "implementation" in desc_lower or (
                "engineer" in agent_id and "data" not in agent_id
            ):
                selection_map["Implementation tasks"] = (
                    f"{agent['display_name']} (`{agent_id}`)"
                )
            if "codebase analysis" in desc_lower or "research" in agent_id:
                selection_map["Codebase analysis"] = (
                    f"{agent['display_name']} (`{agent_id}`)"
                )
            if "testing" in desc_lower or "qa" in agent_id:
                selection_map["Testing/quality"] = (
                    f"{agent['display_name']} (`{agent_id}`)"
                )
            if "documentation" in desc_lower:
                selection_map["Documentation"] = (
                    f"{agent['display_name']} (`{agent_id}`)"
                )
            if "security" in desc_lower or "sast" in desc_lower:
                selection_map["Security operations"] = (
                    f"{agent['display_name']} (`{agent_id}`)"
                )
            if (
                "deployment" in desc_lower
                or "infrastructure" in desc_lower
                or "ops" in agent_id
            ):
                selection_map["Deployment/infrastructure"] = (
                    f"{agent['display_name']} (`{agent_id}`)"
                )
            if "data" in desc_lower and (
                "pipeline" in desc_lower or "etl" in desc_lower
            ):
                selection_map["Data pipeline/ETL"] = (
                    f"{agent['display_name']} (`{agent_id}`)"
                )
            if "git" in desc_lower or "version control" in desc_lower:
                selection_map["Version control"] = (
                    f"{agent['display_name']} (`{agent_id}`)"
                )
            if "ticket" in desc_lower or "epic" in desc_lower:
                selection_map["Ticket/issue management"] = (
                    f"{agent['display_name']} (`{agent_id}`)"
                )
            if "browser" in desc_lower or "e2e" in desc_lower:
                selection_map["Browser/E2E testing"] = (
                    f"{agent['display_name']} (`{agent_id}`)"
                )
            if "frontend" in desc_lower or "ui" in desc_lower or "html" in desc_lower:
                selection_map["Frontend/UI development"] = (
                    f"{agent['display_name']} (`{agent_id}`)"
                )

        # Always include PM questions
        selection_map["PM questions"] = "Answer directly (only exception)"

        # Format the selection guide
        for task_type, agent_info in selection_map.items():
            guide += f"- **{task_type}** → {agent_info}\n"

        return guide

    def _get_fallback_capabilities(self) -> str:
        """Return fallback capabilities when dynamic discovery fails."""
        return """

## Available Agent Capabilities

You have the following specialized agents available for delegation:

- **Engineer** (`engineer`): Code implementation and development
- **Research** (`research-agent`): Investigation and analysis
- **QA** (`qa-agent`): Testing and quality assurance
- **Documentation** (`documentation-agent`): Documentation creation and maintenance
- **Security** (`security-agent`): Security analysis and protection
- **Data Engineer** (`data-engineer`): Data management and pipelines
- **Ops** (`ops-agent`): Deployment and operations
- **Version Control** (`version-control`): Git operations and version management

**IMPORTANT**: Use the exact agent ID in parentheses when delegating tasks.
"""

    def _format_minimal_framework(self) -> str:
        """Format minimal framework instructions when full framework not available."""
        return """
# Claude PM Framework Instructions

You are operating within a Claude PM Framework deployment.

## Role
You are a multi-agent orchestrator. Your primary responsibilities:
- Delegate tasks to specialized agents via Task Tool
- Coordinate multi-agent workflows
- Extract TODO/BUG/FEATURE items for ticket creation
- NEVER perform direct implementation work

## Core Agents
- Documentation Agent - Documentation tasks
- Engineer Agent - Code implementation
- QA Agent - Testing and validation
- Research Agent - Investigation and analysis
- Version Control Agent - Git operations

## Important Rules
1. Always delegate work via Task Tool
2. Provide comprehensive context to agents
3. Track all TODO/BUG/FEATURE items
4. Maintain project visibility

---
"""

    def get_agent_list(self) -> list:
        """Get list of available agents."""
        # First try agent registry
        if self.agent_registry:
            agents = self.agent_registry.list_agents()
            if agents:
                return list(agents.keys())

        # Fallback to loaded content
        return list(self.framework_content["agents"].keys())

    def get_agent_definition(self, agent_name: str) -> Optional[str]:
        """Get specific agent definition."""
        # First try agent registry
        if self.agent_registry:
            definition = self.agent_registry.get_agent_definition(agent_name)
            if definition:
                return definition

        # Fallback to loaded content
        return self.framework_content["agents"].get(agent_name)

    def get_agent_hierarchy(self) -> Dict[str, list]:
        """Get agent hierarchy from registry."""
        if self.agent_registry:
            return self.agent_registry.get_agent_hierarchy()
        return {"project": [], "user": [], "system": []}

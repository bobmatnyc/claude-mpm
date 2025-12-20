"""Framework loader for Claude MPM - Refactored modular version."""

import asyncio
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

# Import framework components
from claude_mpm.core.framework import (
    AgentLoader,
    CapabilityGenerator,
    ContentFormatter,
    ContextGenerator,
    FileLoader,
    InstructionLoader,
    MemoryProcessor,
    MetadataProcessor,
    PackagedLoader,
    TemplateProcessor,
)
from claude_mpm.core.logging_utils import get_logger
from claude_mpm.utils.imports import safe_import

# Import with fallback support
AgentRegistryAdapter = safe_import(
    "claude_mpm.core.agent_registry", "core.agent_registry", ["AgentRegistryAdapter"]
)

# Import API validator
try:
    from claude_mpm.core.api_validator import validate_api_keys
except ImportError:
    from ..core.api_validator import validate_api_keys

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

    This refactored version uses modular components for better maintainability
    and testability while maintaining backward compatibility.

    Components:
    - Loaders: Handle file I/O and resource loading
    - Formatters: Generate and format content sections
    - Processors: Process metadata, templates, and memories
    """

    def __init__(
        self,
        framework_path: Optional[Path] = None,
        agents_dir: Optional[Path] = None,
        service_container: Optional[ServiceContainer] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize framework loader with modular components.

        Args:
            framework_path: Explicit path to framework (auto-detected if None)
            agents_dir: Custom agents directory (overrides framework agents)
            service_container: Optional service container for dependency injection
            config: Optional configuration dictionary for API validation and other settings
        """
        self.logger = get_logger("framework_loader")
        self.agents_dir = agents_dir
        self.framework_version = None
        self.framework_last_modified = None
        self.config = config or {}

        # Validate API keys on startup (before any other initialization)
        self._validate_api_keys()

        # Initialize service container
        self.container = service_container or get_global_container()
        self._register_services()

        # Resolve services from container
        self._cache_manager = self.container.resolve(ICacheManager)
        self._path_resolver = self.container.resolve(IPathResolver)
        self._memory_manager = self.container.resolve(IMemoryManager)

        # Initialize framework path
        self.framework_path = (
            framework_path or self._path_resolver.detect_framework_path()
        )

        # Initialize modular components
        self._init_components()

        # Keep cache TTL constants for backward compatibility
        self._init_cache_ttl()

        # Load framework content
        self.framework_content = self._load_framework_content()

        # Initialize agent registry
        self.agent_registry = AgentRegistryAdapter(self.framework_path)

        # Output style manager (deferred initialization)
        self.output_style_manager = None

    def _validate_api_keys(self) -> None:
        """Validate API keys if enabled in config."""
        if self.config.get("validate_api_keys", True):
            try:
                self.logger.info("Validating configured API keys...")
                validate_api_keys(config=self.config, strict=True)
                self.logger.info("✅ API key validation completed successfully")
            except ValueError as e:
                self.logger.error(f"❌ API key validation failed: {e}")
                raise
            except Exception as e:
                self.logger.error(f"❌ Unexpected error during API validation: {e}")
                raise

    def _register_services(self) -> None:
        """Register services in the container if not already registered."""
        if not self.container.is_registered(ICacheManager):
            self.container.register(ICacheManager, CacheManager, True)

        if not self.container.is_registered(IPathResolver):
            cache_manager = self.container.resolve(ICacheManager)
            path_resolver = PathResolver(cache_manager=cache_manager)
            self.container.register_instance(IPathResolver, path_resolver)

        if not self.container.is_registered(IMemoryManager):
            cache_manager = self.container.resolve(ICacheManager)
            path_resolver = self.container.resolve(IPathResolver)
            memory_manager = MemoryManager(
                cache_manager=cache_manager, path_resolver=path_resolver
            )
            self.container.register_instance(IMemoryManager, memory_manager)

    def _init_components(self) -> None:
        """Initialize modular components."""
        # Loaders
        self.file_loader = FileLoader()
        self.packaged_loader = PackagedLoader()
        self.instruction_loader = InstructionLoader(self.framework_path)
        self.agent_loader = AgentLoader(self.framework_path)

        # Formatters
        self.content_formatter = ContentFormatter()
        self.capability_generator = CapabilityGenerator()
        self.context_generator = ContextGenerator()

        # Processors
        self.metadata_processor = MetadataProcessor()
        self.template_processor = TemplateProcessor(self.framework_path)
        self.memory_processor = MemoryProcessor()

    def _init_cache_ttl(self) -> None:
        """Initialize cache TTL constants for backward compatibility."""
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

    # === Cache Management Methods (backward compatibility) ===

    def clear_all_caches(self) -> None:
        """Clear all caches to force reload on next access."""
        self._cache_manager.clear_all()

    def clear_agent_caches(self) -> None:
        """Clear agent-related caches."""
        self._cache_manager.clear_agent_caches()

    def clear_memory_caches(self) -> None:
        """Clear memory-related caches."""
        self._cache_manager.clear_memory_caches()

    # === Content Loading Methods ===

    def _load_framework_content(self) -> Dict[str, Any]:
        """Load framework content using modular components."""
        content = {
            "claude_md": "",
            "agents": {},
            "version": "unknown",
            "loaded": False,
            "working_claude_md": "",
            "framework_instructions": "",
            "workflow_instructions": "",
            "workflow_instructions_level": "",
            "memory_instructions": "",
            "memory_instructions_level": "",
            "project_workflow": "",  # Deprecated
            "project_memory": "",  # Deprecated
            "actual_memories": "",
            "agent_memories": {},
        }

        # Load all instructions
        self.instruction_loader.load_all_instructions(content)

        # Transfer metadata from loaders
        if self.file_loader.framework_version:
            self.framework_version = self.file_loader.framework_version
            content["version"] = self.framework_version
        if self.file_loader.framework_last_modified:
            self.framework_last_modified = self.file_loader.framework_last_modified

        # Load memories
        self._load_actual_memories(content)

        # Discover and load agents
        agents_dir, templates_dir, main_dir = self._path_resolver.discover_agent_paths(
            agents_dir=self.agents_dir, framework_path=self.framework_path
        )
        agents = self.agent_loader.load_agents_directory(
            agents_dir, templates_dir, main_dir
        )
        if agents:
            content["agents"] = agents
            content["loaded"] = True

        return content

    def _load_actual_memories(self, content: Dict[str, Any]) -> None:
        """Load actual memories using the MemoryManager service."""
        memories = self._memory_manager.load_memories()

        # Only load PM memories (PM.md)
        # Agent memories are loaded at deployment time in agent_template_builder.py
        if "actual_memories" in memories:
            content["actual_memories"] = memories["actual_memories"]
        # NOTE: agent_memories are no longer loaded for PM instructions
        # They are injected per-agent at deployment time

    # === Agent Discovery Methods ===

    def _get_deployed_agents(self) -> Set[str]:
        """Get deployed agents with caching."""
        cached = self._cache_manager.get_deployed_agents()
        if cached is not None:
            return cached

        deployed = self.agent_loader.get_deployed_agents()
        self._cache_manager.set_deployed_agents(deployed)
        return deployed

    def _discover_local_json_templates(self) -> Dict[str, Dict[str, Any]]:
        """Discover local JSON agent templates."""
        return self.agent_loader.discover_local_json_templates()

    def _parse_agent_metadata(self, agent_file: Path) -> Optional[Dict[str, Any]]:
        """Parse agent metadata with caching."""
        cache_key = str(agent_file)
        file_mtime = agent_file.stat().st_mtime

        # Try cache first
        cached_result = self._cache_manager.get_agent_metadata(cache_key)
        if cached_result is not None:
            cached_data, cached_mtime = cached_result
            if cached_mtime == file_mtime:
                self.logger.debug(f"Using cached metadata for {agent_file.name}")
                return cached_data

        # Cache miss - parse the file
        agent_data = self.metadata_processor.parse_agent_metadata(agent_file)

        # Add routing information if not present
        if agent_data and "routing" not in agent_data:
            template_data = self.template_processor.load_template(agent_file.stem)
            if template_data:
                routing = self.template_processor.extract_routing(template_data)
                if routing:
                    agent_data["routing"] = routing
                memory_routing = self.template_processor.extract_memory_routing(
                    template_data
                )
                if memory_routing:
                    agent_data["memory_routing"] = memory_routing

        # Cache the result
        if agent_data:
            self._cache_manager.set_agent_metadata(cache_key, agent_data, file_mtime)

        return agent_data

    # === Framework Instructions Generation ===

    def get_framework_instructions(self) -> str:
        """
        Get formatted framework instructions for injection.

        Returns:
            Complete framework instructions ready for injection
        """
        # Log the system prompt if needed
        self._log_system_prompt()

        # Generate the instructions
        if self.framework_content["loaded"]:
            return self._format_full_framework()
        return self._format_minimal_framework()

    def _format_full_framework(self) -> str:
        """Format full framework instructions using modular components."""
        # Initialize output style manager on first use
        if self.output_style_manager is None:
            self._initialize_output_style()

        # Check if we need to inject output style
        inject_output_style = False
        output_style_content = None
        if self.output_style_manager:
            inject_output_style = self.output_style_manager.should_inject_content()
            if inject_output_style:
                output_style_content = self.output_style_manager.get_injectable_content(
                    framework_loader=self
                )
                self.logger.info("Injecting output style content for Claude < 1.0.83")

        # Generate dynamic sections
        capabilities_section = self._generate_agent_capabilities_section()
        context_section = self.context_generator.generate_temporal_user_context()

        # Format the complete framework
        return self.content_formatter.format_full_framework(
            self.framework_content,
            capabilities_section,
            context_section,
            inject_output_style,
            output_style_content,
        )

    def _format_minimal_framework(self) -> str:
        """Format minimal framework instructions."""
        return self.content_formatter.format_minimal_framework(self.framework_content)

    def _generate_agent_capabilities_section(self) -> str:
        """Generate agent capabilities section with caching."""
        # Try cache first
        cached_capabilities = self._cache_manager.get_capabilities()
        if cached_capabilities is not None:
            return cached_capabilities

        self.logger.debug("Generating agent capabilities (cache miss)")

        try:
            # Discover local JSON templates
            local_agents = self._discover_local_json_templates()

            # Get deployed agents from .claude/agents/
            deployed_agents = []
            agents_dirs = [
                Path.cwd() / ".claude" / "agents",
                Path.home() / ".claude" / "agents",
            ]

            for agents_dir in agents_dirs:
                if agents_dir.exists():
                    for agent_file in agents_dir.glob("*.md"):
                        if not agent_file.name.startswith("."):
                            agent_data = self._parse_agent_metadata(agent_file)
                            if agent_data:
                                deployed_agents.append(agent_data)

            # Generate capabilities section
            section = self.capability_generator.generate_capabilities_section(
                deployed_agents, local_agents
            )

            # Cache the result
            self._cache_manager.set_capabilities(section)
            self.logger.debug(f"Cached agent capabilities ({len(section)} chars)")

            return section

        except Exception as e:
            self.logger.warning(f"Could not generate agent capabilities: {e}")
            fallback = self.content_formatter.get_fallback_capabilities()
            self._cache_manager.set_capabilities(fallback)
            return fallback

    # === Output Style Management ===

    def _initialize_output_style(self) -> None:
        """Initialize output style management."""
        try:
            from claude_mpm.core.output_style_manager import OutputStyleManager

            self.output_style_manager = OutputStyleManager()
            self._log_output_style_status()

            # Extract and save output style content
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
                self.logger.info("📝 Output style will be injected into instructions")

        except Exception as e:
            self.logger.warning(f"❌ Failed to initialize output style manager: {e}")

    def _log_output_style_status(self) -> None:
        """Log output style status information."""
        if not self.output_style_manager:
            return

        claude_version = self.output_style_manager.claude_version
        if claude_version:
            self.logger.info(f"Claude Code version detected: {claude_version}")

            if self.output_style_manager.supports_output_styles():
                self.logger.info("✅ Claude Code supports output styles (>= 1.0.83)")
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
                    f"⚠️ Claude Code {claude_version} does not support output styles"
                )
                self.logger.info(
                    "📝 Output style will be injected into framework instructions"
                )
        else:
            self.logger.info("⚠️ Claude Code not detected or version unknown")
            self.logger.info("📝 Output style will be injected as fallback")

    # === Logging Methods ===

    def _log_system_prompt(self) -> None:
        """Log the system prompt if LogManager is available."""
        try:
            from .log_manager import get_log_manager

            log_manager = get_log_manager()
        except ImportError:
            return

        try:
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
            }

            # Log the prompt asynchronously
            instructions = (
                self._format_full_framework()
                if self.framework_content["loaded"]
                else self._format_minimal_framework()
            )
            metadata["instructions_length"] = len(instructions)

            if loop.is_running():
                _task = asyncio.create_task(
                    log_manager.log_prompt("system_prompt", instructions, metadata)
                )  # Fire-and-forget logging
            else:
                loop.run_until_complete(
                    log_manager.log_prompt("system_prompt", instructions, metadata)
                )

            self.logger.debug("System prompt logged to prompts directory")
        except Exception as e:
            self.logger.debug(f"Could not log system prompt: {e}")

    # === Agent Registry Methods (backward compatibility) ===

    def get_agent_list(self) -> List[str]:
        """Get list of available agents."""
        if self.agent_registry:
            agents = self.agent_registry.list_agents()
            if agents:
                return list(agents.keys())
        return list(self.framework_content["agents"].keys())

    def get_agent_definition(self, agent_name: str) -> Optional[str]:
        """Get specific agent definition."""
        if self.agent_registry:
            definition = self.agent_registry.get_agent_definition(agent_name)
            if definition:
                return definition
        return self.framework_content["agents"].get(agent_name)

    def get_agent_hierarchy(self) -> Dict[str, List]:
        """Get agent hierarchy from registry."""
        if self.agent_registry:
            return self.agent_registry.get_agent_hierarchy()
        return {"project": [], "user": [], "system": []}

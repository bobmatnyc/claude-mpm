"""Agent deployment service for Claude Code native subagents.

This service handles the complete lifecycle of agent deployment:
1. Building agent YAML files from JSON templates
2. Managing versioning and updates
3. Deploying to Claude Code's .claude/agents directory
4. Environment configuration for agent discovery
5. Deployment verification and cleanup

OPERATIONAL CONSIDERATIONS:
- Deployment is idempotent - safe to run multiple times
- Version checking prevents unnecessary rebuilds (saves I/O)
- Supports force rebuild for troubleshooting
- Maintains backward compatibility with legacy versions
- Handles migration from old serial versioning to semantic versioning

MONITORING:
- Check logs for deployment status and errors
- Monitor disk space in .claude/agents directory
- Track version migration progress
- Verify agent discovery after deployment

ROLLBACK PROCEDURES:
- Keep backups of .claude/agents before major updates
- Use clean_deployment() to remove system agents
- User-created agents are preserved during cleanup
- Version tracking allows targeted rollbacks
"""

import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from claude_mpm.config.paths import paths
from claude_mpm.constants import Paths
from claude_mpm.core.config import Config
from claude_mpm.core.exceptions import AgentDeploymentError
from claude_mpm.core.interfaces import AgentDeploymentInterface
from claude_mpm.services.shared import ConfigServiceBase

from .agent_configuration_manager import AgentConfigurationManager
from .agent_discovery_service import AgentDiscoveryService
from .agent_environment_manager import AgentEnvironmentManager
from .agent_filesystem_manager import AgentFileSystemManager
from .agent_format_converter import AgentFormatConverter
from .agent_metrics_collector import AgentMetricsCollector
from .agent_template_builder import AgentTemplateBuilder
from .agent_validator import AgentValidator
from .agent_version_manager import AgentVersionManager
from .base_agent_locator import BaseAgentLocator
from .deployment_results_manager import DeploymentResultsManager
from .multi_source_deployment_service import MultiSourceAgentDeploymentService
from .single_agent_deployer import SingleAgentDeployer


class AgentDeploymentService(ConfigServiceBase, AgentDeploymentInterface):
    """Service for deploying Claude Code native agents.

    METRICS COLLECTION OPPORTUNITIES:
    This service could collect valuable deployment metrics including:
    - Agent deployment frequency and success rates
    - Template validation performance
    - Version migration patterns
    - Deployment duration by agent type
    - Cache hit rates for agent templates
    - Resource usage during deployment (memory, CPU)
    - Agent file sizes and complexity metrics
    - Deployment failure reasons and patterns

    DEPLOYMENT PIPELINE:
    1. Initialize with template and base agent paths
    2. Load base agent configuration (shared settings)
    3. Iterate through agent templates
    4. Check version and update requirements
    5. Build YAML files with proper formatting
    6. Deploy to target directory
    7. Set environment variables for discovery
    8. Verify deployment success

    ENVIRONMENT REQUIREMENTS:
    - Write access to .claude/agents directory
    - Python 3.8+ for pathlib and typing features
    - JSON parsing for template files
    - YAML generation capabilities
    """

    def __init__(
        self,
        templates_dir: Optional[Path] = None,
        base_agent_path: Optional[Path] = None,
        working_directory: Optional[Path] = None,
        config: Optional[Config] = None,
    ):
        """
        Initialize agent deployment service.

        Args:
            templates_dir: Directory containing agent JSON files
            base_agent_path: Path to base_agent.md file
            working_directory: User's working directory (for project agents)
            config: Configuration instance

        METRICS OPPORTUNITY: Track initialization performance:
        - Template directory scan time
        - Base agent loading time
        - Initial validation overhead
        """
        # Initialize base class with configuration
        super().__init__("agent_deployment", config=config)

        # Initialize template builder service
        self.template_builder = AgentTemplateBuilder()

        # Initialize version manager service
        self.version_manager = AgentVersionManager()

        # Initialize metrics collector service
        self.metrics_collector = AgentMetricsCollector()

        # Initialize environment manager service
        self.environment_manager = AgentEnvironmentManager()

        # Initialize validator service
        self.validator = AgentValidator()

        # Initialize base agent locator service
        self.base_agent_locator = BaseAgentLocator(self.logger)

        # Initialize deployment results manager
        self.results_manager = DeploymentResultsManager(self.logger)

        # Initialize single agent deployer
        self.single_agent_deployer = SingleAgentDeployer(
            self.template_builder,
            self.version_manager,
            self.results_manager,
            self.logger,
        )

        # Initialize filesystem manager service
        self.filesystem_manager = AgentFileSystemManager()

        # Determine the actual working directory using configuration
        # Priority: param > config > environment > current directory
        self.working_directory = self.get_config_value(
            "working_directory",
            default=working_directory or Path.cwd(),
            config_type=Path,
        )
        self.logger.info(f"Working directory for deployment: {self.working_directory}")

        # Find templates directory using configuration
        # Priority: param > config > default paths
        self.templates_dir = self.get_config_value(
            "templates_dir",
            default=templates_dir or paths.agents_dir / "templates",
            config_type=Path,
        )

        # Initialize discovery service (after templates_dir is set)
        self.discovery_service = AgentDiscoveryService(self.templates_dir)

        # Initialize multi-source deployment service for version comparison
        self.multi_source_service = MultiSourceAgentDeploymentService()

        # Find base agent file using configuration
        # Priority: param > config > search
        configured_base_agent = self.get_config_value(
            "base_agent_path", config_type=Path
        )
        if base_agent_path:
            self.base_agent_path = Path(base_agent_path)
        elif configured_base_agent:
            self.base_agent_path = configured_base_agent
        else:
            # Priority-based search for base_agent.json
            self.base_agent_path = self.base_agent_locator.find_base_agent_file(
                paths.agents_dir
            )

        # Initialize configuration manager (after base_agent_path is set)
        self.configuration_manager = AgentConfigurationManager(self.base_agent_path)

        # Initialize format converter service
        self.format_converter = AgentFormatConverter()

        self.logger.info(f"Templates directory: {self.templates_dir}")
        self.logger.info(f"Base agent path: {self.base_agent_path}")

    def deploy_agents(
        self,
        target_dir: Optional[Path] = None,
        force_rebuild: bool = False,
        deployment_mode: str = "update",
        config: Optional[Config] = None,
        use_async: bool = False,
    ) -> Dict[str, Any]:
        """
        Build and deploy agents by combining base_agent.md with templates.
        Also deploys system instructions for PM framework.

        DEPLOYMENT MODES:
        - "update": Normal update mode - skip agents with matching versions (default)
        - "project": Project deployment mode - always deploy all agents regardless of version

        CONFIGURATION:
        The config parameter or default configuration is used to determine:
        - Which agents to exclude from deployment
        - Case sensitivity for agent name matching
        - Whether to exclude agent dependencies

        METRICS COLLECTED:
        - Deployment start/end timestamps
        - Individual agent deployment durations
        - Success/failure rates by agent type
        - Version migration statistics
        - Template validation performance
        - Error type frequencies

        OPERATIONAL FLOW:
        0. Validates and repairs broken frontmatter in existing agents (Step 0)
        1. Validates target directory (creates if needed)
        2. Loads base agent configuration
        3. Discovers all agent templates
        4. For each agent:
           - Checks if update needed (version comparison)
           - Builds YAML configuration
           - Writes to target directory
           - Tracks deployment status

        PERFORMANCE CONSIDERATIONS:
        - Skips unchanged agents (version-based caching)
        - Batch processes all agents in single pass
        - Minimal file I/O with in-memory building
        - Parallel-safe (no shared state mutations)

        ERROR HANDLING:
        - Continues deployment on individual agent failures
        - Collects all errors for reporting
        - Logs detailed error context
        - Returns comprehensive results dict

        MONITORING POINTS:
        - Track total deployment time
        - Monitor skipped vs updated vs new agents
        - Check error rates and patterns
        - Verify migration completion

        Args:
            target_dir: Target directory for agents (default: .claude/agents/)
            force_rebuild: Force rebuild even if agents exist (useful for troubleshooting)
            deployment_mode: "update" for version-aware updates, "project" for always deploy
            config: Optional configuration object (loads default if not provided)
            use_async: Use async operations for 50-70% faster deployment (default: True)

        Returns:
            Dictionary with deployment results:
            - target_dir: Deployment location
            - deployed: List of newly deployed agents
            - updated: List of updated agents
            - migrated: List of agents migrated to new version format
            - skipped: List of unchanged agents
            - errors: List of deployment errors
            - total: Total number of agents processed
            - repaired: List of agents with repaired frontmatter
        """
        # METRICS: Record deployment start time for performance tracking
        deployment_start_time = time.time()

        # Try async deployment for better performance if requested
        if use_async:
            async_results = self._try_async_deployment(
                target_dir=target_dir,
                force_rebuild=force_rebuild,
                config=config,
                deployment_start_time=deployment_start_time,
            )
            if async_results is not None:
                return async_results

        # Continue with synchronous deployment
        self.logger.info("Using synchronous deployment")

        # Load and process configuration
        config, excluded_agents = self._load_deployment_config(config)

        # Determine target agents directory
        agents_dir = self._determine_agents_directory(target_dir)

        # Initialize results dictionary
        results = self.results_manager.initialize_deployment_results(
            agents_dir, deployment_start_time
        )

        try:
            # Create agents directory if needed
            agents_dir.mkdir(parents=True, exist_ok=True)

            # STEP 0: Validate and repair broken frontmatter in existing agents
            self._repair_existing_agents(agents_dir, results)

            # Log deployment source tier
            source_tier = self.base_agent_locator.determine_source_tier(
                self.templates_dir
            )
            self.logger.info(
                f"Building and deploying {source_tier} agents to: {agents_dir}"
            )

            # Note: System instructions are now loaded directly by SimpleClaudeRunner

            # Check if templates directory exists
            if not self.templates_dir.exists():
                error_msg = f"Agents directory not found: {self.templates_dir}"
                self.logger.error(error_msg)
                results["errors"].append(error_msg)
                return results

            # Convert any existing YAML files to MD format
            conversion_results = self._convert_yaml_to_md(agents_dir)
            results["converted"] = conversion_results.get("converted", [])

            # Load base agent content
            base_agent_data, base_agent_version = self._load_base_agent()

            # Check if we should use multi-source deployment
            use_multi_source = self._should_use_multi_source_deployment(deployment_mode)

            if use_multi_source:
                # Use multi-source deployment to get highest version agents
                template_files, agent_sources, cleanup_results = (
                    self._get_multi_source_templates(
                        excluded_agents, config, agents_dir, force_rebuild
                    )
                )
                results["total"] = len(template_files)
                results["multi_source"] = True
                results["agent_sources"] = agent_sources
                results["cleanup"] = cleanup_results

                # Log cleanup results if any agents were removed
                if cleanup_results.get("removed"):
                    self.logger.info(
                        f"Cleaned up {len(cleanup_results['removed'])} outdated user agents"
                    )
                    for removed in cleanup_results["removed"]:
                        self.logger.debug(
                            f"  - Removed: {removed['name']} v{removed['version']} ({removed['reason']})"
                        )
            else:
                # Get and filter template files from single source
                template_files = self._get_filtered_templates(excluded_agents, config)
                results["total"] = len(template_files)
                agent_sources = {}

            # Deploy each agent template
            for template_file in template_files:
                template_file_path = (
                    template_file
                    if isinstance(template_file, Path)
                    else Path(template_file)
                )
                agent_name = template_file_path.stem

                # Get source info for this agent (agent_sources now uses file stems as keys)
                source_info = (
                    agent_sources.get(agent_name, "unknown")
                    if agent_sources
                    else "single"
                )

                self.single_agent_deployer.deploy_single_agent(
                    template_file=template_file_path,
                    agents_dir=agents_dir,
                    base_agent_data=base_agent_data,
                    base_agent_version=base_agent_version,
                    force_rebuild=force_rebuild,
                    deployment_mode=deployment_mode,
                    results=results,
                    source_info=source_info,
                )

            # CRITICAL: System instructions deployment disabled to prevent automatic file creation
            # The system should NEVER automatically write INSTRUCTIONS.md, MEMORY.md, WORKFLOW.md
            # to .claude/ directory. These files should only be created when explicitly requested
            # by the user through agent-manager commands.
            # See deploy_system_instructions_explicit() for manual deployment.
            # self._deploy_system_instructions(agents_dir, force_rebuild, results)

            self.logger.info(
                f"Deployed {len(results['deployed'])} agents, "
                f"updated {len(results['updated'])}, "
                f"migrated {len(results['migrated'])}, "
                f"converted {len(results['converted'])} YAML files, "
                f"repaired {len(results['repaired'])} frontmatter, "
                f"skipped {len(results['skipped'])}, "
                f"errors: {len(results['errors'])}"
            )

        except AgentDeploymentError as e:
            # Custom error with context already formatted
            self.logger.error(str(e))
            results["errors"].append(str(e))
        except Exception as e:
            # Wrap unexpected errors
            error_msg = f"Agent deployment failed: {e}"
            self.logger.error(error_msg)
            results["errors"].append(error_msg)

            # METRICS: Track deployment failure
            self.results_manager.update_deployment_metrics(False, type(e).__name__)

        # METRICS: Calculate final deployment metrics
        self.results_manager.finalize_results(results, deployment_start_time)

        # METRICS: Update rolling averages and statistics
        deployment_duration = results["metrics"].get("duration_ms", 0)
        self.metrics_collector.update_deployment_metrics(deployment_duration, results)

        return results

    def get_deployment_metrics(self) -> Dict[str, Any]:
        """Get current deployment metrics."""
        return self.results_manager.get_deployment_metrics()

    def reset_metrics(self) -> None:
        """Reset deployment metrics."""
        return self.results_manager.reset_metrics()

    def set_claude_environment(
        self, config_dir: Optional[Path] = None
    ) -> Dict[str, str]:
        """Set Claude environment variables for agent discovery."""
        if not config_dir:
            config_dir = self.working_directory / Paths.CLAUDE_CONFIG_DIR.value
        return self.environment_manager.set_claude_environment(config_dir)

    def verify_deployment(self, config_dir: Optional[Path] = None) -> Dict[str, Any]:
        """Verify agent deployment and Claude configuration."""
        if not config_dir:
            config_dir = self.working_directory / ".claude"
        return self.validator.verify_deployment(config_dir)

    def deploy_agent(
        self, agent_name: str, target_dir: Path, force_rebuild: bool = False
    ) -> bool:
        """
        Deploy a single agent to the specified directory.

        Args:
            agent_name: Name of the agent to deploy
            target_dir: Target directory for deployment (Path object)
            force_rebuild: Whether to force rebuild even if version is current

        Returns:
            True if deployment was successful, False otherwise

        WHY: Single agent deployment because:
        - Users may want to deploy specific agents only
        - Reduces deployment time for targeted updates
        - Enables selective agent management in projects

        FIXED: Method now correctly handles all internal calls to:
        - _check_agent_needs_update (with 3 arguments)
        - _build_agent_markdown (with 3 arguments including base_agent_data)
        - Properly loads base_agent_data before building agent content
        """
        try:
            return self.single_agent_deployer.deploy_agent(
                agent_name,
                self.templates_dir,
                target_dir,
                self.base_agent_path,
                force_rebuild,
                self.working_directory,
            )

        except AgentDeploymentError:
            # Re-raise our custom exceptions
            raise
        except Exception as e:
            # Wrap generic exceptions with context
            raise AgentDeploymentError(
                f"Failed to deploy agent {agent_name}",
                context={"agent_name": agent_name, "error": str(e)},
            ) from e

    def list_available_agents(self) -> List[Dict[str, Any]]:
        """List available agent templates."""
        return self.discovery_service.list_available_agents()

    def clean_deployment(self, config_dir: Optional[Path] = None) -> Dict[str, Any]:
        """Clean up deployed agents."""
        if not config_dir:
            config_dir = self.working_directory / ".claude"
        return self.filesystem_manager.clean_deployment(config_dir)

    def _get_agent_tools(self, agent_name: str, metadata: Dict[str, Any]) -> List[str]:
        """Get appropriate tools for an agent based on its type."""
        from .agent_config_provider import AgentConfigProvider

        return AgentConfigProvider.get_agent_tools(agent_name, metadata)

    def _get_agent_specific_config(self, agent_name: str) -> Dict[str, Any]:
        """Get agent-specific configuration based on agent type."""
        from .agent_config_provider import AgentConfigProvider

        return AgentConfigProvider.get_agent_specific_config(agent_name)

    def _deploy_system_instructions(
        self, target_dir: Path, force_rebuild: bool, results: Dict[str, Any]
    ) -> None:
        """Deploy system instructions and framework files for PM framework."""
        from .system_instructions_deployer import SystemInstructionsDeployer

        deployer = SystemInstructionsDeployer(self.logger, self.working_directory)
        deployer.deploy_system_instructions(target_dir, force_rebuild, results)

    def deploy_system_instructions_explicit(
        self, target_dir: Optional[Path] = None, force_rebuild: bool = False
    ) -> Dict[str, Any]:
        """
        Explicitly deploy system instructions when requested by user.

        This method should ONLY be called when the user explicitly requests
        deployment of system instructions through agent-manager commands.
        It will deploy INSTRUCTIONS.md, MEMORY.md, and WORKFLOW.md to .claude/
        directory in the project.

        Args:
            target_dir: Target directory for deployment (ignored - always uses .claude/)
            force_rebuild: Force rebuild even if files exist

        Returns:
            Dict with deployment results
        """
        results = {
            "deployed": [],
            "updated": [],
            "skipped": [],
            "errors": [],
        }

        try:
            # Always use project's .claude directory
            target_dir = self.working_directory / ".claude"

            # Ensure directory exists
            target_dir.mkdir(parents=True, exist_ok=True)

            # Deploy using the deployer (targeting .claude/)
            from .system_instructions_deployer import SystemInstructionsDeployer

            deployer = SystemInstructionsDeployer(self.logger, self.working_directory)

            # Deploy to .claude directory
            deployer.deploy_system_instructions(target_dir, force_rebuild, results)

            self.logger.info(
                f"Explicitly deployed system instructions to {target_dir}: "
                f"deployed={len(results['deployed'])}, "
                f"updated={len(results['updated'])}, "
                f"skipped={len(results['skipped'])}"
            )

        except Exception as e:
            error_msg = f"Failed to deploy system instructions: {e}"
            self.logger.error(error_msg)
            results["errors"].append(error_msg)

        return results

    def _convert_yaml_to_md(self, target_dir: Path) -> Dict[str, Any]:
        """Convert existing YAML agent files to MD format with YAML frontmatter."""
        return self.format_converter.convert_yaml_to_md(target_dir)

    def _convert_yaml_content_to_md(self, yaml_content: str, agent_name: str) -> str:
        """Convert YAML agent content to MD format with YAML frontmatter."""
        return self.format_converter.convert_yaml_content_to_md(
            yaml_content, agent_name
        )

    def _extract_yaml_field(self, yaml_content: str, field_name: str) -> str:
        """Extract a field value from YAML content."""
        return self.format_converter.extract_yaml_field(yaml_content, field_name)

    def _try_async_deployment(
        self,
        target_dir: Optional[Path],
        force_rebuild: bool,
        config: Optional[Config],
        deployment_start_time: float,
    ) -> Optional[Dict[str, Any]]:
        """
        Try to use async deployment for better performance.

        WHY: Async deployment is 50-70% faster than synchronous deployment
        by using concurrent operations for file I/O and processing.

        Args:
            target_dir: Target directory for deployment
            force_rebuild: Whether to force rebuild
            config: Configuration object
            deployment_start_time: Start time for metrics

        Returns:
            Deployment results if successful, None if async not available
        """
        try:
            from .async_agent_deployment import deploy_agents_async_wrapper

            self.logger.info("Using async deployment for improved performance")

            # Run async deployment
            results = deploy_agents_async_wrapper(
                templates_dir=self.templates_dir,
                base_agent_path=self.base_agent_path,
                working_directory=self.working_directory,
                target_dir=target_dir,
                force_rebuild=force_rebuild,
                config=config,
            )

            # Add metrics about async vs sync
            if "metrics" in results:
                results["metrics"]["deployment_method"] = "async"
                duration_ms = results["metrics"].get("duration_ms", 0)
                self.logger.info(f"Async deployment completed in {duration_ms:.1f}ms")

                # Update internal metrics
                self.results_manager.update_deployment_metrics(
                    not results.get("errors")
                )

            return results

        except ImportError:
            self.logger.warning("Async deployment not available, falling back to sync")
            return None
        except Exception as e:
            self.logger.warning(f"Async deployment failed, falling back to sync: {e}")
            return None

    def _load_deployment_config(self, config: Optional[Config]) -> tuple:
        """Load and process deployment configuration."""
        from .deployment_config_loader import DeploymentConfigLoader

        loader = DeploymentConfigLoader(self.logger)
        return loader.load_deployment_config(config)

    def _determine_agents_directory(self, target_dir: Optional[Path]) -> Path:
        """Determine the correct agents directory based on input."""
        from .agents_directory_resolver import AgentsDirectoryResolver

        resolver = AgentsDirectoryResolver(self.working_directory)
        return resolver.determine_agents_directory(target_dir)

    def _repair_existing_agents(
        self, agents_dir: Path, results: Dict[str, Any]
    ) -> None:
        """
        Validate and repair broken frontmatter in existing agents.

        WHY: Ensures all existing agents have valid YAML frontmatter
        before deployment, preventing runtime errors in Claude Code.

        Args:
            agents_dir: Directory containing agent files
            results: Results dictionary to update
        """
        repair_results = self._validate_and_repair_existing_agents(agents_dir)
        if repair_results["repaired"]:
            results["repaired"] = repair_results["repaired"]
            self.logger.info(
                f"Repaired frontmatter in {len(repair_results['repaired'])} existing agents"
            )
            for agent_name in repair_results["repaired"]:
                self.logger.debug(f"  - Repaired: {agent_name}")

    def _load_base_agent(self) -> tuple:
        """Load base agent content and version."""
        return self.configuration_manager.load_base_agent()

    def _get_filtered_templates(self, excluded_agents: list, config: Config) -> list:
        """Get and filter template files based on exclusion rules."""
        filter_non_mpm = config.get("agent_deployment.filter_non_mpm_agents", True)
        return self.discovery_service.get_filtered_templates(
            excluded_agents, config, filter_non_mpm
        )

    def _validate_and_repair_existing_agents(self, agents_dir: Path) -> Dict[str, Any]:
        """Validate and repair broken frontmatter in existing agent files."""
        from .agent_frontmatter_validator import AgentFrontmatterValidator

        validator = AgentFrontmatterValidator(self.logger)
        return validator.validate_and_repair_existing_agents(agents_dir)

    def _should_use_multi_source_deployment(self, deployment_mode: str) -> bool:
        """Determine if multi-source deployment should be used.

        WHY: Multi-source deployment ensures the highest version wins,
        but we may want to preserve backward compatibility in some modes.

        Args:
            deployment_mode: Current deployment mode

        Returns:
            True if multi-source deployment should be used
        """
        # Always use multi-source for update mode to get highest versions
        if deployment_mode == "update":
            return True

        # For project mode, also use multi-source to ensure highest version wins
        # This is the key change - project mode should also compare versions
        return deployment_mode == "project"

    def _get_multi_source_templates(
        self,
        excluded_agents: List[str],
        config: Config,
        agents_dir: Path,
        force_rebuild: bool = False,
    ) -> Tuple[List[Path], Dict[str, str], Dict[str, Any]]:
        """Get agent templates from multiple sources with version comparison.

        WHY: This method uses the multi-source service to discover agents
        from all available sources and select the highest version of each.

        Args:
            excluded_agents: List of agents to exclude
            config: Configuration object
            agents_dir: Target deployment directory
            force_rebuild: Whether to force rebuild

        Returns:
            Tuple of (template_files, agent_sources, cleanup_results)
        """
        # Determine source directories
        system_templates_dir = self.templates_dir
        project_agents_dir = None
        user_agents_dir = None

        # Check for project agents
        if self.working_directory:
            potential_project_dir = self.working_directory / ".claude-mpm" / "agents"
            if potential_project_dir.exists():
                project_agents_dir = potential_project_dir
                self.logger.info(f"Found project agents at: {project_agents_dir}")

        # Check for user agents
        user_home = Path.home()
        potential_user_dir = user_home / ".claude-mpm" / "agents"
        if potential_user_dir.exists():
            user_agents_dir = potential_user_dir
            self.logger.info(f"Found user agents at: {user_agents_dir}")

        # Get agents with version comparison and cleanup
        agents_to_deploy, agent_sources, cleanup_results = (
            self.multi_source_service.get_agents_for_deployment(
                system_templates_dir=system_templates_dir,
                project_agents_dir=project_agents_dir,
                user_agents_dir=user_agents_dir,
                working_directory=self.working_directory,
                excluded_agents=excluded_agents,
                config=config,
                cleanup_outdated=True,  # Enable cleanup by default
            )
        )

        # Compare with deployed versions if agents directory exists
        if agents_dir.exists():
            comparison_results = self.multi_source_service.compare_deployed_versions(
                deployed_agents_dir=agents_dir,
                agents_to_deploy=agents_to_deploy,
                agent_sources=agent_sources,
            )

            # Log version upgrades and source changes
            if comparison_results.get("version_upgrades"):
                self.logger.info(
                    f"Version upgrades available for {len(comparison_results['version_upgrades'])} agents"
                )
            if comparison_results.get("source_changes"):
                self.logger.info(
                    f"Source changes for {len(comparison_results['source_changes'])} agents"
                )

            # Filter agents based on comparison results (unless force_rebuild is set)
            if not force_rebuild:
                # Only deploy agents that need updates or are new
                agents_needing_update = set(comparison_results.get("needs_update", []))

                # Extract agent names from new_agents list (which contains dicts)
                new_agent_names = [
                    agent["name"] if isinstance(agent, dict) else agent
                    for agent in comparison_results.get("new_agents", [])
                ]
                agents_needing_update.update(new_agent_names)

                # Filter agents_to_deploy to only include those needing updates
                filtered_agents = {
                    name: path
                    for name, path in agents_to_deploy.items()
                    if name in agents_needing_update
                }
                agents_to_deploy = filtered_agents

                self.logger.info(
                    f"Filtered to {len(agents_to_deploy)} agents needing deployment"
                )

        # Convert to list of Path objects
        template_files = list(agents_to_deploy.values())

        return template_files, agent_sources, cleanup_results

    # ================================================================================
    # Interface Adapter Methods
    # ================================================================================
    # These methods adapt the existing implementation to comply with AgentDeploymentInterface

    def validate_agent(self, agent_path: Path) -> tuple[bool, List[str]]:
        """Validate agent configuration and structure.

        WHY: This adapter method provides interface compliance while leveraging
        the existing validation logic in _check_agent_needs_update and other methods.

        Args:
            agent_path: Path to agent configuration file

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []

        try:
            if not agent_path.exists():
                return False, [f"Agent file not found: {agent_path}"]

            content = agent_path.read_text()

            # Check YAML frontmatter format
            if not content.startswith("---"):
                errors.append("Missing YAML frontmatter")

            # Extract and validate version
            import re

            version_match = re.search(
                r'^version:\s*["\']?(.+?)["\']?$', content, re.MULTILINE
            )
            if not version_match:
                errors.append("Missing version field in frontmatter")

            # Check for required fields
            required_fields = ["name", "description", "tools"]
            for field in required_fields:
                field_match = re.search(rf"^{field}:\s*.+$", content, re.MULTILINE)
                if not field_match:
                    errors.append(f"Missing required field: {field}")

            # If no errors, validation passed
            return len(errors) == 0, errors

        except Exception as e:
            return False, [f"Validation error: {e!s}"]

    def get_deployment_status(self) -> Dict[str, Any]:
        """Get current deployment status and metrics."""
        return self.metrics_collector.get_deployment_status()

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

import logging
import os
import shutil
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from claude_mpm.config.paths import paths
from claude_mpm.constants import AgentMetadata, EnvironmentVars, Paths
from claude_mpm.core.config import Config
from claude_mpm.core.constants import ResourceLimits, SystemLimits, TimeoutConfig
from claude_mpm.core.exceptions import AgentDeploymentError
from claude_mpm.core.interfaces import AgentDeploymentInterface
from claude_mpm.core.logging_config import (
    get_logger,
    log_operation,
    log_performance_context,
)

from .agent_configuration_manager import AgentConfigurationManager
from .agent_discovery_service import AgentDiscoveryService
from .agent_environment_manager import AgentEnvironmentManager
from .agent_filesystem_manager import AgentFileSystemManager
from .agent_format_converter import AgentFormatConverter
from .agent_metrics_collector import AgentMetricsCollector
from .agent_template_builder import AgentTemplateBuilder
from .agent_validator import AgentValidator
from .agent_version_manager import AgentVersionManager
from .multi_source_deployment_service import MultiSourceAgentDeploymentService


class AgentDeploymentService(AgentDeploymentInterface):
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
    ):
        """
        Initialize agent deployment service.

        Args:
            templates_dir: Directory containing agent JSON files
            base_agent_path: Path to base_agent.md file
            working_directory: User's working directory (for project agents)

        METRICS OPPORTUNITY: Track initialization performance:
        - Template directory scan time
        - Base agent loading time
        - Initial validation overhead
        """
        self.logger = get_logger(__name__)

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

        # Initialize filesystem manager service
        self.filesystem_manager = AgentFileSystemManager()

        # Initialize deployment metrics tracking
        self._deployment_metrics = {
            "total_deployments": 0,
            "successful_deployments": 0,
            "failed_deployments": 0,
            "migrations_performed": 0,
            "version_migration_count": 0,
            "agent_type_counts": {},
            "deployment_errors": {},
        }

        # Determine the actual working directory
        # For deployment, we need to track the working directory but NOT use it
        # for determining where system agents go (they always go to ~/.claude/agents/)
        # Priority: working_directory param > current directory
        if working_directory:
            self.working_directory = Path(working_directory)
        else:
            # Use current directory but don't let CLAUDE_MPM_USER_PWD affect system agent deployment
            self.working_directory = Path.cwd()

        self.logger.info(f"Working directory for deployment: {self.working_directory}")

        # Find templates directory using centralized path management
        if templates_dir:
            self.templates_dir = Path(templates_dir)
        else:
            # Use centralized paths instead of fragile parent calculations
            # For system agents, still use templates subdirectory
            # For project/user agents, this should be overridden with actual agents dir
            self.templates_dir = paths.agents_dir / "templates"

        # Initialize discovery service (after templates_dir is set)
        self.discovery_service = AgentDiscoveryService(self.templates_dir)
        
        # Initialize multi-source deployment service for version comparison
        self.multi_source_service = MultiSourceAgentDeploymentService()

        # Find base agent file
        if base_agent_path:
            self.base_agent_path = Path(base_agent_path)
        else:
            # Use centralized paths for consistency
            self.base_agent_path = paths.agents_dir / "base_agent.json"

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
        results = self._initialize_deployment_results(agents_dir, deployment_start_time)

        try:
            # Create agents directory if needed
            agents_dir.mkdir(parents=True, exist_ok=True)

            # STEP 0: Validate and repair broken frontmatter in existing agents
            self._repair_existing_agents(agents_dir, results)

            # Log deployment source tier
            source_tier = self._determine_source_tier()
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
                template_files, agent_sources = self._get_multi_source_templates(
                    excluded_agents, config, agents_dir
                )
                results["total"] = len(template_files)
                results["multi_source"] = True
                results["agent_sources"] = agent_sources
            else:
                # Get and filter template files from single source
                template_files = self._get_filtered_templates(excluded_agents, config)
                results["total"] = len(template_files)
                agent_sources = {}

            # Deploy each agent template
            for template_file in template_files:
                template_file_path = template_file if isinstance(template_file, Path) else Path(template_file)
                agent_name = template_file_path.stem
                
                # Get source info for this agent (agent_sources now uses file stems as keys)
                source_info = agent_sources.get(agent_name, "unknown") if agent_sources else "single"
                
                self._deploy_single_agent(
                    template_file=template_file_path,
                    agents_dir=agents_dir,
                    base_agent_data=base_agent_data,
                    base_agent_version=base_agent_version,
                    force_rebuild=force_rebuild,
                    deployment_mode=deployment_mode,
                    results=results,
                    source_info=source_info,
                )

            # Deploy system instructions and framework files
            self._deploy_system_instructions(agents_dir, force_rebuild, results)

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
            self._deployment_metrics["failed_deployments"] += 1
            error_type = type(e).__name__
            self._deployment_metrics["deployment_errors"][error_type] = (
                self._deployment_metrics["deployment_errors"].get(error_type, 0) + 1
            )

        # METRICS: Calculate final deployment metrics
        deployment_end_time = time.time()
        deployment_duration = (deployment_end_time - deployment_start_time) * 1000  # ms

        results["metrics"]["end_time"] = deployment_end_time
        results["metrics"]["duration_ms"] = deployment_duration

        # METRICS: Update rolling averages and statistics
        self.metrics_collector.update_deployment_metrics(deployment_duration, results)

        return results

    def get_deployment_metrics(self) -> Dict[str, Any]:
        """Get current deployment metrics."""
        return self.metrics_collector.get_deployment_metrics()

    def reset_metrics(self) -> None:
        """Reset deployment metrics."""
        return self.metrics_collector.reset_metrics()

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
            # Find the template file
            template_file = self.templates_dir / f"{agent_name}.json"
            if not template_file.exists():
                self.logger.error(f"Agent template not found: {agent_name}")
                return False

            # Ensure target directory exists
            agents_dir = target_dir / ".claude" / "agents"
            agents_dir.mkdir(parents=True, exist_ok=True)

            # Build and deploy the agent
            target_file = agents_dir / f"{agent_name}.md"

            # Check if update is needed
            if not force_rebuild and target_file.exists():
                # Load base agent data for version checking
                base_agent_data = {}
                base_agent_version = (0, 0, 0)
                if self.base_agent_path.exists():
                    try:
                        import json

                        base_agent_data = json.loads(self.base_agent_path.read_text())
                        base_agent_version = self.version_manager.parse_version(
                            base_agent_data.get("base_version")
                            or base_agent_data.get("version", 0)
                        )
                    except Exception as e:
                        self.logger.warning(
                            f"Could not load base agent for version check: {e}"
                        )

                needs_update, reason = self.version_manager.check_agent_needs_update(
                    target_file, template_file, base_agent_version
                )
                if not needs_update:
                    self.logger.info(f"Agent {agent_name} is up to date")
                    return True
                else:
                    self.logger.info(f"Updating agent {agent_name}: {reason}")

            # Load base agent data for building
            base_agent_data = {}
            if self.base_agent_path.exists():
                try:
                    import json

                    base_agent_data = json.loads(self.base_agent_path.read_text())
                except Exception as e:
                    self.logger.warning(f"Could not load base agent: {e}")

            # Build the agent markdown
            # For single agent deployment, determine source from template location
            source_info = self._determine_agent_source(template_file)
            agent_content = self.template_builder.build_agent_markdown(
                agent_name, template_file, base_agent_data, source_info
            )
            if not agent_content:
                self.logger.error(f"Failed to build agent content for {agent_name}")
                return False

            # Write to target file
            target_file.write_text(agent_content)
            self.logger.info(
                f"Successfully deployed agent: {agent_name} to {target_file}"
            )

            return True

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
        deployer.deploy_system_instructions(
            target_dir, force_rebuild, results, self._is_project_specific_deployment()
        )

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
                self._deployment_metrics["total_deployments"] += 1
                if not results.get("errors"):
                    self._deployment_metrics["successful_deployments"] += 1
                else:
                    self._deployment_metrics["failed_deployments"] += 1

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

        resolver = AgentsDirectoryResolver(
            self.working_directory,
            self._is_system_agent_deployment(),
            self._is_project_specific_deployment(),
        )
        return resolver.determine_agents_directory(target_dir)

    def _is_system_agent_deployment(self) -> bool:
        """Check if this is a deployment of system agents."""
        from .deployment_type_detector import DeploymentTypeDetector

        return DeploymentTypeDetector.is_system_agent_deployment(self.templates_dir)

    def _is_project_specific_deployment(self) -> bool:
        """Check if deploying project-specific agents."""
        from .deployment_type_detector import DeploymentTypeDetector

        return DeploymentTypeDetector.is_project_specific_deployment(
            self.templates_dir, self.working_directory
        )

    def _is_user_custom_deployment(self) -> bool:
        """Check if deploying user custom agents."""
        from .deployment_type_detector import DeploymentTypeDetector

        return DeploymentTypeDetector.is_user_custom_deployment(self.templates_dir)

    def _initialize_deployment_results(
        self, agents_dir: Path, deployment_start_time: float
    ) -> Dict[str, Any]:
        """
        Initialize the deployment results dictionary.

        WHY: Consistent result structure ensures all deployment
        operations return the same format for easier processing.

        Args:
            agents_dir: Target agents directory
            deployment_start_time: Start time for metrics

        Returns:
            Initialized results dictionary
        """
        return {
            "target_dir": str(agents_dir),
            "deployed": [],
            "errors": [],
            "skipped": [],
            "updated": [],
            "migrated": [],  # Track agents migrated from old format
            "converted": [],  # Track YAML to MD conversions
            "repaired": [],  # Track agents with repaired frontmatter
            "total": 0,
            # METRICS: Add detailed timing and performance data to results
            "metrics": {
                "start_time": deployment_start_time,
                "end_time": None,
                "duration_ms": None,
                "agent_timings": {},  # Track individual agent deployment times
                "validation_times": {},  # Track template validation times
                "resource_usage": {},  # Could track memory/CPU if needed
            },
        }

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

    def _determine_source_tier(self) -> str:
        """Determine the source tier for logging."""
        from .deployment_type_detector import DeploymentTypeDetector

        return DeploymentTypeDetector.determine_source_tier(self.templates_dir)

    def _load_base_agent(self) -> tuple:
        """Load base agent content and version."""
        return self.configuration_manager.load_base_agent()

    def _get_filtered_templates(self, excluded_agents: list, config: Config) -> list:
        """Get and filter template files based on exclusion rules."""
        return self.discovery_service.get_filtered_templates(excluded_agents, config)

    def _deploy_single_agent(
        self,
        template_file: Path,
        agents_dir: Path,
        base_agent_data: dict,
        base_agent_version: tuple,
        force_rebuild: bool,
        deployment_mode: str,
        results: Dict[str, Any],
        source_info: str = "unknown",
    ) -> None:
        """
        Deploy a single agent template.

        WHY: Extracting single agent deployment logic reduces complexity
        and makes the main deployment loop more readable.

        Args:
            template_file: Agent template file
            agents_dir: Target agents directory
            base_agent_data: Base agent data
            base_agent_version: Base agent version
            force_rebuild: Whether to force rebuild
            deployment_mode: Deployment mode (update/project)
            results: Results dictionary to update
            source_info: Source of the agent (system/project/user)
        """
        try:
            # METRICS: Track individual agent deployment time
            agent_start_time = time.time()

            agent_name = template_file.stem
            target_file = agents_dir / f"{agent_name}.md"

            # Check if agent needs update
            needs_update, is_migration, reason = self._check_update_status(
                target_file,
                template_file,
                base_agent_version,
                force_rebuild,
                deployment_mode,
            )

            # Skip if exists and doesn't need update (only in update mode)
            if (
                target_file.exists()
                and not needs_update
                and deployment_mode != "project"
            ):
                results["skipped"].append(agent_name)
                self.logger.debug(f"Skipped up-to-date agent: {agent_name}")
                return

            # Build the agent file as markdown with YAML frontmatter
            agent_content = self.template_builder.build_agent_markdown(
                agent_name, template_file, base_agent_data, source_info
            )

            # Write the agent file
            is_update = target_file.exists()
            target_file.write_text(agent_content)

            # Record metrics and update results
            self._record_agent_deployment(
                agent_name,
                template_file,
                target_file,
                is_update,
                is_migration,
                reason,
                agent_start_time,
                results,
            )

        except AgentDeploymentError as e:
            # Re-raise our custom exceptions
            self.logger.error(str(e))
            results["errors"].append(str(e))
        except Exception as e:
            # Wrap generic exceptions with context
            error_msg = f"Failed to build {template_file.name}: {e}"
            self.logger.error(error_msg)
            results["errors"].append(error_msg)

    def _check_update_status(
        self,
        target_file: Path,
        template_file: Path,
        base_agent_version: tuple,
        force_rebuild: bool,
        deployment_mode: str,
    ) -> tuple:
        """
        Check if agent needs update and determine status.

        WHY: Centralized update checking logic ensures consistent
        version comparison and migration detection.

        Args:
            target_file: Target agent file
            template_file: Template file
            base_agent_version: Base agent version
            force_rebuild: Whether to force rebuild
            deployment_mode: Deployment mode

        Returns:
            Tuple of (needs_update, is_migration, reason)
        """
        needs_update = force_rebuild
        is_migration = False
        reason = ""

        # In project deployment mode, always deploy regardless of version
        if deployment_mode == "project":
            if target_file.exists():
                needs_update = True
                self.logger.debug(
                    f"Project deployment mode: will deploy {template_file.stem}"
                )
            else:
                needs_update = True
        elif not needs_update and target_file.exists():
            # In update mode, check version compatibility
            needs_update, reason = self.version_manager.check_agent_needs_update(
                target_file, template_file, base_agent_version
            )
            if needs_update:
                # Check if this is a migration from old format
                if "migration needed" in reason:
                    is_migration = True
                    self.logger.info(f"Migrating agent {template_file.stem}: {reason}")
                else:
                    self.logger.info(
                        f"Agent {template_file.stem} needs update: {reason}"
                    )

        return needs_update, is_migration, reason

    def _record_agent_deployment(
        self,
        agent_name: str,
        template_file: Path,
        target_file: Path,
        is_update: bool,
        is_migration: bool,
        reason: str,
        agent_start_time: float,
        results: Dict[str, Any],
    ) -> None:
        """
        Record deployment metrics and update results.

        WHY: Centralized metrics recording ensures consistent tracking
        of deployment performance and statistics.

        Args:
            agent_name: Name of the agent
            template_file: Template file
            target_file: Target file
            is_update: Whether this is an update
            is_migration: Whether this is a migration
            reason: Update/migration reason
            agent_start_time: Start time for this agent
            results: Results dictionary to update
        """
        # METRICS: Record deployment time for this agent
        agent_deployment_time = (time.time() - agent_start_time) * 1000  # Convert to ms
        results["metrics"]["agent_timings"][agent_name] = agent_deployment_time

        # METRICS: Update agent type deployment counts
        self._deployment_metrics["agent_type_counts"][agent_name] = (
            self._deployment_metrics["agent_type_counts"].get(agent_name, 0) + 1
        )

        deployment_info = {
            "name": agent_name,
            "template": str(template_file),
            "target": str(target_file),
            "deployment_time_ms": agent_deployment_time,
        }

        if is_migration:
            deployment_info["reason"] = reason
            results["migrated"].append(deployment_info)
            self.logger.info(
                f"Successfully migrated agent: {agent_name} to semantic versioning"
            )

            # METRICS: Track migration statistics
            self._deployment_metrics["migrations_performed"] += 1
            self._deployment_metrics["version_migration_count"] += 1

        elif is_update:
            results["updated"].append(deployment_info)
            self.logger.debug(f"Updated agent: {agent_name}")
        else:
            results["deployed"].append(deployment_info)
            self.logger.debug(f"Built and deployed agent: {agent_name}")

    def _validate_and_repair_existing_agents(self, agents_dir: Path) -> Dict[str, Any]:
        """Validate and repair broken frontmatter in existing agent files."""
        from .agent_frontmatter_validator import AgentFrontmatterValidator

        validator = AgentFrontmatterValidator(self.logger)
        return validator.validate_and_repair_existing_agents(agents_dir)
    
    def _determine_agent_source(self, template_path: Path) -> str:
        """Determine the source of an agent from its template path.
        
        WHY: When deploying single agents, we need to track their source
        for proper version management and debugging.
        
        Args:
            template_path: Path to the agent template
            
        Returns:
            Source string (system/project/user/unknown)
        """
        template_str = str(template_path.resolve())
        
        # Check if it's a system template
        if "/claude_mpm/agents/templates/" in template_str or "/src/claude_mpm/agents/templates/" in template_str:
            return "system"
        
        # Check if it's a project agent
        if "/.claude-mpm/agents/" in template_str:
            # Check if it's in the current working directory
            if str(self.working_directory) in template_str:
                return "project"
            # Check if it's in user home
            elif str(Path.home()) in template_str:
                return "user"
        
        return "unknown"
    
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
        if deployment_mode == "project":
            return True
            
        return False
    
    def _get_multi_source_templates(
        self, excluded_agents: List[str], config: Config, agents_dir: Path
    ) -> Tuple[List[Path], Dict[str, str]]:
        """Get agent templates from multiple sources with version comparison.
        
        WHY: This method uses the multi-source service to discover agents
        from all available sources and select the highest version of each.
        
        Args:
            excluded_agents: List of agents to exclude
            config: Configuration object
            agents_dir: Target deployment directory
            
        Returns:
            Tuple of (template_files, agent_sources)
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
        
        # Get agents with version comparison
        agents_to_deploy, agent_sources = self.multi_source_service.get_agents_for_deployment(
            system_templates_dir=system_templates_dir,
            project_agents_dir=project_agents_dir,
            user_agents_dir=user_agents_dir,
            working_directory=self.working_directory,
            excluded_agents=excluded_agents,
            config=config
        )
        
        # Compare with deployed versions if agents directory exists
        if agents_dir.exists():
            comparison_results = self.multi_source_service.compare_deployed_versions(
                deployed_agents_dir=agents_dir,
                agents_to_deploy=agents_to_deploy,
                agent_sources=agent_sources
            )
            
            # Log version upgrades and source changes
            if comparison_results.get("version_upgrades"):
                self.logger.info(f"Version upgrades available for {len(comparison_results['version_upgrades'])} agents")
            if comparison_results.get("source_changes"):
                self.logger.info(f"Source changes for {len(comparison_results['source_changes'])} agents")
        
        # Convert to list of Path objects
        template_files = list(agents_to_deploy.values())
        
        return template_files, agent_sources

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
            return False, [f"Validation error: {str(e)}"]

    def get_deployment_status(self) -> Dict[str, Any]:
        """Get current deployment status and metrics."""
        return self.metrics_collector.get_deployment_status()

"""Single agent deployer for deploying individual agents."""

import logging
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from claude_mpm.core.exceptions import AgentDeploymentError


class SingleAgentDeployer:
    """Service for deploying individual agents.

    This service handles the deployment of single agent templates,
    including version checking, building, and writing agent files.
    """

    def __init__(
        self,
        template_builder,
        version_manager,
        results_manager,
        logger: Optional[logging.Logger] = None,
    ):
        """Initialize the single agent deployer.

        Args:
            template_builder: Template builder service
            version_manager: Version manager service
            results_manager: Results manager service
            logger: Optional logger instance
        """
        self.template_builder = template_builder
        self.version_manager = version_manager
        self.results_manager = results_manager
        self.logger = logger or logging.getLogger(__name__)

    def deploy_single_agent(
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
        """Deploy a single agent template.

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
            self.results_manager.record_agent_deployment(
                agent_name,
                template_file,
                target_file,
                is_update,
                is_migration,
                reason,
                agent_start_time,
                results,
                self.logger,
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
    ) -> Tuple[bool, bool, str]:
        """Check if agent needs update and determine status.

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

    def deploy_agent(
        self,
        agent_name: str,
        templates_dir: Path,
        target_dir: Path,
        base_agent_path: Path,
        force_rebuild: bool = False,
        working_directory: Optional[Path] = None,
    ) -> bool:
        """Deploy a single agent to the specified directory.

        Args:
            agent_name: Name of the agent to deploy
            templates_dir: Directory containing templates
            target_dir: Target directory for deployment (Path object)
            base_agent_path: Path to base agent configuration
            force_rebuild: Whether to force rebuild even if version is current
            working_directory: Working directory for determining agent source

        Returns:
            True if deployment was successful, False otherwise

        WHY: Single agent deployment because:
        - Users may want to deploy specific agents only
        - Reduces deployment time for targeted updates
        - Enables selective agent management in projects
        """
        try:
            # Find the template file - search multiple sources
            template_file = self._find_agent_template(
                agent_name, templates_dir, working_directory
            )
            if template_file is None:
                self.logger.error(
                    f"Agent template not found in any source: {agent_name}"
                )
                return False

            # Ensure target directory exists
            target_dir.mkdir(parents=True, exist_ok=True)

            # Build and deploy the agent
            target_file = target_dir / f"{agent_name}.md"

            # Check if update is needed
            if not force_rebuild and target_file.exists():
                # Load base agent data for version checking
                base_agent_data = {}
                base_agent_version = (0, 0, 0)
                if base_agent_path.exists():
                    try:
                        import json

                        base_agent_data = json.loads(base_agent_path.read_text())
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
                self.logger.info(f"Updating agent {agent_name}: {reason}")

            # Load base agent data for building
            base_agent_data = {}
            if base_agent_path.exists():
                try:
                    import json

                    base_agent_data = json.loads(base_agent_path.read_text())
                except Exception as e:
                    self.logger.warning(f"Could not load base agent: {e}")

            # Build the agent markdown
            # For single agent deployment, determine source from template location
            source_info = self._determine_agent_source(
                template_file, working_directory or Path.cwd()
            )
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

    def _find_agent_template(
        self,
        agent_name: str,
        templates_dir: Path,
        working_directory: Optional[Path] = None,
    ) -> Optional[Path]:
        """Find agent template across all source tiers.

        Searches for the agent template in this priority order:
        1. System templates directory (templates_dir)
        2. Git cache (remote agents from configured repositories)
        3. Project agents (.claude-mpm/agents/ in working directory)
        4. User agents (~/.claude-mpm/agents/)

        Args:
            agent_name: Name of the agent (file stem without .md)
            templates_dir: System templates directory
            working_directory: Working directory for project agents

        Returns:
            Path to the template file, or None if not found
        """
        # 1. Check system templates directory
        template_file = templates_dir / f"{agent_name}.md"
        if template_file.exists():
            self.logger.debug(f"Found agent '{agent_name}' in system templates")
            return template_file

        # 2. Check git cache via GitSourceManager
        try:
            from claude_mpm.services.agents.git_source_manager import GitSourceManager

            git_mgr = GitSourceManager()
            cached_path = git_mgr.get_agent_path(agent_name)
            if cached_path and cached_path.exists():
                self.logger.debug(
                    f"Found agent '{agent_name}' in git cache: {cached_path}"
                )
                return cached_path
        except Exception as e:
            self.logger.debug(f"Git cache lookup failed for '{agent_name}': {e}")

        # 3. Check project agents
        if working_directory:
            project_agent = (
                working_directory / ".claude-mpm" / "agents" / f"{agent_name}.md"
            )
            if project_agent.exists():
                self.logger.debug(f"Found agent '{agent_name}' in project agents")
                return project_agent

        # 4. Check user agents (deprecated but still supported)
        user_agent = Path.home() / ".claude-mpm" / "agents" / f"{agent_name}.md"
        if user_agent.exists():
            self.logger.debug(f"Found agent '{agent_name}' in user agents")
            return user_agent

        # 5. Scan git cache directories directly as fallback
        # (handles cases where agent_id doesn't match filename)
        try:
            cache_root = Path.home() / ".claude-mpm" / "cache" / "agents"
            if cache_root.exists():
                for md_file in cache_root.rglob(f"{agent_name}.md"):
                    self.logger.debug(
                        f"Found agent '{agent_name}' via cache scan: {md_file}"
                    )
                    return md_file
        except Exception as e:
            self.logger.debug(f"Cache directory scan failed for '{agent_name}': {e}")

        return None

    def _determine_agent_source(
        self, template_path: Path, working_directory: Path
    ) -> str:
        """Determine the source of an agent from its template path.

        WHY: When deploying single agents, we need to track their source
        for proper version management and debugging.

        Args:
            template_path: Path to the agent template
            working_directory: Current working directory

        Returns:
            Source string (system/project/user/unknown)
        """
        template_str = str(template_path.resolve())

        # Check if it's a system template
        if (
            "/claude_mpm/agents/templates/" in template_str
            or "/src/claude_mpm/agents/templates/" in template_str
        ):
            return "system"

        # Check if it's from the git cache (remote agents)
        if "/.claude-mpm/cache/agents/" in template_str:
            return "remote"

        # Check if it's a project agent
        if "/.claude-mpm/agents/" in template_str:
            # Check if it's in the current working directory
            if str(working_directory) in template_str:
                return "project"
            # Check if it's in user home
            if str(Path.home()) in template_str:
                return "user"

        return "unknown"

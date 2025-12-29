"""Local Template Deployment Service for Claude MPM.

This module handles the deployment of local JSON agent templates to Claude Code's
.claude/agents directory. It converts JSON templates to YAML format while preserving
local metadata and ensuring proper priority handling.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from claude_mpm.core.logging_config import get_logger
from claude_mpm.services.agents.local_template_manager import (
    LocalAgentTemplate,
    LocalAgentTemplateManager,
)

logger = get_logger(__name__)


class LocalTemplateDeploymentService:
    """Service for deploying local JSON templates to Claude Code."""

    def __init__(self, working_directory: Optional[Path] = None):
        """Initialize the local template deployment service.

        Args:
            working_directory: Working directory for project-level agents
        """
        self.working_directory = working_directory or Path.cwd()
        self.template_manager = LocalAgentTemplateManager(working_directory)

        # Target directory for Claude Code agents
        self.target_dir = self.working_directory / ".claude" / "agents"

        logger.info(
            f"LocalTemplateDeploymentService initialized for: {self.working_directory}"
        )

    def deploy_local_templates(
        self, force_rebuild: bool = False, tier_filter: Optional[str] = None
    ) -> Dict[str, Any]:
        """Deploy all local JSON templates to Claude Code.

        Args:
            force_rebuild: Force rebuild even if agents exist
            tier_filter: Filter by tier ('project' or 'user')

        Returns:
            Deployment results dictionary
        """
        results = {
            "deployed": [],
            "updated": [],
            "skipped": [],
            "errors": [],
            "total": 0,
        }

        # Ensure target directory exists
        self.target_dir.mkdir(parents=True, exist_ok=True)

        # Discover local templates
        templates = self.template_manager.discover_local_templates()

        # Filter by tier if requested
        if tier_filter:
            templates = {
                agent_id: template
                for agent_id, template in templates.items()
                if template.tier == tier_filter
            }

        results["total"] = len(templates)

        # Deploy each template
        for agent_id, template in templates.items():
            try:
                deployed = self._deploy_single_template(template, force_rebuild)

                if deployed == "deployed":
                    results["deployed"].append(agent_id)
                elif deployed == "updated":
                    results["updated"].append(agent_id)
                else:
                    results["skipped"].append(agent_id)

            except Exception as e:
                logger.error(f"Failed to deploy local template {agent_id}: {e}")
                results["errors"].append(f"{agent_id}: {e}")

        logger.debug(
            f"Local template deployment: deployed={len(results['deployed'])}, "
            f"updated={len(results['updated'])}, skipped={len(results['skipped'])}, "
            f"errors={len(results['errors'])}"
        )

        return results

    def _deploy_single_template(
        self, template: LocalAgentTemplate, force_rebuild: bool
    ) -> str:
        """Deploy a single local template.

        Args:
            template: Template to deploy
            force_rebuild: Force rebuild even if exists

        Returns:
            'deployed', 'updated', or 'skipped'
        """
        target_file = self.target_dir / f"{template.agent_id}.md"

        # Check if needs update
        if not force_rebuild and target_file.exists():
            # Check version
            existing_version = self._get_existing_version(target_file)
            if existing_version and existing_version >= template.agent_version:
                logger.debug(
                    f"Skipping {template.agent_id}: version {existing_version} >= {template.agent_version}"
                )
                return "skipped"

        # Convert JSON template to YAML frontmatter format
        yaml_content = self._convert_to_yaml_format(template)

        # Write to target file
        action = "updated" if target_file.exists() else "deployed"
        target_file.write_text(yaml_content)

        logger.info(
            f"{action.capitalize()} local agent {template.agent_id} (v{template.agent_version})"
        )
        return action

    def _convert_to_yaml_format(self, template: LocalAgentTemplate) -> str:
        """Convert local JSON template to YAML frontmatter format.

        Args:
            template: Template to convert

        Returns:
            YAML formatted agent content
        """
        # Build frontmatter
        frontmatter = {
            "name": template.metadata.get("name", template.agent_id),
            "description": template.metadata.get("description", ""),
            "version": template.agent_version,
            "author": template.author,
            "tier": template.tier,
            "priority": template.priority,
            "tags": template.metadata.get("tags", ["local"]),
            "specializations": template.metadata.get("specializations", []),
        }

        # Add capabilities
        if template.capabilities:
            # Only include model if explicitly set (no default)
            if "model" in template.capabilities:
                frontmatter["model"] = template.capabilities["model"]
            tools = template.capabilities.get("tools", "*")
            if tools == "*":
                frontmatter["tools"] = "all"
            elif isinstance(tools, list):
                frontmatter["tools"] = tools
            else:
                frontmatter["tools"] = tools.split(",") if "," in tools else [tools]

        # Add configuration if present
        if template.configuration:
            frontmatter["temperature"] = template.configuration.get("temperature", 0.7)
            frontmatter["max_tokens"] = template.configuration.get("max_tokens", 4096)

        # Add parent agent reference if present
        if template.parent_agent:
            frontmatter["parent_agent"] = template.parent_agent

        # Add local indicator
        frontmatter["is_local"] = True

        # Build YAML content
        yaml_str = yaml.dump(frontmatter, default_flow_style=False, sort_keys=False)

        # Combine with instructions
        content = f"---\n{yaml_str}---\n\n# {frontmatter['name']}\n\n{frontmatter['description']}\n\n"

        # Add instructions
        if template.instructions:
            content += "## Instructions\n\n"
            content += template.instructions + "\n"
        else:
            content += "## Instructions\n\n"
            content += f"This is a local {template.agent_id} agent for the {template.author} project.\n"

        # Add inheritance note if applicable
        if template.parent_agent:
            content += f"\n## Inheritance\n\nThis agent inherits from: {template.parent_agent}\n"

        return content

    def _get_existing_version(self, agent_file: Path) -> Optional[str]:
        """Get version from existing agent file.

        Args:
            agent_file: Path to agent file

        Returns:
            Version string if found, None otherwise
        """
        try:
            content = agent_file.read_text()

            # Parse YAML frontmatter
            if content.startswith("---"):
                end_marker = content.find("---", 3)
                if end_marker != -1:
                    frontmatter_str = content[3:end_marker].strip()
                    frontmatter = yaml.safe_load(frontmatter_str)
                    return frontmatter.get("version")

        except Exception as e:
            logger.debug(f"Could not extract version from {agent_file}: {e}")

        return None

    def deploy_single_local_template(
        self, agent_id: str, force_rebuild: bool = False
    ) -> bool:
        """Deploy a specific local template by ID.

        Args:
            agent_id: ID of agent to deploy
            force_rebuild: Force rebuild even if exists

        Returns:
            True if deployed successfully, False otherwise
        """
        template = self.template_manager.get_local_template(agent_id)
        if not template:
            logger.error(f"Local template not found: {agent_id}")
            return False

        try:
            result = self._deploy_single_template(template, force_rebuild)
            return result in ["deployed", "updated"]
        except Exception as e:
            logger.error(f"Failed to deploy local template {agent_id}: {e}")
            return False

    def list_deployed_local_agents(self) -> List[Dict[str, Any]]:
        """List all deployed local agents.

        Returns:
            List of deployed local agent information
        """
        deployed = []

        if not self.target_dir.exists():
            return deployed

        for agent_file in self.target_dir.glob("*.md"):
            try:
                content = agent_file.read_text()

                # Parse YAML frontmatter
                if content.startswith("---"):
                    end_marker = content.find("---", 3)
                    if end_marker != -1:
                        frontmatter_str = content[3:end_marker].strip()
                        frontmatter = yaml.safe_load(frontmatter_str)

                        # Check if it's a local agent
                        if frontmatter.get("is_local") or frontmatter.get("tier") in [
                            "project",
                            "user",
                        ]:
                            deployed.append(
                                {
                                    "id": agent_file.stem,
                                    "name": frontmatter.get("name", agent_file.stem),
                                    "version": frontmatter.get("version", "unknown"),
                                    "author": frontmatter.get("author", "unknown"),
                                    "tier": frontmatter.get("tier", "unknown"),
                                    "tags": frontmatter.get("tags", []),
                                    "file": str(agent_file),
                                }
                            )

            except Exception as e:
                logger.debug(f"Could not parse {agent_file}: {e}")

        return deployed

    def clean_local_deployments(self) -> int:
        """Remove all deployed local agents.

        Returns:
            Number of agents removed
        """
        count = 0
        deployed = self.list_deployed_local_agents()

        for agent_info in deployed:
            try:
                agent_file = Path(agent_info["file"])
                if agent_file.exists():
                    agent_file.unlink()
                    count += 1
                    logger.info(f"Removed deployed local agent: {agent_info['id']}")
            except Exception as e:
                logger.error(f"Failed to remove {agent_info['id']}: {e}")

        return count

    def sync_local_templates(self) -> Dict[str, Any]:
        """Synchronize local templates with deployed agents.

        This ensures deployed agents match their source templates.

        Returns:
            Sync results dictionary
        """
        results = {"updated": [], "removed": [], "added": [], "errors": []}

        # Get current state
        templates = self.template_manager.discover_local_templates()
        deployed = {agent["id"]: agent for agent in self.list_deployed_local_agents()}

        # Check for updates and additions
        for agent_id, template in templates.items():
            if agent_id in deployed:
                # Check if needs update
                if deployed[agent_id][
                    "version"
                ] != template.agent_version and self.deploy_single_local_template(
                    agent_id, force_rebuild=True
                ):
                    results["updated"].append(agent_id)
            # New agent to deploy
            elif self.deploy_single_local_template(agent_id):
                results["added"].append(agent_id)

        # Check for orphaned deployments (deployed but no template)
        for agent_id in deployed:
            if agent_id not in templates:
                try:
                    agent_file = Path(deployed[agent_id]["file"])
                    agent_file.unlink()
                    results["removed"].append(agent_id)
                    logger.info(f"Removed orphaned local agent: {agent_id}")
                except Exception as e:
                    logger.error(f"Failed to remove orphaned agent {agent_id}: {e}")
                    results["errors"].append(f"{agent_id}: {e}")

        logger.info(
            f"Sync complete: added={len(results['added'])}, "
            f"updated={len(results['updated'])}, removed={len(results['removed'])}"
        )

        return results

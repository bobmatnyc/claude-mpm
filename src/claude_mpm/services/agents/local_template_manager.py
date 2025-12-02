"""Local Agent Template Manager for Claude MPM.

This module provides comprehensive support for managing local agent templates
stored in project and user directories. It handles JSON template discovery,
validation, deployment, and versioning with proper priority handling.

Key Features:
- Local JSON template discovery in .claude-mpm/agents/
- Project-specific agent templates with project name as author
- Custom versioning for local agents
- Template inheritance from system agents
- Hot-reload support during development
- Proper priority handling (PROJECT > USER > SYSTEM)
"""

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import yaml

from claude_mpm.core.logging_config import get_logger
from claude_mpm.core.unified_paths import get_path_manager

logger = get_logger(__name__)


@dataclass
class LocalAgentTemplate:
    """Model for local agent templates with project-specific metadata."""

    schema_version: str = "1.3.0"
    agent_id: str = ""
    agent_version: str = "1.0.0"
    author: str = ""  # Will be project name for local agents
    agent_type: str = ""  # Backwards compatibility field

    metadata: Dict[str, Any] = None
    capabilities: Dict[str, Any] = None
    instructions: str = ""
    configuration: Dict[str, Any] = None

    # Local-specific fields
    tier: str = "project"
    priority: int = 1000  # Higher priority for local agents
    is_local: bool = True
    parent_agent: Optional[str] = None  # For inheritance from system agents
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def __post_init__(self):
        """Initialize default values."""
        if self.metadata is None:
            self.metadata = {}
        if self.capabilities is None:
            self.capabilities = {"model": "sonnet", "tools": "*"}
        if self.configuration is None:
            self.configuration = {}
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc).isoformat()
        if self.updated_at is None:
            self.updated_at = datetime.now(timezone.utc).isoformat()

        # Ensure metadata has required fields
        if "name" not in self.metadata:
            self.metadata["name"] = self.agent_id.replace("_", " ").title()
        if "description" not in self.metadata:
            self.metadata["description"] = f"Local {self.agent_id} agent"
        if "tier" not in self.metadata:
            self.metadata["tier"] = self.tier
        if "tags" not in self.metadata:
            self.metadata["tags"] = ["local", "custom"]

    def to_json(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dictionary."""
        data = {
            "schema_version": self.schema_version,
            "agent_id": self.agent_id,
            "agent_version": self.agent_version,
            "author": self.author,
            "agent_type": self.agent_type or self.agent_id,
            "metadata": self.metadata,
            "capabilities": self.capabilities,
            "instructions": self.instructions,
            "configuration": self.configuration,
            "priority": self.priority,
        }

        # Add optional fields if present
        if self.parent_agent:
            data["parent_agent"] = self.parent_agent
        if self.created_at:
            data["created_at"] = self.created_at
        if self.updated_at:
            data["updated_at"] = self.updated_at

        return data

    @classmethod
    def from_json(cls, data: Dict[str, Any]) -> "LocalAgentTemplate":
        """Create from JSON dictionary."""
        return cls(
            schema_version=data.get("schema_version", "1.3.0"),
            agent_id=data.get("agent_id", ""),
            agent_version=data.get("agent_version", "1.0.0"),
            author=data.get("author", ""),
            agent_type=data.get("agent_type", ""),
            metadata=data.get("metadata", {}),
            capabilities=data.get("capabilities", {}),
            instructions=data.get("instructions", ""),
            configuration=data.get("configuration", {}),
            tier=data.get("metadata", {}).get("tier", "project"),
            priority=data.get("priority", 1000),
            parent_agent=data.get("parent_agent"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )


class LocalAgentTemplateManager:
    """Manager for local agent templates in project and user directories."""

    def __init__(self, working_directory: Optional[Path] = None):
        """Initialize the local template manager.

        Args:
            working_directory: Working directory for project-level agents
        """
        self.path_manager = get_path_manager()
        self.working_directory = working_directory or Path.cwd()

        # Define local agent directories
        self.project_agents_dir = self.working_directory / ".claude-mpm" / "agents"
        self.user_agents_dir = Path.home() / ".claude-mpm" / "agents"

        # Cache for discovered templates
        self._template_cache: Dict[str, LocalAgentTemplate] = {}
        self._cache_valid = False

        logger.info(
            f"LocalAgentTemplateManager initialized for project: {self.working_directory}"
        )

    def get_project_name(self) -> str:
        """Get the current project name for use as author field.

        Returns:
            Project directory name or 'local-project' as fallback
        """
        try:
            # Use the project directory name
            project_name = self.working_directory.name
            if project_name and project_name != "/":
                return project_name
        except Exception as e:
            logger.warning(f"Failed to get project name: {e}")

        return "local-project"

    def discover_local_templates(
        self, force_refresh: bool = False
    ) -> Dict[str, LocalAgentTemplate]:
        """Discover all local agent templates.

        Args:
            force_refresh: Force re-discovery even if cache is valid

        Returns:
            Dictionary mapping agent IDs to LocalAgentTemplate objects
        """
        if self._cache_valid and not force_refresh:
            return self._template_cache

        self._template_cache.clear()

        # Discover from project directory (highest priority)
        if self.project_agents_dir.exists():
            self._discover_templates_in_dir(self.project_agents_dir, "project")

        # Discover from user directory
        if self.user_agents_dir.exists():
            self._discover_templates_in_dir(self.user_agents_dir, "user")

        self._cache_valid = True
        logger.debug(f"Discovered {len(self._template_cache)} local agent templates")

        return self._template_cache

    def _discover_templates_in_dir(self, directory: Path, tier: str) -> None:
        """Discover templates in a specific directory.

        Args:
            directory: Directory to search for templates
            tier: Tier level ('project' or 'user')
        """
        # Agent templates migrated to Markdown with YAML frontmatter (v4.26.0+)
        for template_file in directory.glob("*.md"):
            try:
                # Read markdown content and extract YAML frontmatter
                content = template_file.read_text()
                frontmatter = self._extract_yaml_frontmatter(content)
                if not frontmatter:
                    logger.warning(f"No YAML frontmatter in {template_file.name}")
                    continue
                data = frontmatter

                # Create LocalAgentTemplate
                template = LocalAgentTemplate.from_json(data)

                # Set tier and author based on location
                template.tier = tier
                if tier == "project" and not template.author:
                    template.author = self.get_project_name()
                elif tier == "user" and not template.author:
                    template.author = Path.home().name

                # Use higher priority for project agents
                if tier == "project":
                    template.priority = 2000
                else:
                    template.priority = 1500

                # Store in cache (project templates override user templates)
                agent_id = template.agent_id or template_file.stem
                if agent_id not in self._template_cache or tier == "project":
                    self._template_cache[agent_id] = template
                    logger.debug(f"Discovered {tier} agent template: {agent_id}")

            except Exception as e:
                logger.error(f"Failed to load template from {template_file}: {e}")

    def _extract_yaml_frontmatter(self, content: str) -> Optional[Dict[str, Any]]:
        """
        Extract and parse YAML frontmatter from markdown content.

        Args:
            content: File content to parse

        Returns:
            Parsed YAML frontmatter as dict, or None if not found/invalid
        """
        if not content.strip().startswith("---"):
            return None

        # Split on --- delimiters
        parts = content.split("---", 2)
        if len(parts) < 3:
            return None

        try:
            return yaml.safe_load(parts[1])
        except yaml.YAMLError as e:
            logger.warning(f"Failed to parse YAML frontmatter: {e}")
            return None

    def create_local_template(
        self,
        agent_id: str,
        name: str,
        description: str,
        instructions: str,
        model: str = "sonnet",
        tools: Union[str, List[str]] = "*",
        parent_agent: Optional[str] = None,
        tier: str = "project",
    ) -> LocalAgentTemplate:
        """Create a new local agent template.

        Args:
            agent_id: Unique identifier for the agent
            name: Human-readable name
            description: Agent description
            instructions: Agent instructions
            model: Model to use (default: sonnet)
            tools: Tools available to agent (default: all)
            parent_agent: Optional parent agent to inherit from
            tier: Tier level ('project' or 'user')

        Returns:
            Created LocalAgentTemplate object
        """
        # Determine author based on tier
        author = self.get_project_name() if tier == "project" else Path.home().name

        # Create template
        return LocalAgentTemplate(
            agent_id=agent_id,
            agent_version="1.0.0",
            author=author,
            agent_type=agent_id,
            metadata={
                "name": name,
                "description": description,
                "tier": tier,
                "tags": ["local", "custom", tier],
                "specializations": [],
            },
            capabilities={
                "model": model,
                "tools": (
                    tools
                    if isinstance(tools, str)
                    else ",".join(tools)
                    if tools
                    else "*"
                ),
            },
            instructions=instructions,
            configuration={"temperature": 0.7, "max_tokens": 4096},
            tier=tier,
            priority=2000 if tier == "project" else 1500,
            parent_agent=parent_agent,
        )

    def save_local_template(
        self, template: LocalAgentTemplate, tier: Optional[str] = None
    ) -> Path:
        """Save a local agent template to disk.

        Args:
            template: Template to save
            tier: Override tier (uses template.tier if not specified)

        Returns:
            Path to saved template file
        """
        # Determine target directory
        tier = tier or template.tier
        if tier == "project":
            target_dir = self.project_agents_dir
        else:
            target_dir = self.user_agents_dir

        # Create directory if needed
        target_dir.mkdir(parents=True, exist_ok=True)

        # Update timestamp
        template.updated_at = datetime.now(timezone.utc).isoformat()

        # Save to JSON file
        template_file = target_dir / f"{template.agent_id}.json"
        with template_file.open("w") as f:
            json.dump(template.to_json(), f, indent=2)

        # Invalidate cache
        self._cache_valid = False

        logger.info(f"Saved local agent template: {template_file}")
        return template_file

    def delete_local_template(
        self,
        agent_id: str,
        tier: str = "project",
        delete_deployment: bool = True,
        backup_first: bool = False,
    ) -> Dict[str, Any]:
        """Delete a local agent template with comprehensive options.

        Args:
            agent_id: The agent ID to delete
            tier: The tier (project/user/all) to delete from
            delete_deployment: Also delete from .claude/agents/
            backup_first: Create backup before deletion

        Returns:
            Dict with status, deleted files, backup location (if applicable)
        """
        result = {
            "success": False,
            "deleted_files": [],
            "errors": [],
            "backup_location": None,
            "agent_id": agent_id,
            "tier": tier,
        }

        # Check if this is a system agent (protected)
        system_agents = [
            "orchestrator",
            "engineer",
            "architecture",
            "documentation",
            "qa",
            "research",
            "ops",
            "security",
            "data_engineer",
            "version_control",
            "pm",
            "project-manager",
            "claude-mpm",
        ]
        if agent_id in system_agents:
            result["errors"].append(f"Cannot delete system agent: {agent_id}")
            return result

        # Determine which directories to check based on tier
        dirs_to_check = []
        if tier in ["project", "all"]:
            dirs_to_check.append(("project", self.project_agents_dir))
        if tier in ["user", "all"]:
            dirs_to_check.append(("user", self.user_agents_dir))

        # Track files to delete
        files_to_delete = []

        # Find template files (templates migrated to .md in v4.26.0+)
        for tier_name, agent_dir in dirs_to_check:
            template_file = agent_dir / f"{agent_id}.md"
            if template_file.exists():
                files_to_delete.append((tier_name, "template", template_file))

                # Check for version history
                versions_dir = agent_dir / "versions" / agent_id
                if versions_dir.exists():
                    for version_file in versions_dir.glob("*.md"):
                        files_to_delete.append((tier_name, "version", version_file))
                    files_to_delete.append((tier_name, "versions_dir", versions_dir))

        # Check for deployment
        if delete_deployment:
            deployment_file = (
                self.working_directory / ".claude" / "agents" / f"{agent_id}.md"
            )
            if deployment_file.exists():
                files_to_delete.append(("deployment", "agent", deployment_file))

        # If no files found, return early
        if not files_to_delete:
            result["errors"].append(f"Agent '{agent_id}' not found in {tier} tier(s)")
            return result

        # Create backup if requested
        if backup_first:
            backup_result = self._create_deletion_backup(agent_id, files_to_delete)
            if backup_result["success"]:
                result["backup_location"] = backup_result["location"]
            else:
                result["errors"].append(f"Backup failed: {backup_result['error']}")
                return result

        # Perform deletion
        for tier_name, file_type, file_path in files_to_delete:
            try:
                if file_type == "versions_dir":
                    # Remove empty directory
                    if file_path.is_dir() and not any(file_path.iterdir()):
                        file_path.rmdir()
                        result["deleted_files"].append(str(file_path))
                        logger.debug(f"Removed empty directory: {file_path}")
                else:
                    file_path.unlink()
                    result["deleted_files"].append(str(file_path))
                    logger.info(f"Deleted {tier_name} {file_type}: {file_path.name}")
            except Exception as e:
                error_msg = f"Failed to delete {file_path}: {e}"
                result["errors"].append(error_msg)
                logger.error(error_msg)

        # Invalidate cache if any deletions succeeded
        if result["deleted_files"]:
            self._cache_valid = False
            result["success"] = True
            logger.info(
                f"Successfully deleted agent '{agent_id}' - removed {len(result['deleted_files'])} file(s)"
            )

        return result

    def _create_deletion_backup(
        self, agent_id: str, files_to_delete: List[Tuple[str, str, Path]]
    ) -> Dict[str, Any]:
        """Create a backup of files before deletion.

        Args:
            agent_id: Agent being deleted
            files_to_delete: List of (tier, type, path) tuples

        Returns:
            Dict with success status and backup location or error
        """
        import shutil
        from datetime import datetime

        result = {"success": False, "location": None, "error": None}

        try:
            # Create backup directory
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            backup_dir = (
                self.working_directory
                / ".claude-mpm"
                / "backups"
                / f"{agent_id}_{timestamp}"
            )
            backup_dir.mkdir(parents=True, exist_ok=True)

            # Copy files to backup
            for tier_name, file_type, file_path in files_to_delete:
                if file_path.exists() and file_type != "versions_dir":
                    # Create subdirectory structure in backup
                    backup_subdir = backup_dir / tier_name
                    backup_subdir.mkdir(exist_ok=True)

                    if file_path.is_file():
                        backup_file = backup_subdir / file_path.name
                        shutil.copy2(file_path, backup_file)
                        logger.debug(f"Backed up {file_path} to {backup_file}")

            result["success"] = True
            result["location"] = str(backup_dir)
            logger.info(f"Created backup for agent '{agent_id}' at {backup_dir}")

        except Exception as e:
            result["error"] = str(e)
            logger.error(f"Failed to create backup for '{agent_id}': {e}")

        return result

    def delete_multiple_templates(
        self,
        agent_ids: List[str],
        tier: str = "project",
        delete_deployment: bool = True,
        backup_first: bool = False,
    ) -> Dict[str, Any]:
        """Delete multiple local agent templates.

        Args:
            agent_ids: List of agent IDs to delete
            tier: The tier (project/user/all) to delete from
            delete_deployment: Also delete from .claude/agents/
            backup_first: Create backup before deletion

        Returns:
            Dict with results for each agent
        """
        results = {
            "successful": [],
            "failed": [],
            "total": len(agent_ids),
            "details": {},
        }

        for agent_id in agent_ids:
            result = self.delete_local_template(
                agent_id=agent_id,
                tier=tier,
                delete_deployment=delete_deployment,
                backup_first=backup_first,
            )

            results["details"][agent_id] = result

            if result["success"]:
                results["successful"].append(agent_id)
            else:
                results["failed"].append(agent_id)

        logger.info(
            f"Bulk deletion complete: {len(results['successful'])} successful, "
            f"{len(results['failed'])} failed"
        )

        return results

    def get_local_template(self, agent_id: str) -> Optional[LocalAgentTemplate]:
        """Get a specific local agent template.

        Args:
            agent_id: ID of agent to retrieve

        Returns:
            LocalAgentTemplate if found, None otherwise
        """
        templates = self.discover_local_templates()
        return templates.get(agent_id)

    def list_local_templates(
        self, tier: Optional[str] = None
    ) -> List[LocalAgentTemplate]:
        """List all local agent templates.

        Args:
            tier: Filter by tier ('project' or 'user'), None for all

        Returns:
            List of LocalAgentTemplate objects
        """
        templates = self.discover_local_templates()

        if tier:
            return [t for t in templates.values() if t.tier == tier]
        return list(templates.values())

    def inherit_from_system_agent(
        self, system_agent_id: str, new_agent_id: str, modifications: Dict[str, Any]
    ) -> LocalAgentTemplate:
        """Create a local agent by inheriting from a system agent.

        Args:
            system_agent_id: ID of system agent to inherit from
            new_agent_id: ID for the new local agent
            modifications: Dictionary of modifications to apply

        Returns:
            Created LocalAgentTemplate object
        """
        # TODO: Load system agent template and merge with modifications
        # For now, create a basic template with parent reference

        template = self.create_local_template(
            agent_id=new_agent_id,
            name=modifications.get("name", f"Custom {system_agent_id}"),
            description=modifications.get(
                "description", f"Customized version of {system_agent_id}"
            ),
            instructions=modifications.get(
                "instructions", f"Based on {system_agent_id} agent"
            ),
            model=modifications.get("model", "sonnet"),
            tools=modifications.get("tools", "*"),
            parent_agent=system_agent_id,
            tier="project",
        )

        # Apply any additional modifications
        if "metadata" in modifications:
            template.metadata.update(modifications["metadata"])
        if "capabilities" in modifications:
            template.capabilities.update(modifications["capabilities"])
        if "configuration" in modifications:
            template.configuration.update(modifications["configuration"])

        return template

    def version_local_template(self, agent_id: str, new_version: str) -> Optional[Path]:
        """Create a versioned copy of a local agent template.

        Args:
            agent_id: ID of agent to version
            new_version: New version string

        Returns:
            Path to versioned template file if successful
        """
        template = self.get_local_template(agent_id)
        if not template:
            logger.error(f"Local agent template not found: {agent_id}")
            return None

        # Create versions directory
        if template.tier == "project":
            versions_dir = self.project_agents_dir / "versions" / agent_id
        else:
            versions_dir = self.user_agents_dir / "versions" / agent_id

        versions_dir.mkdir(parents=True, exist_ok=True)

        # Save current version
        old_version_file = versions_dir / f"{template.agent_version}.json"
        with old_version_file.open("w") as f:
            json.dump(template.to_json(), f, indent=2)

        # Update template version
        template.agent_version = new_version
        template.updated_at = datetime.now(timezone.utc).isoformat()

        # Save updated template
        self.save_local_template(template)

        logger.info(
            f"Versioned local agent {agent_id}: {template.agent_version} -> {new_version}"
        )
        return old_version_file

    def validate_local_template(
        self, template: LocalAgentTemplate
    ) -> Tuple[bool, List[str]]:
        """Validate a local agent template.

        Args:
            template: Template to validate

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []

        # Check required fields
        if not template.agent_id:
            errors.append("agent_id is required")
        if not template.instructions:
            errors.append("instructions are required")
        if not template.metadata.get("name"):
            errors.append("metadata.name is required")

        # Validate capabilities
        if template.capabilities:
            model = template.capabilities.get("model")
            if model and model not in ["opus", "sonnet", "haiku"]:
                errors.append(f"Invalid model: {model}")

        # Check for naming conflicts
        if template.agent_id in ["pm", "project-manager", "claude-mpm"]:
            errors.append(f"Reserved agent ID: {template.agent_id}")

        return len(errors) == 0, errors

    def export_local_templates(self, output_dir: Path) -> int:
        """Export all local templates to a directory.

        Args:
            output_dir: Directory to export templates to

        Returns:
            Number of templates exported
        """
        templates = self.discover_local_templates()
        output_dir.mkdir(parents=True, exist_ok=True)

        count = 0
        for agent_id, template in templates.items():
            output_file = output_dir / f"{agent_id}.json"
            with output_file.open("w") as f:
                json.dump(template.to_json(), f, indent=2)
            count += 1

        logger.info(f"Exported {count} local agent templates to {output_dir}")
        return count

    def import_local_templates(self, input_dir: Path, tier: str = "project") -> int:
        """Import agent templates from a directory.

        Args:
            input_dir: Directory containing template JSON files
            tier: Tier to import into ('project' or 'user')

        Returns:
            Number of templates imported
        """
        if not input_dir.exists():
            logger.error(f"Input directory does not exist: {input_dir}")
            return 0

        count = 0
        # Agent templates migrated to Markdown with YAML frontmatter (v4.26.0+)
        for template_file in input_dir.glob("*.md"):
            try:
                # Read markdown content and extract YAML frontmatter
                content = template_file.read_text()
                frontmatter = self._extract_yaml_frontmatter(content)
                if not frontmatter:
                    logger.warning(f"No YAML frontmatter in {template_file.name}")
                    continue
                data = frontmatter

                template = LocalAgentTemplate.from_json(data)
                template.tier = tier

                # Update author based on tier
                if tier == "project":
                    template.author = self.get_project_name()
                else:
                    template.author = Path.home().name

                # Validate before saving
                is_valid, errors = self.validate_local_template(template)
                if is_valid:
                    self.save_local_template(template)
                    count += 1
                else:
                    logger.warning(
                        f"Skipping invalid template {template_file}: {errors}"
                    )

            except Exception as e:
                logger.error(f"Failed to import template from {template_file}: {e}")

        logger.info(f"Imported {count} local agent templates from {input_dir}")
        return count

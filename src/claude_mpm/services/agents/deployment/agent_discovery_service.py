"""Agent Discovery Service

This service handles the discovery, filtering, and metadata extraction of agent templates.
Provides centralized logic for finding available agents and determining which should be deployed.

Extracted from AgentDeploymentService as part of the refactoring to improve
maintainability and testability.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from claude_mpm.core.config import Config
from claude_mpm.core.logging_config import get_logger


class AgentDiscoveryService:
    """Service for discovering and filtering agent templates.

    This service handles:
    - Agent template discovery across multiple directories
    - Template filtering based on configuration
    - Agent metadata extraction and validation
    - Available agent listing and categorization
    """

    def __init__(self, templates_dir: Path):
        """Initialize the agent discovery service.

        Args:
            templates_dir: Directory containing agent templates
        """
        self.logger = get_logger(__name__)
        self.templates_dir = templates_dir

    def list_available_agents(self, log_discovery: bool = True) -> List[Dict[str, Any]]:
        """
        List all available agent templates with their metadata.

        Args:
            log_discovery: Whether to log discovery results (default: True).
                          Set to False when called from multi-source discovery to avoid duplicate logs.

        Returns:
            List of agent information dictionaries containing:
            - name: Agent name
            - description: Agent description
            - version: Agent version
            - tools: List of tools the agent uses
            - specializations: Agent specializations
            - file_path: Path to template file
        """
        agents = []

        if not self.templates_dir.exists():
            self.logger.warning(
                f"Templates directory does not exist: {self.templates_dir}"
            )
            return agents

        # Find all JSON template files
        template_files = list(self.templates_dir.glob("*.json"))

        for template_file in template_files:
            try:
                agent_info = self._extract_agent_metadata(template_file)
                if agent_info:
                    agents.append(agent_info)

            except Exception as e:
                self.logger.error(
                    f"Failed to process template {template_file.name}: {e}"
                )
                continue

        # Sort by agent name for consistent ordering
        agents.sort(key=lambda x: x.get("name", ""))

        # Only log if requested (to avoid duplicate logging from multi-source discovery)
        if log_discovery:
            self.logger.info(
                f"Discovered {len(agents)} available agent templates from {self.templates_dir.name}"
            )
        return agents

    def get_filtered_templates(
        self,
        excluded_agents: List[str],
        config: Optional[Config] = None,
        filter_non_mpm: bool = False,
    ) -> List[Path]:
        """
        Get filtered list of template files based on configuration.

        Args:
            excluded_agents: List of agent names to exclude
            config: Configuration object for additional filtering
            filter_non_mpm: Whether to filter out non-MPM agents

        Returns:
            List of template file paths to deploy
        """
        if not self.templates_dir.exists():
            self.logger.error(f"Templates directory not found: {self.templates_dir}")
            return []

        # Get all template files
        template_files = list(self.templates_dir.glob("*.json"))

        if not template_files:
            self.logger.warning(f"No agent templates found in {self.templates_dir}")
            return []

        # Apply exclusion filtering
        filtered_files = []
        excluded_count = 0
        non_mpm_count = 0

        for template_file in template_files:
            agent_name = template_file.stem

            # Check if agent is excluded
            if self._is_agent_excluded(agent_name, excluded_agents, config):
                excluded_count += 1
                self.logger.debug(f"Excluding agent: {agent_name}")
                continue

            # Check if we should filter non-MPM agents
            if filter_non_mpm and not self._is_mpm_agent(template_file):
                non_mpm_count += 1
                self.logger.debug(f"Filtering non-MPM agent: {agent_name}")
                continue

            # Validate template file
            if self._validate_template_file(template_file):
                filtered_files.append(template_file)
            else:
                self.logger.warning(f"Invalid template file: {template_file.name}")

        # Log filtering results
        if filter_non_mpm and non_mpm_count > 0:
            self.logger.info(f"Filtered out {non_mpm_count} non-MPM agents")

        self.logger.info(
            f"Found {len(template_files)} templates, excluded {excluded_count}, filtered {non_mpm_count} non-MPM, deploying {len(filtered_files)}"
        )
        return filtered_files

    def find_agent_template(self, agent_name: str) -> Optional[Path]:
        """
        Find template file for a specific agent.

        Args:
            agent_name: Name of the agent to find

        Returns:
            Path to template file if found, None otherwise
        """
        template_file = self.templates_dir / f"{agent_name}.json"

        if template_file.exists():
            if self._validate_template_file(template_file):
                return template_file
            self.logger.error(f"Invalid template file: {template_file}")
            return None

        self.logger.error(f"Template not found for agent: {agent_name}")
        return None

    def get_agent_categories(self) -> Dict[str, List[str]]:
        """
        Categorize available agents by type/specialization.

        Returns:
            Dictionary mapping categories to lists of agent names
        """
        categories = {}
        # Don't log discovery when called internally
        agents = self.list_available_agents(log_discovery=False)

        for agent in agents:
            agent_name = agent.get("name", "unknown")
            specializations = agent.get("specializations", [])

            # Categorize by specializations
            if specializations:
                for spec in specializations:
                    if spec not in categories:
                        categories[spec] = []
                    categories[spec].append(agent_name)
            else:
                # Default category for agents without specializations
                if "general" not in categories:
                    categories["general"] = []
                categories["general"].append(agent_name)

        return categories

    def _extract_agent_metadata(self, template_file: Path) -> Optional[Dict[str, Any]]:
        """
        Extract metadata from an agent template file.

        Args:
            template_file: Path to the template file

        Returns:
            Dictionary with agent metadata or None if extraction fails
        """
        try:
            # Read and parse template file
            template_content = template_file.read_text()
            template_data = json.loads(template_content)

            # Extract basic metadata from the metadata section (per agent schema)
            metadata = template_data.get("metadata", {})
            capabilities = template_data.get("capabilities", {})

            agent_info = {
                "name": metadata.get("name", template_file.stem),
                "description": metadata.get("description", "No description available"),
                "version": template_data.get(
                    "agent_version",
                    template_data.get("version", metadata.get("version", "1.0.0")),
                ),
                "tools": capabilities.get("tools", []),
                "specializations": metadata.get(
                    "tags", []
                ),  # Use tags as specializations
                "file": template_file.name,
                "path": str(template_file),
                "file_path": str(template_file),  # Keep for backward compatibility
                "size": template_file.stat().st_size,
                "model": capabilities.get("model", "sonnet"),
                "author": metadata.get("author", "unknown"),
            }

            # Validate required fields
            if not agent_info["name"]:
                self.logger.warning(f"Template missing name: {template_file.name}")
                return None

            return agent_info

        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in template {template_file.name}: {e}")
            return None
        except Exception as e:
            self.logger.error(
                f"Failed to extract metadata from {template_file.name}: {e}"
            )
            return None

    def _is_mpm_agent(self, template_file: Path) -> bool:
        """Check if agent is authored by Claude MPM team.

        MPM agents must have:
        - An author field containing 'claude mpm', 'claude-mpm', or 'anthropic'
        - A valid agent_version field

        Args:
            template_file: Path to the agent template JSON file

        Returns:
            True if this is an MPM agent, False otherwise
        """
        try:
            template_data = json.loads(template_file.read_text())
            metadata = template_data.get("metadata", {})

            # Check for author field
            author = metadata.get("author", "").lower()
            has_valid_author = any(
                pattern in author
                for pattern in ["claude mpm", "claude-mpm", "anthropic"]
            )

            # Check for version field
            has_version = bool(template_data.get("agent_version"))

            if not has_valid_author or not has_version:
                self.logger.debug(
                    f"Filtered non-MPM agent {template_file.name}: "
                    f"author='{metadata.get('author', 'missing')}', "
                    f"version={'present' if has_version else 'missing'}"
                )

            return has_valid_author and has_version

        except Exception as e:
            self.logger.debug(f"Error checking if {template_file} is MPM agent: {e}")
            return False  # Treat invalid templates as non-MPM

    def _is_agent_excluded(
        self,
        agent_name: str,
        excluded_agents: List[str],
        config: Optional[Config] = None,
    ) -> bool:
        """
        Check if an agent should be excluded from deployment.

        Args:
            agent_name: Name of the agent to check
            excluded_agents: List of explicitly excluded agents
            config: Configuration object for additional exclusion rules

        Returns:
            True if agent should be excluded, False otherwise
        """
        # Check explicit exclusion list
        if excluded_agents:
            # Determine case sensitivity from config
            case_sensitive = True
            if config:
                case_sensitive = config.get(
                    "agent_deployment.case_sensitive_exclusion", True
                )

            if case_sensitive:
                if agent_name in excluded_agents:
                    return True
            else:
                # Case-insensitive comparison
                agent_name_lower = agent_name.lower()
                excluded_lower = [name.lower() for name in excluded_agents]
                if agent_name_lower in excluded_lower:
                    return True

        # Check for additional exclusion rules from config
        if config:
            # Check pattern-based exclusions
            exclusion_patterns = config.get("agent_deployment.exclusion_patterns", [])
            for pattern in exclusion_patterns:
                if pattern in agent_name:
                    return True

            # Check environment-specific exclusions
            environment = config.get("environment", "development")
            env_exclusions = config.get(
                f"agent_deployment.{environment}_exclusions", []
            )
            if agent_name in env_exclusions:
                return True

        return False

    def _validate_template_file(self, template_file: Path) -> bool:
        """
        Validate that a template file is properly formatted.

        Args:
            template_file: Path to template file to validate

        Returns:
            True if template is valid, False otherwise
        """
        try:
            # Check file exists and is readable
            if not template_file.exists():
                return False

            # Parse JSON content
            content = template_file.read_text()
            template_data = json.loads(content)

            # Check required fields in metadata section (per agent schema)
            metadata = template_data.get("metadata", {})
            required_fields = ["name", "description"]
            for field in required_fields:
                if field not in metadata:
                    self.logger.warning(
                        f"Template {template_file.name} missing required field in metadata: {field}"
                    )
                    return False

            # Validate agent ID format (Claude Code requirements)
            # Use agent_id for validation, not the display name
            agent_id = template_data.get("agent_id", "")
            if not self._is_valid_agent_name(agent_id):
                self.logger.warning(
                    f"Invalid agent ID format in {template_file.name}: {agent_id}"
                )
                return False

            return True

        except json.JSONDecodeError:
            self.logger.error(f"Invalid JSON in template: {template_file.name}")
            return False
        except Exception as e:
            self.logger.error(
                f"Template validation failed for {template_file.name}: {e}"
            )
            return False

    def _is_valid_agent_name(self, agent_name: str) -> bool:
        """
        Validate agent name format according to Claude Code requirements.

        Args:
            agent_name: Agent name to validate

        Returns:
            True if name is valid, False otherwise
        """
        import re

        # Claude Code requires lowercase letters, numbers, and hyphens only
        # Must start with letter, no consecutive hyphens, no trailing hyphens
        pattern = r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$"

        return bool(re.match(pattern, agent_name))

    def _is_mpm_agent(
        self, template_file: Path, config: Optional[Config] = None
    ) -> bool:
        """Check if agent is authored by Claude MPM team.

        MPM agents must have:
        - An author field containing configurable MPM patterns (default: 'claude mpm', 'claude-mpm', 'anthropic')
        - A valid agent_version field

        Args:
            template_file: Path to the agent template JSON file
            config: Configuration object for MPM patterns

        Returns:
            True if this is an MPM agent, False otherwise
        """
        try:
            template_data = json.loads(template_file.read_text())
            metadata = template_data.get("metadata", {})

            # Get MPM author patterns from config
            if config:
                mpm_patterns = config.get(
                    "agent_deployment.mpm_author_patterns",
                    ["claude mpm", "claude-mpm", "anthropic"],
                )
            else:
                mpm_patterns = ["claude mpm", "claude-mpm", "anthropic"]

            # Check for author field
            author = metadata.get("author", "").lower()
            has_valid_author = any(
                pattern.lower() in author for pattern in mpm_patterns
            )

            # Check for version field
            has_version = bool(template_data.get("agent_version"))

            return has_valid_author and has_version

        except Exception as e:
            self.logger.debug(f"Error checking if {template_file} is MPM agent: {e}")
            return False  # Treat invalid templates as non-MPM

    def get_discovery_stats(self) -> Dict[str, Any]:
        """
        Get statistics about agent discovery.

        Returns:
            Dictionary with discovery statistics
        """
        stats = {
            "total_templates": 0,
            "valid_templates": 0,
            "invalid_templates": 0,
            "categories": {},
            "templates_directory": str(self.templates_dir),
            "directory_exists": self.templates_dir.exists(),
        }

        if not self.templates_dir.exists():
            return stats

        # Count template files
        template_files = list(self.templates_dir.glob("*.json"))
        stats["total_templates"] = len(template_files)

        # Validate each template
        valid_count = 0
        for template_file in template_files:
            if self._validate_template_file(template_file):
                valid_count += 1

        stats["valid_templates"] = valid_count
        stats["invalid_templates"] = stats["total_templates"] - valid_count

        # Get category distribution
        stats["categories"] = self.get_agent_categories()

        return stats

"""Agent Validator Service

This service handles validation and repair of agent configurations, templates, and deployments.
Ensures agent files meet Claude Code requirements and can fix common issues.

Extracted from AgentDeploymentService as part of the refactoring to improve
maintainability and testability.
"""

import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from claude_mpm.core.logging_config import get_logger


class AgentValidator:
    """Service for validating and repairing agent configurations.

    This service handles:
    - Agent template validation
    - YAML frontmatter validation and repair
    - Agent file structure verification
    - Configuration compliance checking
    """

    def __init__(self):
        """Initialize the agent validator."""
        self.logger = get_logger(__name__)

    def validate_agent(self, agent_path: Path) -> Tuple[bool, List[str]]:
        """
        Validate agent configuration and structure.

        Args:
            agent_path: Path to the agent file to validate

        Returns:
            Tuple of (is_valid: bool, errors: List[str])
        """
        errors = []

        try:
            if not agent_path.exists():
                errors.append(f"Agent file does not exist: {agent_path}")
                return False, errors

            # Read agent content
            content = agent_path.read_text()

            # Validate YAML frontmatter
            frontmatter_valid, frontmatter_errors = self._validate_yaml_frontmatter(
                content
            )
            errors.extend(frontmatter_errors)

            # Validate required fields
            required_fields_valid, field_errors = self._validate_required_fields(
                content
            )
            errors.extend(field_errors)

            # Validate agent name format
            name_valid, name_errors = self._validate_agent_name(content)
            errors.extend(name_errors)

            # Validate tools format
            tools_valid, tools_errors = self._validate_tools_format(content)
            errors.extend(tools_errors)

            is_valid = (
                frontmatter_valid
                and required_fields_valid
                and name_valid
                and tools_valid
            )

        except Exception as e:
            errors.append(f"Error validating agent: {e}")
            is_valid = False

        return is_valid, errors

    def validate_and_repair_existing_agents(self, agents_dir: Path) -> Dict[str, Any]:
        """
        Validate and repair broken frontmatter in existing agent files.

        This method scans all agent files in the directory and attempts to repair
        common issues like malformed YAML frontmatter, missing required fields, etc.

        Args:
            agents_dir: Directory containing agent files

        Returns:
            Dictionary with repair results
        """
        results = {"repaired": [], "errors": [], "skipped": [], "total_checked": 0}

        if not agents_dir.exists():
            self.logger.info(f"Agents directory does not exist: {agents_dir}")
            return results

        # Find all agent files (both .md and .yaml)
        agent_files = list(agents_dir.glob("*.md")) + list(agents_dir.glob("*.yaml"))
        results["total_checked"] = len(agent_files)

        for agent_file in agent_files:
            try:
                self.logger.debug(f"Checking agent file: {agent_file.name}")

                # Read current content
                original_content = agent_file.read_text()

                # Attempt to repair the file
                repaired_content, was_repaired, repair_issues = self._repair_agent_file(
                    original_content
                )

                if was_repaired:
                    # Write repaired content back to file
                    agent_file.write_text(repaired_content)

                    repair_info = {
                        "file": agent_file.name,
                        "issues_fixed": repair_issues,
                    }
                    results["repaired"].append(repair_info)
                    self.logger.info(
                        f"Repaired agent file: {agent_file.name} (fixed: {', '.join(repair_issues)})"
                    )
                else:
                    results["skipped"].append(agent_file.name)
                    self.logger.debug(f"No repairs needed for: {agent_file.name}")

            except Exception as e:
                error_msg = f"Failed to repair {agent_file.name}: {e}"
                results["errors"].append(error_msg)
                self.logger.error(error_msg)

        self.logger.info(
            f"Agent validation complete: {len(results['repaired'])} repaired, {len(results['errors'])} errors"
        )
        return results

    def verify_deployment(self, config_dir: Optional[Path] = None) -> Dict[str, Any]:
        """
        Verify agent deployment and Claude configuration.

        Args:
            config_dir: Claude configuration directory (default: .claude/)

        Returns:
            Dictionary with verification results
        """
        if not config_dir:
            config_dir = Path.cwd() / ".claude"

        results = {
            "config_dir": str(config_dir),
            "agents_found": [],
            "agents_needing_migration": [],
            "environment": {},
            "warnings": [],
        }

        # Check if config directory exists
        if not config_dir.exists():
            results["warnings"].append(f"Config directory does not exist: {config_dir}")
            return results

        # Check agents directory
        agents_dir = config_dir / "agents"
        if not agents_dir.exists():
            results["warnings"].append(f"Agents directory does not exist: {agents_dir}")
            return results

        # Scan for agent files
        agent_files = list(agents_dir.glob("*.md")) + list(agents_dir.glob("*.yaml"))

        for agent_file in agent_files:
            try:
                content = agent_file.read_text()

                # Extract basic info from YAML frontmatter
                agent_info = self._extract_agent_info(content, agent_file)

                # Check if agent needs migration (old version format)
                if self._needs_version_migration(content):
                    agent_info["needs_migration"] = True
                    results["agents_needing_migration"].append(agent_info["name"])

                results["agents_found"].append(agent_info)

            except Exception as e:
                self.logger.warning(
                    f"Could not process agent file {agent_file.name}: {e}"
                )

        # Add environment information
        import os

        results["environment"] = {
            key: value for key, value in os.environ.items() if key.startswith("CLAUDE_")
        }

        return results

    def _validate_yaml_frontmatter(self, content: str) -> Tuple[bool, List[str]]:
        """Validate YAML frontmatter structure."""
        errors = []

        # Check if content starts with YAML frontmatter
        if not content.strip().startswith("---"):
            errors.append("Missing YAML frontmatter")
            return False, errors

        # Find the end of frontmatter
        lines = content.split("\n")
        frontmatter_end = -1

        for i, line in enumerate(lines[1:], 1):  # Skip first ---
            if line.strip() == "---":
                frontmatter_end = i
                break

        if frontmatter_end == -1:
            errors.append("YAML frontmatter not properly closed")
            return False, errors

        return True, errors

    def _validate_required_fields(self, content: str) -> Tuple[bool, List[str]]:
        """Validate required fields in agent content."""
        errors = []
        required_fields = ["name", "description", "tools"]

        for field in required_fields:
            field_pattern = rf"^{field}:\s*.+$"
            if not re.search(field_pattern, content, re.MULTILINE):
                errors.append(f"Missing required field: {field}")

        return len(errors) == 0, errors

    def _validate_agent_name(self, content: str) -> Tuple[bool, List[str]]:
        """Validate agent name format."""
        errors = []

        # Extract name from frontmatter
        name_match = re.search(r'^name:\s*["\']?(.+?)["\']?$', content, re.MULTILINE)
        if name_match:
            name = name_match.group(1).strip()

            # Validate Claude Code name requirements
            if not re.match(r"^[a-z0-9]+(-[a-z0-9]+)*$", name):
                errors.append(
                    f"Invalid agent name format: '{name}'. Must match ^[a-z0-9]+(-[a-z0-9]+)*$"
                )

        return len(errors) == 0, errors

    def _validate_tools_format(self, content: str) -> Tuple[bool, List[str]]:
        """Validate tools format."""
        errors = []

        # Extract tools from frontmatter
        tools_match = re.search(r"^tools:\s*(.+)$", content, re.MULTILINE)
        if tools_match:
            tools_str = tools_match.group(1).strip()

            # Check for spaces in comma-separated tools (not allowed)
            if ", " in tools_str:
                errors.append("Tools must be comma-separated WITHOUT spaces")

        return len(errors) == 0, errors

    def _repair_agent_file(self, content: str) -> Tuple[str, bool, List[str]]:
        """
        Attempt to repair common issues in agent file content.

        Returns:
            Tuple of (repaired_content, was_repaired, issues_fixed)
        """
        repaired_content = content
        issues_fixed = []
        was_repaired = False

        # Fix tools format (remove spaces after commas)
        tools_pattern = r"^(tools:\s*)([^,\n]+(?:,\s+[^,\n]+)+)$"
        tools_match = re.search(tools_pattern, repaired_content, re.MULTILINE)
        if tools_match:
            tools_prefix = tools_match.group(1)
            tools_value = tools_match.group(2)

            if ", " in tools_value:
                # Remove spaces after commas
                fixed_tools = tools_value.replace(", ", ",")
                repaired_content = re.sub(
                    tools_pattern,
                    f"{tools_prefix}{fixed_tools}",
                    repaired_content,
                    flags=re.MULTILINE,
                )
                issues_fixed.append("tools_spacing")
                was_repaired = True

        # Add missing required fields with defaults
        if "description:" not in repaired_content:
            # Insert description after name if possible
            name_match = re.search(r"^(name:\s*.+)$", repaired_content, re.MULTILINE)
            if name_match:
                name_line = name_match.group(1)
                repaired_content = repaired_content.replace(
                    name_line,
                    f'{name_line}\ndescription: "Agent for specialized tasks"',
                )
                issues_fixed.append("missing_description")
                was_repaired = True

        return repaired_content, was_repaired, issues_fixed

    def _extract_agent_info(self, content: str, agent_file: Path) -> Dict[str, Any]:
        """Extract basic agent information from content."""
        agent_info = {
            "file": agent_file.name,
            "name": agent_file.stem,
            "path": str(agent_file),
            "description": "No description",
            "version": "unknown",
            "type": "agent",  # Default type
        }

        # Extract ONLY from YAML frontmatter (between --- markers)
        lines = content.split("\n")
        in_frontmatter = False
        frontmatter_ended = False

        for line in lines:
            stripped_line = line.strip()

            # Track frontmatter boundaries
            if stripped_line == "---":
                if not in_frontmatter:
                    in_frontmatter = True
                    continue
                frontmatter_ended = True
                break  # Stop parsing after frontmatter ends

            # Only parse within frontmatter
            if not in_frontmatter or frontmatter_ended:
                continue

            if stripped_line.startswith("name:"):
                agent_info["name"] = stripped_line.split(":", 1)[1].strip().strip("\"'")
            elif stripped_line.startswith("description:"):
                agent_info["description"] = (
                    stripped_line.split(":", 1)[1].strip().strip("\"'")
                )
            elif stripped_line.startswith("version:"):
                agent_info["version"] = (
                    stripped_line.split(":", 1)[1].strip().strip("\"'")
                )
            elif stripped_line.startswith("type:"):
                agent_info["type"] = stripped_line.split(":", 1)[1].strip().strip("\"'")

        return agent_info

    def _needs_version_migration(self, content: str) -> bool:
        """Check if agent needs version migration."""
        version_match = re.search(
            r'^version:\s*["\']?(.+?)["\']?$', content, re.MULTILINE
        )
        if version_match:
            version_str = version_match.group(1)
            # Check for old format (contains hyphen and all digits)
            return bool(re.match(r"^\d+-\d+$", version_str))
        return False

"""Agent Version Manager Service

This service handles all version-related operations for agent deployment,
including version parsing, comparison, migration detection, and format conversion.

Extracted from AgentDeploymentService as part of the refactoring to improve
maintainability and testability.
"""

import re
from pathlib import Path
from typing import Any, Tuple

from claude_mpm.core.logging_config import get_logger


class AgentVersionManager:
    """Service for managing agent versions and migrations.

    This service handles:
    - Version parsing from various formats (integer, semantic, legacy)
    - Version comparison for update decisions
    - Migration detection from old to new formats
    - Version format validation and conversion
    """

    def __init__(self):
        """Initialize the version manager."""
        self.logger = get_logger(__name__)

    def parse_version(self, version_value: Any) -> Tuple[int, int, int]:
        """
        Parse version from various formats to semantic version tuple.

        Handles:
        - Integer values: 5 -> (0, 5, 0)
        - String integers: "5" -> (0, 5, 0)
        - Semantic versions: "2.1.0" -> (2, 1, 0)
        - Invalid formats: returns (0, 0, 0)

        Args:
            version_value: Version in various formats

        Returns:
            Tuple of (major, minor, patch) for comparison
        """
        if isinstance(version_value, int):
            # Legacy integer version - treat as minor version
            return (0, version_value, 0)

        if isinstance(version_value, str):
            # Try to parse as simple integer
            if version_value.isdigit():
                return (0, int(version_value), 0)

            # Try to parse semantic version (e.g., "2.1.0" or "v2.1.0")
            sem_ver_match = re.match(r"^v?(\d+)\.(\d+)\.(\d+)", version_value)
            if sem_ver_match:
                major = int(sem_ver_match.group(1))
                minor = int(sem_ver_match.group(2))
                patch = int(sem_ver_match.group(3))
                return (major, minor, patch)

            # Try to extract first number from string as minor version
            num_match = re.search(r"(\d+)", version_value)
            if num_match:
                return (0, int(num_match.group(1)), 0)

        # Default to 0.0.0 for invalid formats
        return (0, 0, 0)

    def format_version_display(self, version_tuple: Tuple[int, int, int]) -> str:
        """
        Format version tuple for display.

        Args:
            version_tuple: Tuple of (major, minor, patch)

        Returns:
            Formatted version string
        """
        if isinstance(version_tuple, tuple) and len(version_tuple) == 3:
            major, minor, patch = version_tuple
            return f"{major}.{minor}.{patch}"
        # Fallback for legacy format
        return str(version_tuple)

    def is_old_version_format(self, version_str: str) -> bool:
        """
        Check if a version string is in the old serial format.

        Old formats include:
        - Serial format: "0002-0005" (contains hyphen, all digits)
        - Missing version field
        - Non-semantic version formats

        Args:
            version_str: Version string to check

        Returns:
            True if old format, False if semantic version
        """
        if not version_str:
            return True

        # Check for serial format (e.g., "0002-0005")
        if re.match(r"^\d+-\d+$", version_str):
            return True

        # Check for semantic version format (e.g., "2.1.0")
        if re.match(r"^v?\d+\.\d+\.\d+$", version_str):
            return False

        # Any other format is considered old
        return True

    def compare_versions(
        self, v1: Tuple[int, int, int], v2: Tuple[int, int, int]
    ) -> int:
        """
        Compare two version tuples.

        Args:
            v1: First version tuple
            v2: Second version tuple

        Returns:
            -1 if v1 < v2, 0 if equal, 1 if v1 > v2
        """
        for a, b in zip(v1, v2):
            if a < b:
                return -1
            if a > b:
                return 1
        return 0

    def extract_version_from_content(self, content: str, version_marker: str) -> int:
        """
        Extract version number from content using a marker.

        Args:
            content: File content
            version_marker: Version marker to look for (e.g., "AGENT_VERSION:" or "BASE_AGENT_VERSION:")

        Returns:
            Version number or 0 if not found
        """
        pattern = rf"<!-- {version_marker} (\d+) -->"
        match = re.search(pattern, content)
        if match:
            return int(match.group(1))
        return 0

    def extract_version_from_frontmatter(
        self, content: str
    ) -> Tuple[Tuple[int, int, int], bool, str]:
        """
        Extract version information from YAML frontmatter.

        Args:
            content: File content with YAML frontmatter

        Returns:
            Tuple of (version_tuple, is_old_format, version_string)
        """
        is_old_format = False
        version_string = None

        # Try legacy combined format (e.g., "0002-0005")
        legacy_match = re.search(
            r'^version:\s*["\']?(\d+)-(\d+)["\']?', content, re.MULTILINE
        )
        if legacy_match:
            is_old_format = True
            version_string = f"{legacy_match.group(1)}-{legacy_match.group(2)}"
            # Convert legacy format to semantic version
            # Treat the agent version (second number) as minor version
            version_tuple = (0, int(legacy_match.group(2)), 0)
            self.logger.info(f"Detected old serial version format: {version_string}")
            return version_tuple, is_old_format, version_string

        # Try to extract semantic version format (e.g., "2.1.0")
        version_match = re.search(
            r'^version:\s*["\']?v?(\d+)\.(\d+)\.(\d+)["\']?', content, re.MULTILINE
        )
        if version_match:
            version_tuple = (
                int(version_match.group(1)),
                int(version_match.group(2)),
                int(version_match.group(3)),
            )
            version_string = f"{version_match.group(1)}.{version_match.group(2)}.{version_match.group(3)}"
            return version_tuple, is_old_format, version_string

        # Fallback: try separate fields (very old format)
        agent_version_match = re.search(
            r"^agent_version:\s*(\d+)", content, re.MULTILINE
        )
        if agent_version_match:
            is_old_format = True
            version_string = f"agent_version: {agent_version_match.group(1)}"
            version_tuple = (0, int(agent_version_match.group(1)), 0)
            self.logger.info(f"Detected old separate version format: {version_string}")
            return version_tuple, is_old_format, version_string

        # Check for missing version field
        if "version:" not in content:
            is_old_format = True
            version_string = "missing"
            version_tuple = (0, 0, 0)
            self.logger.info("Detected missing version field")
            return version_tuple, is_old_format, version_string

        # Default case
        return (0, 0, 0), False, "0.0.0"

    def check_agent_needs_update(
        self,
        deployed_file: Path,
        template_file: Path,
        current_base_version: Tuple[int, int, int],
    ) -> Tuple[bool, str]:
        """
        Check if a deployed agent needs to be updated.

        Args:
            deployed_file: Path to the deployed agent file
            template_file: Path to the template file
            current_base_version: Current base agent version (for compatibility)

        Returns:
            Tuple of (needs_update: bool, reason: str)
        """
        try:
            # Read deployed agent content
            deployed_content = deployed_file.read_text()

            # Skip non-system agents (user-created)
            # Check for various author formats used by system agents
            if not any(
                author in deployed_content.lower()
                for author in [
                    "author: claude-mpm",
                    "author: claude mpm team",
                    "author: claude mpm",
                ]
            ):
                return (False, "not a system agent")

            # Extract version info from YAML frontmatter
            (
                deployed_version,
                is_old_format,
                old_version_str,
            ) = self.extract_version_from_frontmatter(deployed_content)

            # Read template to get current agent version
            import json

            template_data = json.loads(template_file.read_text())

            # Extract agent version from template
            metadata = template_data.get("metadata", {})
            current_agent_version = self.parse_version(
                template_data.get("agent_version")
                or template_data.get("version")
                or metadata.get("version", 0)
            )

            # If old format detected, always trigger update for migration
            if is_old_format:
                new_version_str = self.format_version_display(current_agent_version)
                return (
                    True,
                    f"migration needed from old format ({old_version_str}) to semantic version ({new_version_str})",
                )

            # Check if agent template version is newer
            if self.compare_versions(current_agent_version, deployed_version) > 0:
                deployed_str = self.format_version_display(deployed_version)
                current_str = self.format_version_display(current_agent_version)
                return (
                    True,
                    f"agent template updated ({deployed_str} -> {current_str})",
                )

            return (False, "up to date")

        except Exception as e:
            self.logger.warning(f"Error checking agent update status: {e}")
            # On error, assume update is needed
            return (True, "version check failed")

    def validate_version_in_content(self, content: str) -> Tuple[bool, list]:
        """
        Validate version information in agent content.

        Args:
            content: Agent file content

        Returns:
            Tuple of (is_valid: bool, errors: list)
        """
        errors = []

        # Check for YAML frontmatter
        if not content.strip().startswith("---"):
            errors.append("Missing YAML frontmatter")
            return False, errors

        # Extract and validate version
        version_match = re.search(
            r'^version:\s*["\']?(.+?)["\']?$', content, re.MULTILINE
        )
        if not version_match:
            errors.append("Missing version field in frontmatter")
        else:
            version_str = version_match.group(1)
            if self.is_old_version_format(version_str):
                errors.append(f"Old version format detected: {version_str}")

        return len(errors) == 0, errors

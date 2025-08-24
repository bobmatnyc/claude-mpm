from pathlib import Path

"""
Deployment management for framework CLAUDE.md templates.

Handles deployment operations to parent directories.
"""

from datetime import datetime, timezone
from typing import Optional, Tuple

# Import framework detection utilities
from ...utils.framework_detection import is_framework_source_directory
from .content_validator import ContentValidator
from .version_manager import VersionManager


class DeploymentManager:
    """Manages deployment of framework CLAUDE.md to parent directories."""

    def __init__(
        self,
        version_manager: VersionManager,
        validator: ContentValidator,
        target_filename: str = "INSTRUCTIONS.md",
    ):
        """
        Initialize deployment manager.

        Args:
            version_manager: Version management instance
            validator: Content validator instance
            target_filename: Target filename for deployment (default: "INSTRUCTIONS.md")
                           Can be set to "CLAUDE.md" for legacy compatibility
        """
        self.version_manager = version_manager
        self.validator = validator
        self.target_filename = target_filename

    def deploy_to_parent(
        self, content: str, parent_path: Path, force: bool = False
    ) -> Tuple[bool, str]:
        """
        Deploy generated content to a parent directory.

        WHY: Enhanced to ensure fresh agent capabilities generation on each deployment.
        - Checks for template variables that need processing
        - Re-processes content to get current deployed agents
        - Ensures INSTRUCTIONS.md always reflects latest agent configuration

        Args:
            content: Content to deploy
            parent_path: Path to parent directory
            force: Force deployment even if versions match

        Returns:
            Tuple of (success, message)
        """
        # Check if we're in the framework source directory
        is_framework, markers = is_framework_source_directory(parent_path)
        if is_framework:
            return (
                True,
                f"Skipping deployment - detected framework source directory (markers: {', '.join(markers)})",
            )

        # Use configured target filename
        target_file = parent_path / self.target_filename

        # Check if content contains template variables that need processing
        if "{{capabilities-list}}" in content:
            # Content needs processing - let ContentAssembler handle it
            from .content_assembler import ContentAssembler

            assembler = ContentAssembler()

            # Re-process content to get fresh agent data
            # Pass content as a single section to preserve structure
            processed_content = assembler.apply_template_variables(content)
            content = processed_content

        # Validate content before deployment
        # Skip validation for INSTRUCTIONS.md format (different from CLAUDE.md)
        if (
            "<!-- FRAMEWORK_VERSION:" in content
            and "# Claude Multi-Agent Project Manager Instructions" in content
        ):
            # This is INSTRUCTIONS.md format, skip CLAUDE.md validation
            pass
        else:
            # This is CLAUDE.md format, validate normally
            is_valid, issues = self.validator.validate_content(content)
            if not is_valid:
                return False, f"Validation failed: {'; '.join(issues)}"

        # Check if file exists and compare versions
        if target_file.exists() and not force:
            with open(target_file) as f:
                existing_content = f.read()
                existing_fw_ver = self.version_manager.parse_current_version(
                    existing_content
                )

            if existing_fw_ver == self.version_manager.framework_version:
                return True, f"Version {existing_fw_ver} already deployed"

        # Deploy
        try:
            # Ensure parent directory exists
            parent_path.mkdir(parents=True, exist_ok=True)

            # Write content
            with open(target_file, "w") as f:
                f.write(content)

            # Get version info for success message
            fw_ver = self.version_manager.parse_current_version(content)
            version_str = fw_ver

            return True, f"Successfully deployed version {version_str}"
        except Exception as e:
            return False, f"Deployment failed: {e!s}"

    def check_deployment_needed(self, parent_path: Path) -> Tuple[bool, str]:
        """
        Check if deployment is needed for a parent directory.

        Args:
            parent_path: Path to parent directory

        Returns:
            Tuple of (needed, reason)
        """
        target_file = parent_path / self.target_filename

        if not target_file.exists():
            return True, f"{self.target_filename} does not exist"

        try:
            with open(target_file) as f:
                existing_content = f.read()
                existing_fw_ver = self.version_manager.parse_current_version(
                    existing_content
                )

            if existing_fw_ver != self.version_manager.framework_version:
                return (
                    True,
                    f"Version mismatch: {existing_fw_ver} vs {self.version_manager.framework_version}",
                )

            return False, "Already up to date"
        except Exception as e:
            return True, f"Error checking existing file: {e!s}"

    def backup_existing(self, parent_path: Path) -> Optional[Path]:
        """
        Create a backup of existing target file before deployment.

        Args:
            parent_path: Path to parent directory

        Returns:
            Path to backup file if created, None otherwise
        """
        target_file = parent_path / self.target_filename

        if not target_file.exists():
            return None

        # Create backup filename with timestamp
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        backup_file = parent_path / f"{self.target_filename}.backup.{timestamp}"

        try:
            import shutil

            shutil.copy2(target_file, backup_file)
            return backup_file
        except Exception:
            return None

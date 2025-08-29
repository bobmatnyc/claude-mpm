"""Service for deploying MPM slash commands to user's Claude configuration.

This service handles:
1. Copying command markdown files from source to user's ~/.claude/commands directory
2. Creating the commands directory if it doesn't exist
3. Overwriting existing commands to ensure they're up-to-date
"""

import shutil
from pathlib import Path
from typing import Any, Dict, List

from claude_mpm.core.base_service import BaseService
from claude_mpm.core.logger import get_logger


class CommandDeploymentService(BaseService):
    """Service for deploying MPM slash commands."""

    def __init__(self):
        """Initialize the command deployment service."""
        super().__init__(name="command_deployment")

        # Source commands directory in the package - use proper resource resolution
        try:
            from ..core.unified_paths import get_package_resource_path

            self.source_dir = get_package_resource_path("commands")
        except FileNotFoundError:
            # Fallback to old method for development environments
            self.source_dir = Path(__file__).parent.parent / "commands"

        # Target directory in user's home
        self.target_dir = Path.home() / ".claude" / "commands"

    async def _initialize(self) -> None:
        """Initialize the service."""

    async def _cleanup(self) -> None:
        """Cleanup service resources."""

    def deploy_commands(self, force: bool = False) -> Dict[str, Any]:
        """Deploy MPM slash commands to user's Claude configuration.

        Args:
            force: Force deployment even if files exist

        Returns:
            Dictionary with deployment results
        """
        result = {
            "success": False,
            "deployed": [],
            "errors": [],
            "target_dir": str(self.target_dir),
        }

        try:
            # Check if source directory exists
            if not self.source_dir.exists():
                self.logger.warning(
                    f"Source commands directory not found: {self.source_dir}"
                )
                result["errors"].append(
                    f"Source directory not found: {self.source_dir}"
                )
                return result

            # Create target directory if it doesn't exist
            self.target_dir.mkdir(parents=True, exist_ok=True)
            self.logger.debug(f"Ensured target directory exists: {self.target_dir}")

            # Get all .md files from source directory
            command_files = list(self.source_dir.glob("*.md"))

            if not command_files:
                self.logger.info("No command files found to deploy")
                result["success"] = True
                return result

            # Deploy each command file
            for source_file in command_files:
                target_file = self.target_dir / source_file.name

                try:
                    # Check if file exists and if we should overwrite
                    if target_file.exists() and not force:
                        # Check if source is newer
                        if source_file.stat().st_mtime <= target_file.stat().st_mtime:
                            self.logger.debug(
                                f"Skipping {source_file.name} - target is up to date"
                            )
                            continue

                    # Copy the file
                    shutil.copy2(source_file, target_file)
                    self.logger.info(f"Deployed command: {source_file.name}")
                    result["deployed"].append(source_file.name)

                except Exception as e:
                    error_msg = f"Failed to deploy {source_file.name}: {e}"
                    self.logger.error(error_msg)
                    result["errors"].append(error_msg)

            result["success"] = len(result["errors"]) == 0

            if result["deployed"]:
                self.logger.info(
                    f"Successfully deployed {len(result['deployed'])} commands to {self.target_dir}"
                )

            return result

        except Exception as e:
            error_msg = f"Command deployment failed: {e}"
            self.logger.error(error_msg)
            result["errors"].append(error_msg)
            return result

    def list_available_commands(self) -> List[str]:
        """List available commands in the source directory.

        Returns:
            List of command file names
        """
        if not self.source_dir.exists():
            return []

        return [f.name for f in self.source_dir.glob("*.md")]

    def list_deployed_commands(self) -> List[str]:
        """List deployed commands in the target directory.

        Returns:
            List of deployed command file names
        """
        if not self.target_dir.exists():
            return []

        return [f.name for f in self.target_dir.glob("mpm*.md")]

    def remove_deployed_commands(self) -> int:
        """Remove all deployed MPM commands from target directory.

        Returns:
            Number of files removed
        """
        if not self.target_dir.exists():
            return 0

        removed = 0
        for file in self.target_dir.glob("mpm*.md"):
            try:
                file.unlink()
                self.logger.info(f"Removed command: {file.name}")
                removed += 1
            except Exception as e:
                self.logger.error(f"Failed to remove {file.name}: {e}")

        return removed


def deploy_commands_on_startup(force: bool = False) -> None:
    """Convenience function to deploy commands during startup.

    Args:
        force: Force deployment even if files exist
    """
    service = CommandDeploymentService()
    result = service.deploy_commands(force=force)

    if result["deployed"]:
        logger = get_logger("startup")
        logger.info(f"MPM commands deployed: {', '.join(result['deployed'])}")

    if result["errors"]:
        logger = get_logger("startup")
        for error in result["errors"]:
            logger.warning(f"Command deployment issue: {error}")

"""Service for deploying MPM slash commands to user's Claude configuration.

This service handles:
1. Copying command markdown files from source to user's ~/.claude/commands directory
2. Creating the commands directory if it doesn't exist
3. Overwriting existing commands to ensure they're up-to-date
4. Parsing and validating YAML frontmatter for namespace metadata (Phase 1 - 1M-400)
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

from claude_mpm.core.base_service import BaseService
from claude_mpm.core.logger import get_logger


class CommandDeploymentService(BaseService):
    """Service for deploying MPM slash commands."""

    # Deprecated commands that have been replaced (cleanup on startup)
    DEPRECATED_COMMANDS = [
        "mpm-agents.md",  # Replaced by mpm-agents-list.md
        "mpm-auto-configure.md",  # Replaced by mpm-agents-auto-configure.md
        "mpm-config-view.md",  # Replaced by mpm-config.md
        "mpm-resume.md",  # Replaced by mpm-session-resume.md
        "mpm-ticket.md",  # Replaced by mpm-ticket-view.md
        # Removed - consolidated into /mpm-configure
        "mpm-agents-list.md",  # Consolidated into /mpm-configure
        "mpm-agents-detect.md",  # Consolidated into /mpm-configure
        "mpm-agents-auto-configure.md",  # Consolidated into /mpm-configure
        "mpm-agents-recommend.md",  # Consolidated into /mpm-configure
    ]

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

    def _parse_frontmatter(self, content: str) -> Tuple[Optional[Dict[str, Any]], str]:
        """Parse YAML frontmatter from command file.

        Ticket: 1M-400 Phase 1 - Enhanced Flat Naming with Namespace Metadata

        Args:
            content: Command file content

        Returns:
            Tuple of (frontmatter_dict, content_without_frontmatter)
            If no frontmatter found, returns (None, original_content)
        """
        if not content.startswith("---\n"):
            return None, content

        try:
            # Split on closing ---
            parts = content.split("\n---\n", 1)
            if len(parts) != 2:
                return None, content

            frontmatter_str = parts[0].replace("---\n", "", 1)
            body = parts[1]

            frontmatter = yaml.safe_load(frontmatter_str)
            return frontmatter, body
        except yaml.YAMLError as e:
            self.logger.warning(f"YAML parsing error: {e}")
            return None, content

    def _validate_frontmatter(
        self, frontmatter: Dict[str, Any], filepath: Path
    ) -> List[str]:
        """Validate frontmatter schema.

        Ticket: 1M-400 Phase 1 - Enhanced Flat Naming with Namespace Metadata

        Args:
            frontmatter: Parsed frontmatter dictionary
            filepath: Path to command file (for error reporting)

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        required_fields = ["namespace", "command", "category", "description"]

        for field in required_fields:
            if field not in frontmatter:
                errors.append(f"Missing required field: {field}")

        # Validate category
        valid_categories = ["agents", "config", "tickets", "session", "system"]
        if (
            "category" in frontmatter
            and frontmatter["category"] not in valid_categories
        ):
            errors.append(
                f"Invalid category: {frontmatter['category']} "
                f"(must be one of {valid_categories})"
            )

        # Validate data types
        if "aliases" in frontmatter and not isinstance(frontmatter["aliases"], list):
            errors.append("Field 'aliases' must be a list")

        if "deprecated_aliases" in frontmatter and not isinstance(
            frontmatter["deprecated_aliases"], list
        ):
            errors.append("Field 'deprecated_aliases' must be a list")

        return errors

    def _strip_deprecated_aliases(self, content: str) -> str:
        """Strip deprecated_aliases from frontmatter to hide them from Claude Code UI.

        This prevents deprecated aliases from appearing in the command list while
        maintaining backward compatibility through command routing.

        Args:
            content: Command file content with frontmatter

        Returns:
            Content with deprecated_aliases removed from frontmatter
        """
        frontmatter, body = self._parse_frontmatter(content)

        if not frontmatter or "deprecated_aliases" not in frontmatter:
            return content

        # Remove deprecated_aliases from frontmatter
        frontmatter_copy = frontmatter.copy()
        del frontmatter_copy["deprecated_aliases"]

        # Reconstruct the file with modified frontmatter
        frontmatter_yaml = yaml.dump(
            frontmatter_copy, default_flow_style=False, sort_keys=False
        )
        return f"---\n{frontmatter_yaml}---\n{body}"

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
                    # Validate frontmatter if present (1M-400 Phase 1)
                    content = source_file.read_text()
                    frontmatter, _ = self._parse_frontmatter(content)

                    if frontmatter:
                        validation_errors = self._validate_frontmatter(
                            frontmatter, source_file
                        )
                        if validation_errors:
                            self.logger.warning(
                                f"Frontmatter validation issues in {source_file.name}: "
                                f"{'; '.join(validation_errors)}"
                            )
                            # Continue deployment but log warnings

                    # Check if file exists and if we should overwrite
                    if (
                        target_file.exists()
                        and not force
                        and source_file.stat().st_mtime <= target_file.stat().st_mtime
                    ):
                        self.logger.debug(
                            f"Skipping {source_file.name} - target is up to date"
                        )
                        continue

                    # Strip deprecated_aliases from content before deployment
                    # This prevents them from appearing in Claude Code's command list UI
                    cleaned_content = self._strip_deprecated_aliases(content)

                    # Write the cleaned content to target
                    target_file.write_text(cleaned_content)
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

    def remove_deprecated_commands(self) -> int:
        """Remove deprecated MPM commands that have been replaced.

        This method cleans up old command files that have been superseded by
        new hierarchical command names. It's called automatically on startup
        to ensure users don't have both old and new versions.

        Returns:
            Number of deprecated files removed
        """
        if not self.target_dir.exists():
            self.logger.debug(
                f"Target directory does not exist: {self.target_dir}, skipping deprecated command cleanup"
            )
            return 0

        removed = 0
        self.logger.info("Cleaning up deprecated commands...")

        # Mapping of deprecated commands to their replacements for informative logging
        replacement_map = {
            "mpm-agents.md": "mpm-agents-list.md",
            "mpm-auto-configure.md": "mpm-agents-auto-configure.md",
            "mpm-config-view.md": "mpm-config.md",
            "mpm-resume.md": "mpm-session-resume.md",
            "mpm-ticket.md": "mpm-ticket-view.md",
            # Removed commands - consolidated into /mpm-configure
            "mpm-agents-list.md": "mpm-configure (use /mpm-configure)",
            "mpm-agents-detect.md": "mpm-configure (use /mpm-configure)",
            "mpm-agents-auto-configure.md": "mpm-configure (use /mpm-configure)",
            "mpm-agents-recommend.md": "mpm-configure (use /mpm-configure)",
        }

        for deprecated_cmd in self.DEPRECATED_COMMANDS:
            deprecated_file = self.target_dir / deprecated_cmd
            replacement = replacement_map.get(deprecated_cmd, "a newer command")

            if deprecated_file.exists():
                try:
                    deprecated_file.unlink()
                    self.logger.debug(
                        f"Removed deprecated command: {deprecated_cmd} (replaced by {replacement})"
                    )
                    removed += 1
                except Exception as e:
                    # Log error but don't fail startup - this is non-critical
                    self.logger.warning(
                        f"Failed to remove deprecated command {deprecated_cmd}: {e}"
                    )

        if removed > 0:
            self.logger.info(f"Removed {removed} deprecated command(s)")
        else:
            self.logger.debug("No deprecated commands found to remove")

        return removed

    def remove_stale_commands(self) -> int:
        """Remove stale MPM commands that no longer exist in source.

        This method cleans up deployed commands that have been deleted or renamed
        in the source directory. It's called automatically on startup to ensure
        deployed commands stay in sync with source.

        Returns:
            Number of stale files removed
        """
        if not self.target_dir.exists():
            self.logger.debug(
                f"Target directory does not exist: {self.target_dir}, skipping stale command cleanup"
            )
            return 0

        if not self.source_dir.exists():
            self.logger.warning(
                f"Source directory does not exist: {self.source_dir}, cannot detect stale commands"
            )
            return 0

        # Get current source commands (ground truth)
        source_commands = {f.name for f in self.source_dir.glob("mpm*.md")}

        # Get deployed commands
        deployed_commands = {f.name for f in self.target_dir.glob("mpm*.md")}

        # Find stale commands (deployed but not in source, excluding deprecated)
        stale_commands = (
            deployed_commands - source_commands - set(self.DEPRECATED_COMMANDS)
        )

        if not stale_commands:
            self.logger.debug("No stale commands found to remove")
            return 0

        removed = 0
        self.logger.info(f"Cleaning up {len(stale_commands)} stale command(s)...")

        for stale_cmd in stale_commands:
            stale_file = self.target_dir / stale_cmd
            try:
                stale_file.unlink()
                self.logger.info(
                    f"Removed stale command: {stale_cmd} (no longer in source)"
                )
                removed += 1
            except Exception as e:
                # Log error but don't fail startup - this is non-critical
                self.logger.warning(f"Failed to remove stale command {stale_cmd}: {e}")

        if removed > 0:
            self.logger.info(f"Removed {removed} stale command(s)")

        return removed


def deploy_commands_on_startup(force: bool = False) -> None:
    """Convenience function to deploy commands during startup.

    This function:
    1. Removes deprecated commands that have been replaced
    2. Removes stale commands that no longer exist in source
    3. Deploys current command files

    Args:
        force: Force deployment even if files exist
    """
    service = CommandDeploymentService()
    logger = get_logger("startup")

    # Clean up deprecated commands FIRST (known old commands)
    deprecated_count = service.remove_deprecated_commands()
    if deprecated_count > 0:
        logger.info(f"Cleaned up {deprecated_count} deprecated command(s)")

    # Clean up stale commands SECOND (deployed but not in source anymore)
    stale_count = service.remove_stale_commands()
    if stale_count > 0:
        logger.info(f"Cleaned up {stale_count} stale command(s)")

    # Deploy current commands LAST
    result = service.deploy_commands(force=force)

    if result["deployed"]:
        logger.info(f"MPM commands deployed: {', '.join(result['deployed'])}")

    if result["errors"]:
        for error in result["errors"]:
            logger.warning(f"Command deployment issue: {error}")

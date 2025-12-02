"""
Upgrade command implementation for claude-mpm.

WHY: This module provides a manual upgrade command that allows users to check
for and install the latest version of claude-mpm without waiting for the
automatic startup check.

DESIGN DECISIONS:
- Use BaseCommand for consistent CLI patterns
- Leverage SelfUpgradeService for upgrade functionality
- Support multiple installation methods (pip, pipx, npm)
- Skip editable/development installations (must upgrade manually)
- Provide clear feedback on available updates and upgrade progress
"""

import asyncio

from ..shared import BaseCommand, CommandResult


class UpgradeCommand(BaseCommand):
    """Upgrade command using shared utilities."""

    def __init__(self):
        super().__init__("upgrade")

    def validate_args(self, args) -> str:
        """Validate command arguments."""
        # Upgrade command doesn't require specific validation
        return None

    def run(self, args) -> CommandResult:
        """Execute the upgrade command."""
        try:
            from ...services.self_upgrade_service import (
                InstallationMethod,
                SelfUpgradeService,
            )

            # Create upgrade service
            upgrade_service = SelfUpgradeService()

            # Check installation method
            if upgrade_service.installation_method == InstallationMethod.EDITABLE:
                self.logger.info(
                    "Editable installation detected - upgrade must be done manually"
                )
                print("\n⚠️  Editable Installation Detected")
                print(
                    "\nYou are running claude-mpm from an editable installation (development mode)."
                )
                print("To upgrade, run:")
                print("  cd /path/to/claude-mpm")
                print("  git pull")
                print("  pip install -e .")
                return CommandResult.success_result(
                    "Upgrade information provided for editable installation"
                )

            # Check for updates
            print("\n🔍 Checking for updates...")
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                update_info = loop.run_until_complete(
                    upgrade_service.check_for_update()
                )
            finally:
                loop.close()

            if not update_info or not update_info.get("update_available"):
                print(
                    f"\n✅ You are already on the latest version (v{upgrade_service.current_version})"
                )
                return CommandResult.success_result("Already on latest version")

            # Display update information
            current = update_info["current"]
            latest = update_info["latest"]
            method = update_info.get("installation_method", "unknown")

            print("\n🎉 New version available!")
            print(f"   Current: v{current}")
            print(f"   Latest:  v{latest}")
            print(f"   Installation method: {method}")

            # Check if --yes flag is set for non-interactive upgrade
            force_upgrade = getattr(args, "yes", False) or getattr(args, "force", False)

            if not force_upgrade:
                # Prompt user for confirmation
                if not upgrade_service.prompt_for_upgrade(update_info):
                    print("\n⏸️  Upgrade cancelled by user")
                    return CommandResult.success_result("Upgrade cancelled by user")

            # Perform upgrade
            success, message = upgrade_service.perform_upgrade(update_info)
            print(f"\n{message}")

            if success:
                # Restart after successful upgrade
                upgrade_service.restart_after_upgrade()
                # Note: This line won't be reached as restart replaces process
                return CommandResult.success_result(f"Upgraded to v{latest}")
            return CommandResult.error_result("Upgrade failed")

        except Exception as e:
            self.logger.error(f"Error during upgrade: {e}", exc_info=True)
            return CommandResult.error_result(f"Error during upgrade: {e}")


def add_upgrade_parser(subparsers):
    """
    Add upgrade command parser.

    WHY: This command helps users check for and install the latest version of
    claude-mpm without waiting for the automatic startup check.

    Args:
        subparsers: The subparser action object to add the upgrade command to
    """
    parser = subparsers.add_parser(
        "upgrade",
        help="Check for and install latest claude-mpm version",
        description="Check for updates and upgrade claude-mpm to the latest version from PyPI/npm",
    )

    parser.add_argument(
        "-y",
        "--yes",
        action="store_true",
        help="Skip confirmation prompt and upgrade immediately if available",
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help="Force upgrade even if already on latest version (alias for --yes)",
    )

    return parser


def upgrade(args):
    """
    Main entry point for upgrade command.

    This function maintains backward compatibility while using the new BaseCommand pattern.
    """
    command = UpgradeCommand()
    result = command.execute(args)
    return result.exit_code

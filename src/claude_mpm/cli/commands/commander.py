"""Commander command handler for CLI."""

import asyncio
import logging

logger = logging.getLogger(__name__)


def handle_commander_command(args) -> int:
    """Handle the commander command.

    Args:
        args: Parsed command line arguments with:
            - port: Port for internal services (default: 8765)
            - state_dir: Optional state directory path
            - debug: Enable debug logging

    Returns:
        Exit code (0 for success, 1 for error)
    """
    try:
        # Import here to avoid circular dependencies
        from claude_mpm.commander.chat.cli import run_commander

        # Setup debug logging if requested
        if getattr(args, "debug", False):
            logging.basicConfig(
                level=logging.DEBUG,
                format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            )

        # Get arguments
        port = getattr(args, "port", 8765)
        state_dir = getattr(args, "state_dir", None)

        # Run commander
        asyncio.run(run_commander(port=port, state_dir=state_dir))

        return 0

    except KeyboardInterrupt:
        logger.info("Commander interrupted by user")
        return 0
    except Exception as e:
        logger.error(f"Commander error: {e}", exc_info=True)
        return 1

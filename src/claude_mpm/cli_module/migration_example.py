"""Example migration showing how to refactor main() using registries.

This file demonstrates how to reduce the complexity of the main() function
from 16 to under 10 by using ArgumentRegistry and CommandRegistry.
"""

import argparse
import sys
from typing import Optional

from claude_mpm._version import __version__
from claude_mpm.cli import ArgumentRegistry, CommandRegistry, register_standard_commands
from claude_mpm.core.logger import get_logger, setup_logging
from claude_mpm.services.hook_service_manager import HookServiceManager


def main_refactored(argv: Optional[list] = None):
    """Refactored main CLI entry point with reduced complexity.

    This version uses registries to manage arguments and commands,
    reducing cyclomatic complexity from 16 to approximately 8.
    """
    # Initialize registries
    arg_registry = ArgumentRegistry()
    cmd_registry = CommandRegistry(arg_registry)

    # Register standard commands
    register_standard_commands(cmd_registry)

    # Create parser with basic info
    parser = argparse.ArgumentParser(
        prog="claude-mpm",
        description=f"Claude Multi-Agent Project Manager v{__version__} - Orchestrate Claude with agent delegation and ticket tracking",
        epilog="By default, runs an orchestrated Claude session. Use 'claude-mpm' for interactive mode or 'claude-mpm -i \"prompt\"' for non-interactive mode.",
    )

    # Store version for ArgumentRegistry
    parser._version = f"claude-mpm {__version__}"

    # Apply global arguments
    arg_registry.apply_arguments(parser, groups=["global"])

    # Apply run arguments at top level (for default behavior)
    arg_registry.apply_arguments(parser, groups=["run"], exclude=["no_hooks"])

    # Set up subcommands
    cmd_registry.setup_subcommands(parser)

    # Parse arguments
    args = parser.parse_args(argv)

    # Set up logging
    _setup_logging(args)

    # Initialize hook service
    hook_manager = _initialize_hook_service(args)

    try:
        # Execute command
        result = cmd_registry.execute_command(args, hook_manager=hook_manager)
        if result is None and not args.command:
            parser.print_help()
            return 1
        return result or 0

    except KeyboardInterrupt:
        get_logger("cli").info("Session interrupted by user")
        return 0
    except Exception as e:
        logger = get_logger("cli")
        logger.error(f"Error: {e}")
        if args.debug:
            import traceback

            traceback.print_exc()
        return 1
    finally:
        # Clean up hook service
        if hook_manager:
            hook_manager.stop_service()


def _setup_logging(args):
    """Set up logging based on arguments (extracted helper)."""
    # Handle deprecated --debug flag
    if args.debug and args.logging == "OFF":
        args.logging = "DEBUG"

    # Only setup logging if not OFF
    if args.logging != "OFF":
        setup_logging(level=args.logging, log_dir=args.log_dir)
    else:
        # Minimal logger for CLI feedback
        import logging

        logger = logging.getLogger("cli")
        logger.setLevel(logging.WARNING)


def _initialize_hook_service(args):
    """Initialize hook service if enabled (extracted helper)."""
    if getattr(args, "no_hooks", False):
        return None

    try:
        # Check if hooks are enabled via config
        from claude_mpm.config.hook_config import HookConfig

        if not HookConfig.is_hooks_enabled():
            get_logger("cli").info("Hooks disabled via configuration")
            return None

        hook_manager = HookServiceManager(log_dir=args.log_dir)
        if hook_manager.start_service():
            logger = get_logger("cli")
            logger.info(f"Hook service started on port {hook_manager.port}")
            print(f"Hook service started on port {hook_manager.port}")
            return hook_manager
        logger = get_logger("cli")
        logger.warning("Failed to start hook service, continuing without hooks")
        print("Failed to start hook service, continuing without hooks")
        return None

    except Exception as e:
        get_logger("cli").warning(
            f"Hook service initialization failed: {e}, continuing without hooks"
        )
        return None


# Example of how to add custom commands
def extend_with_custom_commands(cmd_registry: CommandRegistry):
    """Example of adding custom commands to the registry."""

    def validate_command(args, **kwargs):
        """Custom validation command."""
        print("Running validation...")
        # Implementation here
        return 0

    # Register custom command
    cmd_registry.register(
        name="validate",
        help_text="Validate project configuration and agent setup",
        handler=validate_command,
        argument_groups=["framework"],
        extra_args={
            "strict": {
                "flags": ["--strict"],
                "action": "store_true",
                "help": "Enable strict validation mode",
            }
        },
    )


# Comparison with original main() function

if __name__ == "__main__":
    # Example usage of refactored main
    sys.exit(main_refactored())

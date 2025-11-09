"""MPM initialization command package.

This package provides comprehensive project initialization and update capabilities
for Claude Code and Claude MPM. It includes:

- Core command class (MPMInitCommand) for orchestrating initialization
- Click CLI commands for command-line interface
- Modular components for prompts, display, git analysis, and modes
- Support for multiple initialization modes (create, update, review, quick-update, catchup)

Main Components:
- core.py: MPMInitCommand class - main initialization orchestrator
- mpm_init_cli.py: Click command definitions and CLI entry points
- prompts.py: Prompt building functions for agent delegation
- display.py: Display and UI helper functions
- git_activity.py: Git history analysis and context building
- modes.py: Mode-specific handlers (review, dry-run, quick-update, etc.)

Public API:
- MPMInitCommand: Main command class (from core)
- mpm_init: Click command group (from mpm_init_cli)

Example Usage:
    # Programmatic usage
    from claude_mpm.cli.commands.mpm_init import MPMInitCommand
    command = MPMInitCommand(project_path)
    result = command.initialize_project()

    # CLI usage (via Click)
    from claude_mpm.cli.commands.mpm_init import mpm_init
    # Command is registered with Click and invoked via CLI
"""

# Import core components for re-export
from .core import MPMInitCommand

# Import the Click command group - this must be imported from parent level
# to avoid circular dependencies, as mpm_init_cli imports from core
# We'll handle this via late import in __all__

__all__ = [
    # Main command class
    "MPMInitCommand",
    "core",
    # Internal modules (for internal package use)
    "display",
    "git_activity",
    "modes",
    # Click CLI command (imported via __getattr__ to avoid circular import)
    "mpm_init",
    "prompts",
]


def __getattr__(name):
    """Lazy import to avoid circular dependencies.

    This allows importing mpm_init Click command without importing
    mpm_init_cli at module load time, which would cause circular imports.
    """
    if name == "mpm_init":
        # Lazy import the Click command group
        from ..mpm_init_cli import mpm_init as _mpm_init

        return _mpm_init

    # For internal module imports, import them directly
    if name in ("display", "git_activity", "prompts", "modes", "core"):
        import importlib

        return importlib.import_module(f".{name}", __package__)

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

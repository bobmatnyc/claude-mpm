"""Shared module-level objects for the setup package.

Centralizes the Rich :class:`Console` instance so every handler/mixin and the
top-level package use the same object. Tests that need to suppress output
typically patch ``claude_mpm.cli.commands.setup.console``; the package
``__init__`` re-exports this same instance so that patch targets the binding
test code expects.
"""

from rich.console import Console

console = Console()

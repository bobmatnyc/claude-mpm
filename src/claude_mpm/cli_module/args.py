"""Argument registry for consolidating CLI argument definitions."""

import argparse
from pathlib import Path
from typing import Any, Dict, Optional


class ArgumentRegistry:
    """Registry for managing CLI argument definitions.

    This class consolidates argument definitions to reduce duplication
    and simplify the main CLI function.
    """

    def __init__(self):
        """Initialize the registry with common argument groups."""
        self._arguments: Dict[str, Dict[str, Any]] = {}
        self._groups: Dict[str, list] = {
            "global": [],
            "run": [],
            "logging": [],
            "framework": [],
            "orchestration": [],
        }
        self._register_common_arguments()

    def _register_common_arguments(self):
        """Register all common argument definitions."""
        # Version argument
        self.register(
            "version",
            {
                "flags": ["--version"],
                "action": "version",
                "help": "Show version and exit",
                "groups": ["global"],
            },
        )

        # Logging arguments
        self.register(
            "debug",
            {
                "flags": ["-d", "--debug"],
                "action": "store_true",
                "help": "Enable debug logging (deprecated, use --logging DEBUG)",
                "groups": ["logging", "global"],
            },
        )

        self.register(
            "logging",
            {
                "flags": ["--logging"],
                "choices": ["OFF", "INFO", "DEBUG"],
                "default": "OFF",
                "help": "Logging level (default: OFF)",
                "groups": ["logging", "global"],
            },
        )

        self.register(
            "log_dir",
            {
                "flags": ["--log-dir"],
                "type": Path,
                "help": "Custom log directory (default: ~/.claude-mpm/logs)",
                "groups": ["logging", "global"],
            },
        )

        # Framework arguments
        self.register(
            "framework_path",
            {
                "flags": ["--framework-path"],
                "type": Path,
                "help": "Path to claude-mpm framework",
                "groups": ["framework", "global"],
            },
        )

        self.register(
            "agents_dir",
            {
                "flags": ["--agents-dir"],
                "type": Path,
                "help": "Custom agents directory to use",
                "groups": ["framework", "global"],
            },
        )

        self.register(
            "no_hooks",
            {
                "flags": ["--no-hooks"],
                "action": "store_true",
                "help": "Disable hook service (runs without hooks)",
                "groups": ["framework", "global", "run"],
            },
        )

        # Run command arguments
        self.register(
            "no_tickets",
            {
                "flags": ["--no-tickets"],
                "action": "store_true",
                "help": "Disable automatic ticket creation",
                "groups": ["run"],
            },
        )

        self.register(
            "input",
            {
                "flags": ["-i", "--input"],
                "type": str,
                "help": "Input text or file path (for non-interactive mode)",
                "groups": ["run"],
            },
        )

        self.register(
            "non_interactive",
            {
                "flags": ["--non-interactive"],
                "action": "store_true",
                "help": "Run in non-interactive mode (read from stdin or --input)",
                "groups": ["run"],
            },
        )

        # Orchestration arguments
        self.register(
            "subprocess",
            {
                "flags": ["--subprocess"],
                "action": "store_true",
                "help": "Use subprocess orchestration for agent delegations",
                "groups": ["orchestration", "run"],
            },
        )

        self.register(
            "interactive_subprocess",
            {
                "flags": ["--interactive-subprocess"],
                "action": "store_true",
                "help": "Use interactive subprocess orchestration with pexpect control",
                "groups": ["orchestration", "run"],
            },
        )

        self.register(
            "todo_hijack",
            {
                "flags": ["--todo-hijack"],
                "action": "store_true",
                "help": "Enable TODO hijacking to transform Claude's TODOs into agent delegations",
                "groups": ["orchestration", "run"],
            },
        )

        # Ticket list arguments
        self.register(
            "limit",
            {
                "flags": ["-n", "--limit"],
                "type": int,
                "default": 10,
                "help": "Number of tickets to show",
                "groups": ["tickets"],
            },
        )

    def register(self, name: str, definition: Dict[str, Any]):
        """Register a new argument definition.

        Args:
            name: Internal name for the argument
            definition: Dictionary containing argument configuration:
                - flags: List of flag strings (e.g., ['-d', '--debug'])
                - groups: List of group names this argument belongs to
                - All other kwargs are passed to add_argument()
        """
        self._arguments[name] = definition

        # Add to groups
        for group in definition.get("groups", []):
            if group not in self._groups:
                self._groups[group] = []
            self._groups[group].append(name)

    def apply_arguments(
        self,
        parser: argparse.ArgumentParser,
        groups: Optional[list] = None,
        exclude: Optional[list] = None,
    ):
        """Apply argument definitions to a parser.

        Args:
            parser: ArgumentParser or subparser to add arguments to
            groups: List of group names to include (None = all)
            exclude: List of argument names to exclude
        """
        # Determine which arguments to add
        if groups is None:
            arg_names = list(self._arguments.keys())
        else:
            arg_names = []
            for group in groups:
                arg_names.extend(self._groups.get(group, []))
            # Remove duplicates while preserving order
            seen = set()
            arg_names = [x for x in arg_names if not (x in seen or seen.add(x))]

        # Apply exclusions
        if exclude:
            arg_names = [n for n in arg_names if n not in exclude]

        # Add arguments to parser
        for name in arg_names:
            definition = self._arguments[name].copy()
            flags = definition.pop("flags")
            definition.pop("groups", None)  # Remove groups from kwargs

            # Special handling for version
            if name == "version" and hasattr(parser, "_version"):
                definition["version"] = parser._version

            parser.add_argument(*flags, **definition)

    def get_argument_groups(self) -> Dict[str, list]:
        """Get all argument groups and their members."""
        return self._groups.copy()

    def get_argument_definition(self, name: str) -> Optional[Dict[str, Any]]:
        """Get the definition for a specific argument."""
        return self._arguments.get(name, {}).copy()

    def create_argument_group(
        self,
        parser: argparse.ArgumentParser,
        group_name: str,
        title: str,
        description: Optional[str] = None,
    ):
        """Create an argument group and add arguments from a named group.

        Args:
            parser: Parser to add the group to
            group_name: Name of the argument group in registry
            title: Title for the argument group
            description: Optional description for the group
        """
        group = parser.add_argument_group(title, description)

        # Get arguments for this group
        arg_names = self._groups.get(group_name, [])

        for name in arg_names:
            definition = self._arguments[name].copy()
            flags = definition.pop("flags")
            definition.pop("groups", None)

            group.add_argument(*flags, **definition)

        return group

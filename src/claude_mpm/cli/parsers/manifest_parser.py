"""
Manifest command parser for claude-mpm CLI.

WHAT: Registers the ``manifest`` top-level command and its three subcommands
(``init``, ``validate``, ``show``) with the argparse subparser tree.

WHY: Keeping the parser definition separate from the command implementation
follows the project's established pattern (one parser module per command
domain, one commands/ module per implementation) and allows the executor to
import only the parser at startup, deferring the heavier manifest imports
until the command actually runs.

References
----------
SPEC-MANIFEST-05~1 : docs/specs/manifest.md#SPEC-MANIFEST-05~1
"""

from __future__ import annotations

import argparse
from pathlib import Path


def add_manifest_subparser(subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    """Add the ``manifest`` command and its subcommands to *subparsers*.

    WHAT: Creates ``manifest`` as a top-level command with three second-level
    subcommands: ``init``, ``validate``, and ``show``.  All three subcommands
    store their chosen action in ``args.manifest_command`` so the executor and
    ``manage_manifest`` can dispatch without inspecting ``sys.argv`` directly.

    WHY: Mirroring the ``config`` command's nested-subparser pattern keeps the
    parser tree consistent and gives ``--help`` output that matches user
    expectations for a three-verb command group.

    Test: Call ``add_manifest_subparser(subparsers)``; parse
    ``["manifest", "validate"]`` with the resulting parser; assert
    ``args.command == "manifest"`` and ``args.manifest_command == "validate"``.

    :spec: SPEC-MANIFEST-05~1
    """
    manifest_parser = subparsers.add_parser(
        "manifest",
        help="Manage the .claude-mpm/manifest.json configuration file",
        description=(
            "Manage the .claude-mpm/manifest.json manifest configuration.\n"
            "\n"
            "Available subcommands:\n"
            "  init       Scaffold .claude-mpm/manifest.json (interactive or non-interactive)\n"
            "  validate   Validate the manifest against the schema and resolve presets\n"
            "  show       Print the fully-resolved effective configuration as JSON\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    manifest_subparsers = manifest_parser.add_subparsers(
        dest="manifest_command",
        help="Manifest subcommands",
        metavar="SUBCOMMAND",
    )

    # ------------------------------------------------------------------
    # ``manifest init``
    # ------------------------------------------------------------------
    init_parser = manifest_subparsers.add_parser(
        "init",
        help="Scaffold .claude-mpm/manifest.json",
        description=(
            "Interactively scaffold .claude-mpm/manifest.json at the repo root.\n"
            "\n"
            "In interactive mode (default when stdin is a TTY), prompts for the\n"
            "preset to extend and which empty sections to seed.\n"
            "\n"
            "Use --non-interactive (or --yes) for scripted / CI usage — combine\n"
            "with --extends to set the preset name without prompting.\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  # Interactive scaffold\n"
            "  claude-mpm manifest init\n"
            "\n"
            "  # Non-interactive, extend the 'default' preset\n"
            "  claude-mpm manifest init --non-interactive --extends default\n"
            "\n"
            "  # Overwrite an existing manifest\n"
            "  claude-mpm manifest init --force --extends minimal\n"
        ),
    )

    init_parser.add_argument(
        "--extends",
        metavar="PRESET",
        default=None,
        help=(
            "Built-in preset to extend (default/minimal/enterprise) or 'none'. "
            "If omitted in interactive mode, the user is prompted."
        ),
    )
    init_parser.add_argument(
        "--force",
        "-f",
        action="store_true",
        default=False,
        help="Overwrite an existing manifest.json without confirmation.",
    )
    init_parser.add_argument(
        "--non-interactive",
        "--yes",
        "-y",
        dest="non_interactive",
        action="store_true",
        default=False,
        help="Skip all interactive prompts (CI/script-safe mode).",
    )
    init_parser.add_argument(
        "--seed-agents",
        action="store_true",
        default=False,
        help="Include an empty 'agents' section in the generated manifest.",
    )
    init_parser.add_argument(
        "--seed-settings",
        action="store_true",
        default=False,
        help="Include an empty 'settings' section in the generated manifest.",
    )
    init_parser.add_argument(
        "--seed-services",
        action="store_true",
        default=False,
        help="Include an empty 'setup.services' list in the generated manifest.",
    )
    init_parser.add_argument(
        "--path",
        metavar="PATH",
        type=Path,
        default=None,
        help=(
            "Write the manifest to this exact file path instead of the default "
            "<repo-root>/.claude-mpm/manifest.json."
        ),
    )

    # ------------------------------------------------------------------
    # ``manifest validate``
    # ------------------------------------------------------------------
    validate_parser = manifest_subparsers.add_parser(
        "validate",
        help="Validate the manifest against the schema and resolve the extends preset",
        description=(
            "Validate .claude-mpm/manifest.json against the JSON schema and confirm\n"
            "that the 'extends' preset (if any) can be resolved.\n"
            "\n"
            "Exit codes:\n"
            "  0  Manifest is valid, or no manifest found (system dormant).\n"
            "  1  Manifest is invalid, or preset cannot be resolved.\n"
            "\n"
            "Suitable for CI pipelines.\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  claude-mpm manifest validate\n"
            "  claude-mpm manifest validate --path path/to/manifest.json\n"
        ),
    )
    validate_parser.add_argument(
        "--path",
        metavar="PATH",
        type=Path,
        default=None,
        help="Validate a specific manifest file instead of the auto-discovered one.",
    )

    # ------------------------------------------------------------------
    # ``manifest show``
    # ------------------------------------------------------------------
    show_parser = manifest_subparsers.add_parser(
        "show",
        help="Print the fully-resolved effective configuration as JSON",
        description=(
            "Load, resolve, and deep-merge the manifest, then print the fully-merged\n"
            "effective configuration to stdout as pretty-printed JSON.\n"
            "\n"
            "If no manifest is found (system dormant), prints a message to stderr\n"
            "and exits 0.\n"
            "\n"
            "Pipe into 'jq' to query specific sections:\n"
            "  claude-mpm manifest show | jq '.agents'\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  claude-mpm manifest show\n"
            "  claude-mpm manifest show | jq '.settings'\n"
            "  claude-mpm manifest show --path path/to/manifest.json\n"
        ),
    )
    show_parser.add_argument(
        "--path",
        metavar="PATH",
        type=Path,
        default=None,
        help="Show the resolved config for a specific manifest file.",
    )

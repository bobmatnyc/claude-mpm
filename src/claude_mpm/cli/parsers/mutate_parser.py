#!/usr/bin/env python3
"""
Mutate Parser
=============

WHAT: Define and validate the argument surface for the ``claude-mpm mutate``
      CLI command — an advisory wrapper over the merged mutation runner that
      scopes a mutmut run to a single eligible source file plus its test file.
WHY:  Centralizes the CLI contract (target resolution, auto-discovery base,
      exclude expression, advisory-by-default threshold, dry-run, output
      format) so the executor and command handler share one validated shape,
      mirroring the existing ``AnalyzeCodeParser`` inline-class pattern.

References
----------
LINK: SPEC-MUTATION-02~1 : docs/specs/mutation.md#SPEC-MUTATION-02~1
"""

import argparse
from pathlib import Path


class MutateParser:
    """Parser for the ``mutate`` command arguments.

    WHAT: Configures the ``mutate`` subparser and validates the parsed
          namespace (target must be an existing ``.py`` file under ``src/``;
          ``--max-files`` must be >= 1).
    WHY:  Keeps argument definition and validation next to each other and
          consistent with the other CLI parsers so the command behaves
          predictably and fails fast on bad input.
    """

    def __init__(self):
        self.command_name = "mutate"
        self.help_text = (
            "Run advisory mutation testing on an eligible source file "
            "(wraps the mutmut runner)"
        )

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Add ``mutate``-specific arguments to the parser.

        WHAT: Register the positional ``target`` plus the scope options
              (``--tests-file``, ``--base``, ``--exclude-tests``,
              ``--max-files``, ``--force``) and behavior options
              (``--threshold``, ``--dry-run``, ``--output``).
        WHY:  Grouping the flags into scope vs behavior keeps ``--help`` legible
              and matches the command's two concerns: *what* to mutate and *how*
              to report/gate. Defaults encode the advisory-by-default contract
              (``--threshold`` unset, ``--max-files`` 1, ``--base`` origin/main).

        Args:
            parser: Argument parser to configure.

        :spec: SPEC-MUTATION-02~1
        """
        parser.add_argument(
            "target",
            type=str,
            nargs="?",
            default=None,
            help=(
                "Optional .py file under src/ to mutate. If omitted, "
                "auto-discover changed eligible files vs --base (git diff)."
            ),
        )

        scope_group = parser.add_argument_group("scope options")
        scope_group.add_argument(
            "--tests-file",
            type=str,
            metavar="PATH",
            default=None,
            help=(
                "Paired unit test file. If omitted, auto-infer from the "
                "target module stem (tests/**/test_<stem>.py)."
            ),
        )
        scope_group.add_argument(
            "--base",
            type=str,
            metavar="BRANCH",
            default="origin/main",
            help="Base ref for auto-discovery (default: origin/main).",
        )
        scope_group.add_argument(
            "--exclude-tests",
            type=str,
            metavar="EXPR",
            default=None,
            help=(
                "pytest -k expression to drop slow suites (passed to the "
                "runner, which validates it against shell-injection)."
            ),
        )
        scope_group.add_argument(
            "--max-files",
            type=int,
            metavar="N",
            default=1,
            help="Cap on auto-discovered targets (default: 1).",
        )
        scope_group.add_argument(
            "--force",
            action="store_true",
            help="Bypass the eligibility heuristic (human override).",
        )

        behavior_group = parser.add_argument_group("behavior options")
        behavior_group.add_argument(
            "--threshold",
            type=int,
            metavar="N",
            default=None,
            help=(
                "Survivor gate. --threshold 0 means zero survivors tolerated "
                "(ANY survivor fails, exit 1); --threshold N exits 1 when "
                "survivors > N. If UNSET (default), the command is purely "
                "advisory and ALWAYS exits 0 (survivors are signal, not "
                "failure)."
            ),
        )
        behavior_group.add_argument(
            "--dry-run",
            action="store_true",
            help="Print resolved scope + the would-run command, then exit 0.",
        )
        behavior_group.add_argument(
            "--output",
            choices=["text", "json"],
            default="text",
            help=(
                "Output format (default: text). json emits "
                "dataclasses.asdict(MutationResult)."
            ),
        )

    def validate_args(self, args: argparse.Namespace) -> str | None:
        """Validate parsed arguments.

        Args:
            args: Parsed arguments.

        Returns:
            Error message string if validation fails, ``None`` otherwise.
        """
        if args.target is not None:
            target = Path(args.target)
            if not target.exists():
                return f"Target does not exist: {target}"
            if target.suffix != ".py":
                return f"Target must be a .py file: {target}"
            # Must live under a src/ path component.
            if "src" not in target.parts:
                return f"Target must be under src/: {target}"

        if args.max_files is not None and args.max_files < 1:
            return "--max-files must be at least 1"

        return None

    def get_examples(self) -> list:
        """Get usage examples.

        Returns:
            List of example command strings.
        """
        return [
            "claude-mpm mutate",
            "claude-mpm mutate src/claude_mpm/services/foo.py",
            "claude-mpm mutate src/claude_mpm/services/foo.py "
            "--tests-file tests/services/test_foo.py",
            "claude-mpm mutate --base origin/main --max-files 3",
            "claude-mpm mutate src/claude_mpm/services/foo.py --dry-run",
            "claude-mpm mutate src/claude_mpm/services/foo.py --output json",
            "claude-mpm mutate src/claude_mpm/services/foo.py --threshold 0",
            "claude-mpm mutate src/claude_mpm/cli/commands/bar.py --force",
        ]

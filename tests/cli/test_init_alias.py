"""Tests for 'init' as an alias for 'mpm-init'.

WHY: Issue #553 — users naturally type `claude-mpm init` but the command was
registered only as `mpm-init`, causing an "invalid choice" error.  The fix
registers `init` as an argparse alias so both forms work identically.

These tests verify that:
1. `claude-mpm init` resolves to the same command value as `claude-mpm mpm-init`.
2. All flags/args accepted by `mpm-init` are also accepted by `init`.
3. Sub-commands (context, pause) are accessible via the alias.
4. `claude-mpm init --help` exits with 0 (no "invalid choice" error).
"""

import io
import sys
from unittest.mock import patch

import pytest

from claude_mpm.cli.parsers import create_parser


class TestInitAlias:
    """Verify that 'init' is a functional alias for 'mpm-init'."""

    def _parser(self):
        """Return a fresh parser for each test."""
        return create_parser(version="0.0.0-test")

    # ------------------------------------------------------------------
    # Core alias resolution
    # ------------------------------------------------------------------

    def test_init_resolves_to_mpm_init_command(self):
        """'init' must set args.command == 'mpm-init', same as 'mpm-init'."""
        parser = self._parser()
        args_alias = parser.parse_args(["init"])
        args_canonical = parser.parse_args(["mpm-init"])

        assert args_alias.command == "mpm-init", (
            f"Expected 'mpm-init', got '{args_alias.command}'"
        )
        assert args_alias.command == args_canonical.command

    def test_init_default_project_path(self):
        """'init' with no arguments defaults project_path to '.'."""
        args = self._parser().parse_args(["init"])
        assert args.project_path == "."

    def test_init_project_path_defaults_when_no_args(self):
        """With no positional arg, project_path defaults to '.' for both forms."""
        parser = self._parser()
        args_alias = parser.parse_args(["init"])
        args_canonical = parser.parse_args(["mpm-init"])
        assert args_alias.project_path == "."
        assert args_canonical.project_path == "."

    # ------------------------------------------------------------------
    # Flag parity between 'init' and 'mpm-init'
    # ------------------------------------------------------------------

    @pytest.mark.parametrize(
        "flag,attr,expected",
        [
            ("--force", "force", True),
            ("--update", "update", True),
            ("--dry-run", "dry_run", True),
            ("--verbose", "verbose", True),
            ("--review", "review", True),
            ("--organize", "organize", True),
            ("--minimal", "minimal", True),
            ("--comprehensive", "comprehensive", True),
            ("--quick-update", "quick_update", True),
            ("--catchup", "catchup", True),
            ("--non-interactive", "non_interactive", True),
            ("--json", "json", True),
            ("--list-templates", "list_templates", True),
            ("--skip-archive", "skip_archive", True),
        ],
    )
    def test_init_accepts_same_flags_as_mpm_init(self, flag, attr, expected):
        """Every boolean flag supported by 'mpm-init' must work via 'init'."""
        parser = self._parser()
        args = parser.parse_args(["init", flag])
        assert args.command == "mpm-init"
        assert getattr(args, attr) == expected, (
            f"Flag {flag!r} should set args.{attr}={expected}, "
            f"got {getattr(args, attr)!r}"
        )

    def test_init_with_project_type(self):
        """'init --project-type web' is accepted."""
        args = self._parser().parse_args(["init", "--project-type", "web"])
        assert args.project_type == "web"

    def test_init_with_framework(self):
        """'init --framework react' is accepted."""
        args = self._parser().parse_args(["init", "--framework", "react"])
        assert args.framework == "react"

    def test_init_with_language(self):
        """'init --language python' is accepted."""
        args = self._parser().parse_args(["init", "--language", "python"])
        assert args.language == "python"

    def test_init_with_days(self):
        """'init --days 7' passes through correctly."""
        args = self._parser().parse_args(["init", "--days", "7"])
        assert args.days == 7

    def test_init_with_archive_dir(self):
        """'init --archive-dir /tmp/archive' passes through."""
        args = self._parser().parse_args(["init", "--archive-dir", "/tmp/archive"])
        assert args.archive_dir == "/tmp/archive"

    def test_init_with_template(self):
        """'init --template my-template' passes through."""
        args = self._parser().parse_args(["init", "--template", "my-template"])
        assert args.template == "my-template"

    # ------------------------------------------------------------------
    # Sub-command accessibility via alias
    # ------------------------------------------------------------------

    def test_init_context_subcommand(self):
        """'init context' sub-command resolves correctly."""
        args = self._parser().parse_args(["init", "context"])
        assert args.command == "mpm-init"
        assert args.subcommand == "context"

    def test_init_pause_subcommand(self):
        """'init pause' sub-command resolves correctly."""
        args = self._parser().parse_args(["init", "pause"])
        assert args.command == "mpm-init"
        assert args.subcommand == "pause"

    def test_init_resume_subcommand(self):
        """'init resume' (deprecated) sub-command resolves correctly."""
        args = self._parser().parse_args(["init", "resume"])
        assert args.command == "mpm-init"
        assert args.subcommand == "resume"

    # ------------------------------------------------------------------
    # Help / no-error behaviour
    # ------------------------------------------------------------------

    def test_init_help_exits_zero(self):
        """'claude-mpm init --help' must exit with code 0, not 2."""
        parser = self._parser()
        with pytest.raises(SystemExit) as exc_info:
            parser.parse_args(["init", "--help"])
        assert exc_info.value.code == 0, (
            f"Expected exit code 0 for --help, got {exc_info.value.code}"
        )

    def test_mpm_init_help_exits_zero(self):
        """Baseline: 'claude-mpm mpm-init --help' also exits with 0."""
        parser = self._parser()
        with pytest.raises(SystemExit) as exc_info:
            parser.parse_args(["mpm-init", "--help"])
        assert exc_info.value.code == 0

    def test_init_does_not_raise_invalid_choice(self):
        """Typing 'init' must never trigger 'invalid choice' from argparse."""
        parser = self._parser()
        # If 'init' were not registered, argparse would call sys.exit(2).
        # A successful parse (no exception) proves the alias works.
        try:
            args = parser.parse_args(["init"])
        except SystemExit as exc:
            pytest.fail(
                f"'claude-mpm init' raised SystemExit({exc.code}); "
                "the 'init' alias may not be registered correctly."
            )
        assert args.command == "mpm-init"

    # ------------------------------------------------------------------
    # Argument value parity
    # ------------------------------------------------------------------

    def test_init_and_mpm_init_produce_identical_defaults(self):
        """Parsed defaults for 'init' and 'mpm-init' must be identical."""
        parser = self._parser()
        args_alias = parser.parse_args(["init"])
        args_canonical = parser.parse_args(["mpm-init"])

        alias_ns = vars(args_alias)
        canonical_ns = vars(args_canonical)

        # Both must agree on every key
        assert alias_ns == canonical_ns, (
            f"Namespace mismatch between 'init' and 'mpm-init':\n"
            f"  alias:     {alias_ns}\n"
            f"  canonical: {canonical_ns}"
        )

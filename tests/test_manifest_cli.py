"""
tests/test_manifest_cli.py — Unit tests for the manifest CLI commands.

WHAT: Exercises ``manifest init``, ``manifest validate``, and ``manifest show``
via argparse end-to-end (parser → executor → handler) using the project's
subprocess / argparse pattern and direct handler function calls with
temporary directories.

WHY: The CLI surface is the primary developer and CI touchpoint for the
manifest subsystem.  Correct exit-code behaviour (especially dormant → exit 0)
is critical; a regression here could cause CI failures in repos that have not
opted in to the manifest system.

References
----------
SPEC-MANIFEST-05~1 : docs/specs/manifest.md#SPEC-MANIFEST-05~1
"""

from __future__ import annotations

import argparse
import json
import sys
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pytest

# ---------------------------------------------------------------------------
# Helpers — thin wrappers that call the CLI handler functions directly
# ---------------------------------------------------------------------------


def _make_args(**kwargs) -> argparse.Namespace:
    """Return an argparse Namespace pre-populated with sensible defaults."""
    defaults: dict = {
        "manifest_command": None,
        "path": None,
        "force": False,
        "extends": None,
        "non_interactive": True,  # non-interactive by default in tests
        "yes": False,
        "seed_agents": False,
        "seed_settings": False,
        "seed_services": False,
    }
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def _write_manifest(directory: Path, content: dict | str) -> Path:
    """Write a manifest file into *directory*/.claude-mpm/manifest.json."""
    manifest_dir = directory / ".claude-mpm"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = manifest_dir / "manifest.json"
    if isinstance(content, dict):
        manifest_path.write_text(json.dumps(content), encoding="utf-8")
    else:
        manifest_path.write_text(str(content), encoding="utf-8")
    return manifest_path


# ---------------------------------------------------------------------------
# Import the handlers under test
# ---------------------------------------------------------------------------

from claude_mpm.cli.commands.manifest_commands import (
    _cmd_init,
    _cmd_show,
    _cmd_validate,
    manage_manifest,
)

# ===========================================================================
# manifest init
# ===========================================================================


class TestManifestInit:
    """Tests for ``claude-mpm manifest init``."""

    def test_creates_manifest_in_temp_dir(self, tmp_path: Path) -> None:
        """Non-interactive init writes a valid manifest.json.

        Why: The most common CI use-case — scaffold with no prompts.
        Test: Assert file exists and is valid JSON with version "1.0".

        :spec: SPEC-MANIFEST-05~1
        """
        from claude_mpm.manifest.schema import validate_manifest

        manifest_path = tmp_path / ".claude-mpm" / "manifest.json"
        args = _make_args(
            manifest_command="init",
            path=manifest_path,
            non_interactive=True,
        )

        with patch(
            "claude_mpm.cli.commands.manifest_commands._repo_root",
            return_value=tmp_path,
        ):
            exit_code = _cmd_init(args)

        assert exit_code == 0
        assert manifest_path.exists()
        data = json.loads(manifest_path.read_text())
        assert data["version"] == "1.0"
        validate_manifest(data)  # Must not raise.

    def test_non_interactive_with_extends(self, tmp_path: Path) -> None:
        """--extends default writes extends key to the manifest.

        Test: Assert 'extends' == 'default' in written file.

        :spec: SPEC-MANIFEST-05~1
        """
        manifest_path = tmp_path / ".claude-mpm" / "manifest.json"
        args = _make_args(
            path=manifest_path,
            non_interactive=True,
            extends="default",
        )
        with patch(
            "claude_mpm.cli.commands.manifest_commands._repo_root",
            return_value=tmp_path,
        ):
            exit_code = _cmd_init(args)

        assert exit_code == 0
        data = json.loads(manifest_path.read_text())
        assert data.get("extends") == "default"

    def test_refuses_overwrite_without_force(self, tmp_path: Path) -> None:
        """Without --force, a second init on an existing file returns exit 1.

        Test: Create a manifest, run init again, assert exit_code == 1 and
        the original file is unchanged.

        :spec: SPEC-MANIFEST-05~1
        """
        original_content = {"version": "1.0", "settings": {"my": "value"}}
        manifest_path = _write_manifest(tmp_path, original_content)

        args = _make_args(
            path=manifest_path,
            non_interactive=True,
            force=False,
        )

        exit_code = _cmd_init(args)

        assert exit_code == 1
        # File must be unchanged.
        data = json.loads(manifest_path.read_text())
        assert data == original_content

    def test_force_overwrites_existing(self, tmp_path: Path) -> None:
        """--force overwrites an existing manifest without error.

        Test: Write an original manifest, then init --force --extends minimal;
        assert exit_code == 0 and file now has extends == 'minimal'.

        :spec: SPEC-MANIFEST-05~1
        """
        original = {"version": "1.0", "settings": {"old": "data"}}
        manifest_path = _write_manifest(tmp_path, original)

        args = _make_args(
            path=manifest_path,
            non_interactive=True,
            force=True,
            extends="minimal",
        )
        exit_code = _cmd_init(args)

        assert exit_code == 0
        data = json.loads(manifest_path.read_text())
        assert data.get("extends") == "minimal"
        # Old key must be gone.
        assert "settings" not in data

    def test_output_validates_against_schema(self, tmp_path: Path) -> None:
        """The written manifest must pass validate_manifest().

        Test: Run init, read the file, call validate_manifest; assert no
        exception is raised.

        :spec: SPEC-MANIFEST-05~1
        """
        from claude_mpm.manifest.schema import validate_manifest

        manifest_path = tmp_path / ".claude-mpm" / "manifest.json"
        args = _make_args(
            path=manifest_path,
            non_interactive=True,
            extends="default",
            seed_agents=True,
            seed_settings=True,
            seed_services=True,
        )
        with patch(
            "claude_mpm.cli.commands.manifest_commands._repo_root",
            return_value=tmp_path,
        ):
            exit_code = _cmd_init(args)

        assert exit_code == 0
        data = json.loads(manifest_path.read_text())
        validate_manifest(data)

    def test_seed_flags_add_sections(self, tmp_path: Path) -> None:
        """Seed flags produce expected empty sections.

        Test: Run init with all seed flags; assert 'agents', 'settings',
        and 'setup.services' are present.

        :spec: SPEC-MANIFEST-05~1
        """
        manifest_path = tmp_path / ".claude-mpm" / "manifest.json"
        args = _make_args(
            path=manifest_path,
            non_interactive=True,
            seed_agents=True,
            seed_settings=True,
            seed_services=True,
        )
        with patch(
            "claude_mpm.cli.commands.manifest_commands._repo_root",
            return_value=tmp_path,
        ):
            exit_code = _cmd_init(args)

        assert exit_code == 0
        data = json.loads(manifest_path.read_text())
        assert "agents" in data
        assert "settings" in data
        assert "setup" in data
        assert data["setup"]["services"] == []


# ===========================================================================
# manifest validate
# ===========================================================================


class TestManifestValidate:
    """Tests for ``claude-mpm manifest validate``."""

    def test_dormant_no_file_exits_zero(self, tmp_path: Path) -> None:
        """When no manifest exists, validate must exit 0 (system dormant).

        Test: Point --path at a non-existent file; assert exit_code == 0.

        :spec: SPEC-MANIFEST-05~1
        """
        missing = tmp_path / ".claude-mpm" / "manifest.json"
        args = _make_args(path=missing)

        exit_code = _cmd_validate(args)

        assert exit_code == 0

    def test_valid_manifest_exits_zero(self, tmp_path: Path) -> None:
        """A valid manifest.json → exit 0.

        Test: Write {"version": "1.0"}; assert exit_code == 0.

        :spec: SPEC-MANIFEST-05~1
        """
        manifest_path = _write_manifest(tmp_path, {"version": "1.0"})
        args = _make_args(path=manifest_path)

        exit_code = _cmd_validate(args)

        assert exit_code == 0

    def test_valid_manifest_with_extends_exits_zero(self, tmp_path: Path) -> None:
        """A manifest with a resolvable 'extends' preset → exit 0.

        Test: Write {"version": "1.0", "extends": "default"}; assert exit_code == 0.

        :spec: SPEC-MANIFEST-05~1
        """
        manifest_path = _write_manifest(
            tmp_path, {"version": "1.0", "extends": "default"}
        )
        args = _make_args(path=manifest_path)

        exit_code = _cmd_validate(args)

        assert exit_code == 0

    def test_invalid_schema_exits_nonzero(self, tmp_path: Path, capsys) -> None:
        """A manifest failing schema validation → exit 1 + clear message.

        Test: Write {"version": "2.0"} (invalid version); assert exit_code == 1
        and stderr contains a message.

        :spec: SPEC-MANIFEST-05~1
        """
        manifest_path = _write_manifest(tmp_path, {"version": "2.0"})
        args = _make_args(path=manifest_path)

        exit_code = _cmd_validate(args)

        assert exit_code == 1
        captured = capsys.readouterr()
        # The error must mention something actionable.
        assert "Error" in captured.err or "error" in captured.err.lower()

    def test_unresolvable_preset_exits_nonzero(self, tmp_path: Path, capsys) -> None:
        """An unresolvable 'extends' preset → exit 1 + clear message.

        Test: Write {"version": "1.0", "extends": "nonexistent-preset-xyz"};
        assert exit_code == 1 and stderr mentions "preset".

        :spec: SPEC-MANIFEST-05~1
        """
        manifest_path = _write_manifest(
            tmp_path,
            {"version": "1.0", "extends": "nonexistent-preset-xyz-abc"},
        )
        args = _make_args(path=manifest_path)

        exit_code = _cmd_validate(args)

        assert exit_code == 1
        captured = capsys.readouterr()
        assert "preset" in captured.err.lower() or "nonexistent" in captured.err

    def test_invalid_json_exits_nonzero(self, tmp_path: Path, capsys) -> None:
        """A manifest with malformed JSON → exit 1 + clear message.

        Test: Write "not-json"; assert exit_code == 1.

        :spec: SPEC-MANIFEST-05~1
        """
        manifest_path = _write_manifest(tmp_path, "not valid json {{{")
        args = _make_args(path=manifest_path)

        exit_code = _cmd_validate(args)

        assert exit_code == 1

    def test_dormant_auto_discovery_exits_zero(self, tmp_path: Path) -> None:
        """Auto-discovery in an empty directory → exit 0 (dormant).

        Test: Patch find_manifest to return None (simulates a repo with no
        manifest file); assert exit_code == 0.

        :spec: SPEC-MANIFEST-05~1
        """
        args = _make_args(path=None)

        with patch(
            "claude_mpm.cli.commands.manifest_commands.find_manifest",
            return_value=None,
        ):
            exit_code = _cmd_validate(args)

        assert exit_code == 0


# ===========================================================================
# manifest show
# ===========================================================================


class TestManifestShow:
    """Tests for ``claude-mpm manifest show``."""

    def test_dormant_exits_zero(self, tmp_path: Path, capsys) -> None:
        """No manifest → exit 0, nothing on stdout.

        Test: Call show with --path pointing at a non-existent file; assert
        exit_code == 0 and stdout is empty.

        :spec: SPEC-MANIFEST-05~1
        """
        missing = tmp_path / ".claude-mpm" / "manifest.json"
        args = _make_args(path=missing)

        exit_code = _cmd_show(args)

        assert exit_code == 0
        captured = capsys.readouterr()
        assert captured.out.strip() == ""

    def test_show_valid_manifest_prints_json(self, tmp_path: Path, capsys) -> None:
        """A valid manifest without extends → exit 0, valid JSON on stdout.

        Test: Write {"version": "1.0"}; run show; assert output parses as JSON
        and contains "version".

        :spec: SPEC-MANIFEST-05~1
        """
        manifest_path = _write_manifest(tmp_path, {"version": "1.0"})
        args = _make_args(path=manifest_path)

        exit_code = _cmd_show(args)

        assert exit_code == 0
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["version"] == "1.0"

    def test_show_with_extends_default_contains_merged_keys(
        self, tmp_path: Path, capsys
    ) -> None:
        """manifest show with extends: default → merged JSON includes preset keys.

        Test: Write {"version": "1.0", "extends": "default"}; run show; assert
        exit_code == 0 and output parses as JSON.

        :spec: SPEC-MANIFEST-05~1
        """
        manifest_path = _write_manifest(
            tmp_path, {"version": "1.0", "extends": "default"}
        )
        args = _make_args(path=manifest_path)

        exit_code = _cmd_show(args)

        assert exit_code == 0
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        # Must be a non-empty dict.
        assert isinstance(data, dict)
        assert data["version"] == "1.0"

    def test_show_invalid_manifest_exits_nonzero(self, tmp_path: Path, capsys) -> None:
        """An invalid manifest → exit 1.

        Test: Write {"version": "bad"}; run show; assert exit_code == 1.

        :spec: SPEC-MANIFEST-05~1
        """
        manifest_path = _write_manifest(tmp_path, {"version": "bad"})
        args = _make_args(path=manifest_path)

        exit_code = _cmd_show(args)

        assert exit_code == 1

    def test_show_auto_discovery_dormant(self, tmp_path: Path, capsys) -> None:
        """Auto-discovery in an empty directory → exit 0, no stdout.

        Test: Patch find_manifest to return None; assert exit_code == 0.

        :spec: SPEC-MANIFEST-05~1
        """
        args = _make_args(path=None)

        with patch(
            "claude_mpm.cli.commands.manifest_commands.find_manifest",
            return_value=None,
        ):
            exit_code = _cmd_show(args)

        assert exit_code == 0
        captured = capsys.readouterr()
        assert captured.out.strip() == ""


# ===========================================================================
# manage_manifest dispatcher
# ===========================================================================


class TestManageManifest:
    """Tests for the ``manage_manifest`` dispatcher."""

    def test_dispatches_validate(self, tmp_path: Path) -> None:
        """manage_manifest with manifest_command='validate' calls _cmd_validate.

        Test: Patch _cmd_validate; call manage_manifest; assert the patch was
        called once.

        :spec: SPEC-MANIFEST-05~1
        """
        args = _make_args(
            manifest_command="validate", path=tmp_path / ".claude-mpm" / "manifest.json"
        )

        with patch(
            "claude_mpm.cli.commands.manifest_commands._cmd_validate",
            return_value=0,
        ) as mock:
            result = manage_manifest(args)

        mock.assert_called_once_with(args)
        assert result == 0

    def test_dispatches_show(self, tmp_path: Path) -> None:
        """manage_manifest with manifest_command='show' calls _cmd_show.

        :spec: SPEC-MANIFEST-05~1
        """
        args = _make_args(manifest_command="show", path=None)

        with patch(
            "claude_mpm.cli.commands.manifest_commands._cmd_show",
            return_value=0,
        ) as mock:
            result = manage_manifest(args)

        mock.assert_called_once_with(args)
        assert result == 0

    def test_unknown_subcommand_returns_one(self, capsys) -> None:
        """An unknown subcommand → exit 1.

        :spec: SPEC-MANIFEST-05~1
        """
        args = _make_args(manifest_command="nonexistent")
        result = manage_manifest(args)
        assert result == 1

    def test_no_subcommand_returns_one(self, capsys) -> None:
        """No subcommand → exit 1.

        :spec: SPEC-MANIFEST-05~1
        """
        args = _make_args(manifest_command=None)
        result = manage_manifest(args)
        assert result == 1


# ===========================================================================
# Parser registration smoke-test
# ===========================================================================


class TestManifestParserRegistration:
    """Smoke-test that the manifest parser is registered in the main CLI tree."""

    def test_manifest_parser_registered(self) -> None:
        """create_parser() must produce a parser that accepts 'manifest validate'.

        Test: Parse ['manifest', 'validate'] with the main parser; assert
        args.command == 'manifest' and args.manifest_command == 'validate'.

        :spec: SPEC-MANIFEST-05~1
        """
        from claude_mpm.cli.parsers.base_parser import create_parser

        parser = create_parser(version="0.0.0")
        args = parser.parse_args(["manifest", "validate"])
        assert args.command == "manifest"
        assert args.manifest_command == "validate"

    def test_manifest_init_flags(self) -> None:
        """manifest init --non-interactive --extends minimal parses correctly.

        :spec: SPEC-MANIFEST-05~1
        """
        from claude_mpm.cli.parsers.base_parser import create_parser

        parser = create_parser(version="0.0.0")
        args = parser.parse_args(
            ["manifest", "init", "--non-interactive", "--extends", "minimal"]
        )
        assert args.manifest_command == "init"
        assert args.non_interactive is True
        assert args.extends == "minimal"

    def test_manifest_show_path_flag(self) -> None:
        """manifest show --path /tmp/m.json parses correctly.

        :spec: SPEC-MANIFEST-05~1
        """
        from claude_mpm.cli.parsers.base_parser import create_parser

        parser = create_parser(version="0.0.0")
        args = parser.parse_args(["manifest", "show", "--path", "/tmp/m.json"])
        assert args.manifest_command == "show"
        assert args.path == Path("/tmp/m.json")

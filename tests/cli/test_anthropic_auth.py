"""Tests for Anthropic authentication guidance and pre-flight checks."""

import os
import subprocess
from io import StringIO
from unittest.mock import MagicMock, patch

import pytest


class TestSwitchToAnthropicAuthInstructions:
    """Test that _switch_to_anthropic() shows actionable auth instructions."""

    def test_switch_to_anthropic_shows_auth_instructions(self, tmp_path):
        """Verify output contains 'claude auth login' and '/login' guidance."""
        from claude_mpm.cli.commands.provider import ProviderCommand

        # Create a minimal config file so save succeeds
        config_dir = tmp_path / ".claude-mpm"
        config_dir.mkdir(parents=True)

        args = MagicMock()
        args.config = str(config_dir / "configuration.yaml")
        args.model = None

        command = ProviderCommand()

        # Remove ANTHROPIC_API_KEY so the guidance block triggers
        env = os.environ.copy()
        env.pop("ANTHROPIC_API_KEY", None)

        captured = StringIO()
        with (
            patch.dict(os.environ, env, clear=True),
            patch("claude_mpm.cli.commands.provider.console") as mock_console,
        ):
            # Collect all print calls
            printed_lines: list[str] = []
            mock_console.print = lambda *a, **kw: printed_lines.append(
                " ".join(str(x) for x in a)
            )

            command._switch_to_anthropic(args)

        output = "\n".join(printed_lines)
        assert "claude auth login" in output, (
            f"Expected 'claude auth login' in output, got:\n{output}"
        )
        assert "/login" in output, f"Expected '/login' in output, got:\n{output}"


class TestCheckAnthropicAuth:
    """Test the _check_anthropic_auth pre-flight check in startup.py."""

    def test_check_anthropic_auth_with_api_key_no_warning(self, capsys):
        """When ANTHROPIC_API_KEY is set, no warning should be printed."""
        from claude_mpm.cli.startup import _check_anthropic_auth

        with patch.dict(
            os.environ,
            {"ANTHROPIC_API_KEY": "sk-ant-test123"},  # pragma: allowlist secret
            clear=False,
        ):
            _check_anthropic_auth(env_changes={})

        captured = capsys.readouterr()
        assert "Not authenticated" not in captured.out

    def test_check_anthropic_auth_not_anthropic_backend(self, capsys):
        """When backend is bedrock, no auth check should run."""
        from claude_mpm.cli.startup import _check_anthropic_auth

        env = os.environ.copy()
        env.pop("ANTHROPIC_API_KEY", None)
        env["CLAUDE_CODE_USE_BEDROCK"] = "1"

        with patch.dict(os.environ, env, clear=True):
            _check_anthropic_auth(env_changes={})

        captured = capsys.readouterr()
        assert "Not authenticated" not in captured.out

    def test_check_anthropic_auth_logged_in_no_warning(self, capsys):
        """When 'claude auth status' reports logged in, no warning."""
        from claude_mpm.cli.startup import _check_anthropic_auth

        env = os.environ.copy()
        env.pop("ANTHROPIC_API_KEY", None)
        env.pop("CLAUDE_CODE_USE_BEDROCK", None)

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "You are logged in as user@example.com"

        with (
            patch.dict(os.environ, env, clear=True),
            patch("subprocess.run", return_value=mock_result),
            patch("sys.stdout") as mock_stdout,
        ):
            mock_stdout.isatty.return_value = True
            _check_anthropic_auth(env_changes={})

        # Since we mocked sys.stdout, check that print was not called with warning
        # Re-run without mocking stdout to verify via capsys
        with (
            patch.dict(os.environ, env, clear=True),
            patch("subprocess.run", return_value=mock_result),
        ):
            _check_anthropic_auth(env_changes={})

        captured = capsys.readouterr()
        assert "Not authenticated" not in captured.out

    def test_check_anthropic_auth_not_logged_in_shows_warning(self, capsys):
        """When auth status fails and no API key, show warning."""
        from claude_mpm.cli.startup import _check_anthropic_auth

        env = os.environ.copy()
        env.pop("ANTHROPIC_API_KEY", None)
        env.pop("CLAUDE_CODE_USE_BEDROCK", None)

        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""

        with (
            patch.dict(os.environ, env, clear=True),
            patch("subprocess.run", return_value=mock_result),
            patch("sys.stdout.isatty", return_value=True),
        ):
            _check_anthropic_auth(env_changes={})

        captured = capsys.readouterr()
        assert "Not authenticated" in captured.out
        assert "claude auth login" in captured.out

    def test_check_anthropic_auth_none_env_changes_skips(self, capsys):
        """When env_changes is None (config load failed), skip check."""
        from claude_mpm.cli.startup import _check_anthropic_auth

        env = os.environ.copy()
        env.pop("ANTHROPIC_API_KEY", None)
        env.pop("CLAUDE_CODE_USE_BEDROCK", None)

        with patch.dict(os.environ, env, clear=True):
            _check_anthropic_auth(env_changes=None)

        captured = capsys.readouterr()
        assert "Not authenticated" not in captured.out

    def test_check_anthropic_auth_subprocess_timeout_shows_warning(self, capsys):
        """When claude auth status times out, show warning (fail-open)."""
        from claude_mpm.cli.startup import _check_anthropic_auth

        env = os.environ.copy()
        env.pop("ANTHROPIC_API_KEY", None)
        env.pop("CLAUDE_CODE_USE_BEDROCK", None)

        with (
            patch.dict(os.environ, env, clear=True),
            patch("subprocess.run", side_effect=subprocess.TimeoutExpired("claude", 5)),
            patch("sys.stdout.isatty", return_value=True),
        ):
            _check_anthropic_auth(env_changes={})

        captured = capsys.readouterr()
        assert "Not authenticated" in captured.out

    def test_check_anthropic_auth_claude_not_found_shows_warning(self, capsys):
        """When claude binary not found, show warning (fail-open)."""
        from claude_mpm.cli.startup import _check_anthropic_auth

        env = os.environ.copy()
        env.pop("ANTHROPIC_API_KEY", None)
        env.pop("CLAUDE_CODE_USE_BEDROCK", None)

        with (
            patch.dict(os.environ, env, clear=True),
            patch("subprocess.run", side_effect=FileNotFoundError),
            patch("sys.stdout.isatty", return_value=True),
        ):
            _check_anthropic_auth(env_changes={})

        captured = capsys.readouterr()
        assert "Not authenticated" in captured.out

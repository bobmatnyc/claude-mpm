"""Tests for Anthropic authentication guidance and pre-flight checks."""

import os
import subprocess
from io import StringIO
from unittest.mock import MagicMock, patch

import pytest
import yaml


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


class TestSwitchToAnthropicLogin:
    """Tests for the anthropic-login provider subcommand."""

    def _make_args(self, config_path: str) -> MagicMock:
        args = MagicMock()
        args.config = config_path
        args.model = None
        return args

    def test_switch_to_anthropic_login_clears_env_vars(self, tmp_path):
        """ANTHROPIC_API_KEY is removed from os.environ after switch."""
        from claude_mpm.cli.commands.provider import ProviderCommand

        config_dir = tmp_path / ".claude-mpm"
        config_dir.mkdir(parents=True)

        args = self._make_args(str(config_dir / "configuration.yaml"))
        command = ProviderCommand()

        env = os.environ.copy()
        env["ANTHROPIC_API_KEY"] = "sk-ant-stale123"  # pragma: allowlist secret
        env["CLAUDE_CODE_USE_BEDROCK"] = "1"
        env["ANTHROPIC_BEDROCK_BASE_URL"] = "https://bedrock.example.com"

        mock_login = MagicMock(returncode=0)
        mock_status = MagicMock(
            returncode=0,
            stdout="You are logged in as user@example.com",
        )

        with (
            patch.dict(os.environ, env, clear=True),
            patch("claude_mpm.cli.commands.provider.console"),
            patch(
                "claude_mpm.cli.commands.provider.subprocess.run",
                side_effect=[mock_login, mock_status],
            ),
        ):
            command._switch_to_anthropic_login(args)

            # Verify env vars were cleared
            assert "ANTHROPIC_API_KEY" not in os.environ  # pragma: allowlist secret
            assert "CLAUDE_CODE_USE_BEDROCK" not in os.environ
            assert "ANTHROPIC_BEDROCK_BASE_URL" not in os.environ

    def test_switch_to_anthropic_login_clears_env_local(self, tmp_path, monkeypatch):
        """ANTHROPIC_API_KEY line is removed from .env.local."""
        from claude_mpm.cli.commands.provider import ProviderCommand

        config_dir = tmp_path / ".claude-mpm"
        config_dir.mkdir(parents=True)
        args = self._make_args(str(config_dir / "configuration.yaml"))

        # Create .env.local with API key and other content
        env_local = tmp_path / ".env.local"
        env_local.write_text(
            "OTHER_VAR=keep_this\n"
            "ANTHROPIC_API_KEY=sk-ant-remove-me\n"  # pragma: allowlist secret
            "ANOTHER_VAR=also_keep\n"
        )

        monkeypatch.chdir(tmp_path)
        command = ProviderCommand()

        mock_login = MagicMock(returncode=0)
        mock_status = MagicMock(returncode=0, stdout="logged in")

        env = os.environ.copy()
        env.pop("ANTHROPIC_API_KEY", None)

        with (
            patch.dict(os.environ, env, clear=True),
            patch("claude_mpm.cli.commands.provider.console"),
            patch(
                "claude_mpm.cli.commands.provider.subprocess.run",
                side_effect=[mock_login, mock_status],
            ),
        ):
            command._switch_to_anthropic_login(args)

        content = env_local.read_text()
        assert "ANTHROPIC_API_KEY" not in content  # pragma: allowlist secret
        assert "OTHER_VAR=keep_this" in content
        assert "ANOTHER_VAR=also_keep" in content

    def test_switch_to_anthropic_login_triggers_login(self, tmp_path):
        """subprocess.run is called with ['claude', 'auth', 'login']."""
        from claude_mpm.cli.commands.provider import ProviderCommand

        config_dir = tmp_path / ".claude-mpm"
        config_dir.mkdir(parents=True)
        args = self._make_args(str(config_dir / "configuration.yaml"))
        command = ProviderCommand()

        mock_login = MagicMock(returncode=0)
        mock_status = MagicMock(returncode=0, stdout="logged in")

        env = os.environ.copy()
        env.pop("ANTHROPIC_API_KEY", None)

        with (
            patch.dict(os.environ, env, clear=True),
            patch("claude_mpm.cli.commands.provider.console"),
            patch(
                "claude_mpm.cli.commands.provider.subprocess.run",
                side_effect=[mock_login, mock_status],
            ) as mock_run,
        ):
            command._switch_to_anthropic_login(args)

        # First call should be claude auth login (interactive, no capture_output)
        first_call = mock_run.call_args_list[0]
        assert first_call[0][0] == ["claude", "auth", "login"]
        # Should NOT have capture_output=True (must be interactive)
        assert first_call[1].get("capture_output") is not True

    def test_switch_to_anthropic_login_shows_success(self, tmp_path):
        """On successful auth, output contains success message."""
        from claude_mpm.cli.commands.provider import ProviderCommand

        config_dir = tmp_path / ".claude-mpm"
        config_dir.mkdir(parents=True)
        args = self._make_args(str(config_dir / "configuration.yaml"))
        command = ProviderCommand()

        mock_login = MagicMock(returncode=0)
        mock_status = MagicMock(
            returncode=0,
            stdout="You are logged in as user@example.com",
        )

        env = os.environ.copy()
        env.pop("ANTHROPIC_API_KEY", None)

        printed: list[str] = []
        with (
            patch.dict(os.environ, env, clear=True),
            patch("claude_mpm.cli.commands.provider.console") as mock_console,
            patch(
                "claude_mpm.cli.commands.provider.subprocess.run",
                side_effect=[mock_login, mock_status],
            ),
        ):
            mock_console.print = lambda *a, **kw: printed.append(
                " ".join(str(x) for x in a)
            )
            result = command._switch_to_anthropic_login(args)

        output = "\n".join(printed)
        assert result.exit_code == 0
        assert "Authenticated via Claude.ai" in output

    def test_switch_to_anthropic_login_handles_login_failure(self, tmp_path):
        """On failed auth, output contains failure message."""
        from claude_mpm.cli.commands.provider import ProviderCommand

        config_dir = tmp_path / ".claude-mpm"
        config_dir.mkdir(parents=True)
        args = self._make_args(str(config_dir / "configuration.yaml"))
        command = ProviderCommand()

        mock_login = MagicMock(returncode=1)
        mock_status = MagicMock(returncode=1, stdout="")

        env = os.environ.copy()
        env.pop("ANTHROPIC_API_KEY", None)

        printed: list[str] = []
        with (
            patch.dict(os.environ, env, clear=True),
            patch("claude_mpm.cli.commands.provider.console") as mock_console,
            patch(
                "claude_mpm.cli.commands.provider.subprocess.run",
                side_effect=[mock_login, mock_status],
            ),
        ):
            mock_console.print = lambda *a, **kw: printed.append(
                " ".join(str(x) for x in a)
            )
            result = command._switch_to_anthropic_login(args)

        output = "\n".join(printed)
        assert result.exit_code != 0
        assert "Authentication failed" in output
        assert "claude auth login" in output

    def test_switch_to_anthropic_login_removes_api_key_from_config(self, tmp_path):
        """api_key field in configuration.yaml is removed."""
        from claude_mpm.cli.commands.provider import ProviderCommand

        config_dir = tmp_path / ".claude-mpm"
        config_dir.mkdir(parents=True)
        config_path = config_dir / "configuration.yaml"

        # Write a config with api_key field
        config_data = {
            "api_provider": {
                "backend": "anthropic",
                "api_key": "sk-ant-stale",  # pragma: allowlist secret
                "anthropic": {
                    "model": "sonnet",
                    "api_key": "sk-ant-nested",  # pragma: allowlist secret
                },
            }
        }
        with open(config_path, "w") as f:
            yaml.dump(config_data, f)

        args = self._make_args(str(config_path))
        command = ProviderCommand()

        mock_login = MagicMock(returncode=0)
        mock_status = MagicMock(returncode=0, stdout="logged in")

        env = os.environ.copy()
        env.pop("ANTHROPIC_API_KEY", None)

        with (
            patch.dict(os.environ, env, clear=True),
            patch("claude_mpm.cli.commands.provider.console"),
            patch(
                "claude_mpm.cli.commands.provider.subprocess.run",
                side_effect=[mock_login, mock_status],
            ),
        ):
            command._switch_to_anthropic_login(args)

        # Verify api_key fields are removed
        with open(config_path) as f:
            saved = yaml.safe_load(f)

        api_provider = saved.get("api_provider", {})
        assert "api_key" not in api_provider
        assert "api_key" not in api_provider.get("anthropic", {})

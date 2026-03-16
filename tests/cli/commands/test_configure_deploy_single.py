"""Phase 1a: Tests for _deploy_single_agent() using deploy_agent_file().

WHY: Verifies that _deploy_single_agent() now delegates to the shared
deploy_agent_file() utility rather than using shutil.copy2() directly.
This ensures all agent deployment paths use the same code for consistent
filename normalization, frontmatter injection, and legacy cleanup.

DESIGN: deploy_agent_file is imported locally inside _deploy_single_agent,
so we patch it at its canonical source location
(claude_mpm.services.agents.deployment_utils.deploy_agent_file).
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from claude_mpm.cli.commands.configure import AgentConfig, ConfigureCommand

# Canonical patch target — import is done locally inside the method, so we
# patch the function where it lives, not where it's imported.
_DEPLOY_FN = "claude_mpm.services.agents.deployment_utils.deploy_agent_file"


def _make_agent_config(
    source_file: Path, full_agent_id: str = "engineer"
) -> AgentConfig:
    """Build a minimal AgentConfig with source_dict for remote-agent path."""
    cfg = MagicMock(spec=AgentConfig)
    cfg.name = full_agent_id
    cfg.full_agent_id = full_agent_id
    cfg.source_dict = {"source_file": str(source_file)}
    return cfg


class TestConfigureDeploySingleAgent:
    """Verify _deploy_single_agent() delegates to deploy_agent_file()."""

    @pytest.fixture
    def configure_cmd(self, tmp_path):
        """Return a ConfigureCommand with console and _ctx mocked."""
        with patch("claude_mpm.cli.commands.configure.Console"):
            cmd = ConfigureCommand.__new__(ConfigureCommand)
            cmd.console = MagicMock()
            cmd.logger = MagicMock()
            agents_dir = tmp_path / "agents"
            agents_dir.mkdir(parents=True, exist_ok=True)
            ctx = MagicMock()
            ctx.agents_dir = agents_dir
            cmd._ctx = ctx
            return cmd

    # ------------------------------------------------------------------
    # Happy-path: deploy_agent_file is called, not shutil.copy2
    # ------------------------------------------------------------------

    @patch(_DEPLOY_FN)
    def test_calls_deploy_agent_file_not_shutil(
        self, mock_deploy_fn, configure_cmd, tmp_path
    ):
        """_deploy_single_agent must call deploy_agent_file, not shutil.copy2."""
        source = tmp_path / "engineer.md"
        source.write_text("---\nname: Engineer\n---\n# Engineer\n", encoding="utf-8")

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.action = "deployed"
        mock_deploy_fn.return_value = mock_result

        agent = _make_agent_config(source_file=source, full_agent_id="engineer")
        result = configure_cmd._deploy_single_agent(agent, show_feedback=False)

        assert result is True
        mock_deploy_fn.assert_called_once()

    @patch(_DEPLOY_FN)
    def test_passes_force_true(self, mock_deploy_fn, configure_cmd, tmp_path):
        """deploy_agent_file must be called with force=True."""
        source = tmp_path / "engineer.md"
        source.write_text("---\nname: Engineer\n---\n# Engineer\n", encoding="utf-8")

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.action = "deployed"
        mock_deploy_fn.return_value = mock_result

        agent = _make_agent_config(source_file=source, full_agent_id="engineer")
        configure_cmd._deploy_single_agent(agent, show_feedback=False)

        call_kwargs = mock_deploy_fn.call_args
        assert call_kwargs is not None, "deploy_agent_file was not called"
        assert call_kwargs.kwargs.get("force") is True, (
            f"Expected force=True, got: {call_kwargs.kwargs}"
        )

    @patch(_DEPLOY_FN)
    def test_passes_source_file_and_deployment_dir(
        self, mock_deploy_fn, configure_cmd, tmp_path
    ):
        """deploy_agent_file receives the correct source_file and deployment_dir."""
        source = tmp_path / "python-engineer.md"
        source.write_text(
            "---\nname: Python Engineer\n---\n# Python\n", encoding="utf-8"
        )

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.action = "deployed"
        mock_deploy_fn.return_value = mock_result

        agent = _make_agent_config(source_file=source, full_agent_id="python-engineer")
        configure_cmd._deploy_single_agent(agent, show_feedback=False)

        call_kwargs = mock_deploy_fn.call_args
        assert call_kwargs is not None
        assert call_kwargs.kwargs.get("source_file") == source
        assert call_kwargs.kwargs.get("deployment_dir") == configure_cmd._ctx.agents_dir

    # ------------------------------------------------------------------
    # Failure propagation: deploy_agent_file failure → returns False
    # ------------------------------------------------------------------

    @patch(_DEPLOY_FN)
    def test_returns_false_on_deploy_failure(
        self, mock_deploy_fn, configure_cmd, tmp_path
    ):
        """When deploy_agent_file returns success=False, method returns False."""
        source = tmp_path / "engineer.md"
        source.write_text("---\nname: Engineer\n---\n# Engineer\n", encoding="utf-8")

        mock_result = MagicMock()
        mock_result.success = False
        mock_result.error = "Permission denied"
        mock_deploy_fn.return_value = mock_result

        agent = _make_agent_config(source_file=source, full_agent_id="engineer")
        result = configure_cmd._deploy_single_agent(agent, show_feedback=False)

        assert result is False

    @patch(_DEPLOY_FN)
    def test_failure_prints_error_when_show_feedback(
        self, mock_deploy_fn, configure_cmd, tmp_path
    ):
        """On failure with show_feedback=True, an error message is printed."""
        source = tmp_path / "engineer.md"
        source.write_text("---\nname: Engineer\n---\n# Engineer\n", encoding="utf-8")

        mock_result = MagicMock()
        mock_result.success = False
        mock_result.error = "Permission denied"
        mock_deploy_fn.return_value = mock_result

        agent = _make_agent_config(source_file=source, full_agent_id="engineer")
        result = configure_cmd._deploy_single_agent(agent, show_feedback=True)

        assert result is False
        configure_cmd.console.print.assert_called()
        printed = " ".join(
            str(a) for c in configure_cmd.console.print.call_args_list for a in c[0]
        )
        assert any(
            word in printed
            for word in ("Failed", "failed", "Permission", "Error", "error")
        )

    # ------------------------------------------------------------------
    # Missing source file: early return before calling deploy_agent_file
    # ------------------------------------------------------------------

    @patch(_DEPLOY_FN)
    def test_missing_source_file_returns_false_without_calling_deploy(
        self, mock_deploy_fn, configure_cmd, tmp_path
    ):
        """If source_file does not exist, returns False without calling deploy_agent_file."""
        missing = tmp_path / "nonexistent.md"
        # Do NOT create the file

        agent = _make_agent_config(source_file=missing, full_agent_id="nonexistent")
        result = configure_cmd._deploy_single_agent(agent, show_feedback=False)

        assert result is False
        mock_deploy_fn.assert_not_called()

    # ------------------------------------------------------------------
    # No source_dict: falls through to legacy path (returns False)
    # ------------------------------------------------------------------

    @patch(_DEPLOY_FN)
    def test_no_source_dict_returns_false(self, mock_deploy_fn, configure_cmd):
        """Agent with no source_dict returns False (legacy path not implemented)."""
        cfg = MagicMock(spec=AgentConfig)
        cfg.name = "local-agent"
        cfg.full_agent_id = "local-agent"
        cfg.source_dict = None  # triggers the legacy branch

        result = configure_cmd._deploy_single_agent(cfg, show_feedback=False)

        assert result is False
        mock_deploy_fn.assert_not_called()

    # ------------------------------------------------------------------
    # cleanup_legacy and ensure_frontmatter are both passed as True
    # ------------------------------------------------------------------

    @patch(_DEPLOY_FN)
    def test_passes_cleanup_legacy_and_ensure_frontmatter(
        self, mock_deploy_fn, configure_cmd, tmp_path
    ):
        """deploy_agent_file is called with cleanup_legacy=True and ensure_frontmatter=True."""
        source = tmp_path / "engineer.md"
        source.write_text("---\nname: Engineer\n---\n# Engineer\n", encoding="utf-8")

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.action = "deployed"
        mock_deploy_fn.return_value = mock_result

        agent = _make_agent_config(source_file=source, full_agent_id="engineer")
        configure_cmd._deploy_single_agent(agent, show_feedback=False)

        call_kwargs = mock_deploy_fn.call_args
        assert call_kwargs is not None
        assert call_kwargs.kwargs.get("cleanup_legacy") is True
        assert call_kwargs.kwargs.get("ensure_frontmatter") is True

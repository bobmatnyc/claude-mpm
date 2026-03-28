"""Tests for output style injection into SDK-based sessions.

Verifies that SessionWorker and SDKAgentRunner inject the configured
outputStyle from ~/.claude/settings.json into the system prompt for
SDK sessions that don't load user settings automatically.
"""

from __future__ import annotations

import json
from pathlib import Path  # noqa: TC003
from unittest.mock import MagicMock, patch  # noqa: TC003

import pytest

# ---------------------------------------------------------------------------
# SessionWorker._get_output_style_content tests
# ---------------------------------------------------------------------------


class TestSessionWorkerOutputStyleInjection:
    """Test output style injection in SessionWorker."""

    def _make_worker(self) -> MagicMock:
        """Create a minimal SessionWorker-like object for testing the method."""
        from claude_mpm.services.channels.session_worker import SessionWorker

        # We only need the method, so create a bare instance via __new__
        # and set up minimal attributes
        worker = object.__new__(SessionWorker)
        return worker

    def test_output_style_injection_returns_content(self, tmp_path: Path) -> None:
        """When outputStyle is configured and valid, content is returned."""
        worker = self._make_worker()

        settings = {"outputStyle": "claude_mpm"}
        settings_path = tmp_path / ".claude" / "settings.json"
        settings_path.parent.mkdir(parents=True)
        settings_path.write_text(json.dumps(settings))

        fake_content = "# Test Style Content\nSome instructions here."

        with (
            patch("pathlib.Path.home", return_value=tmp_path),
            patch(
                "claude_mpm.core.output_style_manager.OutputStyleManager.get_injectable_content",
                return_value=fake_content,
            ),
        ):
            result = worker._get_output_style_content()

        assert result == fake_content

    def test_no_output_style_configured(self, tmp_path: Path) -> None:
        """When outputStyle is not set in settings, returns None."""
        worker = self._make_worker()

        settings = {"someOtherSetting": True}
        settings_path = tmp_path / ".claude" / "settings.json"
        settings_path.parent.mkdir(parents=True)
        settings_path.write_text(json.dumps(settings))

        with patch("pathlib.Path.home", return_value=tmp_path):
            result = worker._get_output_style_content()

        assert result is None

    def test_output_style_file_missing(self, tmp_path: Path) -> None:
        """When get_injectable_content returns None, returns None gracefully."""
        worker = self._make_worker()

        settings = {"outputStyle": "claude_mpm"}
        settings_path = tmp_path / ".claude" / "settings.json"
        settings_path.parent.mkdir(parents=True)
        settings_path.write_text(json.dumps(settings))

        with (
            patch("pathlib.Path.home", return_value=tmp_path),
            patch(
                "claude_mpm.core.output_style_manager.OutputStyleManager.get_injectable_content",
                return_value=None,
            ),
        ):
            result = worker._get_output_style_content()

        assert result is None

    def test_settings_file_missing(self, tmp_path: Path) -> None:
        """When ~/.claude/settings.json doesn't exist, returns None without crash."""
        worker = self._make_worker()

        with patch("pathlib.Path.home", return_value=tmp_path):
            result = worker._get_output_style_content()

        assert result is None

    def test_unknown_style_id_returns_none(self, tmp_path: Path) -> None:
        """When outputStyle is an unknown ID, returns None."""
        worker = self._make_worker()

        settings = {"outputStyle": "some_unknown_style"}
        settings_path = tmp_path / ".claude" / "settings.json"
        settings_path.parent.mkdir(parents=True)
        settings_path.write_text(json.dumps(settings))

        with patch("pathlib.Path.home", return_value=tmp_path):
            result = worker._get_output_style_content()

        assert result is None

    def test_teacher_style_injection(self, tmp_path: Path) -> None:
        """Teaching style is resolved correctly."""
        worker = self._make_worker()

        settings = {"outputStyle": "claude_mpm_teacher"}
        settings_path = tmp_path / ".claude" / "settings.json"
        settings_path.parent.mkdir(parents=True)
        settings_path.write_text(json.dumps(settings))

        fake_content = "# Teaching Style\nTeach adaptively."

        with (
            patch("pathlib.Path.home", return_value=tmp_path),
            patch(
                "claude_mpm.core.output_style_manager.OutputStyleManager.get_injectable_content",
                return_value=fake_content,
            ) as mock_get,
        ):
            result = worker._get_output_style_content()

        assert result == fake_content
        mock_get.assert_called_once_with(style="teaching")

    def test_research_style_injection(self, tmp_path: Path) -> None:
        """Research style is resolved correctly."""
        worker = self._make_worker()

        settings = {"outputStyle": "claude_mpm_research"}
        settings_path = tmp_path / ".claude" / "settings.json"
        settings_path.parent.mkdir(parents=True)
        settings_path.write_text(json.dumps(settings))

        fake_content = "# Research Style"

        with (
            patch("pathlib.Path.home", return_value=tmp_path),
            patch(
                "claude_mpm.core.output_style_manager.OutputStyleManager.get_injectable_content",
                return_value=fake_content,
            ) as mock_get,
        ):
            result = worker._get_output_style_content()

        assert result == fake_content
        mock_get.assert_called_once_with(style="research")

    def test_exception_in_style_loading_returns_none(self, tmp_path: Path) -> None:
        """Exceptions during style loading are caught gracefully."""
        worker = self._make_worker()

        settings = {"outputStyle": "claude_mpm"}
        settings_path = tmp_path / ".claude" / "settings.json"
        settings_path.parent.mkdir(parents=True)
        settings_path.write_text(json.dumps(settings))

        with (
            patch("pathlib.Path.home", return_value=tmp_path),
            patch(
                "claude_mpm.core.output_style_manager.OutputStyleManager.get_injectable_content",
                side_effect=FileNotFoundError("style source not found"),
            ),
        ):
            result = worker._get_output_style_content()

        assert result is None


# ---------------------------------------------------------------------------
# SDKAgentRunner._get_output_style_content tests
# ---------------------------------------------------------------------------


class TestSDKAgentRunnerOutputStyleInjection:
    """Test output style injection in SDKAgentRunner."""

    def test_build_options_injects_style(self, tmp_path: Path) -> None:
        """_build_options prepends style content to the system prompt."""
        from claude_mpm.services.agents.sdk_runtime import SDKAgentRunner

        runner = SDKAgentRunner(system_prompt="Base prompt.")
        fake_content = "# Style Header\nStyle instructions."

        with patch.object(
            runner, "_get_output_style_content", return_value=fake_content
        ):
            options = runner._build_options()

        assert options.system_prompt.startswith("# Style Header")
        assert "Base prompt." in options.system_prompt

    def test_build_options_no_style_leaves_prompt_unchanged(self) -> None:
        """_build_options preserves system prompt when no style is configured."""
        from claude_mpm.services.agents.sdk_runtime import SDKAgentRunner

        runner = SDKAgentRunner(system_prompt="Original prompt.")

        with patch.object(runner, "_get_output_style_content", return_value=None):
            options = runner._build_options()

        assert options.system_prompt == "Original prompt."

    def test_build_options_style_only_when_no_system_prompt(self) -> None:
        """_build_options uses only style content when no system prompt set."""
        from claude_mpm.services.agents.sdk_runtime import SDKAgentRunner

        runner = SDKAgentRunner()
        fake_content = "# Style Only"

        with patch.object(
            runner, "_get_output_style_content", return_value=fake_content
        ):
            options = runner._build_options()

        assert options.system_prompt == "# Style Only"

    def test_style_id_mapping(self, tmp_path: Path) -> None:
        """Verify the reverse mapping from style IDs to types."""
        from claude_mpm.core.output_style_manager import _STYLE_ID_TO_TYPE

        assert _STYLE_ID_TO_TYPE["claude_mpm"] == "professional"
        assert _STYLE_ID_TO_TYPE["claude_mpm_teacher"] == "teaching"
        assert _STYLE_ID_TO_TYPE["claude_mpm_research"] == "research"

    def test_settings_file_missing_returns_none(self, tmp_path: Path) -> None:
        """No crash when settings.json is missing."""
        from claude_mpm.services.agents.sdk_runtime import SDKAgentRunner

        runner = SDKAgentRunner()

        with patch("pathlib.Path.home", return_value=tmp_path):
            result = runner._get_output_style_content()

        assert result is None

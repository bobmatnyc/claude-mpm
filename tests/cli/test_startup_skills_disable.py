"""Tests for issue #492: skill auto-deploy disable mechanisms.

Verifies the three fixes:
1. ``skills.auto_deploy: false`` in YAML config actually skips deployment
   (previously the import path was wrong, the ImportError was swallowed,
   and the setting silently did nothing).
2. ``CLAUDE_MPM_DISABLE_AUTO_DEPLOY_PM_SKILLS`` env var skips PM skill
   deployment / verification (previously only honored by the now-deleted
   ``optimized_startup.py``).
3. When the claude-mpm Claude Code plugin is detected in
   ``~/.claude/plugins/installed_plugins.json``, deployment is skipped to
   avoid duplicate skills appearing in Claude Code.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def bypass_ttl():
    """Force the deploy path to run regardless of TTL state."""
    with patch("claude_mpm.cli.startup._is_sync_fresh", return_value=False):
        yield


@pytest.fixture(autouse=True)
def no_plugin_by_default(tmp_path, monkeypatch):
    """Point HOME at an empty tmp dir so plugin detection returns False
    unless a test explicitly writes a plugins file."""
    monkeypatch.setenv("HOME", str(tmp_path))
    # Path.home() reads HOME on POSIX
    yield


class TestPluginDetection:
    def test_returns_false_when_file_missing(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path))
        from claude_mpm.cli.startup import _is_claude_mpm_plugin_installed

        assert _is_claude_mpm_plugin_installed() is False

    def test_detects_plugin_in_real_schema(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path))
        plugins_dir = tmp_path / ".claude" / "plugins"
        plugins_dir.mkdir(parents=True)
        (plugins_dir / "installed_plugins.json").write_text(
            json.dumps(
                {
                    "version": 2,
                    "plugins": {
                        "claude-mpm@claude-mpm-marketplace": [
                            {"scope": "user", "version": "5.11.4"}
                        ]
                    },
                }
            )
        )
        from claude_mpm.cli.startup import _is_claude_mpm_plugin_installed

        assert _is_claude_mpm_plugin_installed() is True

    def test_returns_false_for_unrelated_plugins(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path))
        plugins_dir = tmp_path / ".claude" / "plugins"
        plugins_dir.mkdir(parents=True)
        (plugins_dir / "installed_plugins.json").write_text(
            json.dumps({"plugins": {"pyright-lsp@official": [{"scope": "user"}]}})
        )
        from claude_mpm.cli.startup import _is_claude_mpm_plugin_installed

        assert _is_claude_mpm_plugin_installed() is False

    def test_handles_corrupt_json_gracefully(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path))
        plugins_dir = tmp_path / ".claude" / "plugins"
        plugins_dir.mkdir(parents=True)
        (plugins_dir / "installed_plugins.json").write_text("{not valid json")
        from claude_mpm.cli.startup import _is_claude_mpm_plugin_installed

        # Conservative behavior: failure to parse means we do NOT suppress deploy.
        assert _is_claude_mpm_plugin_installed() is False


class TestDeployBundledSkillsKillSwitches:
    @patch("claude_mpm.skills.skills_service.SkillsService")
    def test_env_var_skips_deployment(self, mock_service_cls, monkeypatch):
        monkeypatch.setenv("CLAUDE_MPM_DISABLE_AUTO_DEPLOY_PM_SKILLS", "1")
        from claude_mpm.cli.startup import deploy_bundled_skills

        deploy_bundled_skills(force_deploy=True)
        mock_service_cls.assert_not_called()

    @patch("claude_mpm.cli.startup._is_claude_mpm_plugin_installed", return_value=True)
    @patch("claude_mpm.skills.skills_service.SkillsService")
    def test_plugin_present_skips_deployment(
        self, mock_service_cls, _mock_plugin, monkeypatch
    ):
        monkeypatch.delenv("CLAUDE_MPM_DISABLE_AUTO_DEPLOY_PM_SKILLS", raising=False)
        from claude_mpm.cli.startup import deploy_bundled_skills

        deploy_bundled_skills(force_deploy=True)
        mock_service_cls.assert_not_called()

    @patch("claude_mpm.cli.startup._is_claude_mpm_plugin_installed", return_value=False)
    @patch("claude_mpm.skills.skills_service.SkillsService")
    @patch("claude_mpm.core.shared.config_loader.ConfigLoader")
    def test_auto_deploy_false_in_config_skips_deployment(
        self, mock_loader_cls, mock_service_cls, _mock_plugin, monkeypatch
    ):
        """Bug 1: setting skills.auto_deploy: false in YAML must take effect."""
        monkeypatch.delenv("CLAUDE_MPM_DISABLE_AUTO_DEPLOY_PM_SKILLS", raising=False)

        cfg = MagicMock()
        cfg.get.return_value = {"auto_deploy": False}
        loader = MagicMock()
        loader.load_main_config.return_value = cfg
        mock_loader_cls.return_value = loader

        from claude_mpm.cli.startup import deploy_bundled_skills

        deploy_bundled_skills(force_deploy=True)

        loader.load_main_config.assert_called_once()
        mock_service_cls.assert_not_called()

    @patch("claude_mpm.cli.startup._is_claude_mpm_plugin_installed", return_value=False)
    @patch("claude_mpm.skills.skills_service.SkillsService")
    @patch("claude_mpm.core.shared.config_loader.ConfigLoader")
    def test_auto_deploy_true_default_runs_deployment(
        self, mock_loader_cls, mock_service_cls, _mock_plugin, monkeypatch
    ):
        monkeypatch.delenv("CLAUDE_MPM_DISABLE_AUTO_DEPLOY_PM_SKILLS", raising=False)

        cfg = MagicMock()
        cfg.get.return_value = {}  # auto_deploy defaults to True
        loader = MagicMock()
        loader.load_main_config.return_value = cfg
        mock_loader_cls.return_value = loader

        instance = MagicMock()
        instance.deploy_bundled_skills.return_value = {"deployed": [], "errors": []}
        mock_service_cls.return_value = instance

        from claude_mpm.cli.startup import deploy_bundled_skills

        deploy_bundled_skills(force_deploy=True)
        mock_service_cls.assert_called_once()


class TestVerifyAndShowPmSkillsKillSwitches:
    @patch("claude_mpm.services.pm_skills_deployer.PMSkillsDeployerService")
    def test_env_var_skips_verification(self, mock_deployer_cls, monkeypatch):
        monkeypatch.setenv("CLAUDE_MPM_DISABLE_AUTO_DEPLOY_PM_SKILLS", "1")
        from claude_mpm.cli.startup import verify_and_show_pm_skills

        verify_and_show_pm_skills()
        mock_deployer_cls.assert_not_called()

    @patch("claude_mpm.cli.startup._is_claude_mpm_plugin_installed", return_value=True)
    @patch("claude_mpm.services.pm_skills_deployer.PMSkillsDeployerService")
    def test_plugin_present_skips_verification(
        self, mock_deployer_cls, _mock_plugin, monkeypatch
    ):
        monkeypatch.delenv("CLAUDE_MPM_DISABLE_AUTO_DEPLOY_PM_SKILLS", raising=False)
        from claude_mpm.cli.startup import verify_and_show_pm_skills

        verify_and_show_pm_skills()
        mock_deployer_cls.assert_not_called()

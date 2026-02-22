"""Integration tests for auto-configure handler-to-service boundary."""

from pathlib import Path
from unittest.mock import patch

import pytest


class TestAutoConfigManagerInitialization:
    """Test that the handler singleton creates a functional service."""

    def setup_method(self):
        """Reset singleton before each test."""
        import claude_mpm.services.config_api.autoconfig_handler as handler_module

        handler_module._auto_config_manager = None
        handler_module._toolchain_analyzer = None

    def test_get_auto_config_manager_creates_functional_service(self):
        from claude_mpm.services.config_api.autoconfig_handler import (
            _get_auto_config_manager,
        )

        manager = _get_auto_config_manager()
        assert manager is not None
        assert manager._toolchain_analyzer is not None
        assert manager._agent_recommender is not None

    def test_get_auto_config_manager_returns_same_instance(self):
        from claude_mpm.services.config_api.autoconfig_handler import (
            _get_auto_config_manager,
        )

        manager1 = _get_auto_config_manager()
        manager2 = _get_auto_config_manager()
        assert manager1 is manager2

    def test_preview_configuration_succeeds(self, tmp_path):
        from claude_mpm.services.config_api.autoconfig_handler import (
            _get_auto_config_manager,
        )

        project_dir = tmp_path / "test_project"
        project_dir.mkdir()
        (project_dir / "requirements.txt").write_text("fastapi\nuvicorn\n")
        (project_dir / "main.py").write_text(
            "from fastapi import FastAPI\napp = FastAPI()\n"
        )

        manager = _get_auto_config_manager()
        preview = manager.preview_configuration(project_dir, min_confidence=0.5)

        assert preview is not None
        assert isinstance(preview.would_deploy, list)
        assert isinstance(preview.recommendations, list)

    def test_singleton_does_not_cache_on_failure(self):
        import claude_mpm.services.config_api.autoconfig_handler as handler_module

        with patch(
            "claude_mpm.services.agents.recommender.AgentRecommenderService.__init__",
            side_effect=FileNotFoundError("agent_capabilities.yaml not found"),
        ):
            with pytest.raises(FileNotFoundError):
                handler_module._get_auto_config_manager()

        assert handler_module._auto_config_manager is None

    def test_reset_auto_config_manager(self):
        from claude_mpm.services.config_api.autoconfig_handler import (
            _get_auto_config_manager,
            _reset_auto_config_manager,
        )

        _get_auto_config_manager()
        _reset_auto_config_manager()

        import claude_mpm.services.config_api.autoconfig_handler as handler_module

        assert handler_module._auto_config_manager is None

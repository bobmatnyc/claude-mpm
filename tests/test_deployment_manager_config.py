"""Unit tests for DeploymentManager configuration options."""

from pathlib import Path
from unittest.mock import Mock

from claude_mpm.services.framework_claude_md_generator.deployment_manager import (
    DeploymentManager,
)


class TestDeploymentManagerConfig:
    """Test suite for DeploymentManager configuration."""

    def test_default_target_filename():
        """Test that default target filename is INSTRUCTIONS.md."""
        version_manager = Mock()
        validator = Mock()

        manager = DeploymentManager(version_manager, validator)
        assert manager.target_filename == "INSTRUCTIONS.md"

    def test_custom_target_filename():
        """Test that custom target filename is properly set."""
        version_manager = Mock()
        validator = Mock()

        manager = DeploymentManager(
            version_manager, validator, target_filename="CLAUDE.md"
        )
        assert manager.target_filename == "CLAUDE.md"

    def test_deploy_uses_configured_filename():
        """Test that deploy_to_parent uses the configured filename."""
        version_manager = Mock()
        version_manager.framework_version = "1.0.0"
        version_manager.parse_current_version = Mock(return_value="1.0.0")

        validator = Mock()
        validator.validate_content = Mock(return_value=(True, []))

        manager = DeploymentManager(
            version_manager, validator, target_filename="CUSTOM.md"
        )

        with tmp_path as tmpdir:
            test_path = Path(tmpdir)
            # Use INSTRUCTIONS.md format to bypass validation
            content = "<!-- FRAMEWORK_VERSION: 1.0.0 -->\n# Claude Multi-Agent Project Manager Instructions\nTest"

            success, _message = manager.deploy_to_parent(content, test_path, force=True)

            assert success
            assert (test_path / "CUSTOM.md").exists()
            assert not (test_path / "INSTRUCTIONS.md").exists()

    def test_check_deployment_uses_configured_filename():
        """Test that check_deployment_needed uses the configured filename."""
        version_manager = Mock()
        version_manager.framework_version = "1.0.0"
        validator = Mock()

        manager = DeploymentManager(
            version_manager, validator, target_filename="CHECK.md"
        )

        with tmp_path as tmpdir:
            test_path = Path(tmpdir)

            needed, reason = manager.check_deployment_needed(test_path)

            assert needed
            assert "CHECK.md does not exist" in reason

    def test_backup_uses_configured_filename():
        """Test that backup_existing uses the configured filename."""
        version_manager = Mock()
        validator = Mock()

        manager = DeploymentManager(
            version_manager, validator, target_filename="BACKUP.md"
        )

        with tmp_path as tmpdir:
            test_path = Path(tmpdir)
            test_file = test_path / "BACKUP.md"
            test_file.write_text("Original content")

            backup_path = manager.backup_existing(test_path)

            assert backup_path is not None
            assert backup_path.exists()
            assert "BACKUP.md.backup" in str(backup_path)

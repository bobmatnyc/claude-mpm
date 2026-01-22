"""Test that user output style preferences are preserved across deployments.

This test verifies the fix for bug #222 where agent deployment would overwrite
user preferences before Claude Code launch.

Bug: Every run would overwrite activeOutputStyle in settings.json
Fix: Only set activeOutputStyle on first deployment or when explicitly requested
"""

import json
import tempfile
from pathlib import Path

import pytest

from claude_mpm.core.output_style_manager import OutputStyleManager


@pytest.fixture
def temp_home(monkeypatch):
    """Create temporary home directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_path = Path(tmpdir)
        monkeypatch.setenv("HOME", str(temp_path))
        yield temp_path


def test_first_deployment_sets_active_style(temp_home):
    """Test 1: First deployment should set activeOutputStyle."""
    # Create fresh OutputStyleManager (simulates first run)
    manager = OutputStyleManager()

    # Mock version to support output styles
    manager.claude_version = "1.0.83"

    # Deploy all styles
    results = manager.deploy_all_styles(activate_default=True)

    # Verify deployment succeeded
    assert results.get("professional"), "Professional style should deploy successfully"

    # Verify activeOutputStyle was set
    settings_path = temp_home / ".claude" / "settings.json"
    assert settings_path.exists(), "settings.json should be created"

    settings = json.loads(settings_path.read_text())
    assert settings.get("activeOutputStyle") == "Claude MPM", (
        "activeOutputStyle should be set to 'Claude MPM' on first deployment"
    )


def test_second_deployment_preserves_user_choice(temp_home):
    """Test 2: Second deployment should NOT overwrite user's active style choice."""
    # First deployment
    manager = OutputStyleManager()
    manager.claude_version = "1.0.83"
    manager.deploy_all_styles(activate_default=True)

    # User changes their preference to a different style
    settings_path = temp_home / ".claude" / "settings.json"
    settings = json.loads(settings_path.read_text())
    settings["activeOutputStyle"] = "My Custom Style"
    settings_path.write_text(json.dumps(settings, indent=2))

    # Second deployment (simulates running mpm again)
    manager2 = OutputStyleManager()
    manager2.claude_version = "1.0.83"
    manager2.deploy_all_styles(activate_default=True)

    # Verify user's choice was preserved
    settings_after = json.loads(settings_path.read_text())
    assert settings_after.get("activeOutputStyle") == "My Custom Style", (
        "User's custom style choice should be preserved on second deployment"
    )


def test_redeployment_after_file_deletion_sets_active_style(temp_home):
    """Test 3: If style file is deleted, re-deployment should set activeOutputStyle."""
    # First deployment
    manager = OutputStyleManager()
    manager.claude_version = "1.0.83"
    manager.deploy_all_styles(activate_default=True)

    # User deletes the style file
    style_file = temp_home / ".claude" / "output-styles" / "claude-mpm.md"
    style_file.unlink()

    # User had changed their preference
    settings_path = temp_home / ".claude" / "settings.json"
    settings = json.loads(settings_path.read_text())
    settings["activeOutputStyle"] = "My Custom Style"
    settings_path.write_text(json.dumps(settings, indent=2))

    # Re-deployment after file deletion
    manager2 = OutputStyleManager()
    manager2.claude_version = "1.0.83"
    manager2.deploy_all_styles(activate_default=True)

    # Verify activeOutputStyle was reset (because file was deleted - fresh install)
    settings_after = json.loads(settings_path.read_text())
    assert settings_after.get("activeOutputStyle") == "Claude MPM", (
        "activeOutputStyle should be reset when file is re-deployed after deletion"
    )


def test_no_active_style_set_activates_default(temp_home):
    """Test 4: If no activeOutputStyle is set, deployment should set it."""
    # Create settings without activeOutputStyle
    settings_path = temp_home / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_text(json.dumps({"someOtherSetting": "value"}, indent=2))

    # Deploy with existing settings but no activeOutputStyle
    manager = OutputStyleManager()
    manager.claude_version = "1.0.83"
    manager.deploy_all_styles(activate_default=True)

    # Verify activeOutputStyle was set
    settings_after = json.loads(settings_path.read_text())
    assert settings_after.get("activeOutputStyle") == "Claude MPM", (
        "activeOutputStyle should be set when missing"
    )
    assert settings_after.get("someOtherSetting") == "value", (
        "Other settings should be preserved"
    )


def test_deploy_output_style_with_activate_false(temp_home):
    """Test 5: deploy_output_style with activate=False should NOT set activeOutputStyle."""
    manager = OutputStyleManager()
    manager.claude_version = "1.0.83"

    # Deploy without activation
    result = manager.deploy_output_style(style="professional", activate=False)
    assert result, "Deployment should succeed"

    # Verify activeOutputStyle was NOT set
    settings_path = temp_home / ".claude" / "settings.json"
    if settings_path.exists():
        settings = json.loads(settings_path.read_text())
        assert (
            "activeOutputStyle" not in settings
            or settings.get("activeOutputStyle") is None
        ), "activeOutputStyle should NOT be set when activate=False"


def test_deploy_output_style_with_activate_true_on_fresh_install(temp_home):
    """Test 6: deploy_output_style with activate=True should set activeOutputStyle on fresh install."""
    manager = OutputStyleManager()
    manager.claude_version = "1.0.83"

    # Deploy with activation (fresh install)
    result = manager.deploy_output_style(style="professional", activate=True)
    assert result, "Deployment should succeed"

    # Verify activeOutputStyle was set
    settings_path = temp_home / ".claude" / "settings.json"
    assert settings_path.exists(), "settings.json should be created"

    settings = json.loads(settings_path.read_text())
    assert settings.get("activeOutputStyle") == "Claude MPM", (
        "activeOutputStyle should be set on fresh install with activate=True"
    )


def test_deploy_output_style_with_activate_true_preserves_user_choice(temp_home):
    """Test 7: deploy_output_style with activate=True should preserve user choice on re-deployment."""
    manager = OutputStyleManager()
    manager.claude_version = "1.0.83"

    # First deployment
    manager.deploy_output_style(style="professional", activate=True)

    # User changes preference
    settings_path = temp_home / ".claude" / "settings.json"
    settings = json.loads(settings_path.read_text())
    settings["activeOutputStyle"] = "User's Preference"
    settings_path.write_text(json.dumps(settings, indent=2))

    # Second deployment with activate=True
    manager2 = OutputStyleManager()
    manager2.claude_version = "1.0.83"
    manager2.deploy_output_style(style="professional", activate=True)

    # Verify user preference was preserved
    settings_after = json.loads(settings_path.read_text())
    assert settings_after.get("activeOutputStyle") == "User's Preference", (
        "User preference should be preserved even with activate=True on re-deployment"
    )


if __name__ == "__main__":
    pytest.main([__file__, "-xvs"])

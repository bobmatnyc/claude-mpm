"""Test that user output style preferences are preserved across deployments.

This test verifies the fix for bug #222 where agent deployment would overwrite
user preferences before Claude Code launch.

Bug: Every run would overwrite activeOutputStyle in settings.json
Fix: Only set outputStyle on first deployment or when explicitly requested
Migration: Use single outputStyle key instead of dual-key model
"""

import json
import tempfile
from pathlib import Path

import pytest

from claude_mpm.core.output_style_manager import OutputStyleManager


@pytest.fixture
def temp_home(monkeypatch):
    """Create temporary home directory for testing.

    Also chdir into it so the project-local ``.claude/settings.json`` that the
    output-style activation now writes (issue #924) resolves under the same
    temp tree as the HOME-based output-styles directory.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_path = Path(tmpdir)
        monkeypatch.setenv("HOME", str(temp_path))
        monkeypatch.chdir(temp_path)
        yield temp_path


def test_first_deployment_sets_active_style(temp_home):
    """Test 1: First deployment should set outputStyle."""
    # Create fresh OutputStyleManager (simulates first run)
    manager = OutputStyleManager()

    # Mock version to support output styles
    manager.claude_version = "1.0.83"

    # Deploy all styles
    results = manager.deploy_all_styles(activate_default=True)

    # Verify deployment succeeded
    assert results.get("professional"), "Professional style should deploy successfully"

    # Verify outputStyle was set
    settings_path = temp_home / ".claude" / "settings.json"
    assert settings_path.exists(), "settings.json should be created"

    settings = json.loads(settings_path.read_text())
    assert settings.get("outputStyle") == "claude_mpm", (
        "outputStyle should be set to 'claude_mpm' on first deployment"
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
    settings["outputStyle"] = "my_custom_style"
    settings_path.write_text(json.dumps(settings, indent=2))

    # Second deployment (simulates running mpm again)
    manager2 = OutputStyleManager()
    manager2.claude_version = "1.0.83"
    manager2.deploy_all_styles(activate_default=True)

    # Verify user's choice was preserved
    settings_after = json.loads(settings_path.read_text())
    assert settings_after.get("outputStyle") == "my_custom_style", (
        "User's custom style choice should be preserved on second deployment"
    )
    # Verify legacy key was cleaned up
    assert "activeOutputStyle" not in settings_after, (
        "Legacy activeOutputStyle key should be removed during migration"
    )


def test_redeployment_after_file_deletion_sets_active_style(temp_home):
    """Test 3: If style file is deleted, re-deployment should set outputStyle."""
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
    settings["outputStyle"] = "my_custom_style"
    settings_path.write_text(json.dumps(settings, indent=2))

    # Re-deployment after file deletion
    manager2 = OutputStyleManager()
    manager2.claude_version = "1.0.83"
    manager2.deploy_all_styles(activate_default=True)

    # Verify outputStyle was reset (because file was deleted - fresh install)
    settings_after = json.loads(settings_path.read_text())
    assert settings_after.get("outputStyle") == "claude_mpm", (
        "outputStyle should be reset when file is re-deployed after deletion"
    )


def test_no_active_style_set_activates_default(temp_home):
    """Test 4: If no outputStyle is set, deployment should set it."""
    # Create settings without outputStyle
    settings_path = temp_home / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_text(json.dumps({"someOtherSetting": "value"}, indent=2))

    # Deploy with existing settings but no outputStyle
    manager = OutputStyleManager()
    manager.claude_version = "1.0.83"
    manager.deploy_all_styles(activate_default=True)

    # Verify outputStyle was set
    settings_after = json.loads(settings_path.read_text())
    assert settings_after.get("outputStyle") == "claude_mpm", (
        "outputStyle should be set when missing"
    )
    assert settings_after.get("someOtherSetting") == "value", (
        "Other settings should be preserved"
    )


def test_deploy_output_style_with_activate_false(temp_home):
    """Test 5: deploy_output_style with activate=False should NOT set outputStyle."""
    manager = OutputStyleManager()
    manager.claude_version = "1.0.83"

    # Deploy without activation
    result = manager.deploy_output_style(style="professional", activate=False)
    assert result, "Deployment should succeed"

    # Verify outputStyle was NOT set
    settings_path = temp_home / ".claude" / "settings.json"
    if settings_path.exists():
        settings = json.loads(settings_path.read_text())
        assert "outputStyle" not in settings or settings.get("outputStyle") is None, (
            "outputStyle should NOT be set when activate=False"
        )


def test_deploy_output_style_with_activate_true_on_fresh_install(temp_home):
    """Test 6: deploy_output_style with activate=True should set outputStyle on fresh install."""
    manager = OutputStyleManager()
    manager.claude_version = "1.0.83"

    # Deploy with activation (fresh install)
    result = manager.deploy_output_style(style="professional", activate=True)
    assert result, "Deployment should succeed"

    # Verify outputStyle was set
    settings_path = temp_home / ".claude" / "settings.json"
    assert settings_path.exists(), "settings.json should be created"

    settings = json.loads(settings_path.read_text())
    assert settings.get("outputStyle") == "claude_mpm", (
        "outputStyle should be set on fresh install with activate=True"
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
    settings["outputStyle"] = "users_preference"
    settings_path.write_text(json.dumps(settings, indent=2))

    # Second deployment with activate=True
    manager2 = OutputStyleManager()
    manager2.claude_version = "1.0.83"
    manager2.deploy_output_style(style="professional", activate=True)

    # Verify user preference was preserved
    settings_after = json.loads(settings_path.read_text())
    assert settings_after.get("outputStyle") == "users_preference", (
        "User preference should be preserved even with activate=True on re-deployment"
    )
    # Verify legacy key was cleaned up
    assert "activeOutputStyle" not in settings_after, (
        "Legacy activeOutputStyle key should be removed"
    )


def test_settings_file_ends_with_single_trailing_newline(temp_home):
    """Test 8: Regression test for issue #944.

    Every write to ``.claude/settings.json`` via ``_activate_output_style``
    must end with exactly one trailing newline. Writing JSON without a
    trailing newline deterministically diverges from the POSIX-text-file
    convention used elsewhere in the repo, which caused ``cz bump`` to see a
    spurious diff on every release.
    """
    manager = OutputStyleManager()
    manager.claude_version = "1.0.83"
    manager.deploy_all_styles(activate_default=True)

    settings_path = temp_home / ".claude" / "settings.json"
    raw = settings_path.read_text()
    assert raw.endswith("\n"), "settings.json must end with a trailing newline"
    assert not raw.endswith("\n\n"), "settings.json must not end with a blank line"


def test_cleanup_global_output_style_writes_trailing_newline(temp_home):
    """Test 9: Regression test for issue #944.

    ``_cleanup_global_output_style`` (issue #924 self-heal path) writes the
    shared global settings file directly and must also end with exactly one
    trailing newline.
    """
    settings_path = temp_home / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_text(json.dumps({"outputStyle": "claude_mpm"}, indent=2))

    manager = OutputStyleManager()
    manager._cleanup_global_output_style()

    raw = settings_path.read_text()
    assert raw.endswith("\n"), "settings.json must end with a trailing newline"
    assert not raw.endswith("\n\n"), "settings.json must not end with a blank line"
    settings = json.loads(raw)
    assert "outputStyle" not in settings, (
        "MPM-owned outputStyle should be stripped from the global settings file"
    )


if __name__ == "__main__":
    pytest.main([__file__, "-xvs"])

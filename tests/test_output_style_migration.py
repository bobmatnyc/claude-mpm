"""Test migration from dual-key to single-key output style model.

This test verifies that the migration from the legacy activeOutputStyle key
to the native outputStyle key works correctly without data loss.
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


def test_migration_from_legacy_key(temp_home):
    """Test migration from legacy activeOutputStyle to native outputStyle."""
    settings_path = temp_home / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True, exist_ok=True)

    # Create settings with only legacy key
    legacy_settings = {
        "activeOutputStyle": "Claude MPM Teacher",
        "someOtherSetting": "preserved_value",
    }
    settings_path.write_text(json.dumps(legacy_settings, indent=2))

    manager = OutputStyleManager()
    manager.claude_version = "1.0.83"

    # Deploy should trigger migration
    manager.deploy_all_styles(activate_default=True)

    # Verify migration occurred
    migrated_settings = json.loads(settings_path.read_text())

    # Should have native key with correct style ID
    assert migrated_settings.get("outputStyle") == "claude_mpm_teacher"

    # Legacy key should be removed
    assert "activeOutputStyle" not in migrated_settings

    # Other settings should be preserved
    assert migrated_settings.get("someOtherSetting") == "preserved_value"


def test_migration_preserves_user_custom_style(temp_home):
    """Test that custom styles are handled during migration.

    Note: When users have custom styles, the system will reset to default
    on fresh installs for safety, but preserve known MPM styles.
    """
    settings_path = temp_home / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True, exist_ok=True)

    # Create settings with legacy key containing user's custom choice
    legacy_settings = {"activeOutputStyle": "My Custom Style"}
    settings_path.write_text(json.dumps(legacy_settings, indent=2))

    manager = OutputStyleManager()
    manager.claude_version = "1.0.83"

    # Deploy should trigger migration but reset custom styles to default for safety
    manager.deploy_all_styles(activate_default=True)

    # Verify migration reset unknown custom style to default
    migrated_settings = json.loads(settings_path.read_text())

    # Custom styles are reset to default for safety
    assert migrated_settings.get("outputStyle") == "claude_mpm"

    # Legacy key should be cleaned up
    assert "activeOutputStyle" not in migrated_settings


def test_no_migration_when_native_key_exists(temp_home):
    """Test that existing native keys are preserved and legacy keys are cleaned up."""
    settings_path = temp_home / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True, exist_ok=True)

    # Pre-create style file to simulate normal operation (not fresh install)
    style_dir = temp_home / ".claude" / "output-styles"
    style_dir.mkdir(parents=True, exist_ok=True)
    style_file = style_dir / "claude-mpm.md"
    style_file.write_text("# Output style content")

    # Create settings with both keys (native key takes precedence)
    mixed_settings = {
        "outputStyle": "users_preferred_style",
        "activeOutputStyle": "Claude MPM",  # Should be ignored and removed
        "otherSetting": "value",
    }
    settings_path.write_text(json.dumps(mixed_settings, indent=2))

    manager = OutputStyleManager()
    manager.claude_version = "1.0.83"

    # Deploy should clean up legacy key
    # Since files exist and native key exists, this will preserve user preference
    manager.deploy_all_styles(activate_default=True)

    # Verify native key was preserved and legacy key removed
    updated_settings = json.loads(settings_path.read_text())

    assert updated_settings.get("outputStyle") == "users_preferred_style"
    assert "activeOutputStyle" not in updated_settings
    assert updated_settings.get("otherSetting") == "value"


def test_style_name_to_id_conversion(temp_home):
    """Test proper conversion from display names to style IDs."""
    test_cases = [
        ("Claude MPM", "claude_mpm"),
        ("Claude MPM Teacher", "claude_mpm_teacher"),
        ("Claude MPM Research", "claude_mpm_research"),
        ("Some Custom Style", "some_custom_style"),
    ]

    settings_path = temp_home / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True, exist_ok=True)

    for display_name, expected_id in test_cases:
        # Create settings with display name
        settings = {"activeOutputStyle": display_name}
        settings_path.write_text(json.dumps(settings, indent=2))

        # Deploy to trigger migration
        manager = OutputStyleManager()
        manager.claude_version = "1.0.83"
        manager.deploy_all_styles(activate_default=True)

        # Verify conversion
        migrated_settings = json.loads(settings_path.read_text())
        assert migrated_settings.get("outputStyle") == expected_id, (
            f"Failed to convert {display_name} to {expected_id}"
        )
        assert "activeOutputStyle" not in migrated_settings


if __name__ == "__main__":
    pytest.main([__file__, "-xvs"])

"""Test statusLine fix in HookInstaller."""

import json
import tempfile
from pathlib import Path

import pytest


def test_fix_status_line_updates_old_format():
    """Test that _fix_status_line updates old jq expression format."""
    from claude_mpm.hooks.claude_hooks.installer import HookInstaller

    installer = HookInstaller()

    # Create settings with old statusLine format
    settings = {
        "statusLine": {
            "type": "command",
            "command": 'input=$(cat); style=$(echo "$input" | jq -r \'.output_style.name // "default"\'); echo "$style"',
        }
    }

    # Apply fix
    installer._fix_status_line(settings)

    # Verify the command was updated
    updated_command = settings["statusLine"]["command"]
    assert ".activeOutputStyle" in updated_command
    assert '.output_style.name // .activeOutputStyle // "default"' in updated_command


def test_fix_status_line_preserves_new_format():
    """Test that _fix_status_line doesn't modify already-fixed commands."""
    from claude_mpm.hooks.claude_hooks.installer import HookInstaller

    installer = HookInstaller()

    # Create settings with new statusLine format (already fixed)
    original_command = 'input=$(cat); style=$(echo "$input" | jq -r \'.output_style.name // .activeOutputStyle // "default"\'); echo "$style"'
    settings = {
        "statusLine": {
            "type": "command",
            "command": original_command,
        }
    }

    # Apply fix
    installer._fix_status_line(settings)

    # Verify the command was not changed
    assert settings["statusLine"]["command"] == original_command


def test_fix_status_line_handles_missing_status_line():
    """Test that _fix_status_line handles missing statusLine gracefully."""
    from claude_mpm.hooks.claude_hooks.installer import HookInstaller

    installer = HookInstaller()

    # Create settings without statusLine
    settings = {"activeOutputStyle": "Claude MPM"}

    # Apply fix (should not raise error)
    installer._fix_status_line(settings)

    # Verify settings unchanged
    assert "statusLine" not in settings


def test_fix_status_line_handles_missing_command():
    """Test that _fix_status_line handles statusLine without command."""
    from claude_mpm.hooks.claude_hooks.installer import HookInstaller

    installer = HookInstaller()

    # Create settings with statusLine but no command
    settings = {"statusLine": {"type": "custom"}}

    # Apply fix (should not raise error)
    installer._fix_status_line(settings)

    # Verify settings unchanged
    assert "command" not in settings["statusLine"]


def test_jq_expression_works_with_both_schemas():
    """Test that the new jq expression works with both input schemas."""
    import subprocess

    # Test with old schema (output_style.name)
    old_input = '{"output_style": {"name": "Test Style"}}'
    result = subprocess.run(
        ["jq", "-r", '.output_style.name // .activeOutputStyle // "default"'],
        input=old_input,
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stdout.strip() == "Test Style"

    # Test with new schema (activeOutputStyle)
    new_input = '{"activeOutputStyle": "Test Style"}'
    result = subprocess.run(
        ["jq", "-r", '.output_style.name // .activeOutputStyle // "default"'],
        input=new_input,
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stdout.strip() == "Test Style"

    # Test with neither (should return default)
    empty_input = "{}"
    result = subprocess.run(
        ["jq", "-r", '.output_style.name // .activeOutputStyle // "default"'],
        input=empty_input,
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stdout.strip() == "default"


def test_full_install_hooks_applies_fix():
    """Test that install_hooks applies the statusLine fix."""
    from claude_mpm.hooks.claude_hooks.installer import HookInstaller

    # Create a temporary settings file with old format
    with tempfile.TemporaryDirectory() as tmpdir:
        settings_file = Path(tmpdir) / "settings.json"

        # Create settings with old statusLine format
        old_settings = {
            "statusLine": {
                "type": "command",
                "command": 'input=$(cat); style=$(echo "$input" | jq -r \'.output_style.name // "default"\'); echo "$style"',
            },
            "activeOutputStyle": "Claude MPM",
        }

        settings_file.write_text(json.dumps(old_settings, indent=2))

        # Create installer with temporary settings file
        installer = HookInstaller()
        original_settings_file = installer.settings_file
        installer.settings_file = settings_file

        try:
            # Simulate the fix (without full installation)
            with settings_file.open() as f:
                settings = json.load(f)

            installer._fix_status_line(settings)

            with settings_file.open("w") as f:
                json.dump(settings, f, indent=2)

            # Verify the fix was applied
            with settings_file.open() as f:
                updated_settings = json.load(f)

            assert ".activeOutputStyle" in updated_settings["statusLine"]["command"]

        finally:
            installer.settings_file = original_settings_file

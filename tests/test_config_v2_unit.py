#!/usr/bin/env python3
"""Unit tests for ConfigScreenV2 components."""

import sys
from pathlib import Path

import yaml

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# NOTE: Manager module and ConfigScreenV2 were removed from the codebase
# These tests are for legacy UI functionality that no longer exists
import pytest

pytest.skip(
    "Manager module and ConfigScreenV2 UI components were removed",
    allow_module_level=True,
)

# Original imports (no longer available):
# from claude_mpm.manager.discovery import Installation
# from claude_mpm.manager.screens.config_screen_v2 import (
#     EnhancedConfigEditor,
#     YAMLFormWidget,
# )


def test_yaml_form_widget():
    """Test YAML form widget functionality."""
    print("Testing YAML Form Widget...")

    # Create a test YAML configuration
    test_config = {
        "project": {
            "name": "test-project",
            "type": "web",
            "enabled": True,
            "port": 8080,
            "features": ["auth", "api", "ui"],
        },
        "database": {"host": "localhost", "port": 5432, "ssl": False},
    }

    yaml_text = yaml.dump(test_config, default_flow_style=False)
    print(f"Test YAML:\n{yaml_text}")

    # Test form widget
    form = YAMLFormWidget()

    # Load YAML
    print("Loading YAML into form...")
    form.load_yaml(yaml_text)

    # Check that data was loaded
    assert form.data == test_config, "YAML data should be loaded correctly"
    print("✓ YAML loading successful")

    # Test field generation
    assert form.widgets_map, "Form fields should be generated"
    print(f"✓ Generated {len(form.widgets_map)} form fields")

    # Test has_changes (initially should be False)
    assert not form.has_changes(), "Form should have no changes initially"
    print("✓ Initial change detection working")

    # Test get_yaml
    output_yaml = form.get_yaml()
    reconstructed_data = yaml.safe_load(output_yaml)
    assert reconstructed_data == test_config, "Generated YAML should match original"
    print("✓ YAML generation successful")

    print("YAML Form Widget tests passed!\n")


def test_enhanced_config_editor():
    """Test enhanced config editor."""
    print("Testing Enhanced Config Editor...")

    # Create temporary installation for testing
    with tmp_path as temp_dir:
        temp_path = Path(temp_dir)
        config_path = temp_path / ".claude-mpm" / "config.yaml"
        config_path.parent.mkdir(parents=True, exist_ok=True)

        # Create test config
        test_config = {
            "project": {"name": "test-installation", "type": "test"},
            "monitoring": {"enabled": True},
        }

        # Create test installation with proper config
        installation = Installation(
            path=temp_path, config=test_config, name=temp_path.name
        )

        with config_path.open("w") as f:
            yaml.dump(test_config, f)

        print(f"Created test installation at: {temp_path}")

        # Test editor
        editor = EnhancedConfigEditor()

        # Load installation
        print("Loading installation...")
        editor.load_installation(installation)

        # Check that data was loaded
        if editor.edit_mode == "form":
            loaded_data = editor.form_editor.data
        else:
            loaded_data = yaml.safe_load(editor.yaml_editor.get_edit_text())

        assert loaded_data == test_config, "Config should be loaded correctly"
        print("✓ Installation loading successful")

        # Test save functionality
        print("Testing save functionality...")
        success, error = editor.save()
        assert success, f"Save should succeed: {error}"
        print("✓ Save functionality working")

        # Test mode toggle
        print("Testing form/YAML mode toggle...")
        original_mode = editor.edit_mode
        editor._toggle_mode(editor.mode_button)
        assert editor.edit_mode != original_mode, "Mode should toggle"
        print(f"✓ Mode toggled from {original_mode} to {editor.edit_mode}")

        print("Enhanced Config Editor tests passed!\n")


def test_error_handling():
    """Test error handling scenarios."""
    print("Testing Error Handling...")

    # Test invalid YAML
    form = YAMLFormWidget()
    invalid_yaml = "invalid: yaml: [unclosed bracket"

    print("Loading invalid YAML...")
    form.load_yaml(invalid_yaml)
    print("✓ Invalid YAML handled gracefully")

    # Test save without installation
    editor = EnhancedConfigEditor()
    success, error = editor.save()
    assert not success, "Save should fail without installation"
    assert error == "No installation selected", "Error message should be correct"
    print("✓ Save without installation handled correctly")

    print("Error handling tests passed!\n")


def test_field_type_handling():
    """Test different field type handling."""
    print("Testing Field Type Handling...")

    test_config = {
        "string_field": "hello",
        "int_field": 42,
        "float_field": 3.14,
        "bool_field": True,
        "list_field": ["item1", "item2", "item3"],
        "dict_field": {"nested_string": "world", "nested_int": 100},
    }

    form = YAMLFormWidget()
    form.load_yaml(yaml.dump(test_config))

    # Check that appropriate widgets were created for each type
    field_types = {
        field_key: widget_type
        for field_key, (widget_type, widget) in form.widgets_map.items()
    }

    print("Generated field types:")
    for field, ftype in field_types.items():
        print(f"  {field}: {ftype}")

    # Basic checks
    assert any("int" in ftype for ftype in field_types.values()), (
        "Should have integer fields"
    )
    assert any("float" in ftype for ftype in field_types.values()), (
        "Should have float fields"
    )
    assert any("bool" in ftype for ftype in field_types.values()), (
        "Should have boolean fields"
    )
    assert any("text" in ftype for ftype in field_types.values()), (
        "Should have text fields"
    )

    print("✓ All field types handled correctly")
    print("Field type handling tests passed!\n")


def main():
    """Run all tests."""
    print("=== ConfigScreenV2 Unit Tests ===\n")

    try:
        test_yaml_form_widget()
        test_enhanced_config_editor()
        test_error_handling()
        test_field_type_handling()

        print("=== ALL TESTS PASSED ===")
        return 0

    except Exception as e:
        print("=== TEST FAILED ===")
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

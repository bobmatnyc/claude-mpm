#!/usr/bin/env python3
"""Test UI navigation and keyboard interactions for ConfigScreenV2."""

import sys
import tempfile
import yaml
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.manager.screens.config_screen_v2 import ConfigScreenV2, YAMLFormWidget, EnhancedConfigEditor
from claude_mpm.manager.discovery import Installation


class MockApp:
    """Mock application for testing."""
    def __init__(self):
        self.dialogs = []
        
    def show_dialog(self, title, content):
        self.dialogs.append({"title": title, "content": content})
        print(f"Dialog shown: {title}")
    
    def close_dialog(self):
        if self.dialogs:
            dialog = self.dialogs.pop()
            print(f"Dialog closed: {dialog['title']}")


def test_keyboard_shortcuts():
    """Test keyboard shortcut handling."""
    print("Testing Keyboard Shortcuts...")
    
    app = MockApp()
    config_screen = ConfigScreenV2(app)
    
    # Test refresh shortcut
    print("Testing F5/Ctrl+R refresh shortcut...")
    handled = config_screen.handle_input('f5')
    assert handled, "F5 should be handled for refresh"
    print("✓ F5 refresh handled")
    
    handled = config_screen.handle_input('ctrl r')
    assert handled, "Ctrl+R should be handled for refresh"
    print("✓ Ctrl+R refresh handled")
    
    # Test save shortcut
    print("Testing Ctrl+S save shortcut...")
    handled = config_screen.handle_input('ctrl s')
    assert handled, "Ctrl+S should be handled for save"
    print("✓ Ctrl+S save handled")
    
    # Test unhandled keys
    handled = config_screen.handle_input('x')
    assert not handled, "Random keys should not be handled"
    print("✓ Unhandled keys properly ignored")
    
    print("Keyboard shortcuts test completed!\n")


def test_tab_navigation():
    """Test tab switching functionality."""
    print("Testing Tab Navigation...")
    
    app = MockApp()
    config_screen = ConfigScreenV2(app)
    
    # Build widget to initialize main_content
    config_screen.build_widget()
    
    # Test initial state
    assert config_screen.current_tab == 'configuration', "Should start on configuration tab"
    print("✓ Initial tab is configuration")
    
    # Test tab switching
    print("Testing tab switching...")
    
    # Mock button with _tab_name attribute
    class MockButton:
        def __init__(self, tab_name):
            self._tab_name = tab_name
    
    # Switch to instructions tab
    instructions_button = MockButton('instructions')
    config_screen._switch_tab(instructions_button)
    assert config_screen.current_tab == 'instructions', "Should switch to instructions tab"
    print("✓ Switched to instructions tab")
    
    # Switch to agents tab
    agents_button = MockButton('agents')
    config_screen._switch_tab(agents_button)
    assert config_screen.current_tab == 'agents', "Should switch to agents tab"
    print("✓ Switched to agents tab")
    
    # Switch back to configuration
    config_button = MockButton('configuration')
    config_screen._switch_tab(config_button)
    assert config_screen.current_tab == 'configuration', "Should switch back to configuration tab"
    print("✓ Switched back to configuration tab")
    
    # Test switching to same tab (should be no-op)
    config_screen._switch_tab(config_button)
    assert config_screen.current_tab == 'configuration', "Should remain on configuration tab"
    print("✓ Same tab switch handled correctly")
    
    print("Tab navigation test completed!\n")


def test_installation_selection():
    """Test installation selection functionality."""
    print("Testing Installation Selection...")
    
    app = MockApp()
    config_screen = ConfigScreenV2(app)
    
    # Build widget to initialize main_content
    config_screen.build_widget()
    
    # Create test installation
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        config_path = temp_path / '.claude-mpm' / 'config.yaml'
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        test_config = {
            "project": {
                "name": "test-installation",
                "type": "test"
            }
        }
        
        with open(config_path, 'w') as f:
            yaml.dump(test_config, f)
        
        installation = Installation(
            path=temp_path,
            config=test_config,
            name=temp_path.name
        )
        
        # Test selection
        print("Selecting installation...")
        config_screen._select_installation(installation)
        
        assert config_screen.current_installation == installation, "Installation should be selected"
        print("✓ Installation selected successfully")
        
        # Test that status was updated
        status_text = config_screen.status_text.text
        assert "Selected:" in status_text or installation.display_name in status_text, "Status should be updated"
        print("✓ Status updated on selection")
    
    print("Installation selection test completed!\n")


def test_dialog_functionality():
    """Test dialog showing and closing."""
    print("Testing Dialog Functionality...")
    
    app = MockApp()
    config_screen = ConfigScreenV2(app)
    
    # Create test installation for agent dialogs
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        installation = Installation(
            path=temp_path,
            config={"project": {"name": "test"}},
            name=temp_path.name
        )
        
        config_screen.current_installation = installation
        
        print("Testing Install Agents dialog...")
        
        # Mock button press
        class MockButton:
            pass
        
        button = MockButton()
        
        # This should show the install agents dialog
        config_screen._on_install_agents(button)
        
        # Check if dialog was shown
        assert len(app.dialogs) > 0, "Install agents dialog should be shown"
        print("✓ Install Agents dialog shown")
        
        # Test import agents dialog
        print("Testing Import Agents dialog...")
        config_screen._on_import_agents(button)
        
        # Check if second dialog was shown
        assert len(app.dialogs) > 1, "Import agents dialog should be shown"
        print("✓ Import Agents dialog shown")
        
        # Test error cases
        print("Testing error cases...")
        
        # Clear installation
        config_screen.current_installation = None
        
        # Try to show dialogs without installation
        config_screen._on_install_agents(button)
        config_screen._on_import_agents(button)
        
        # Should handle gracefully (no crashes)
        print("✓ Error cases handled gracefully")
    
    print("Dialog functionality test completed!\n")


def test_form_mode_toggle():
    """Test form/YAML mode toggle functionality."""
    print("Testing Form/YAML Mode Toggle...")
    
    editor = EnhancedConfigEditor()
    
    # Test initial state
    assert editor.edit_mode == 'form', "Should start in form mode"
    print("✓ Initial mode is form")
    
    # Load some test data
    test_config = {
        "test": {
            "value": "hello",
            "number": 42
        }
    }
    
    yaml_text = yaml.dump(test_config)
    editor.form_editor.load_yaml(yaml_text)
    
    # Test toggle to YAML mode
    print("Testing toggle to YAML mode...")
    editor._toggle_mode(editor.mode_button)
    assert editor.edit_mode == 'yaml', "Should be in YAML mode"
    assert editor.mode_button.label == "Switch to Form", "Button should show 'Switch to Form'"
    print("✓ Toggled to YAML mode")
    
    # Test toggle back to form mode
    print("Testing toggle to form mode...")
    editor._toggle_mode(editor.mode_button)
    assert editor.edit_mode == 'form', "Should be back in form mode"
    assert editor.mode_button.label == "Switch to YAML", "Button should show 'Switch to YAML'"
    print("✓ Toggled back to form mode")
    
    # Test invalid YAML prevention
    print("Testing invalid YAML toggle prevention...")
    editor._toggle_mode(editor.mode_button)  # Switch to YAML
    editor.yaml_editor.set_edit_text("invalid: yaml: [")  # Invalid YAML
    editor._toggle_mode(editor.mode_button)  # Try to switch back
    assert editor.edit_mode == 'yaml', "Should remain in YAML mode with invalid YAML"
    print("✓ Invalid YAML toggle prevented")
    
    print("Form/YAML mode toggle test completed!\n")


def test_field_interaction():
    """Test field interaction in YAML form."""
    print("Testing Field Interaction...")
    
    form = YAMLFormWidget()
    
    test_config = {
        "string_field": "hello",
        "int_field": 42,
        "bool_field": True,
        "list_field": ["item1", "item2"]
    }
    
    # Load data into form
    form.load_yaml(yaml.dump(test_config))
    
    # Test field changes
    print("Testing field change detection...")
    
    # Simulate field change
    form._on_field_change("string_field", "world")
    
    # Check that data was updated
    assert form.data["string_field"] == "world", "Field should be updated"
    print("✓ String field change handled")
    
    # Test numeric field change
    form._on_field_change("int_field", "100")
    assert form.data["int_field"] == 100, "Numeric field should be converted"
    print("✓ Numeric field change handled")
    
    # Test boolean field change
    form._on_field_change("bool_field", False)
    assert form.data["bool_field"] is False, "Boolean field should be updated"
    print("✓ Boolean field change handled")
    
    # Test change detection
    assert form.has_changes(), "Form should detect changes"
    print("✓ Change detection working")
    
    # Test revert
    form.revert()
    assert not form.has_changes(), "Form should have no changes after revert"
    assert form.data == test_config, "Data should be reverted"
    print("✓ Revert functionality working")
    
    print("Field interaction test completed!\n")


def main():
    """Run all UI navigation tests."""
    print("=== ConfigScreenV2 UI Navigation Tests ===\n")
    
    try:
        test_keyboard_shortcuts()
        test_tab_navigation()
        test_installation_selection()
        test_dialog_functionality()
        test_form_mode_toggle()
        test_field_interaction()
        
        print("=== UI NAVIGATION TESTS PASSED ===")
        
        print(f"\nSummary:")
        print(f"  Keyboard shortcuts: ✓ Working")
        print(f"  Tab navigation: ✓ Working")
        print(f"  Installation selection: ✓ Working")
        print(f"  Dialog functionality: ✓ Working")
        print(f"  Form/YAML toggle: ✓ Working")
        print(f"  Field interaction: ✓ Working")
        
        return 0
        
    except Exception as e:
        print(f"=== UI NAVIGATION TESTS FAILED ===")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
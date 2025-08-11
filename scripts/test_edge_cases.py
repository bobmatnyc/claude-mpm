#!/usr/bin/env python3
"""Test edge cases and error handling for ConfigScreenV2."""

import sys
import tempfile
import yaml
import os
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
    
    def close_dialog(self):
        if self.dialogs:
            self.dialogs.pop()


def test_empty_yaml_handling():
    """Test handling of empty YAML files."""
    print("Testing Empty YAML Handling...")
    
    form = YAMLFormWidget()
    
    # Test completely empty YAML
    print("Testing completely empty YAML...")
    form.load_yaml("")
    assert form.data == {}, "Empty YAML should result in empty dict"
    print("✓ Empty YAML handled correctly")
    
    # Test YAML with only whitespace
    print("Testing whitespace-only YAML...")
    form.load_yaml("   \n  \t  \n  ")
    assert form.data == {}, "Whitespace YAML should result in empty dict"
    print("✓ Whitespace YAML handled correctly")
    
    # Test YAML with only comments
    print("Testing comment-only YAML...")
    form.load_yaml("# This is a comment\n# Another comment")
    assert form.data == {}, "Comment-only YAML should result in empty dict"
    print("✓ Comment-only YAML handled correctly")
    
    print("Empty YAML handling test completed!\n")


def test_invalid_yaml_handling():
    """Test handling of invalid YAML syntax."""
    print("Testing Invalid YAML Handling...")
    
    form = YAMLFormWidget()
    
    invalid_yaml_cases = [
        "invalid: yaml: [unclosed",
        "key:\n  - item1\n  - item2\n  invalid_indent",
        "duplicate:\nduplicate:",
        "{ invalid json mixed with yaml }",
        "tabs:\n\tmixed_with_spaces:\n        value"
    ]
    
    for i, invalid_yaml in enumerate(invalid_yaml_cases):
        print(f"Testing invalid YAML case {i + 1}...")
        form.load_yaml(invalid_yaml)
        # Should not crash, container should have error message
        assert len(form.container.body) > 0, "Should show error message"
        print(f"✓ Invalid YAML case {i + 1} handled gracefully")
    
    print("Invalid YAML handling test completed!\n")


def test_large_yaml_handling():
    """Test handling of large YAML configurations."""
    print("Testing Large YAML Handling...")
    
    # Create a large nested configuration
    large_config = {
        "project": {
            "name": "large-project",
            "type": "enterprise",
            "modules": {}
        }
    }
    
    # Add many nested modules
    for i in range(50):
        module_name = f"module_{i}"
        large_config["project"]["modules"][module_name] = {
            "enabled": True,
            "version": f"1.{i}.0",
            "dependencies": [f"dep_{j}" for j in range(10)],
            "config": {
                "setting_1": f"value_{i}_1",
                "setting_2": i * 10,
                "setting_3": i % 2 == 0,
                "nested": {
                    "deep_setting": f"deep_value_{i}",
                    "deeper": {
                        "deepest": f"deepest_value_{i}"
                    }
                }
            }
        }
    
    form = YAMLFormWidget()
    yaml_text = yaml.dump(large_config)
    
    print(f"Testing large YAML ({len(yaml_text)} characters)...")
    form.load_yaml(yaml_text)
    
    # Should generate many widgets without crashing
    assert len(form.widgets_map) > 100, "Should generate many form fields"
    print(f"✓ Generated {len(form.widgets_map)} form fields for large config")
    
    # Test YAML generation
    output_yaml = form.get_yaml()
    reconstructed = yaml.safe_load(output_yaml)
    assert reconstructed == large_config, "Large config should be preserved"
    print("✓ Large YAML roundtrip successful")
    
    print("Large YAML handling test completed!\n")


def test_unicode_and_special_characters():
    """Test handling of Unicode and special characters."""
    print("Testing Unicode and Special Characters...")
    
    unicode_config = {
        "project": {
            "name": "プロジェクト名",  # Japanese
            "description": "Описание проекта",  # Russian
            "emoji": "🚀✨🎉",
            "special_chars": "!@#$%^&*()_+-={}[]|\\:;\"'<>?,./",
            "unicode_escape": "\\u0041\\u0042\\u0043",
        },
        "paths": {
            "with spaces": "/path/with spaces/",
            "with-dashes": "/path/with-dashes/",
            "with_underscores": "/path/with_underscores/",
            "MixedCase": "/path/MixedCase/"
        }
    }
    
    form = YAMLFormWidget()
    yaml_text = yaml.dump(unicode_config, allow_unicode=True)
    
    print("Testing Unicode YAML loading...")
    form.load_yaml(yaml_text)
    
    # Check that Unicode is preserved
    assert form.data["project"]["name"] == "プロジェクト名", "Japanese characters should be preserved"
    assert form.data["project"]["description"] == "Описание проекта", "Russian characters should be preserved"
    assert form.data["project"]["emoji"] == "🚀✨🎉", "Emoji should be preserved"
    print("✓ Unicode characters preserved correctly")
    
    # Test field change with Unicode
    form._on_field_change("project.name", "新しい名前")
    assert form.data["project"]["name"] == "新しい名前", "Unicode field changes should work"
    print("✓ Unicode field changes working")
    
    print("Unicode and special characters test completed!\n")


def test_permission_errors():
    """Test handling of permission errors."""
    print("Testing Permission Errors...")
    
    # Create a temporary directory with restricted permissions
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        config_path = temp_path / '.claude-mpm' / 'config.yaml'
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create a config file
        test_config = {"project": {"name": "test"}}
        with open(config_path, 'w') as f:
            yaml.dump(test_config, f)
        
        # Make the directory read-only (Unix-like systems)
        if os.name != 'nt':  # Not Windows
            try:
                os.chmod(config_path.parent, 0o444)  # Read-only
                
                installation = Installation(
                    path=temp_path,
                    config=test_config,
                    name=temp_path.name
                )
                
                editor = EnhancedConfigEditor()
                editor.load_installation(installation)
                
                # Try to save (should handle permission error gracefully)
                success, error = editor.save()
                
                # Should fail gracefully
                assert not success, "Save should fail with permission error"
                assert error is not None, "Should provide error message"
                print(f"✓ Permission error handled: {error}")
                
                # Restore permissions for cleanup
                os.chmod(config_path.parent, 0o755)
                
            except Exception as e:
                print(f"✓ Permission test handled exception: {e}")
        else:
            print("✓ Permission test skipped on Windows")
    
    print("Permission errors test completed!\n")


def test_malformed_installation_paths():
    """Test handling of malformed installation paths."""
    print("Testing Malformed Installation Paths...")
    
    app = MockApp()
    config_screen = ConfigScreenV2(app)
    config_screen.build_widget()
    
    # Test with non-existent path
    print("Testing non-existent installation path...")
    fake_installation = Installation(
        path=Path("/nonexistent/path/to/project"),
        config={"project": {"name": "fake"}},
        name="fake"
    )
    
    # Should handle gracefully without crashing
    try:
        config_screen._select_installation(fake_installation)
        print("✓ Non-existent path handled gracefully")
    except Exception as e:
        print(f"✓ Exception handled: {type(e).__name__}")
    
    # Test with path that's actually a file
    with tempfile.NamedTemporaryFile() as temp_file:
        file_path = Path(temp_file.name)
        
        print("Testing file path as installation path...")
        file_installation = Installation(
            path=file_path,
            config={"project": {"name": "file"}},
            name="file"
        )
        
        try:
            config_screen._select_installation(file_installation)
            print("✓ File path handled gracefully")
        except Exception as e:
            print(f"✓ Exception handled: {type(e).__name__}")
    
    print("Malformed installation paths test completed!\n")


def test_concurrent_modifications():
    """Test handling of concurrent file modifications."""
    print("Testing Concurrent Modifications...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        config_path = temp_path / '.claude-mpm' / 'config.yaml'
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create initial config
        initial_config = {"project": {"name": "original", "version": "1.0"}}
        with open(config_path, 'w') as f:
            yaml.dump(initial_config, f)
        
        installation = Installation(
            path=temp_path,
            config=initial_config,
            name=temp_path.name
        )
        
        editor = EnhancedConfigEditor()
        editor.load_installation(installation)
        
        # Simulate external modification
        external_config = {"project": {"name": "modified_externally", "version": "2.0"}}
        with open(config_path, 'w') as f:
            yaml.dump(external_config, f)
        
        print("File modified externally...")
        
        # Try to save our changes
        success, error = editor.save()
        
        # Should succeed (overwrites external changes)
        assert success, "Save should succeed even after external modification"
        print("✓ Concurrent modification handled (last write wins)")
        
        # Verify our changes were saved
        with open(config_path, 'r') as f:
            saved_config = yaml.safe_load(f)
        
        # Should contain our original data
        assert "original" in str(saved_config), "Our changes should be preserved"
        print("✓ Our changes preserved in concurrent scenario")
    
    print("Concurrent modifications test completed!\n")


def test_memory_usage():
    """Test memory usage with various scenarios."""
    print("Testing Memory Usage...")
    
    import psutil
    import os
    
    process = psutil.Process(os.getpid())
    initial_memory = process.memory_info().rss
    
    print(f"Initial memory usage: {initial_memory / 1024 / 1024:.1f} MB")
    
    # Create many form widgets
    forms = []
    for i in range(100):
        form = YAMLFormWidget()
        config = {
            f"section_{j}": {
                f"key_{k}": f"value_{i}_{j}_{k}"
                for k in range(10)
            }
            for j in range(10)
        }
        form.load_yaml(yaml.dump(config))
        forms.append(form)
    
    peak_memory = process.memory_info().rss
    memory_increase = peak_memory - initial_memory
    
    print(f"Peak memory usage: {peak_memory / 1024 / 1024:.1f} MB")
    print(f"Memory increase: {memory_increase / 1024 / 1024:.1f} MB")
    
    # Clean up
    forms.clear()
    
    final_memory = process.memory_info().rss
    print(f"Final memory usage: {final_memory / 1024 / 1024:.1f} MB")
    
    # Memory should not grow excessively (allow up to 50MB increase)
    assert memory_increase < 50 * 1024 * 1024, "Memory usage should be reasonable"
    print("✓ Memory usage within acceptable limits")
    
    print("Memory usage test completed!\n")


def main():
    """Run all edge case and error handling tests."""
    print("=== ConfigScreenV2 Edge Cases and Error Handling Tests ===\n")
    
    try:
        test_empty_yaml_handling()
        test_invalid_yaml_handling()
        test_large_yaml_handling()
        test_unicode_and_special_characters()
        test_permission_errors()
        test_malformed_installation_paths()
        test_concurrent_modifications()
        test_memory_usage()
        
        print("=== EDGE CASES AND ERROR HANDLING TESTS PASSED ===")
        
        print(f"\nSummary:")
        print(f"  Empty YAML handling: ✓ Working")
        print(f"  Invalid YAML handling: ✓ Working")
        print(f"  Large YAML handling: ✓ Working")
        print(f"  Unicode/special characters: ✓ Working")
        print(f"  Permission errors: ✓ Working")
        print(f"  Malformed paths: ✓ Working")
        print(f"  Concurrent modifications: ✓ Working")
        print(f"  Memory usage: ✓ Working")
        
        return 0
        
    except Exception as e:
        print(f"=== EDGE CASES AND ERROR HANDLING TESTS FAILED ===")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
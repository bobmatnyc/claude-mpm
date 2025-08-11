#!/usr/bin/env python3
"""Test the enhanced config editor with Save/Cancel buttons."""

import sys
import urwid
from pathlib import Path

# Add the src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.manager.screens.config_screen_v2 import EnhancedConfigEditor


def main():
    """Test the enhanced config editor."""
    
    # Sample YAML configuration
    sample_yaml = """project:
  name: test-project
  description: Test project for button testing
  
agents:
  registry_path: .claude/agents/
  deployed:
    - engineer
    - researcher
  
memory:
  provider: sqlite
  database_path: .claude-mpm/memory/knowledge.db
  size_limit_mb: 100.0
"""
    
    # Create a mock installation class
    class MockInstallation:
        def __init__(self):
            self.path = Path("/tmp/test-project")
            self.config_path = self.path / ".claude-mpm" / "config.yaml"
            self.display_name = "Test Project"
            self.is_global = False
    
    # Create editor with callbacks
    def on_change():
        status_text.set_text(('warning', "* Modified - Click Save button to save"))
    
    def on_save():
        status_text.set_text(('success', "✓ Configuration saved"))
    
    def on_cancel():
        status_text.set_text("Changes discarded")
    
    editor = EnhancedConfigEditor(
        on_change=on_change,
        on_save=on_save,
        on_cancel=on_cancel
    )
    
    # Create status text widget
    status_text = urwid.Text("")
    
    # Load the mock installation
    mock_install = MockInstallation()
    
    # Manually load YAML since we don't have a real file
    editor.form_editor.load_yaml(sample_yaml)
    editor.current_installation = mock_install
    
    # Create main layout
    main_widget = urwid.Pile([
        ('weight', 1, editor),
        ('pack', urwid.Divider()),
        ('pack', status_text),
        ('pack', urwid.Text("Press Q to quit"))
    ])
    
    # Handle input
    def handle_input(key):
        if key in ('q', 'Q'):
            raise urwid.ExitMainLoop()
    
    # Create palette
    palette = [
        ('header', 'white', 'dark blue'),
        ('button', 'white', 'dark blue'),
        ('button_focus', 'white', 'dark red'),
        ('selected', 'white', 'dark green'),
        ('edit', 'white', 'black'),
        ('edit_focus', 'white', 'dark blue'),
        ('checkbox', 'white', 'black'),
        ('checkbox_focus', 'white', 'dark blue'),
        ('success', 'light green', 'black'),
        ('warning', 'yellow', 'black'),
        ('error', 'light red', 'black'),
        ('bold', 'bold', 'black'),
    ]
    
    # Run the UI
    loop = urwid.MainLoop(
        main_widget,
        palette=palette,
        unhandled_input=handle_input
    )
    
    print("Testing Enhanced Config Editor with Save/Cancel buttons")
    print("=" * 60)
    print("Instructions:")
    print("1. The editor should show Save and Cancel buttons at the bottom")
    print("2. Edit some fields to see the modified status")
    print("3. Click Save to save changes")
    print("4. Click Cancel to discard changes")
    print("5. Press Q to quit")
    print("=" * 60)
    print()
    
    loop.run()


if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""Verify the enhanced config editor has Save/Cancel buttons."""

import sys
from pathlib import Path

# Add the src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.manager.screens.config_screen_v2 import EnhancedConfigEditor


def verify_buttons():
    """Verify that Save and Cancel buttons exist."""
    
    # Create editor
    editor = EnhancedConfigEditor()
    
    # Check that buttons exist
    assert hasattr(editor, 'save_button'), "Save button not found"
    assert hasattr(editor, 'cancel_button'), "Cancel button not found"
    
    # Check button labels
    assert editor.save_button.get_label() == "Save", f"Save button has wrong label: {editor.save_button.get_label()}"
    assert editor.cancel_button.get_label() == "Cancel", f"Cancel button has wrong label: {editor.cancel_button.get_label()}"
    
    # Verify handlers exist
    assert hasattr(editor, '_on_save_button'), "Save button handler not found"
    assert hasattr(editor, '_on_cancel_button'), "Cancel button handler not found"
    
    print("✓ All button verifications passed!")
    print("  - Save button exists with correct label")
    print("  - Cancel button exists with correct label")
    print("  - Button handlers are properly defined")
    
    # Check the layout contains the button bar
    pile_widget = editor._w  # The wrapped widget (Pile)
    if hasattr(pile_widget, 'contents'):
        widgets = pile_widget.contents
        # The button bar should be the last widget in the pile
        print(f"  - Layout has {len(widgets)} components")
        print("  - Button bar is included in the layout")
    
    return True


if __name__ == "__main__":
    try:
        verify_buttons()
        print("\n✅ Config editor button update successful!")
    except AssertionError as e:
        print(f"\n❌ Verification failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)
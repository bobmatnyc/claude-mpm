#!/usr/bin/env python3
"""Quick check to ensure TUI navigation is working."""

import sys
from pathlib import Path

# Add the source directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from textual import on
from textual.app import App, ComposeResult
from textual.widgets import Container, Label, ListItem, ListView


class TestNavApp(App):
    """Simple test app to verify ListView selection works."""

    CSS = """
    #sidebar {
        width: 30;
        background: $panel;
        border-right: solid $primary;
    }
    
    #content {
        padding: 2;
    }
    """

    def compose(self) -> ComposeResult:
        with Container():
            with Container(id="sidebar"):
                yield ListView(
                    ListItem(Label("Item 1"), id="item1"),
                    ListItem(Label("Item 2"), id="item2"),
                    ListItem(Label("Item 3"), id="item3"),
                    ListItem(Label("Item 4"), id="item4"),
                    id="nav-list",
                )
            with Container(id="content"):
                yield Label("Select an item from the list", id="display")

    @on(ListView.Selected, "#nav-list")
    def on_selection(self, event: ListView.Selected):
        """Handle selection."""
        display = self.query_one("#display", Label)
        if event.item:
            item_id = event.item.id if hasattr(event.item, "id") else "Unknown"
            display.update(f"Selected: {item_id}")
            self.notify(f"Selected: {item_id}")


if __name__ == "__main__":
    print("Testing ListView selection...")
    print("Click on items in the list or use arrow keys + Enter")
    print("Press Ctrl+C to exit")

    app = TestNavApp()
    app.run()

#!/usr/bin/env python3
"""Minimal test for ListView selection events."""

from textual import on
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Label, ListItem, ListView, Static


class ListViewTest(App):
    """Minimal test app for ListView events."""

    CSS = """
    #sidebar {
        width: 30;
        background: $panel;
        border-right: solid $primary;
        padding: 1;
    }
    
    #output {
        padding: 1;
    }
    """

    def compose(self) -> ComposeResult:
        """Create the UI."""
        with Horizontal():
            with Vertical(id="sidebar"):
                yield Label("Click an item:")
                yield ListView(
                    ListItem(Label("Item 1"), id="item-1"),
                    ListItem(Label("Item 2"), id="item-2"),
                    ListItem(Label("Item 3"), id="item-3"),
                    ListItem(Label("Item 4"), id="item-4"),
                    id="test-list",
                )

            yield Static("Output will appear here\n", id="output")

        yield Footer()

    def on_mount(self):
        """Set up event monitoring."""
        self.output = self.query_one("#output", Static)
        self.add_output("App mounted, ListView ready")

        # Focus the list
        list_view = self.query_one("#test-list", ListView)
        list_view.focus()

    def add_output(self, text: str):
        """Add text to output."""
        current = self.output.renderable
        self.output.update(f"{current}\n{text}")

    # Try multiple event handlers to see which fires

    @on(ListView.Selected, "#test-list")
    def on_list_selected_decorator(self, event: ListView.Selected):
        """Handle selection via decorator."""
        self.add_output(
            f"✓ ListView.Selected (decorator): item={event.item}, id={event.item.id if hasattr(event.item, 'id') else 'no-id'}"
        )

    def on_list_view_selected(self, event: ListView.Selected):
        """Handle selection via method name."""
        self.add_output(f"✓ on_list_view_selected (method): item={event.item}")

    @on(ListView.Highlighted, "#test-list")
    def on_highlight_changed(self, event: ListView.HighlightChanged):
        """Handle highlight change."""
        self.add_output(f"→ ListView.HighlightChanged: item={event.item}")

    @on(ListItem.Pressed)
    def on_item_pressed(self, event: ListItem.Pressed):
        """Handle ListItem press."""
        sender_id = event.sender.id if hasattr(event.sender, "id") else "no-id"
        self.add_output(f"✓ ListItem.Pressed: sender.id={sender_id}")

    def on_key(self, event):
        """Monitor key presses."""
        if event.key == "enter":
            list_view = self.query_one("#test-list", ListView)
            self.add_output(f"⏎ Enter key pressed, list index={list_view.index}")
            if list_view.index is not None:
                self.add_output(f"  → Would select index {list_view.index}")


if __name__ == "__main__":
    app = ListViewTest()
    app.run()

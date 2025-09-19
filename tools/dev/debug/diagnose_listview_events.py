#!/usr/bin/env python3
"""Diagnostic script to understand ListView event handling in Textual."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from textual import events, on
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.widgets import Footer, Header, Label, ListItem, ListView, Static


class DiagnosticApp(App):
    """App to diagnose ListView event handling."""

    CSS = """
    #nav-list {
        width: 30;
        height: 100%;
        border: solid blue;
    }

    #nav-list > ListItem {
        padding: 1;
    }

    #nav-list > ListItem.--highlight {
        background: yellow;
    }

    #log {
        width: 100%;
        height: 100%;
        border: solid green;
        overflow-y: scroll;
    }
    """

    def __init__(self):
        super().__init__()
        self.log_messages = []

    def compose(self) -> ComposeResult:
        yield Header()

        with Horizontal():
            # Navigation list
            nav_list = ListView(id="nav-list")

            # Add items
            for i in range(5):
                item = ListItem(Label(f"Item {i+1}"))
                item.data = f"screen_{i+1}"
                nav_list.append(item)

            yield nav_list

            # Log area
            with Vertical(id="log-container"):
                yield Label("Event Log:", id="log-title")
                yield Static("Waiting for events...", id="log")

        yield Footer()

    def on_mount(self):
        """Initialize the app."""
        self.title = "ListView Event Diagnostic"
        self.log_event("App mounted")

        # Set focus on nav list
        nav_list = self.query_one("#nav-list", ListView)
        nav_list.focus()
        self.log_event("Focus set on nav-list")

        # Try to set up watcher
        try:
            self.watch(nav_list, "index", self._on_index_changed)
            self.log_event("Index watcher set up successfully")
        except Exception as e:
            self.log_event(f"Failed to set up index watcher: {e}")

        # Try to set up highlighted watcher
        try:
            self.watch(nav_list, "highlighted", self._on_highlighted_changed)
            self.log_event("Highlighted watcher set up successfully")
        except Exception as e:
            self.log_event(f"Failed to set up highlighted watcher: {e}")

    def _on_index_changed(self, old_value, new_value):
        """Handle index changes."""
        self.log_event(f"Index changed: {old_value} -> {new_value}")

    def _on_highlighted_changed(self, old_value, new_value):
        """Handle highlighted changes."""
        self.log_event(f"Highlighted changed: {old_value} -> {new_value}")

    def on_message(self, message: Message):
        """Catch all messages for debugging."""
        # Log specific ListView-related messages
        if (
            "ListView" in message.__class__.__name__
            or "ListItem" in message.__class__.__name__
        ):
            self.log_event(f"Message: {message.__class__.__name__}")
        return super().on_message(message)

    @on(ListView.Selected)
    def on_any_listview_selected(self, event: ListView.Selected):
        """Handle any ListView selection."""
        self.log_event("ListView.Selected (generic handler)")
        self.log_event(f"  - event.item: {event.item}")
        self.log_event(f"  - event.list_view: {event.list_view}")
        if hasattr(event, "list_view") and event.list_view:
            self.log_event(f"  - list_view.index: {event.list_view.index}")
        if hasattr(event.item, "data"):
            self.log_event(f"  - item.data: {event.item.data}")

    @on(ListView.Selected, "#nav-list")
    def on_nav_list_selected(self, event: ListView.Selected):
        """Handle nav-list specific selection."""
        self.log_event("ListView.Selected (#nav-list specific)")
        if event.item and hasattr(event.item, "data"):
            self.log_event(f"  - Selected item data: {event.item.data}")

    @on(ListView.Highlighted)
    def on_any_listview_highlighted(self, event: ListView.Highlighted):
        """Handle any ListView highlight."""
        self.log_event("ListView.Highlighted")
        if hasattr(event, "list_view") and event.list_view:
            self.log_event(f"  - list_view.index: {event.list_view.index}")

    def on_list_view_selected(self, event: ListView.Selected):
        """Traditional event handler (method name based)."""
        self.log_event("on_list_view_selected (traditional handler)")

    def on_key(self, event: events.Key):
        """Log key events."""
        if event.key in ["up", "down", "enter", "space"]:
            self.log_event(f"Key pressed: {event.key}")

            # Check ListView state
            try:
                nav_list = self.query_one("#nav-list", ListView)
                self.log_event(f"  - Current index: {nav_list.index}")
                if nav_list.highlighted:
                    self.log_event(f"  - Highlighted: {nav_list.highlighted}")
            except Exception:
                pass

    def on_click(self, event: events.Click):
        """Log click events."""
        self.log_event(f"Click at ({event.x}, {event.y})")

    def log_event(self, message: str):
        """Log an event to the display."""
        self.log_messages.append(message)
        # Keep only last 20 messages
        if len(self.log_messages) > 20:
            self.log_messages.pop(0)

        # Update log display
        try:
            log_widget = self.query_one("#log", Static)
            log_widget.update("\n".join(self.log_messages))
        except Exception:
            pass


if __name__ == "__main__":
    print("Starting ListView Event Diagnostic...")
    print("Try the following:")
    print("1. Use arrow keys to navigate")
    print("2. Press Enter to select")
    print("3. Click with mouse")
    print("4. Watch the event log on the right")
    print("\nPress Ctrl+C to quit")

    app = DiagnosticApp()
    try:
        app.run()
    except KeyboardInterrupt:
        print("\nDiagnostic complete")

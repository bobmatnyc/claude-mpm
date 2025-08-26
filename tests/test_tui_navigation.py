#!/usr/bin/env python3
"""Test script to verify TUI navigation works correctly."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from textual import on
from textual.app import App, ComposeResult
from textual.containers import Horizontal
from textual.widgets import (
    ContentSwitcher,
    Footer,
    Header,
    Label,
    ListItem,
    ListView,
    Screen,
)


class TestScreen(Screen):
    """Simple test screen."""

    def __init__(self, name: str):
        super().__init__()
        self.name = name
        self.id = name.lower()

    def compose(self) -> ComposeResult:
        yield Label(f"This is the {self.name} screen", id="screen-label")


class TestNavigationApp(App):
    """Test app to verify ListView navigation works."""

    CSS = """
    #nav-list {
        width: 30;
        height: 100%;
        border-right: solid blue;
    }

    #nav-list > ListItem {
        padding: 1;
    }

    #nav-list > ListItem.--highlight {
        background: $boost;
    }
    """

    def __init__(self):
        super().__init__()
        self.current_screen = "first"

    def compose(self) -> ComposeResult:
        yield Header()

        with Horizontal():
            # Navigation list
            nav_list = ListView(id="nav-list")

            # Add items with data attributes
            items = [
                ("First Screen", "first"),
                ("Second Screen", "second"),
                ("Third Screen", "third"),
            ]

            for label, screen_name in items:
                item = ListItem(Label(label))
                item.data = screen_name
                nav_list.append(item)

            yield nav_list

            # Content area
            with ContentSwitcher(initial="first", id="content"):
                yield TestScreen("First")
                yield TestScreen("Second")
                yield TestScreen("Third")

        yield Footer()

    def on_mount(self):
        """Initialize the app."""
        self.title = "Navigation Test"

        # Set focus on nav list
        nav_list = self.query_one("#nav-list", ListView)
        nav_list.focus()

        # Watch for index changes
        self.watch(nav_list, "index", self._on_nav_index_changed)

    def _on_nav_index_changed(self, old_index: int, new_index: int) -> None:
        """Handle index changes."""
        if new_index is not None:
            screens = ["first", "second", "third"]
            if 0 <= new_index < len(screens):
                screen_name = screens[new_index]
                self.log(f"Index changed to {new_index}, switching to {screen_name}")
                if screen_name != self.current_screen:
                    self.switch_screen(screen_name)

    @on(ListView.Selected, "#nav-list")
    def on_nav_selected(self, event: ListView.Selected) -> None:
        """Handle ListView selection."""
        self.log("ListView.Selected triggered")

        # Try to get screen name from item data
        if event.item and hasattr(event.item, "data"):
            screen_name = event.item.data
            self.log(f"Selected item with data: {screen_name}")
            self.switch_screen(screen_name)
        # Fallback to index
        elif event.list_view and event.list_view.index is not None:
            screens = ["first", "second", "third"]
            index = event.list_view.index
            if 0 <= index < len(screens):
                screen_name = screens[index]
                self.log(f"Using index: {index} -> {screen_name}")
                self.switch_screen(screen_name)

    def switch_screen(self, screen_name: str):
        """Switch to a different screen."""
        if screen_name == self.current_screen:
            return

        try:
            switcher = self.query_one("#content", ContentSwitcher)
            switcher.current = screen_name
            self.current_screen = screen_name
            self.notify(f"Switched to {screen_name}")
        except Exception as e:
            self.notify(f"Error: {e}", severity="error")


if __name__ == "__main__":
    app = TestNavigationApp()
    print("Starting test navigation app...")
    print("Use arrow keys to navigate, Enter to select, Ctrl+C to quit")

    try:
        app.run()
    except KeyboardInterrupt:
        print("\nApp terminated")

#!/usr/bin/env python3
"""Demonstrate the clean menu style for the TUI."""

from textual import on
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal
from textual.widgets import Footer, Header, Label, ListItem, ListView, Static


class DemoMenuApp(App):
    """Demo app showing the clean menu style."""

    CSS = """
    /* Clean minimal sidebar menu style */
    #sidebar {
        width: 20;
        background: $panel;
        border-right: solid $primary;
        padding: 0;
    }
    
    .sidebar-title {
        text-style: bold;
        padding: 1;
        background: $boost;
        margin-bottom: 0;
        border-bottom: solid $primary;
    }
    
    #menu-list {
        height: 100%;
        padding: 0;
        margin: 0;
    }
    
    /* Single-line list items */
    #menu-list > ListItem {
        padding: 0 2;
        margin: 0;
        height: 1;  /* Single line height */
        background: transparent;
    }
    
    #menu-list > ListItem Label {
        padding: 0;
        margin: 0;
        width: 100%;
    }
    
    /* Hover state - light background */
    #menu-list > ListItem:hover {
        background: $boost;
    }
    
    /* Highlighted state - accent background with bold */
    #menu-list > ListItem.--highlight {
        background: $accent 30%;
        text-style: bold;
    }
    
    /* Active selected state - primary background with bold */
    #menu-list > ListItem.active {
        background: $primary 50%;
        text-style: bold;
    }
    
    #content {
        padding: 2;
    }
    """

    def compose(self) -> ComposeResult:
        yield Header()

        with Horizontal():
            # Clean sidebar menu
            with Container(id="sidebar"):
                yield Label("Menu", classes="sidebar-title")
                yield ListView(
                    ListItem(Label("Agents"), id="item-agents"),
                    ListItem(Label("Templates"), id="item-templates"),
                    ListItem(Label("Behaviors"), id="item-behaviors"),
                    ListItem(Label("Settings"), id="item-settings"),
                    id="menu-list"
                )

            # Content area
            yield Static("Select a menu item to see content", id="content")

        yield Footer()

    def on_mount(self):
        """Set initial selection."""
        menu = self.query_one("#menu-list", ListView)
        menu.index = 0
        # Mark first item as active
        if menu.children:
            menu.children[0].add_class("active")

    @on(ListView.Selected, "#menu-list")
    def on_menu_selected(self, event: ListView.Selected):
        """Handle menu selection."""
        # Update active state
        menu = self.query_one("#menu-list", ListView)
        for item in menu.children:
            item.remove_class("active")

        if event.item:
            event.item.add_class("active")

            # Update content
            content = self.query_one("#content", Static)
            item_text = event.item.children[0].renderable if event.item.children else "Unknown"
            content.update(f"Selected: {item_text}\n\nThis demonstrates the clean, minimal menu style:\n- Single-line items\n- No excessive padding\n- Clean hover/selection states\n- Bold text for selected items")

if __name__ == "__main__":
    app = DemoMenuApp()
    app.run()

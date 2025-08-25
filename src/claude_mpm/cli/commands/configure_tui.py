"""
Full-screen terminal interface for claude-mpm configuration using Textual.

WHY: Provides a modern, user-friendly TUI for managing configurations with
keyboard navigation, mouse support, and responsive layouts.

DESIGN DECISIONS:
- Use Textual for modern full-screen terminal interface
- Implement multiple screens with sidebar navigation
- Support both keyboard and mouse interaction
- Provide live search and filtering capabilities
- Use modal dialogs for confirmations
- Maintain consistency with existing configuration logic
"""

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime

from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.css.query import NoMatches
from textual.reactive import reactive, var
from textual.screen import ModalScreen, Screen
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    ListView,
    ListItem,
    LoadingIndicator,
    Placeholder,
    Static,
    Switch,
    TextArea,
    Tree,
)
from textual.widgets.tree import TreeNode

from ...core.config import Config
from ...services.version_service import VersionService
from ..shared import CommandResult


class AgentConfig:
    """Agent configuration model matching the existing implementation."""
    
    def __init__(self, name: str, description: str = "", dependencies: List[str] = None):
        self.name = name
        self.description = description
        self.dependencies = dependencies or []
        self.enabled = True


class SimpleAgentManager:
    """Agent manager matching the existing implementation."""
    
    def __init__(self, config_dir: Path):
        self.config_dir = config_dir
        self.config_file = config_dir / "agent_states.json"
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self._load_states()
        self.templates_dir = Path(__file__).parent.parent.parent / "agents" / "templates"
    
    def _load_states(self):
        """Load agent states from file."""
        if self.config_file.exists():
            with open(self.config_file) as f:
                self.states = json.load(f)
        else:
            self.states = {}
    
    def _save_states(self):
        """Save agent states to file."""
        with open(self.config_file, 'w') as f:
            json.dump(self.states, f, indent=2)
    
    def is_agent_enabled(self, agent_name: str) -> bool:
        """Check if an agent is enabled."""
        return self.states.get(agent_name, {}).get("enabled", True)
    
    def set_agent_enabled(self, agent_name: str, enabled: bool):
        """Set agent enabled state."""
        if agent_name not in self.states:
            self.states[agent_name] = {}
        self.states[agent_name]["enabled"] = enabled
        self._save_states()
    
    def discover_agents(self) -> List[AgentConfig]:
        """Discover available agents from template JSON files."""
        agents = []
        
        if not self.templates_dir.exists():
            return [
                AgentConfig("engineer", "Engineering agent (templates not found)", []),
                AgentConfig("research", "Research agent (templates not found)", [])
            ]
        
        try:
            for template_file in sorted(self.templates_dir.glob("*.json")):
                if "backup" in template_file.name.lower():
                    continue
                    
                try:
                    with open(template_file, 'r') as f:
                        template_data = json.load(f)
                    
                    agent_id = template_data.get("agent_id", template_file.stem)
                    metadata = template_data.get("metadata", {})
                    name = metadata.get("name", agent_id)
                    description = metadata.get("description", "No description available")
                    
                    capabilities = template_data.get("capabilities", {})
                    tools = capabilities.get("tools", [])
                    display_tools = tools[:3] if len(tools) > 3 else tools
                    
                    normalized_id = agent_id.replace("-agent", "").replace("_", "-")
                    
                    agent = AgentConfig(
                        name=normalized_id,
                        description=description[:80] + "..." if len(description) > 80 else description,
                        dependencies=display_tools
                    )
                    agent.enabled = self.is_agent_enabled(normalized_id)
                    agents.append(agent)
                    
                except (json.JSONDecodeError, KeyError):
                    continue
                    
        except Exception:
            return [
                AgentConfig("engineer", "Error loading templates", []),
                AgentConfig("research", "Research agent", [])
            ]
        
        agents.sort(key=lambda a: a.name)
        return agents if agents else [AgentConfig("engineer", "No agents found", [])]


class ConfirmDialog(ModalScreen):
    """Modal dialog for confirmations."""
    
    def __init__(self, message: str, title: str = "Confirm"):
        super().__init__()
        self.message = message
        self.title = title
    
    def compose(self) -> ComposeResult:
        with Container(id="confirm-dialog"):
            yield Label(self.title, id="confirm-title")
            yield Label(self.message, id="confirm-message")
            with Horizontal(id="confirm-buttons"):
                yield Button("Yes", variant="primary", id="confirm-yes")
                yield Button("No", variant="default", id="confirm-no")
    
    @on(Button.Pressed, "#confirm-yes")
    def on_yes(self):
        self.dismiss(True)
    
    @on(Button.Pressed, "#confirm-no")
    def on_no(self):
        self.dismiss(False)


class EditTemplateDialog(ModalScreen):
    """Modal dialog for template editing."""
    
    def __init__(self, agent_name: str, template: Dict[str, Any]):
        super().__init__()
        self.agent_name = agent_name
        self.template = template
    
    def compose(self) -> ComposeResult:
        with Container(id="edit-dialog"):
            yield Label(f"Edit Template: {self.agent_name}", id="edit-title")
            yield TextArea(
                json.dumps(self.template, indent=2),
                id="template-editor"
            )
            with Horizontal(id="edit-buttons"):
                yield Button("Save", variant="primary", id="save-template")
                yield Button("Cancel", variant="default", id="cancel-edit")
    
    @on(Button.Pressed, "#save-template")
    def on_save(self):
        editor = self.query_one("#template-editor", TextArea)
        try:
            template = json.loads(editor.text)
            self.dismiss(template)
        except json.JSONDecodeError as e:
            # Show error in the editor
            self.notify(f"Invalid JSON: {e}", severity="error")
    
    @on(Button.Pressed, "#cancel-edit")
    def on_cancel(self):
        self.dismiss(None)


class AgentManagementScreen(Screen):
    """Screen for agent management."""
    
    def __init__(self, agent_manager: SimpleAgentManager):
        super().__init__()
        self.agent_manager = agent_manager
        self.agents = []
        self.filtered_agents = []
    
    def compose(self) -> ComposeResult:
        with Container(id="agent-screen"):
            yield Label("Agent Management", id="screen-title")
            yield Input(placeholder="Search agents...", id="agent-search")
            
            # Create data table for agents
            table = DataTable(id="agent-table")
            table.add_columns("Name", "Status", "Description", "Tools")
            yield table
            
            with Horizontal(id="agent-actions"):
                yield Button("Enable All", id="enable-all", variant="success")
                yield Button("Disable All", id="disable-all", variant="warning")
                yield Button("Refresh", id="refresh-agents", variant="default")
    
    def on_mount(self):
        """Load agents when screen is mounted."""
        self.load_agents()
    
    def load_agents(self):
        """Load and display agents."""
        self.agents = self.agent_manager.discover_agents()
        self.filtered_agents = self.agents
        self.update_table()
    
    def update_table(self):
        """Update the agent table with current data."""
        table = self.query_one("#agent-table", DataTable)
        table.clear()
        
        for agent in self.filtered_agents:
            status = "✓ Enabled" if agent.enabled else "✗ Disabled"
            tools = ", ".join(agent.dependencies[:2]) + "..." if len(agent.dependencies) > 2 else ", ".join(agent.dependencies)
            table.add_row(
                agent.name,
                status,
                agent.description,
                tools or "Default",
                key=agent.name
            )
    
    @on(Input.Changed, "#agent-search")
    def on_search_changed(self, event: Input.Changed):
        """Filter agents based on search input."""
        search_term = event.value.lower()
        if search_term:
            self.filtered_agents = [
                agent for agent in self.agents
                if search_term in agent.name.lower() or search_term in agent.description.lower()
            ]
        else:
            self.filtered_agents = self.agents
        self.update_table()
    
    @on(DataTable.RowSelected)
    def on_row_selected(self, event: DataTable.RowSelected):
        """Toggle agent enabled state when row is selected."""
        if event.row_key:
            agent_name = str(event.row_key.value)
            agent = next((a for a in self.agents if a.name == agent_name), None)
            if agent:
                agent.enabled = not agent.enabled
                self.agent_manager.set_agent_enabled(agent_name, agent.enabled)
                self.update_table()
                self.notify(f"Agent '{agent_name}' {'enabled' if agent.enabled else 'disabled'}")
    
    @on(Button.Pressed, "#enable-all")
    async def on_enable_all(self):
        """Enable all agents."""
        result = await self.app.push_screen_wait(
            ConfirmDialog("Enable all agents?", "Confirm Enable All")
        )
        if result:
            for agent in self.agents:
                agent.enabled = True
                self.agent_manager.set_agent_enabled(agent.name, True)
            self.update_table()
            self.notify("All agents enabled")
    
    @on(Button.Pressed, "#disable-all")
    async def on_disable_all(self):
        """Disable all agents."""
        result = await self.app.push_screen_wait(
            ConfirmDialog("Disable all agents?", "Confirm Disable All")
        )
        if result:
            for agent in self.agents:
                agent.enabled = False
                self.agent_manager.set_agent_enabled(agent.name, False)
            self.update_table()
            self.notify("All agents disabled")
    
    @on(Button.Pressed, "#refresh-agents")
    def on_refresh(self):
        """Refresh agent list."""
        self.load_agents()
        self.notify("Agents refreshed")


class TemplateEditingScreen(Screen):
    """Screen for template editing."""
    
    def __init__(self, agent_manager: SimpleAgentManager, current_scope: str, project_dir: Path):
        super().__init__()
        self.agent_manager = agent_manager
        self.current_scope = current_scope
        self.project_dir = project_dir
        self.templates = []
    
    def compose(self) -> ComposeResult:
        with Container(id="template-screen"):
            yield Label("Template Editing", id="screen-title")
            
            with Horizontal(id="template-layout"):
                # Template list
                with Vertical(id="template-list-container"):
                    yield Label("Templates", id="list-title")
                    yield ListView(id="template-list")
                
                # Template viewer
                with Vertical(id="template-viewer-container"):
                    yield Label("Template Content", id="viewer-title")
                    yield TextArea(
                        "",
                        read_only=True,
                        id="template-viewer"
                    )
                    with Horizontal(id="template-actions"):
                        yield Button("Edit", id="edit-template", variant="primary")
                        yield Button("Create Copy", id="copy-template", variant="default")
                        yield Button("Reset", id="reset-template", variant="warning")
    
    def on_mount(self):
        """Load templates when screen is mounted."""
        self.load_templates()
    
    def load_templates(self):
        """Load available templates."""
        self.templates = []
        agents = self.agent_manager.discover_agents()
        
        list_view = self.query_one("#template-list", ListView)
        # Clear existing items
        list_view.clear()
        
        # Create list items and append them
        items_to_add = []
        for agent in agents:
            template_path = self._get_agent_template_path(agent.name)
            is_custom = not str(template_path).startswith(str(self.agent_manager.templates_dir))
            
            label = f"{agent.name} {'(custom)' if is_custom else '(system)'}"
            list_item = ListItem(Label(label))
            list_item.data = {"name": agent.name, "path": template_path, "is_custom": is_custom}
            items_to_add.append(list_item)
            self.templates.append((agent.name, template_path, is_custom))
        
        # Batch append all items at once
        for item in items_to_add:
            list_view.append(item)
    
    def _get_agent_template_path(self, agent_name: str) -> Path:
        """Get the path to an agent's template file."""
        if self.current_scope == "project":
            config_dir = self.project_dir / ".claude-mpm" / "agents"
        else:
            config_dir = Path.home() / ".claude-mpm" / "agents"
        
        config_dir.mkdir(parents=True, exist_ok=True)
        custom_template = config_dir / f"{agent_name}.json"
        
        if custom_template.exists():
            return custom_template
        
        possible_names = [
            f"{agent_name}.json",
            f"{agent_name.replace('-', '_')}.json",
            f"{agent_name}-agent.json",
            f"{agent_name.replace('-', '_')}_agent.json"
        ]
        
        for name in possible_names:
            system_template = self.agent_manager.templates_dir / name
            if system_template.exists():
                return system_template
        
        return custom_template
    
    @on(ListView.Selected)
    def on_template_selected(self, event: ListView.Selected):
        """Display selected template."""
        if event.item and hasattr(event.item, 'data'):
            data = event.item.data
            template_path = data['path']
            
            if template_path.exists():
                with open(template_path) as f:
                    template = json.load(f)
                
                viewer = self.query_one("#template-viewer", TextArea)
                viewer.text = json.dumps(template, indent=2)
                
                # Update button states
                edit_btn = self.query_one("#edit-template", Button)
                copy_btn = self.query_one("#copy-template", Button)
                reset_btn = self.query_one("#reset-template", Button)
                
                if data['is_custom']:
                    edit_btn.disabled = False
                    copy_btn.disabled = True
                    reset_btn.disabled = False
                else:
                    edit_btn.disabled = True
                    copy_btn.disabled = False
                    reset_btn.disabled = True
    
    @on(Button.Pressed, "#edit-template")
    async def on_edit_template(self):
        """Edit the selected template."""
        list_view = self.query_one("#template-list", ListView)
        if list_view.highlighted and hasattr(list_view.highlighted, 'data'):
            data = list_view.highlighted.data
            viewer = self.query_one("#template-viewer", TextArea)
            
            try:
                template = json.loads(viewer.text)
                result = await self.app.push_screen_wait(
                    EditTemplateDialog(data['name'], template)
                )
                
                if result:
                    # Save the edited template
                    with open(data['path'], 'w') as f:
                        json.dump(result, f, indent=2)
                    
                    viewer.text = json.dumps(result, indent=2)
                    self.notify(f"Template '{data['name']}' saved")
            except json.JSONDecodeError:
                self.notify("Invalid JSON in viewer", severity="error")
    
    @on(Button.Pressed, "#copy-template")
    async def on_copy_template(self):
        """Create a custom copy of a system template."""
        list_view = self.query_one("#template-list", ListView)
        if list_view.highlighted and hasattr(list_view.highlighted, 'data'):
            data = list_view.highlighted.data
            
            if not data['is_custom']:
                viewer = self.query_one("#template-viewer", TextArea)
                try:
                    template = json.loads(viewer.text)
                    
                    if self.current_scope == "project":
                        config_dir = self.project_dir / ".claude-mpm" / "agents"
                    else:
                        config_dir = Path.home() / ".claude-mpm" / "agents"
                    
                    config_dir.mkdir(parents=True, exist_ok=True)
                    custom_path = config_dir / f"{data['name']}.json"
                    
                    proceed = True
                    if custom_path.exists():
                        proceed = await self.app.push_screen_wait(
                            ConfirmDialog("Custom template already exists. Overwrite?", "Confirm Overwrite")
                        )
                    
                    if proceed:
                        with open(custom_path, 'w') as f:
                            json.dump(template, f, indent=2)
                        
                        self.load_templates()
                        self.notify(f"Created custom template for '{data['name']}'")
                        
                except json.JSONDecodeError:
                    self.notify("Invalid JSON in viewer", severity="error")
    
    @on(Button.Pressed, "#reset-template")
    async def on_reset_template(self):
        """Reset a custom template to system defaults."""
        list_view = self.query_one("#template-list", ListView)
        if list_view.highlighted and hasattr(list_view.highlighted, 'data'):
            data = list_view.highlighted.data
            
            if data['is_custom']:
                result = await self.app.push_screen_wait(
                    ConfirmDialog(f"Reset '{data['name']}' to system defaults?", "Confirm Reset")
                )
                
                if result:
                    data['path'].unlink(missing_ok=True)
                    self.load_templates()
                    self.notify(f"Template '{data['name']}' reset to defaults")


class BehaviorFilesScreen(Screen):
    """Screen for behavior file management."""
    
    def __init__(self, current_scope: str, project_dir: Path):
        super().__init__()
        self.current_scope = current_scope
        self.project_dir = project_dir
    
    def compose(self) -> ComposeResult:
        with Container(id="behavior-screen"):
            yield Label("Behavior Files", id="screen-title")
            
            with Horizontal(id="behavior-layout"):
                # File tree
                with Vertical(id="file-tree-container"):
                    yield Label("Files", id="tree-title")
                    tree = Tree("Behavior Files", id="behavior-tree")
                    tree.root.expand()
                    yield tree
                
                # File editor
                with Vertical(id="file-editor-container"):
                    yield Label("File Content", id="editor-title")
                    yield TextArea(
                        "",
                        id="behavior-editor"
                    )
                    with Horizontal(id="behavior-actions"):
                        yield Button("Save", id="save-behavior", variant="primary")
                        yield Button("Import", id="import-behavior", variant="default")
                        yield Button("Export", id="export-behavior", variant="default")
    
    def on_mount(self):
        """Load behavior files when screen is mounted."""
        self.load_behavior_files()
    
    def load_behavior_files(self):
        """Load and display behavior files."""
        if self.current_scope == "project":
            config_dir = self.project_dir / ".claude-mpm" / "behaviors"
        else:
            config_dir = Path.home() / ".claude-mpm" / "behaviors"
        
        config_dir.mkdir(parents=True, exist_ok=True)
        
        tree = self.query_one("#behavior-tree", Tree)
        tree.clear()
        
        # Add identity and workflow files
        for filename in ["identity.yaml", "workflow.yaml"]:
            file_path = config_dir / filename
            node = tree.root.add(filename)
            node.data = file_path
            
            if file_path.exists():
                node.set_label(f"{filename} ✓")
            else:
                node.set_label(f"{filename} ✗")
    
    @on(Tree.NodeSelected)
    def on_node_selected(self, event: Tree.NodeSelected):
        """Load file content when node is selected."""
        if event.node.data:
            file_path = event.node.data
            editor = self.query_one("#behavior-editor", TextArea)
            
            if file_path.exists():
                with open(file_path) as f:
                    editor.text = f.read()
                editor.read_only = False
            else:
                editor.text = f"# {file_path.name}\n# File does not exist yet\n"
                editor.read_only = False
            
            # Update editor title
            title = self.query_one("#editor-title", Label)
            title.update(f"Editing: {file_path.name}")
    
    @on(Button.Pressed, "#save-behavior")
    def on_save_behavior(self):
        """Save the current behavior file."""
        tree = self.query_one("#behavior-tree", Tree)
        if tree.cursor_node and tree.cursor_node.data:
            file_path = tree.cursor_node.data
            editor = self.query_one("#behavior-editor", TextArea)
            
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, 'w') as f:
                f.write(editor.text)
            
            # Update tree node
            tree.cursor_node.set_label(f"{file_path.name} ✓")
            self.notify(f"Saved {file_path.name}")
    
    @on(Button.Pressed, "#import-behavior")
    async def on_import_behavior(self):
        """Import a behavior file."""
        # In a real implementation, this would open a file dialog
        self.notify("Import functionality would open a file dialog", severity="information")
    
    @on(Button.Pressed, "#export-behavior")
    async def on_export_behavior(self):
        """Export a behavior file."""
        tree = self.query_one("#behavior-tree", Tree)
        if tree.cursor_node and tree.cursor_node.data:
            file_path = tree.cursor_node.data
            if file_path.exists():
                # In a real implementation, this would open a save dialog
                self.notify(f"Would export {file_path.name} to chosen location", severity="information")
            else:
                self.notify("File does not exist", severity="error")


class SettingsScreen(Screen):
    """Screen for settings and version information."""
    
    def __init__(self, current_scope: str, project_dir: Path):
        super().__init__()
        self.current_scope = current_scope
        self.project_dir = project_dir
        self.version_service = VersionService()
    
    def compose(self) -> ComposeResult:
        with Container(id="settings-screen"):
            yield Label("Settings", id="screen-title")
            
            with Vertical(id="settings-content"):
                # Scope settings
                with Container(id="scope-section", classes="settings-section"):
                    yield Label("Configuration Scope", classes="section-title")
                    with Horizontal(classes="setting-row"):
                        yield Label("Current Scope:", classes="setting-label")
                        yield Label(self.current_scope.upper(), id="current-scope", classes="setting-value")
                        yield Button("Switch", id="switch-scope", variant="default")
                    
                    with Horizontal(classes="setting-row"):
                        yield Label("Directory:", classes="setting-label")
                        yield Label(str(self.project_dir), id="current-dir", classes="setting-value")
                
                # Version information
                with Container(id="version-section", classes="settings-section"):
                    yield Label("Version Information", classes="section-title")
                    yield Container(id="version-info")
                
                # Export/Import
                with Container(id="export-section", classes="settings-section"):
                    yield Label("Configuration Management", classes="section-title")
                    with Horizontal(classes="setting-row"):
                        yield Button("Export Configuration", id="export-config", variant="primary")
                        yield Button("Import Configuration", id="import-config", variant="default")
    
    def on_mount(self):
        """Load version information when screen is mounted."""
        self.load_version_info()
    
    def load_version_info(self):
        """Load and display version information."""
        mpm_version = self.version_service.get_version()
        build_number = self.version_service.get_build_number()
        
        # Try to get Claude version
        claude_version = "Unknown"
        try:
            import subprocess
            result = subprocess.run(
                ["claude", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                claude_version = result.stdout.strip()
        except:
            pass
        
        version_container = self.query_one("#version-info", Container)
        version_container.remove_children()
        
        version_text = f"""Claude MPM: v{mpm_version} (build {build_number})
Claude Code: {claude_version}
Python: {sys.version.split()[0]}"""
        
        for line in version_text.split('\n'):
            version_container.mount(Label(line, classes="version-line"))
    
    @on(Button.Pressed, "#switch-scope")
    def on_switch_scope(self):
        """Switch configuration scope."""
        self.current_scope = "user" if self.current_scope == "project" else "project"
        
        scope_label = self.query_one("#current-scope", Label)
        scope_label.update(self.current_scope.upper())
        
        # Update agent manager in the app
        if hasattr(self.app, 'agent_manager'):
            if self.current_scope == "project":
                config_dir = self.project_dir / ".claude-mpm"
            else:
                config_dir = Path.home() / ".claude-mpm"
            self.app.agent_manager = SimpleAgentManager(config_dir)
        
        self.notify(f"Switched to {self.current_scope} scope")
    
    @on(Button.Pressed, "#export-config")
    async def on_export_config(self):
        """Export configuration."""
        # In a real implementation, this would open a save dialog
        self.notify("Export functionality would save configuration to chosen file", severity="information")
    
    @on(Button.Pressed, "#import-config")
    async def on_import_config(self):
        """Import configuration."""
        # In a real implementation, this would open a file dialog
        self.notify("Import functionality would load configuration from chosen file", severity="information")


class ConfigureTUI(App):
    """Main Textual application for configuration management."""
    
    CSS = """
    /* Global styles */
    Screen {
        background: $surface;
    }
    
    #screen-title {
        text-style: bold;
        text-align: center;
        padding: 1;
        background: $primary;
        color: $text;
        margin-bottom: 1;
    }
    
    /* Header styles */
    Header {
        background: $primary;
    }
    
    /* Sidebar navigation */
    #sidebar {
        width: 30;
        background: $panel;
        border-right: solid $primary;
        padding: 1;
    }
    
    #nav-list {
        height: 100%;
    }
    
    .nav-item {
        padding: 1;
        margin: 0 1;
    }
    
    .nav-item:hover {
        background: $boost;
    }
    
    .nav-item.active {
        background: $primary;
        text-style: bold;
    }
    
    /* Main content area */
    #content {
        padding: 1;
    }
    
    /* Agent screen styles */
    #agent-search {
        margin-bottom: 1;
    }
    
    #agent-table {
        height: 100%;
        margin-bottom: 1;
    }
    
    #agent-actions {
        align: center middle;
        height: 3;
    }
    
    #agent-actions Button {
        margin: 0 1;
    }
    
    /* Template screen styles */
    #template-layout {
        height: 100%;
    }
    
    #template-list-container {
        width: 40%;
        border-right: solid $primary;
        padding-right: 1;
    }
    
    #template-viewer-container {
        width: 60%;
        padding-left: 1;
    }
    
    #template-viewer {
        height: 100%;
    }
    
    #template-actions {
        align: center middle;
        height: 3;
        margin-top: 1;
    }
    
    #template-actions Button {
        margin: 0 1;
    }
    
    /* Behavior screen styles */
    #behavior-layout {
        height: 100%;
    }
    
    #file-tree-container {
        width: 30%;
        border-right: solid $primary;
        padding-right: 1;
    }
    
    #file-editor-container {
        width: 70%;
        padding-left: 1;
    }
    
    #behavior-editor {
        height: 100%;
    }
    
    #behavior-actions {
        align: center middle;
        height: 3;
        margin-top: 1;
    }
    
    #behavior-actions Button {
        margin: 0 1;
    }
    
    /* Settings screen styles */
    #settings-content {
        padding: 2;
        max-width: 80;
    }
    
    .settings-section {
        margin-bottom: 2;
        border: solid $primary;
        padding: 1;
    }
    
    .section-title {
        text-style: bold;
        margin-bottom: 1;
        color: $primary;
    }
    
    .setting-row {
        align: left middle;
        height: 3;
    }
    
    .setting-label {
        width: 20;
    }
    
    .setting-value {
        width: 40;
        color: $text-muted;
    }
    
    .version-line {
        padding: 0 1;
        margin: 0;
    }
    
    /* Modal dialog styles */
    #confirm-dialog, #edit-dialog {
        align: center middle;
        background: $panel;
        border: thick $primary;
        padding: 2;
        margin: 4 8;
    }
    
    #confirm-title, #edit-title {
        text-style: bold;
        margin-bottom: 1;
    }
    
    #confirm-message {
        margin-bottom: 2;
    }
    
    #confirm-buttons, #edit-buttons {
        align: center middle;
        height: 3;
    }
    
    #confirm-buttons Button, #edit-buttons Button {
        margin: 0 1;
    }
    
    #template-editor {
        width: 80;
        height: 30;
        margin: 1 0;
    }
    
    /* Footer styles */
    Footer {
        background: $panel;
    }
    """
    
    BINDINGS = [
        Binding("ctrl+a", "navigate('agents')", "Agents", key_display="^A"),
        Binding("ctrl+t", "navigate('templates')", "Templates", key_display="^T"),
        Binding("ctrl+b", "navigate('behaviors')", "Behaviors", key_display="^B"),
        Binding("ctrl+s", "navigate('settings')", "Settings", key_display="^S"),
        Binding("ctrl+q", "quit", "Quit", key_display="^Q"),
        Binding("f1", "help", "Help", key_display="F1"),
    ]
    
    def __init__(self, current_scope: str = "project", project_dir: Path = None):
        super().__init__()
        self.current_scope = current_scope
        self.project_dir = project_dir or Path.cwd()
        
        # Initialize agent manager
        if self.current_scope == "project":
            config_dir = self.project_dir / ".claude-mpm"
        else:
            config_dir = Path.home() / ".claude-mpm"
        self.agent_manager = SimpleAgentManager(config_dir)
        
        # Track current screen
        self.current_screen_name = "agents"
        
        # Version service
        self.version_service = VersionService()
    
    def compose(self) -> ComposeResult:
        """Create the main application layout."""
        # Header with version info
        mpm_version = self.version_service.get_version()
        yield Header(show_clock=True)
        
        with Horizontal():
            # Sidebar navigation
            with Container(id="sidebar"):
                yield Label("Navigation", classes="sidebar-title")
                # Yield ListView with its items directly
                yield ListView(
                    ListItem(Label("🤖 Agent Management"), id="nav-agents"),
                    ListItem(Label("📝 Template Editing"), id="nav-templates"),
                    ListItem(Label("📁 Behavior Files"), id="nav-behaviors"),
                    ListItem(Label("⚙️  Settings"), id="nav-settings"),
                    id="nav-list"
                )
            
            # Main content area
            with Container(id="content"):
                yield AgentManagementScreen(self.agent_manager)
        
        # Footer with shortcuts
        yield Footer()
    
    def on_mount(self):
        """Initialize the application."""
        self.title = f"Claude MPM Configuration v{self.version_service.get_version()}"
        self.sub_title = f"Scope: {self.current_scope.upper()} | {self.project_dir}"
        
        # Highlight the first navigation item
        list_view = self.query_one("#nav-list", ListView)
        if list_view.children:
            first_item = list_view.children[0]
            if isinstance(first_item, ListItem):
                first_item.add_class("active")
    
    @on(ListView.Selected, "#nav-list")
    def on_nav_selected(self, event: ListView.Selected):
        """Handle navigation selection."""
        if event.item.id == "nav-agents":
            self.switch_screen("agents")
        elif event.item.id == "nav-templates":
            self.switch_screen("templates")
        elif event.item.id == "nav-behaviors":
            self.switch_screen("behaviors")
        elif event.item.id == "nav-settings":
            self.switch_screen("settings")
    
    def switch_screen(self, screen_name: str):
        """Switch to a different screen."""
        if screen_name == self.current_screen_name:
            return
        
        # Remove current screen
        content = self.query_one("#content", Container)
        content.remove_children()
        
        # Create and mount new screen
        if screen_name == "agents":
            screen = AgentManagementScreen(self.agent_manager)
        elif screen_name == "templates":
            screen = TemplateEditingScreen(self.agent_manager, self.current_scope, self.project_dir)
        elif screen_name == "behaviors":
            screen = BehaviorFilesScreen(self.current_scope, self.project_dir)
        elif screen_name == "settings":
            screen = SettingsScreen(self.current_scope, self.project_dir)
        else:
            return
        
        content.mount(screen)
        self.current_screen_name = screen_name
        
        # Update navigation highlight
        list_view = self.query_one("#nav-list", ListView)
        for item in list_view.children:
            if isinstance(item, ListItem):
                item.remove_class("active")
                if item.id == f"nav-{screen_name}":
                    item.add_class("active")
    
    def action_navigate(self, screen: str):
        """Navigate to a specific screen via keyboard shortcut."""
        self.switch_screen(screen)
    
    def action_help(self):
        """Show help information."""
        self.notify(
            "Keyboard Shortcuts:\n"
            "Ctrl+A: Agent Management\n"
            "Ctrl+T: Template Editing\n"
            "Ctrl+B: Behavior Files\n"
            "Ctrl+S: Settings\n"
            "Ctrl+Q: Quit\n"
            "Tab: Navigate UI elements\n"
            "Enter: Select/Activate",
            title="Help",
            timeout=10
        )


def can_use_tui() -> bool:
    """Check if the terminal supports full-screen TUI mode."""
    # Check if we're in an interactive terminal
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        return False
    
    # Check if we're in a supported terminal
    term = os.environ.get('TERM', '')
    if not term or term == 'dumb':
        return False
    
    # Check terminal size
    try:
        import shutil
        cols, rows = shutil.get_terminal_size()
        if cols < 80 or rows < 24:
            return False
    except:
        return False
    
    return True


def launch_tui(current_scope: str = "project", project_dir: Path = None) -> CommandResult:
    """Launch the Textual TUI application."""
    try:
        app = ConfigureTUI(current_scope, project_dir)
        app.run()
        return CommandResult.success_result("Configuration completed")
    except KeyboardInterrupt:
        return CommandResult.success_result("Configuration cancelled")
    except Exception as e:
        return CommandResult.error_result(f"TUI error: {e}")
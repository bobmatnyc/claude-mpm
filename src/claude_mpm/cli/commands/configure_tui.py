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

EVENT HANDLING FIX:
- ListView selection events are handled via on_list_view_selected method
- Multiple event handlers provide fallback for different interaction methods
- Enter key binding (action_select_nav) handles keyboard selection
- Debug logging helps diagnose event flow issues
- Index-based selection is most reliable for screen switching
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import (
    Button,
    ContentSwitcher,
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    ListItem,
    ListView,
    Rule,
    Static,
    TabbedContent,
    TabPane,
    TextArea,
    Tree,
)

from ...services.version_service import VersionService
from ..shared import CommandResult


class AgentConfig:
    """Agent configuration model matching the existing implementation."""

    def __init__(
        self, name: str, description: str = "", dependencies: Optional[List[str]] = None
    ):
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
        self.templates_dir = (
            Path(__file__).parent.parent.parent / "agents" / "templates"
        )

    def _load_states(self):
        """Load agent states from file."""
        if self.config_file.exists():
            with open(self.config_file) as f:
                self.states = json.load(f)
        else:
            self.states = {}

    def _save_states(self):
        """Save agent states to file."""
        with open(self.config_file, "w") as f:
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
                AgentConfig("research", "Research agent (templates not found)", []),
            ]

        try:
            for template_file in sorted(self.templates_dir.glob("*.json")):
                if "backup" in template_file.name.lower():
                    continue

                try:
                    with open(template_file) as f:
                        template_data = json.load(f)

                    agent_id = template_data.get("agent_id", template_file.stem)
                    metadata = template_data.get("metadata", {})
                    metadata.get("name", agent_id)
                    description = metadata.get(
                        "description", "No description available"
                    )

                    capabilities = template_data.get("capabilities", {})
                    tools = capabilities.get("tools", [])
                    display_tools = tools[:3] if len(tools) > 3 else tools

                    normalized_id = agent_id.replace("-agent", "").replace("_", "-")

                    agent = AgentConfig(
                        name=normalized_id,
                        description=(
                            description[:80] + "..."
                            if len(description) > 80
                            else description
                        ),
                        dependencies=display_tools,
                    )
                    agent.enabled = self.is_agent_enabled(normalized_id)
                    agents.append(agent)

                except (json.JSONDecodeError, KeyError):
                    continue

        except Exception:
            return [
                AgentConfig("engineer", "Error loading templates", []),
                AgentConfig("research", "Research agent", []),
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
            yield TextArea(json.dumps(self.template, indent=2), id="template-editor")
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


class AgentInfo:
    """Extended agent information with deployment status."""

    def __init__(
        self,
        name: str,
        category: str,
        template_path: Path,
        description: str = "",
        version: str = "1.0.0",
        tools: Optional[List[str]] = None,
        model: Optional[str] = None,
    ):
        self.name = name
        self.category = category  # "system", "project", "user"
        self.template_path = template_path
        self.description = description
        self.version = version
        self.tools = tools or []
        self.model = model
        self.is_deployed = False
        self.deployment_path = None
        self.metadata = {}
        self.last_modified = None

    def check_deployment(self, project_dir: Path):
        """Check if this agent is deployed to .claude/agents/."""
        claude_agents_dir = project_dir / ".claude" / "agents"
        possible_names = [
            f"{self.name}.md",
            f"{self.name.replace('-', '_')}.md",
            f"{self.name}-agent.md",
            f"{self.name.replace('-', '_')}_agent.md",
        ]

        for name in possible_names:
            deployed_file = claude_agents_dir / name
            if deployed_file.exists():
                self.is_deployed = True
                self.deployment_path = deployed_file
                return True

        self.is_deployed = False
        self.deployment_path = None
        return False


class AgentDiscovery:
    """Service to discover agents from all sources."""

    def __init__(self, project_dir: Path):
        self.project_dir = project_dir
        # System agents from the package
        self.system_templates_dir = (
            Path(__file__).parent.parent.parent / "agents" / "templates"
        )
        # Project agents from .claude-mpm/agents/
        self.project_agents_dir = project_dir / ".claude-mpm" / "agents"
        # User agents from ~/.claude-mpm/agents/
        self.user_agents_dir = Path.home() / ".claude-mpm" / "agents"

    def discover_all_agents(self) -> Dict[str, List[AgentInfo]]:
        """Discover agents from all sources, categorized."""
        agents = {
            "system": self._discover_system_agents(),
            "project": self._discover_project_agents(),
            "user": self._discover_user_agents(),
        }

        # Check deployment status for all agents
        for category in agents.values():
            for agent in category:
                agent.check_deployment(self.project_dir)

        return agents

    def _discover_system_agents(self) -> List[AgentInfo]:
        """Discover system agents from package templates."""
        agents = []
        if self.system_templates_dir.exists():
            for template_file in sorted(self.system_templates_dir.glob("*.json")):
                if "backup" not in template_file.name.lower():
                    agent = self._load_agent_from_template(template_file, "system")
                    if agent:
                        agents.append(agent)
        return agents

    def _discover_project_agents(self) -> List[AgentInfo]:
        """Discover project-specific agents."""
        agents = []
        if self.project_agents_dir.exists():
            for template_file in sorted(self.project_agents_dir.glob("*.json")):
                agent = self._load_agent_from_template(template_file, "project")
                if agent:
                    agents.append(agent)
        return agents

    def _discover_user_agents(self) -> List[AgentInfo]:
        """Discover user-level agents."""
        agents = []
        if self.user_agents_dir.exists():
            for template_file in sorted(self.user_agents_dir.glob("*.json")):
                agent = self._load_agent_from_template(template_file, "user")
                if agent:
                    agents.append(agent)
        return agents

    def _load_agent_from_template(
        self, template_file: Path, category: str
    ) -> Optional[AgentInfo]:
        """Load agent information from a template file."""
        try:
            with open(template_file) as f:
                data = json.load(f)

            agent_id = data.get("agent_id", template_file.stem)
            metadata = data.get("metadata", {})
            capabilities = data.get("capabilities", {})

            agent = AgentInfo(
                name=agent_id.replace("-agent", "").replace("_", "-"),
                category=category,
                template_path=template_file,
                description=metadata.get("description", "No description"),
                version=data.get("agent_version", metadata.get("version", "1.0.0")),
                tools=capabilities.get("tools", []),
                model=metadata.get("model"),
            )

            agent.metadata = metadata

            # Get file modification time
            stat = template_file.stat()
            agent.last_modified = datetime.fromtimestamp(stat.st_mtime)

            return agent

        except Exception:
            return None


class ViewAgentPropertiesDialog(ModalScreen):
    """Modal dialog for viewing agent properties."""

    def __init__(self, agent: AgentInfo):
        super().__init__()
        self.agent = agent

    def compose(self) -> ComposeResult:
        with Container(id="view-properties-dialog"):
            yield Label(f"Agent Properties: {self.agent.name}", id="properties-title")

            # Load and display the JSON template
            try:
                with open(self.agent.template_path) as f:
                    template_data = json.load(f)
                json_text = json.dumps(template_data, indent=2)
            except Exception as e:
                json_text = f"Error loading template: {e}"

            yield TextArea(json_text, read_only=True, id="properties-viewer")

            with Horizontal(id="properties-buttons"):
                yield Button("Close", variant="primary", id="close-properties")

    @on(Button.Pressed, "#close-properties")
    def on_close(self):
        self.dismiss()


class AgentManagementScreen(Container):
    """Comprehensive 3-pane agent management screen."""

    def __init__(
        self, agent_manager: SimpleAgentManager, id: str = "agent-management-screen"
    ):
        super().__init__(id=id)
        self.agent_manager = agent_manager
        self.project_dir = Path.cwd()
        self.discovery = AgentDiscovery(self.project_dir)
        self.all_agents = {}
        self.current_category = "system"
        self.selected_agent = None
        self.current_pane_focus = 0  # 0=categories, 1=list, 2=details

    def compose(self) -> ComposeResult:
        # Simple vertical layout
        yield Label("Agent Management", id="screen-title")

        # Category tabs
        with TabbedContent(id="agent-category-tabs"):
            with TabPane("System", id="tab-system"):
                yield Label("System agents")
            with TabPane("Project", id="tab-project"):
                yield Label("Project agents")
            with TabPane("User", id="tab-user"):
                yield Label("User agents")

        # Search box
        yield Input(placeholder="Search agents...", id="agent-search")

        # Agent table with proper initialization
        table = DataTable(id="agent-list-table", cursor_type="row")
        table.add_columns("Name", "Status", "Version", "Path")
        yield table

        # Simple details area
        yield Static("Select an agent to view details", id="agent-details")

        # Action buttons in a horizontal container
        with Horizontal(id="agent-action-buttons"):
            yield Button("Deploy/Undeploy", id="toggle-deploy", variant="primary")
            yield Button("View Properties", id="view-properties", variant="default")
            yield Button("Edit", id="edit-agent", variant="warning")
            yield Button("Delete", id="delete-agent", variant="error")

    def on_mount(self):
        """Initialize when screen is mounted."""
        # Load agents immediately since we've already set up columns in compose()
        self.load_agents()
        self.update_action_buttons()

    def scroll_to_pane(self, pane_id: str):
        """Simplified scroll method - no longer needed with vertical layout."""

    def focus_next_pane(self):
        """Simplified focus navigation - just focus table."""
        try:
            table = self.query_one("#agent-list-table", DataTable)
            table.focus()
        except Exception:
            pass

    def focus_previous_pane(self):
        """Simplified focus navigation - just focus table."""
        try:
            table = self.query_one("#agent-list-table", DataTable)
            table.focus()
        except Exception:
            pass

    def load_agents(self):
        """Load all agents from all sources."""
        self.all_agents = self.discovery.discover_all_agents()

        # Debug: log what we found
        for category, agents in self.all_agents.items():
            self.log(f"Found {len(agents)} {category} agents")

        # Load the current category into the table
        self.log(f"Loading initial category: {self.current_category}")
        self.load_category_agents(self.current_category)

    def load_category_agents(self, category: str):
        """Load agents from a specific category into the table."""
        self.current_category = category
        table = self.query_one("#agent-list-table", DataTable)

        # Clear only the rows, not the columns
        table.clear()

        agents = self.all_agents.get(category, [])
        self.log(f"Loading {len(agents)} agents in category '{category}'")

        for agent in agents:
            status = "✓ Deployed" if agent.is_deployed else "✗ Not Deployed"
            # Show relative path for readability
            try:
                rel_path = agent.template_path.relative_to(Path.home())
                path_str = f"~/{rel_path}"
            except:
                try:
                    rel_path = agent.template_path.relative_to(self.project_dir)
                    path_str = f"./{rel_path}"
                except:
                    path_str = str(agent.template_path)

            self.log(f"Adding row: {agent.name}, {status}, {agent.version}, {path_str}")
            table.add_row(agent.name, status, agent.version, path_str, key=agent.name)

        # Force a refresh of the table and ensure visibility
        table.refresh()
        table.visible = True

        # Debug: Log the table state
        self.log(f"Table now has {table.row_count} rows, visible={table.visible}")
        if table.row_count == 0:
            self.log("WARNING: No rows were added to the table!")

    @on(TabbedContent.TabActivated)
    def on_tab_changed(self, event: TabbedContent.TabActivated):
        """Handle category tab changes."""
        tab_id = event.pane.id
        if tab_id:
            category = tab_id.replace("tab-", "")
            self.load_category_agents(category)
            self.selected_agent = None
            self.update_agent_details()
            self.update_action_buttons()

    @on(DataTable.RowSelected)
    def on_table_row_selected(self, event: DataTable.RowSelected):
        """Handle agent selection from table."""
        if event.row_key:
            agent_name = str(event.row_key.value)
            # Find the agent in current category
            agents = self.all_agents.get(self.current_category, [])
            agent = next((a for a in agents if a.name == agent_name), None)
            if agent:
                self.selected_agent = agent
                self.update_agent_details()
                self.update_action_buttons()

    def update_agent_details(self):
        """Update the agent details pane."""
        details = self.query_one("#agent-details", Static)

        if not self.selected_agent:
            details.update("Select an agent to view details")
            return

        agent = self.selected_agent

        # Build detailed information
        details_text = f"""[bold]{agent.name}[/bold]

[bold]Category:[/bold] {agent.category.title()}
[bold]Version:[/bold] {agent.version}
[bold]Deployment:[/bold] {'✓ Deployed' if agent.is_deployed else '✗ Not Deployed'}

[bold]Description:[/bold]
{agent.description}

[bold]Template Path:[/bold]
{agent.template_path}
"""

        if agent.is_deployed and agent.deployment_path:
            details_text += f"\n[bold]Deployed To:[/bold]\n{agent.deployment_path}\n"

        if agent.model:
            details_text += f"\n[bold]Model:[/bold] {agent.model}\n"

        if agent.tools:
            details_text += "\n[bold]Tools:[/bold]\n"
            for tool in agent.tools[:10]:  # Show first 10 tools
                details_text += f"  • {tool}\n"
            if len(agent.tools) > 10:
                details_text += f"  ... and {len(agent.tools) - 10} more\n"

        if agent.last_modified:
            details_text += f"\n[bold]Last Modified:[/bold] {agent.last_modified.strftime('%Y-%m-%d %H:%M')}\n"

        details.update(details_text)

    def update_action_buttons(self):
        """Update the state of action buttons based on selected agent."""
        toggle_btn = self.query_one("#toggle-deploy", Button)
        view_btn = self.query_one("#view-properties", Button)
        edit_btn = self.query_one("#edit-agent", Button)
        delete_btn = self.query_one("#delete-agent", Button)

        if not self.selected_agent:
            # Disable all buttons
            toggle_btn.disabled = True
            view_btn.disabled = True
            edit_btn.disabled = True
            delete_btn.disabled = True
            toggle_btn.label = "Deploy/Undeploy"
        else:
            agent = self.selected_agent

            # Toggle deploy button
            toggle_btn.disabled = False
            toggle_btn.label = "Undeploy" if agent.is_deployed else "Deploy"

            # View properties always enabled
            view_btn.disabled = False

            # Edit button - only for project/user agents
            edit_btn.disabled = agent.category == "system"

            # Delete button - only for project/user agents
            delete_btn.disabled = agent.category == "system"

    @work
    @on(Button.Pressed, "#toggle-deploy")
    async def on_toggle_deploy(self):
        """Deploy or undeploy the selected agent."""
        if not self.selected_agent:
            return

        agent = self.selected_agent

        if agent.is_deployed:
            # Undeploy
            result = await self.app.push_screen_wait(
                ConfirmDialog(
                    f"Undeploy agent '{agent.name}' from .claude/agents/?",
                    "Confirm Undeploy",
                )
            )
            if result:
                if agent.deployment_path and agent.deployment_path.exists():
                    try:
                        agent.deployment_path.unlink()
                        self.notify(f"Agent '{agent.name}' undeployed")
                        agent.is_deployed = False
                        agent.deployment_path = None
                        self.load_agents()
                        self.update_agent_details()
                        self.update_action_buttons()
                    except Exception as e:
                        self.notify(f"Failed to undeploy: {e}", severity="error")
        else:
            # Deploy
            self.deploy_agent(agent)

    def deploy_agent(self, agent: AgentInfo):
        """Deploy an agent to .claude/agents/."""
        try:
            # Create .claude/agents directory
            claude_agents_dir = self.project_dir / ".claude" / "agents"
            claude_agents_dir.mkdir(parents=True, exist_ok=True)

            # Load template
            with open(agent.template_path) as f:
                template_data = json.load(f)

            # Convert to YAML format (simplified for this example)
            # In production, use the actual AgentFormatConverter
            agent_content = self._build_agent_markdown(template_data)

            # Write to .claude/agents/
            target_file = claude_agents_dir / f"{agent.name}.md"
            with open(target_file, "w") as f:
                f.write(agent_content)

            self.notify(f"Agent '{agent.name}' deployed to .claude/agents/")
            agent.is_deployed = True
            agent.deployment_path = target_file
            self.load_agents()
            self.update_agent_details()
            self.update_action_buttons()

        except Exception as e:
            self.notify(f"Failed to deploy: {e}", severity="error")

    def _build_agent_markdown(self, template_data: Dict[str, Any]) -> str:
        """Build a simple markdown representation of the agent."""
        metadata = template_data.get("metadata", {})
        capabilities = template_data.get("capabilities", {})
        instructions = template_data.get("instructions", [])

        content = f"""---
agent_id: {template_data.get('agent_id', 'unknown')}
name: {metadata.get('name', 'Unknown')}
version: {metadata.get('version', '1.0.0')}
model: {metadata.get('model', 'claude-3-5-sonnet-20241022')}
---

# {metadata.get('name', 'Agent')}

{metadata.get('description', 'No description')}

## Instructions

"""

        for instruction in instructions:
            if isinstance(instruction, dict):
                content += f"- {instruction.get('content', '')}\n"
            else:
                content += f"- {instruction}\n"

        if capabilities.get("tools"):
            content += "\n## Tools\n\n"
            for tool in capabilities["tools"]:
                content += f"- {tool}\n"

        return content

    @work
    @on(Button.Pressed, "#view-properties")
    async def on_view_properties(self):
        """View the selected agent's properties."""
        if self.selected_agent:
            await self.app.push_screen_wait(
                ViewAgentPropertiesDialog(self.selected_agent)
            )

    @work
    @on(Button.Pressed, "#edit-agent")
    async def on_edit_agent(self):
        """Edit the selected agent (project/user only)."""
        if not self.selected_agent or self.selected_agent.category == "system":
            return

        try:
            with open(self.selected_agent.template_path) as f:
                template_data = json.load(f)

            result = await self.app.push_screen_wait(
                EditTemplateDialog(self.selected_agent.name, template_data)
            )

            if result:
                # Save the edited template
                with open(self.selected_agent.template_path, "w") as f:
                    json.dump(result, f, indent=2)

                self.notify(f"Agent '{self.selected_agent.name}' updated")
                self.load_agents()
                self.update_agent_details()

        except Exception as e:
            self.notify(f"Failed to edit agent: {e}", severity="error")

    @work
    @on(Button.Pressed, "#delete-agent")
    async def on_delete_agent(self):
        """Delete the selected agent (project/user only)."""
        if not self.selected_agent or self.selected_agent.category == "system":
            return

        result = await self.app.push_screen_wait(
            ConfirmDialog(
                f"Delete agent '{self.selected_agent.name}'? This cannot be undone.",
                "Confirm Delete",
            )
        )

        if result:
            try:
                # If deployed, undeploy first
                if (
                    self.selected_agent.is_deployed
                    and self.selected_agent.deployment_path
                ):
                    self.selected_agent.deployment_path.unlink(missing_ok=True)

                # Delete the template file
                self.selected_agent.template_path.unlink()

                self.notify(f"Agent '{self.selected_agent.name}' deleted")
                self.selected_agent = None
                self.load_agents()
                self.update_agent_details()
                self.update_action_buttons()

            except Exception as e:
                self.notify(f"Failed to delete agent: {e}", severity="error")

    @on(Input.Changed, "#agent-search")
    def on_search_changed(self, event: Input.Changed):
        """Filter agents based on search input."""
        search_term = event.value.lower()
        table = self.query_one("#agent-list-table", DataTable)
        table.clear()

        agents = self.all_agents.get(self.current_category, [])

        if search_term:
            # Filter agents
            filtered = [
                agent
                for agent in agents
                if search_term in agent.name.lower()
                or search_term in agent.description.lower()
            ]
        else:
            filtered = agents

        # Repopulate table with filtered agents
        for agent in filtered:
            status = "✓ Deployed" if agent.is_deployed else "✗ Not Deployed"
            try:
                rel_path = agent.template_path.relative_to(Path.home())
                path_str = f"~/{rel_path}"
            except:
                try:
                    rel_path = agent.template_path.relative_to(self.project_dir)
                    path_str = f"./{rel_path}"
                except:
                    path_str = str(agent.template_path)

            table.add_row(agent.name, status, agent.version, path_str, key=agent.name)


class TemplateEditingScreen(Container):
    """Screen for template editing."""

    def __init__(
        self,
        agent_manager: SimpleAgentManager,
        current_scope: str,
        project_dir: Path,
        id: str = "template-screen",
    ):
        super().__init__(id=id)
        self.agent_manager = agent_manager
        self.current_scope = current_scope
        self.project_dir = project_dir
        self.templates = []

    def compose(self) -> ComposeResult:
        yield Label("Template Editing", id="screen-title")

        with Horizontal(id="template-layout"):
            # Template list
            with Vertical(id="template-list-container"):
                yield Label("Templates", classes="pane-title")
                yield ListView(id="template-list")

            # Template viewer
            with Vertical(id="template-viewer-container"):
                yield Label("Content", classes="pane-title")
                yield TextArea("", read_only=True, id="template-viewer")
                with Horizontal(id="template-actions"):
                    yield Button("Edit", id="edit-template", variant="primary")
                    yield Button("Create Copy", id="copy-template", variant="default")
                    yield Button("Reset", id="reset-template", variant="warning")

    def on_mount(self):
        """Load templates when screen is mounted."""
        # Use after_refresh to ensure UI is ready
        self.call_after_refresh(self.load_templates)

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
            is_custom = not str(template_path).startswith(
                str(self.agent_manager.templates_dir)
            )

            label = f"{agent.name} {'(custom)' if is_custom else '(system)'}"
            list_item = ListItem(Label(label))
            list_item.data = {
                "name": agent.name,
                "path": template_path,
                "is_custom": is_custom,
            }
            items_to_add.append(list_item)
            self.templates.append((agent.name, template_path, is_custom))

        # Batch append all items at once
        for item in items_to_add:
            list_view.append(item)

        # Log what we loaded
        self.log(f"Loaded {len(items_to_add)} templates")

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
            f"{agent_name.replace('-', '_')}_agent.json",
        ]

        for name in possible_names:
            system_template = self.agent_manager.templates_dir / name
            if system_template.exists():
                return system_template

        return custom_template

    @on(ListView.Selected)
    def on_template_selected(self, event: ListView.Selected):
        """Display selected template."""
        if event.item and hasattr(event.item, "data"):
            data = event.item.data
            template_path = data["path"]

            if template_path.exists():
                with open(template_path) as f:
                    template = json.load(f)

                viewer = self.query_one("#template-viewer", TextArea)
                viewer.text = json.dumps(template, indent=2)

                # Update button states
                edit_btn = self.query_one("#edit-template", Button)
                copy_btn = self.query_one("#copy-template", Button)
                reset_btn = self.query_one("#reset-template", Button)

                if data["is_custom"]:
                    edit_btn.disabled = False
                    copy_btn.disabled = True
                    reset_btn.disabled = False
                else:
                    edit_btn.disabled = True
                    copy_btn.disabled = False
                    reset_btn.disabled = True

    @work
    @on(Button.Pressed, "#edit-template")
    async def on_edit_template(self):
        """Edit the selected template."""
        list_view = self.query_one("#template-list", ListView)
        if list_view.highlighted and hasattr(list_view.highlighted, "data"):
            data = list_view.highlighted.data
            viewer = self.query_one("#template-viewer", TextArea)

            try:
                template = json.loads(viewer.text)
                result = await self.app.push_screen_wait(
                    EditTemplateDialog(data["name"], template)
                )

                if result:
                    # Save the edited template
                    with open(data["path"], "w") as f:
                        json.dump(result, f, indent=2)

                    viewer.text = json.dumps(result, indent=2)
                    self.notify(f"Template '{data['name']}' saved")
            except json.JSONDecodeError:
                self.notify("Invalid JSON in viewer", severity="error")

    @work
    @on(Button.Pressed, "#copy-template")
    async def on_copy_template(self):
        """Create a custom copy of a system template."""
        list_view = self.query_one("#template-list", ListView)
        if list_view.highlighted and hasattr(list_view.highlighted, "data"):
            data = list_view.highlighted.data

            if not data["is_custom"]:
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
                            ConfirmDialog(
                                "Custom template already exists. Overwrite?",
                                "Confirm Overwrite",
                            )
                        )

                    if proceed:
                        with open(custom_path, "w") as f:
                            json.dump(template, f, indent=2)

                        self.load_templates()
                        self.notify(f"Created custom template for '{data['name']}'")

                except json.JSONDecodeError:
                    self.notify("Invalid JSON in viewer", severity="error")

    @work
    @on(Button.Pressed, "#reset-template")
    async def on_reset_template(self):
        """Reset a custom template to system defaults."""
        list_view = self.query_one("#template-list", ListView)
        if list_view.highlighted and hasattr(list_view.highlighted, "data"):
            data = list_view.highlighted.data

            if data["is_custom"]:
                result = await self.app.push_screen_wait(
                    ConfirmDialog(
                        f"Reset '{data['name']}' to system defaults?", "Confirm Reset"
                    )
                )

                if result:
                    data["path"].unlink(missing_ok=True)
                    self.load_templates()
                    self.notify(f"Template '{data['name']}' reset to defaults")


class BehaviorFilesScreen(Container):
    """Screen for behavior file management."""

    def __init__(
        self, current_scope: str, project_dir: Path, id: str = "behavior-screen"
    ):
        super().__init__(id=id)
        self.current_scope = current_scope
        self.project_dir = project_dir

    def compose(self) -> ComposeResult:
        yield Label("Behavior Files", id="screen-title")

        with Horizontal(id="behavior-layout"):
            # File tree
            with Vertical(id="file-tree-container"):
                yield Label("Files", classes="pane-title")
                tree = Tree("Behavior Files", id="behavior-tree")
                tree.root.expand()
                yield tree

            # File editor
            with Vertical(id="file-editor-container"):
                yield Label("Content", classes="pane-title", id="editor-title")
                yield TextArea("", id="behavior-editor")
                with Horizontal(id="behavior-actions"):
                    yield Button("Save", id="save-behavior", variant="primary")
                    yield Button("Import", id="import-behavior", variant="default")
                    yield Button("Export", id="export-behavior", variant="default")

    def on_mount(self):
        """Load behavior files when screen is mounted."""
        # Use after_refresh to ensure UI is ready
        self.call_after_refresh(self.load_behavior_files)

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
            title.update(f"{file_path.name} ──────")

    @on(Button.Pressed, "#save-behavior")
    def on_save_behavior(self):
        """Save the current behavior file."""
        tree = self.query_one("#behavior-tree", Tree)
        if tree.cursor_node and tree.cursor_node.data:
            file_path = tree.cursor_node.data
            editor = self.query_one("#behavior-editor", TextArea)

            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, "w") as f:
                f.write(editor.text)

            # Update tree node
            tree.cursor_node.set_label(f"{file_path.name} ✓")
            self.notify(f"Saved {file_path.name}")

    @on(Button.Pressed, "#import-behavior")
    async def on_import_behavior(self):
        """Import a behavior file."""
        # In a real implementation, this would open a file dialog
        self.notify(
            "Import functionality would open a file dialog", severity="information"
        )

    @on(Button.Pressed, "#export-behavior")
    async def on_export_behavior(self):
        """Export a behavior file."""
        tree = self.query_one("#behavior-tree", Tree)
        if tree.cursor_node and tree.cursor_node.data:
            file_path = tree.cursor_node.data
            if file_path.exists():
                # In a real implementation, this would open a save dialog
                self.notify(
                    f"Would export {file_path.name} to chosen location",
                    severity="information",
                )
            else:
                self.notify("File does not exist", severity="error")


class SettingsScreen(Container):
    """Screen for settings and version information."""

    def __init__(
        self, current_scope: str, project_dir: Path, id: str = "settings-screen"
    ):
        super().__init__(id=id)
        self.current_scope = current_scope
        self.project_dir = project_dir
        self.version_service = VersionService()

    def compose(self) -> ComposeResult:
        yield Label("Settings", id="screen-title")

        with Vertical(id="settings-content"):
            # Scope settings
            with Container(id="scope-section", classes="settings-section"):
                yield Label("Configuration Scope", classes="section-title")
                with Horizontal(classes="setting-row"):
                    yield Label("Current Scope:", classes="setting-label")
                    yield Label(
                        self.current_scope.upper(),
                        id="current-scope",
                        classes="setting-value",
                    )
                    yield Button("Switch", id="switch-scope", variant="default")

                with Horizontal(classes="setting-row"):
                    yield Label("Directory:", classes="setting-label")
                    yield Label(
                        str(self.project_dir), id="current-dir", classes="setting-value"
                    )

            # Version information
            with Container(id="version-section", classes="settings-section"):
                yield Label("Version Information", classes="section-title")
                yield Container(id="version-info")

            # Export/Import
            with Container(id="export-section", classes="settings-section"):
                yield Label("Configuration Management", classes="section-title")
                with Horizontal(classes="setting-row"):
                    yield Button(
                        "Export Configuration", id="export-config", variant="primary"
                    )
                    yield Button(
                        "Import Configuration", id="import-config", variant="default"
                    )

    def on_mount(self):
        """Load version information when screen is mounted."""
        # Use after_refresh to ensure UI is ready
        self.call_after_refresh(self.load_version_info)

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
                timeout=5,
                check=False,
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

        for line in version_text.split("\n"):
            version_container.mount(Label(line, classes="version-line"))

    @on(Button.Pressed, "#switch-scope")
    def on_switch_scope(self):
        """Switch configuration scope."""
        self.current_scope = "user" if self.current_scope == "project" else "project"

        scope_label = self.query_one("#current-scope", Label)
        scope_label.update(self.current_scope.upper())

        # Update agent manager in the app and all screens
        if hasattr(self.app, "agent_manager"):
            if self.current_scope == "project":
                config_dir = self.project_dir / ".claude-mpm"
            else:
                config_dir = Path.home() / ".claude-mpm"
            self.app.agent_manager = SimpleAgentManager(config_dir)

            # Update all screens with new scope
            try:
                switcher = self.app.query_one("#content-switcher", ContentSwitcher)

                # Update each screen's scope
                for screen_id in ["agents", "templates", "behaviors", "settings"]:
                    screen = switcher.get_child_by_id(screen_id)
                    if screen and hasattr(screen, "current_scope"):
                        screen.current_scope = self.current_scope
                    if screen and hasattr(screen, "agent_manager"):
                        screen.agent_manager = self.app.agent_manager

                # Reload data in the current screen if it has a load method
                current_screen = switcher.get_child_by_id(self.app.current_screen_name)
                if current_screen:
                    if hasattr(current_screen, "load_agents"):
                        current_screen.load_agents()
                    elif hasattr(current_screen, "load_templates"):
                        current_screen.load_templates()
                    elif hasattr(current_screen, "load_behavior_files"):
                        current_screen.load_behavior_files()
            except:
                pass

        self.notify(f"Switched to {self.current_scope} scope")

    @on(Button.Pressed, "#export-config")
    async def on_export_config(self):
        """Export configuration."""
        # In a real implementation, this would open a save dialog
        self.notify(
            "Export functionality would save configuration to chosen file",
            severity="information",
        )

    @on(Button.Pressed, "#import-config")
    async def on_import_config(self):
        """Import configuration."""
        # In a real implementation, this would open a file dialog
        self.notify(
            "Import functionality would load configuration from chosen file",
            severity="information",
        )


class ConfigureTUI(App):
    """Main Textual application for configuration management."""

    CSS = """
    /* Global styles */
    Container {
        background: $surface;
    }

    #screen-title {
        text-style: bold;
        text-align: left;
        padding: 0 1;
        height: 1;
        background: $primary 30%;
        color: $text;
        margin-bottom: 1;
        border-bottom: solid $primary;
    }

    /* Header styles */
    Header {
        background: $primary;
        border-bottom: solid $accent;
    }

    /* Main layout */
    #main-layout {
        height: 100%;
    }

    /* Sidebar navigation - Clean minimal style */
    #sidebar {
        width: 25;
        background: $panel;
        border-right: solid $primary;
        padding: 0;
    }

    .sidebar-title {
        text-style: bold;
        padding: 0 1;
        height: 1;
        background: $primary 20%;
        text-align: left;
        margin-bottom: 0;
        border-bottom: solid $primary;
    }

    #nav-list {
        height: 100%;
        padding: 0;
        margin: 0;
    }

    /* Single-line list items with minimal styling */
    #nav-list > ListItem {
        padding: 0 2;
        margin: 0;
        height: 1;  /* Single line height */
        background: transparent;
    }

    #nav-list > ListItem Label {
        padding: 0;
        margin: 0;
        width: 100%;
    }

    /* Hover state - light background */
    #nav-list > ListItem:hover {
        background: $boost;
    }

    /* Highlighted/Selected state - accent background */
    #nav-list > ListItem.--highlight {
        background: $accent 30%;
        text-style: bold;
    }

    /* Active selected state - primary background with bold text */
    #nav-list > ListItem.active {
        background: $primary 50%;
        text-style: bold;
    }

    /* Main content area */
    #content-switcher {
        padding: 1;
        height: 100%;
        width: 100%;
    }

    /* Content screens (Containers) */
    #agents, #templates, #behaviors, #settings {
        height: 100%;
        width: 100%;
    }

    /* Agent Management simplified layout styles */
    #agent-management-screen {
        height: 100%;
        padding: 1;
    }

    #screen-title {
        text-style: bold;
        padding: 0 1;
        height: 1;
        background: $primary 20%;
        text-align: left;
        margin-bottom: 1;
        border-bottom: solid $primary;
    }

    /* Compact headers for all screens */
    #list-title, #viewer-title, #tree-title, #editor-title {
        text-style: bold;
        padding: 0 1;
        height: 1;
        background: $primary 20%;
        text-align: left;
        margin-bottom: 1;
        border-bottom: solid $primary;
    }

    #agent-search {
        margin-bottom: 1;
        width: 100%;
    }

    #agent-list-table {
        height: 20;
        min-height: 15;
        margin-bottom: 1;
        border: solid $primary;
    }

    #agent-details {
        padding: 1;
        height: 10;
        border: solid $primary;
        margin-bottom: 1;
    }

    #agent-action-buttons {
        height: 3;
        align: center middle;
    }

    #agent-action-buttons Button {
        margin: 0 1;
    }

    #agent-category-tabs {
        height: 3;
        margin-bottom: 1;
    }

    #agent-category-tabs TabPane {
        padding: 0;
    }

    #view-properties-dialog {
        align: center middle;
        background: $panel;
        border: thick $primary;
        padding: 2;
        margin: 2 4;
        width: 90%;
        height: 80%;
    }

    #properties-title {
        text-style: bold;
        margin-bottom: 1;
    }

    #properties-viewer {
        width: 100%;
        height: 100%;
        margin: 1 0;
    }

    #properties-buttons {
        align: center middle;
        height: 3;
        margin-top: 1;
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
        padding: 0 1;
        height: 1;
        margin-bottom: 1;
        color: $primary;
        border-bottom: solid $primary;
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
        Binding("enter", "select_nav", "Select", show=False),
        Binding("ctrl+right", "focus_next_pane", "Next Pane", show=False),
        Binding("ctrl+left", "focus_prev_pane", "Prev Pane", show=False),
    ]

    def __init__(
        self, current_scope: str = "project", project_dir: Optional[Path] = None
    ):
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
        self.version_service.get_version()
        yield Header(show_clock=True)
        yield Rule(line_style="heavy")

        with Horizontal(id="main-layout"):
            # Sidebar navigation
            with Container(id="sidebar"):
                # Use Static instead of Label for the header
                yield Static("MENU", classes="sidebar-title")
                # Create ListView with simple text items - no emojis, clean look
                yield ListView(
                    ListItem(Label("Agents"), id="nav-agents"),
                    ListItem(Label("Templates"), id="nav-templates"),
                    ListItem(Label("Behaviors"), id="nav-behaviors"),
                    ListItem(Label("Settings"), id="nav-settings"),
                    id="nav-list",
                )

            # Main content area with ContentSwitcher
            with ContentSwitcher(initial="agents", id="content-switcher"):
                # Create all screens with proper IDs for ContentSwitcher
                yield AgentManagementScreen(self.agent_manager, id="agents")
                yield TemplateEditingScreen(
                    self.agent_manager,
                    self.current_scope,
                    self.project_dir,
                    id="templates",
                )
                yield BehaviorFilesScreen(
                    self.current_scope, self.project_dir, id="behaviors"
                )
                yield SettingsScreen(
                    self.current_scope, self.project_dir, id="settings"
                )

        # Footer with shortcuts
        yield Footer()

    def on_mount(self):
        """Initialize the application."""
        self.title = f"Claude MPM Configuration v{self.version_service.get_version()}"
        self.sub_title = f"Scope: {self.current_scope.upper()} | {self.project_dir}"

        # Get the navigation list
        list_view = self.query_one("#nav-list", ListView)

        # Highlight the first navigation item
        if list_view.children:
            first_item = list_view.children[0]
            if isinstance(first_item, ListItem):
                first_item.add_class("active")

        # Set focus on the navigation list to enable keyboard navigation
        list_view.focus()

        # Set initial index to 0 (highlight first item)
        list_view.index = 0

        # Initialize all screens that are Containers in ContentSwitcher
        # since ContentSwitcher doesn't automatically call their on_mount
        def initialize_screens():
            try:
                # Initialize agent management screen
                agent_screen = self.query_one("#agents", AgentManagementScreen)
                agent_screen.on_mount()
                self.log("Initialized AgentManagementScreen")

                # Initialize template screen
                template_screen = self.query_one("#templates", TemplateEditingScreen)
                template_screen.on_mount()
                self.log("Initialized TemplateEditingScreen")

                # Initialize behavior screen
                behavior_screen = self.query_one("#behaviors", BehaviorFilesScreen)
                behavior_screen.on_mount()
                self.log("Initialized BehaviorFilesScreen")

                # Initialize settings screen
                settings_screen = self.query_one("#settings", SettingsScreen)
                settings_screen.on_mount()
                self.log("Initialized SettingsScreen")

            except Exception as e:
                self.log(f"Error initializing screens: {e}")

        # Use call_after_refresh to ensure DOM is ready
        self.call_after_refresh(initialize_screens)

    def _on_nav_index_changed(self, old_index: int, new_index: int) -> None:
        """Watch for navigation list index changes as a fallback."""
        if new_index is not None:
            screens = ["agents", "templates", "behaviors", "settings"]
            if 0 <= new_index < len(screens):
                screen_name = screens[new_index]
                self.log(f"Index changed to {new_index}, switching to {screen_name}")
                # Only switch if it's a different screen
                if screen_name != self.current_screen_name:
                    self.switch_screen(screen_name)

    @on(ListView.Selected, "#nav-list")
    def on_nav_list_selected(self, event: ListView.Selected) -> None:
        """Handle navigation ListView selection - primary handler."""
        self.log("Navigation ListView.Selected triggered")

        # Map item IDs to screen names
        id_to_screen = {
            "nav-agents": "agents",
            "nav-templates": "templates",
            "nav-behaviors": "behaviors",
            "nav-settings": "settings",
        }

        # Try to get screen name from item ID first
        if event.item and hasattr(event.item, "id") and event.item.id:
            screen_name = id_to_screen.get(event.item.id)
            if screen_name:
                self.log(f"Selected item by ID: {event.item.id} -> {screen_name}")
                self.switch_screen(screen_name)
                self.notify(f"Switched to {screen_name.title()}", timeout=1)
                return

        # Fallback to index-based selection
        if event.list_view and event.list_view.index is not None:
            screens = ["agents", "templates", "behaviors", "settings"]
            index = event.list_view.index
            if 0 <= index < len(screens):
                screen_name = screens[index]
                self.log(f"Selected by index: {index} -> {screen_name}")
                self.switch_screen(screen_name)
                self.notify(f"Switched to {screen_name.title()}", timeout=1)

    @on(ListView.Highlighted, "#nav-list")
    def on_nav_list_highlighted(self, event: ListView.Highlighted) -> None:
        """Handle ListView highlight changes for mouse hover."""
        # This helps with mouse interaction - when user hovers over items
        if event.list_view and event.list_view.index is not None:
            self.log(f"Navigation item highlighted at index: {event.list_view.index}")

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Traditional method-name based handler as ultimate fallback."""
        self.log("on_list_view_selected (traditional handler) triggered")

        # Try to get the navigation list
        try:
            nav_list = self.query_one("#nav-list", ListView)
            if nav_list and nav_list.index is not None:
                screens = ["agents", "templates", "behaviors", "settings"]
                if 0 <= nav_list.index < len(screens):
                    screen_name = screens[nav_list.index]
                    self.log(f"Traditional handler: switching to {screen_name}")
                    self.switch_screen(screen_name)
                    self.notify(f"Switched to {screen_name.title()}", timeout=1)
        except Exception as e:
            self.log(f"Error in traditional handler: {e}")

    def switch_screen(self, screen_name: str):
        """Switch to a different screen."""
        if screen_name == self.current_screen_name:
            return

        try:
            # Use ContentSwitcher to switch screens
            switcher = self.query_one("#content-switcher", ContentSwitcher)
            switcher.current = screen_name
            self.current_screen_name = screen_name

            # Update navigation highlight
            list_view = self.query_one("#nav-list", ListView)
            for item in list_view.children:
                if isinstance(item, ListItem):
                    item.remove_class("active")
                    if item.id == f"nav-{screen_name}":
                        item.add_class("active")

        except Exception as e:
            self.notify(f"Error switching screen: {e}", severity="error")

    def action_select_nav(self):
        """Handle Enter key on navigation list."""
        self.log("action_select_nav triggered")
        try:
            # Check if the navigation list has focus
            list_view = self.query_one("#nav-list", ListView)
            if self.focused == list_view and list_view.index is not None:
                screens = ["agents", "templates", "behaviors", "settings"]
                if 0 <= list_view.index < len(screens):
                    self.log(f"Selecting screen via Enter: {screens[list_view.index]}")
                    self.switch_screen(screens[list_view.index])
        except Exception as e:
            self.log(f"Error in action_select_nav: {e}")

    def action_navigate(self, screen: str):
        """Navigate to a specific screen via keyboard shortcut."""
        self.switch_screen(screen)

        # Also update the ListView selection to match
        list_view = self.query_one("#nav-list", ListView)
        screens = ["agents", "templates", "behaviors", "settings"]
        if screen in screens:
            index = screens.index(screen)
            list_view.index = index

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
            "Ctrl+→/←: Navigate panes\n"
            "Enter: Select/Activate",
            title="Help",
            timeout=10,
        )

    def action_focus_next_pane(self):
        """Focus next pane in agent management screen."""
        try:
            current_screen = self.query_one(
                "#content-switcher", ContentSwitcher
            ).current
            if current_screen == "agents":
                agent_screen = self.query_one("#agents", AgentManagementScreen)
                agent_screen.focus_next_pane()
        except Exception:
            pass

    def action_focus_prev_pane(self):
        """Focus previous pane in agent management screen."""
        try:
            current_screen = self.query_one(
                "#content-switcher", ContentSwitcher
            ).current
            if current_screen == "agents":
                agent_screen = self.query_one("#agents", AgentManagementScreen)
                agent_screen.focus_previous_pane()
        except Exception:
            pass


def can_use_tui() -> bool:
    """Check if the terminal supports full-screen TUI mode."""
    # Check if we're in an interactive terminal
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        return False

    # Check if we're in a supported terminal
    term = os.environ.get("TERM", "")
    if not term or term == "dumb":
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


def launch_tui(
    current_scope: str = "project", project_dir: Optional[Path] = None
) -> CommandResult:
    """Launch the Textual TUI application."""
    try:
        app = ConfigureTUI(current_scope, project_dir)
        app.run()
        return CommandResult.success_result("Configuration completed")
    except KeyboardInterrupt:
        return CommandResult.success_result("Configuration cancelled")
    except Exception as e:
        return CommandResult.error_result(f"TUI error: {e}")

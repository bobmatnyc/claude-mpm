"""Interactive Agent Creation Wizard for Claude MPM.

This module provides a step-by-step interactive wizard for creating and managing
local agents with user-friendly prompts, intelligent defaults, and validation.
"""

import json
import re
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import questionary
from questionary import Style

from claude_mpm.core.logging_config import get_logger
from claude_mpm.services.agents.local_template_manager import (
    LocalAgentTemplate,
    LocalAgentTemplateManager,
)
from claude_mpm.utils.agent_filters import apply_all_filters

logger = get_logger(__name__)

# Questionary style matching Rich cyan theme (consistent with configure.py)
QUESTIONARY_STYLE = Style(
    [
        ("selected", "fg:cyan bold"),
        ("pointer", "fg:cyan bold"),
        ("highlighted", "fg:cyan"),
        ("question", "fg:cyan bold"),
    ]
)


class AgentWizard:
    """
    Interactive wizard for agent creation and management.

    DEPRECATED: This interface has been superseded by the unified
    configuration interface. Please use 'claude-mpm config' instead.

    This class is retained for backward compatibility but will be
    removed in a future version.
    """

    def __init__(self):
        """Initialize the agent wizard."""
        self.manager = LocalAgentTemplateManager()
        self.logger = logger

        # Initialize remote discovery services
        try:
            from claude_mpm.services.agents.git_source_manager import GitSourceManager

            self.source_manager = GitSourceManager()
            self.discovery_enabled = True
            self.logger.debug("Remote agent discovery enabled")
        except Exception as e:
            self.logger.warning(f"Failed to initialize remote discovery: {e}")
            self.source_manager = None
            self.discovery_enabled = False

    @staticmethod
    def _calculate_column_widths(
        terminal_width: int, columns: Dict[str, int]
    ) -> Dict[str, int]:
        """Calculate dynamic column widths based on terminal size.

        Args:
            terminal_width: Current terminal width in characters
            columns: Dict mapping column names to minimum widths

        Returns:
            Dict mapping column names to calculated widths

        Design:
            - Ensures minimum widths are respected
            - Distributes extra space proportionally
            - Handles narrow terminals gracefully (minimum 80 chars)
        """
        # Ensure minimum terminal width
        min_terminal_width = 80
        terminal_width = max(terminal_width, min_terminal_width)

        # Calculate total minimum width needed
        total_min_width = sum(columns.values())

        # Account for spacing between columns
        overhead = len(columns) + 1
        available_width = terminal_width - overhead

        # If we have extra space, distribute proportionally
        if available_width > total_min_width:
            extra_space = available_width - total_min_width
            total_weight = sum(columns.values())

            result = {}
            for col_name, min_width in columns.items():
                # Distribute extra space based on minimum width proportion
                proportion = min_width / total_weight
                extra = int(extra_space * proportion)
                result[col_name] = min_width + extra
            return result
        # Terminal too narrow, use minimum widths
        return columns.copy()

    def run_interactive_create(self) -> Tuple[bool, str]:
        """Run interactive agent creation wizard.

        Returns:
            Tuple of (success, message)
        """
        try:
            print("\n" + "=" * 60)
            print("🧙‍♂️  Agent Creation Wizard")
            print("=" * 60)
            print("\nI'll guide you through creating a custom local agent.")
            print("Press Ctrl+C anytime to cancel.\n")

            # Step 1: Agent ID
            agent_id = self._get_agent_id()
            if not agent_id:
                return False, "Agent creation cancelled"

            # Step 2: Agent Name
            agent_name = self._get_agent_name(agent_id)

            # Step 3: Agent Type/Category
            agent_type = self._get_agent_type()

            # Step 4: Model Selection
            model = self._get_model_choice()

            # Step 5: Inheritance Option
            parent_agent, _base_template = self._get_inheritance_option()

            # Step 6: Capabilities Configuration
            capabilities = self._get_capabilities_configuration()

            # Step 7: Description
            description = self._get_agent_description(agent_type)

            # Step 8: Instructions
            instructions = self._get_agent_instructions(
                agent_id, agent_type, parent_agent
            )

            # Step 9: Preview Configuration
            config_preview = self._create_preview_config(
                agent_id,
                agent_name,
                agent_type,
                model,
                parent_agent,
                capabilities,
                description,
                instructions,
            )

            # Step 10: Confirmation
            if not self._confirm_creation(config_preview):
                return False, "Agent creation cancelled"

            # Step 11: Create and Save Agent
            template = self._create_agent_template(
                agent_id,
                agent_name,
                agent_type,
                model,
                parent_agent,
                capabilities,
                description,
                instructions,
            )

            template_file = self.manager.save_local_template(template, "project")

            print(f"\n✅ Agent '{agent_id}' created successfully!")
            print(f"📁 Saved to: {template_file}")
            print("\n💡 Next steps:")
            print(
                f"   • Deploy: claude-mpm agent-manager deploy-local --agent-id {agent_id}"
            )
            print(f"   • Edit: Edit {template_file} directly")
            print(f"   • Test: claude-mpm run --agent {agent_id}")

            return True, f"Agent '{agent_id}' created successfully"

        except KeyboardInterrupt:
            print("\n\n❌ Agent creation cancelled by user")
            return False, "Agent creation cancelled"
        except Exception as e:
            error_msg = f"Failed to create agent: {e}"
            self.logger.error(error_msg, exc_info=True)
            return False, error_msg

    def _merge_agent_sources(self) -> List[Dict[str, Any]]:
        """
        Merge agents from all sources with precedence: local > discovered.

        Returns list of agents with metadata:
        {
            "agent_id": "engineer/backend/python-engineer",
            "name": "Python Engineer",
            "description": "...",
            "source_type": "system" | "project",
            "source_identifier": "bobmatnyc/claude-mpm-agents",
            "category": "engineer/backend",
            "deployed": True | False,
            "path": "/path/to/agent.md"
        }
        """
        agents = {}

        # Get discovered agents (system/user sources)
        if self.discovery_enabled and self.source_manager:
            try:
                discovered = self.source_manager.list_cached_agents()
                self.logger.debug(f"Discovered {len(discovered)} remote agents")

                for agent in discovered:
                    agent_id = agent.get("agent_id", "")
                    if not agent_id:
                        continue

                    # Extract metadata
                    metadata = agent.get("metadata", {})
                    agents[agent_id] = {
                        "agent_id": agent_id,
                        "name": metadata.get("name", agent_id),
                        "description": metadata.get("description", ""),
                        "source_type": "system",
                        "source_identifier": agent.get("source", "unknown"),
                        "category": agent.get("category", ""),
                        "deployed": False,  # Will be updated below
                        "path": agent.get("path", agent.get("source_file", "")),
                    }
            except Exception as e:
                self.logger.warning(f"Failed to discover remote agents: {e}")

        # Get local agents (project-level, highest precedence)
        local_templates = self.manager.list_local_templates()
        for template in local_templates:
            agent_id = template.agent_id
            agents[agent_id] = {
                "agent_id": agent_id,
                "name": template.metadata.get("name", agent_id),
                "description": template.metadata.get("description", ""),
                "source_type": "project",
                "source_identifier": "local",
                "category": template.metadata.get("category", ""),
                "deployed": True,  # Local templates are deployed
                "path": str(self._get_template_path(template)),
            }

        # Check deployment status for discovered agents
        deployed_dir = Path.cwd() / ".claude" / "agents"
        if deployed_dir.exists():
            for agent_id, agent_data in agents.items():
                deployed_file = deployed_dir / f"{agent_id.replace('/', '-')}.md"
                # Also check hierarchical path
                deployed_file_alt = deployed_dir / f"{agent_id.split('/')[-1]}.md"
                if deployed_file.exists() or deployed_file_alt.exists():
                    agent_data["deployed"] = True

        # Filter BASE_AGENT from all agent lists (1M-502 Phase 1)
        # BASE_AGENT is a build tool, not a deployable agent
        agent_list = list(agents.values())
        return apply_all_filters(agent_list, filter_base=True, filter_deployed=False)

    def run_interactive_manage(self) -> Tuple[bool, str]:
        """Run interactive agent management menu.

        Returns:
            Tuple of (success, message)
        """
        try:
            while True:
                # Get merged agents from all sources
                all_agents = self._merge_agent_sources()

                print("\n" + "=" * 60)
                print("🔧  Agent Management Menu")
                print("=" * 60)

                if not all_agents:
                    print(
                        "\n📭 No agents found. Configure sources with 'claude-mpm agents discover'"
                    )
                    print("\n1. Create new agent")
                    print("2. Import agents")
                    print("3. Exit")

                    choice = input("\nSelect option [1-3]: ").strip()

                    if choice == "1":
                        return self.run_interactive_create()
                    if choice == "2":
                        return self._interactive_import()
                    if choice == "3":
                        return True, "Management menu exited"
                    print("❌ Invalid choice. Please try again.")
                    continue

                # Show existing agents in a table with dynamic widths
                print(f"\n📋 Found {len(all_agents)} agent(s):\n")

                # Calculate dynamic column widths based on terminal size
                terminal_width = shutil.get_terminal_size().columns
                min_widths = {
                    "#": 4,
                    "Agent ID": 30,
                    "Name": 20,
                    "Source": 15,
                    "Status": 10,
                }
                widths = self._calculate_column_widths(terminal_width, min_widths)

                # Print header with dynamic widths
                print(
                    f"{'#':<{widths['#']}} "
                    f"{'Agent ID':<{widths['Agent ID']}} "
                    f"{'Name':<{widths['Name']}} "
                    f"{'Source':<{widths['Source']}} "
                    f"{'Status':<{widths['Status']}}"
                )
                separator_width = sum(widths.values()) + len(widths) - 1
                print("-" * separator_width)

                for i, agent in enumerate(all_agents, 1):
                    agent_id = agent["agent_id"]
                    # Truncate to fit dynamic width
                    if len(agent_id) > widths["Agent ID"]:
                        agent_id = agent_id[: widths["Agent ID"] - 1] + "…"

                    name = agent["name"]
                    if len(name) > widths["Name"]:
                        name = name[: widths["Name"] - 1] + "…"

                    source_label = (
                        f"[{agent['source_type']}] {agent['source_identifier']}"
                    )
                    if len(source_label) > widths["Source"]:
                        source_label = source_label[: widths["Source"] - 1] + "…"

                    status = "✓ Deployed" if agent["deployed"] else "Available"

                    print(
                        f"{i:<{widths['#']}} "
                        f"{agent_id:<{widths['Agent ID']}} "
                        f"{name:<{widths['Name']}} "
                        f"{source_label:<{widths['Source']}} "
                        f"{status:<{widths['Status']}}"
                    )

                # Build menu choices with arrow-key navigation
                menu_choices = []

                # Add agent viewing options (1-N)
                for i, agent in enumerate(all_agents, 1):
                    menu_choices.append(f"{i}. View agent: {agent['agent_id']}")

                # Add action options
                menu_choices.append(f"{len(all_agents) + 1}. Deploy agent")
                menu_choices.append(f"{len(all_agents) + 2}. Create new agent")
                menu_choices.append(f"{len(all_agents) + 3}. Delete agent(s)")
                menu_choices.append(f"{len(all_agents) + 4}. Import agents")
                menu_choices.append(f"{len(all_agents) + 5}. Export all agents")

                if self.discovery_enabled:
                    menu_choices.append(
                        f"{len(all_agents) + 6}. Browse & filter agents"
                    )
                    menu_choices.append(f"{len(all_agents) + 7}. Deploy preset")
                    menu_choices.append(f"{len(all_agents) + 8}. Manage agent sources")
                    menu_choices.append(f"{len(all_agents) + 9}. Exit")
                    exit_num = len(all_agents) + 9
                else:
                    menu_choices.append(f"{len(all_agents) + 6}. Exit")
                    exit_num = len(all_agents) + 6

                choice = questionary.select(
                    "Agent Management Menu:",
                    choices=menu_choices,
                    style=QUESTIONARY_STYLE,
                ).ask()

                if not choice:  # User pressed Esc
                    return True, "Management menu exited"

                # Parse choice number from "N. Description" format
                choice_num = int(choice.split(".")[0])

                if 1 <= choice_num <= len(all_agents):
                    # View agent details
                    selected_agent = all_agents[choice_num - 1]
                    self._show_agent_details(selected_agent)
                    continue
                if choice_num == len(all_agents) + 1:
                    self._deploy_agent_interactive(all_agents)
                elif choice_num == len(all_agents) + 2:
                    _, message = self.run_interactive_create()
                    if message:
                        print(f"\n{message}")
                    continue
                elif choice_num == len(all_agents) + 3:
                    local_templates = self.manager.list_local_templates()
                    _, message = self._interactive_delete_menu(local_templates)
                    if message:
                        print(f"\n{message}")
                    continue
                elif choice_num == len(all_agents) + 4:
                    _, message = self._interactive_import()
                    if message:
                        print(f"\n{message}")
                    continue
                elif choice_num == len(all_agents) + 5:
                    _success, message = self._interactive_export()
                    if message:
                        print(f"\n{message}")
                    continue
                elif choice_num == len(all_agents) + 6 and self.discovery_enabled:
                    self._browse_agents_interactive()
                    continue
                elif choice_num == len(all_agents) + 7 and self.discovery_enabled:
                    self._deploy_preset_interactive()
                    continue
                elif choice_num == len(all_agents) + 8 and self.discovery_enabled:
                    self._manage_sources_interactive()
                    continue
                elif choice_num == exit_num:
                    return True, "Management menu exited"
                else:
                    print("❌ Invalid choice. Please try again.")

        except KeyboardInterrupt:
            print("\n\n❌ Management menu cancelled")
            return False, "Management cancelled"
        except Exception as e:
            error_msg = f"Management menu error: {e}"
            self.logger.error(error_msg, exc_info=True)
            return False, error_msg

    def _get_agent_id(self) -> Optional[str]:
        """Get and validate agent ID from user."""
        while True:
            agent_id = input(
                "1. What would you like to name your agent?\n   Agent ID (lowercase, hyphens): "
            ).strip()

            if not agent_id:
                print("❌ Agent ID is required.")
                continue

            # Validate format
            if (
                not re.match(r"^[a-z][a-z0-9-]*[a-z0-9]$", agent_id)
                or len(agent_id) > 50
            ):
                print("❌ Agent ID must:")
                print("   • Start with a letter")
                print("   • Contain only lowercase letters, numbers, and hyphens")
                print("   • End with a letter or number")
                print("   • Be 50 characters or less")
                continue

            # Check for conflicts
            existing_template = self.manager.get_local_template(agent_id)
            if existing_template:
                print(f"❌ Agent '{agent_id}' already exists.")
                overwrite = (
                    input("   Overwrite existing agent? [y/N]: ").strip().lower()
                )
                if overwrite not in ["y", "yes"]:
                    continue

            return agent_id

    def _get_agent_name(self, agent_id: str) -> str:
        """Get agent display name."""
        default_name = agent_id.replace("-", " ").title()
        agent_name = input(
            f"\n2. What should be the display name? [{default_name}]: "
        ).strip()
        return agent_name or default_name

    def _get_agent_type(self) -> str:
        """Get agent type/category from user."""
        print("\n3. What type of agent is this?")
        agent_types = [
            (
                "research",
                "Research & Analysis",
                "Gathering information, analyzing data, investigating topics",
            ),
            (
                "engineer",
                "Implementation & Engineering",
                "Writing code, building features, technical development",
            ),
            (
                "qa",
                "Quality Assurance & Testing",
                "Testing code, reviewing quality, finding bugs",
            ),
            (
                "docs",
                "Documentation & Writing",
                "Creating docs, writing content, technical writing",
            ),
            (
                "ops",
                "Operations & Deployment",
                "DevOps, deployment, system administration",
            ),
            ("custom", "Custom/Other", "Specialized or unique functionality"),
        ]

        for i, (_type_id, name, desc) in enumerate(agent_types, 1):
            print(f"   [{i}] {name}")
            print(f"       {desc}")

        while True:
            choice = input(f"\nSelect type [1-{len(agent_types)}]: ").strip()

            try:
                choice_num = int(choice)
                if 1 <= choice_num <= len(agent_types):
                    return agent_types[choice_num - 1][0]
            except ValueError:
                pass

            print("❌ Invalid choice. Please select a number from the list.")

    def _get_model_choice(self) -> str:
        """Get model selection from user."""
        print("\n4. Which model should this agent use?")
        models = [
            (
                "sonnet",
                "claude-3-sonnet (balanced - recommended)",
                "Good balance of capability and speed",
            ),
            (
                "opus",
                "claude-3-opus (powerful)",
                "Most capable but slower and more expensive",
            ),
            ("haiku", "claude-3-haiku (fast)", "Fastest and most economical"),
        ]

        for i, (_model_id, name, desc) in enumerate(models, 1):
            print(f"   [{i}] {name}")
            print(f"       {desc}")

        while True:
            choice = input(f"\nSelect model [1-{len(models)}] [1]: ").strip() or "1"

            try:
                choice_num = int(choice)
                if 1 <= choice_num <= len(models):
                    return models[choice_num - 1][0]
            except ValueError:
                pass

            print("❌ Invalid choice. Please select a number from the list.")

    def _get_inheritance_option(self) -> Tuple[Optional[str], Optional[Dict]]:
        """Get inheritance option from user."""
        print("\n5. Would you like to inherit from an existing agent?")
        print("   [1] No, start fresh")
        print("   [2] Yes, inherit from system agent")

        while True:
            choice = input("\nSelect option [1-2] [1]: ").strip() or "1"

            if choice == "1":
                return None, None
            if choice == "2":
                return self._select_system_agent()
            print("❌ Invalid choice. Please select 1 or 2.")

    def _select_system_agent(self) -> Tuple[Optional[str], Optional[Dict]]:
        """Let user select a system agent to inherit from."""
        try:
            # Get available system agents
            from claude_mpm.services.agents.agent_builder import AgentBuilderService

            builder = AgentBuilderService()
            templates = builder.list_available_templates()

            if not templates:
                print("❌ No system agents found to inherit from.")
                return None, None

            print("\n   Select system agent to inherit from:")
            for i, template in enumerate(templates, 1):
                name = template.get("name", template.get("id", "Unknown"))
                description = template.get("description", "")
                print(f"      [{i}] {name}")
                if description:
                    print(f"          {description[:80]}...")

            while True:
                choice = input(f"\n   Select agent [1-{len(templates)}]: ").strip()

                try:
                    choice_num = int(choice)
                    if 1 <= choice_num <= len(templates):
                        selected = templates[choice_num - 1]
                        return selected.get("id"), selected
                except ValueError:
                    pass

                print("❌ Invalid choice. Please select a number from the list.")

        except Exception as e:
            self.logger.warning(f"Failed to load system agents: {e}")
            print("❌ Could not load system agents for inheritance.")
            return None, None

    def _get_capabilities_configuration(self) -> Dict[str, Any]:
        """Get capabilities configuration from user."""
        print("\n6. What additional capabilities should this agent have?")

        capabilities_options = [
            ("code_analysis", "Code analysis and review"),
            ("test_generation", "Test generation and validation"),
            ("security_scanning", "Security analysis and scanning"),
            ("performance_profiling", "Performance analysis and optimization"),
            ("documentation", "Documentation generation"),
            ("api_design", "API design and documentation"),
            ("data_processing", "Data processing and analysis"),
            ("web_scraping", "Web scraping and data extraction"),
        ]

        print("   Select capabilities (enter multiple numbers separated by spaces):")
        for i, (_cap_id, desc) in enumerate(capabilities_options, 1):
            print(f"   [{i}] {desc}")

        selected_capabilities = []
        while True:
            choices = input(
                f"\nSelect capabilities [1-{len(capabilities_options)}] (space-separated) [none]: "
            ).strip()

            if not choices or choices.lower() == "none":
                break

            try:
                choice_nums = [int(x) for x in choices.split()]
                valid_choices = []

                for num in choice_nums:
                    if 1 <= num <= len(capabilities_options):
                        selected_capabilities.append(capabilities_options[num - 1][0])
                        valid_choices.append(str(num))

                if valid_choices:
                    print(f"✅ Selected: {', '.join(selected_capabilities)}")
                    break
                print("❌ No valid choices selected.")
            except ValueError:
                print("❌ Please enter numbers separated by spaces.")

        return {"specializations": selected_capabilities}

    def _get_agent_description(self, agent_type: str) -> str:
        """Get agent description from user."""
        type_examples = {
            "research": "Specializes in analyzing market trends and competitive intelligence",
            "engineer": "Focused on building scalable web applications using React and Node.js",
            "qa": "Expert in automated testing and code quality assurance",
            "docs": "Creates clear technical documentation and user guides",
            "ops": "Manages CI/CD pipelines and cloud infrastructure",
            "custom": "Handles specialized domain-specific tasks",
        }

        example = type_examples.get(agent_type, "Performs specialized tasks")

        print("\n7. Describe this agent's specialty (one line):")
        print(f"   Example: {example}")

        while True:
            description = input("\n   Description: ").strip()

            if not description:
                print("❌ Description is required.")
                continue

            if len(description) > 200:
                print("❌ Description should be 200 characters or less.")
                continue

            return description

    def _get_agent_instructions(
        self, agent_id: str, agent_type: str, parent_agent: Optional[str]
    ) -> str:
        """Get agent instructions from user."""
        print("\n8. Agent Instructions:")

        if parent_agent:
            print(f"   Since you're inheriting from '{parent_agent}', you can:")
            print("   [1] Use default inherited instructions")
            print("   [2] Add custom instructions")
            print("   [3] Write completely new instructions")

            choice = input("\n   Select option [1-3] [1]: ").strip() or "1"

            if choice == "1":
                return f"Extends the {parent_agent} agent with project-specific enhancements."
            if choice == "2":
                additional = input("\n   Enter additional instructions: ").strip()
                return f"Extends the {parent_agent} agent.\n\nAdditional instructions:\n{additional}"

        # Get custom instructions
        print("   Enter custom instructions for this agent:")
        print("   (Type 'DONE' on a new line when finished)")

        lines = []
        while True:
            line = input("   ")
            if line.strip() == "DONE":
                break
            lines.append(line)

        instructions = "\n".join(lines).strip()

        if not instructions:
            # Provide default based on type
            type_defaults = {
                "research": f"You are {agent_id}, a research and analysis agent. Focus on gathering accurate information, analyzing data, and providing well-researched insights.",
                "engineer": f"You are {agent_id}, a software engineering agent. Focus on writing clean, efficient code and implementing technical solutions.",
                "qa": f"You are {agent_id}, a quality assurance agent. Focus on testing, code review, and ensuring high quality standards.",
                "docs": f"You are {agent_id}, a documentation agent. Focus on creating clear, comprehensive documentation and technical writing.",
                "ops": f"You are {agent_id}, an operations agent. Focus on deployment, infrastructure, and system administration tasks.",
                "custom": f"You are {agent_id}, a specialized agent. Focus on your specific domain expertise.",
            }
            instructions = type_defaults.get(
                agent_type, f"You are {agent_id}, a specialized agent."
            )

        return instructions

    def _create_preview_config(
        self,
        agent_id: str,
        agent_name: str,
        agent_type: str,
        model: str,
        parent_agent: Optional[str],
        capabilities: Dict,
        description: str,
        instructions: str,
    ) -> Dict[str, Any]:
        """Create preview configuration dictionary."""
        config = {
            "agent_id": agent_id,
            "name": agent_name,
            "type": agent_type,
            "model": model,
            "description": description,
            "capabilities": capabilities.get("specializations", []),
            "instructions_preview": (
                instructions[:100] + "..." if len(instructions) > 100 else instructions
            ),
        }

        if parent_agent:
            config["inherits_from"] = parent_agent

        return config

    def _confirm_creation(self, config: Dict[str, Any]) -> bool:
        """Show preview and get confirmation from user."""
        print("\n" + "=" * 60)
        print("📋  Agent Configuration Preview")
        print("=" * 60)

        print(f"Agent ID:     {config['agent_id']}")
        print(f"Name:         {config['name']}")
        print(f"Type:         {config['type']}")
        print(f"Model:        {config['model']}")
        print(f"Description:  {config['description']}")

        if config.get("inherits_from"):
            print(f"Inherits:     {config['inherits_from']}")

        if config.get("capabilities"):
            print(f"Capabilities: {', '.join(config['capabilities'])}")

        print("\nInstructions Preview:")
        print(f"  {config['instructions_preview']}")

        print("\n" + "=" * 60)

        while True:
            confirm = input("\nCreate this agent? [Y/n]: ").strip().lower()

            if confirm in ["", "y", "yes"]:
                return True
            if confirm in ["n", "no"]:
                return False
            print("❌ Please enter 'y' for yes or 'n' for no.")

    def _create_agent_template(
        self,
        agent_id: str,
        agent_name: str,
        agent_type: str,
        model: str,
        parent_agent: Optional[str],
        capabilities: Dict,
        description: str,
        instructions: str,
    ) -> LocalAgentTemplate:
        """Create the actual agent template."""
        return self.manager.create_local_template(
            agent_id=agent_id,
            name=agent_name,
            description=description,
            instructions=instructions,
            model=model,
            tools="*",
            parent_agent=parent_agent,
            tier="project",
        )

    def _manage_single_agent(self, template: LocalAgentTemplate) -> Tuple[bool, str]:
        """Manage a single agent."""
        print(f"\n🔧 Managing Agent: {template.agent_id}")
        print(f"   Name: {template.metadata.get('name', template.agent_id)}")
        print(f"   Tier: {template.tier}")
        print(f"   Version: {template.agent_version}")

        print("\n1. View details")
        print("2. Edit configuration")
        print("3. Deploy agent")
        print("4. Delete agent")
        print("5. Export agent")
        print("6. Back to menu")

        choice = input("\nSelect option [1-6]: ").strip()

        if choice == "1":
            return self._view_agent_details(template)
        if choice == "2":
            return self._edit_agent_config(template)
        if choice == "3":
            return self._deploy_single_agent(template)
        if choice == "4":
            return self._delete_agent(template)
        if choice == "5":
            return self._export_single_agent(template)
        if choice == "6":
            return True, "Back to menu"
        return False, "Invalid choice"

    def _view_agent_details(self, template: LocalAgentTemplate) -> Tuple[bool, str]:
        """View detailed agent information."""
        print(f"\n📄 Agent Details: {template.agent_id}")
        print("=" * 50)
        print(f"Name:         {template.metadata.get('name', template.agent_id)}")
        print(f"Version:      {template.agent_version}")
        print(f"Author:       {template.author}")
        print(f"Tier:         {template.tier}")
        print(f"Model:        {template.capabilities.get('model', 'unknown')}")
        print(f"Tools:        {template.capabilities.get('tools', '*')}")

        if template.parent_agent:
            print(f"Inherits:     {template.parent_agent}")

        print("\nDescription:")
        print(f"  {template.metadata.get('description', 'No description')}")

        print("\nInstructions:")
        print(
            f"  {template.instructions[:200]}{'...' if len(template.instructions) > 200 else ''}"
        )

        input("\nPress Enter to continue...")
        return True, "Agent details viewed"

    def _edit_agent_config(self, template: LocalAgentTemplate) -> Tuple[bool, str]:
        """Edit agent configuration."""
        print(f"\n✏️  Editing Agent: {template.agent_id}")
        print("This will open the JSON file in your default editor.")

        confirm = input("Continue? [y/N]: ").strip().lower()
        if confirm not in ["y", "yes"]:
            return False, "Edit cancelled"

        # Get template file path
        if template.tier == "project":
            template_file = (
                self.manager.project_agents_dir / f"{template.agent_id}.json"
            )
        else:
            template_file = self.manager.user_agents_dir / f"{template.agent_id}.json"

        # Open in editor
        import os
        import subprocess

        editor = os.environ.get("EDITOR", "nano")
        try:
            subprocess.run([editor, str(template_file)], check=True)
            return True, f"Agent {template.agent_id} edited"
        except Exception as e:
            return False, f"Failed to open editor: {e}"

    def _deploy_single_agent(self, template: LocalAgentTemplate) -> Tuple[bool, str]:
        """Deploy a single agent."""
        try:
            from claude_mpm.services.agents.deployment.local_template_deployment import (
                LocalTemplateDeploymentService,
            )

            service = LocalTemplateDeploymentService()
            success = service.deploy_single_local_template(
                template.agent_id, force=True
            )

            if success:
                return True, f"Agent '{template.agent_id}' deployed successfully"
            return False, f"Failed to deploy agent '{template.agent_id}'"

        except Exception as e:
            return False, f"Deployment error: {e}"

    def _delete_agent(self, template: LocalAgentTemplate) -> Tuple[bool, str]:
        """Delete an agent with comprehensive options."""
        print(f"\n🗑️  Delete Agent: {template.agent_id}")
        print(f"   Name: {template.metadata.get('name', template.agent_id)}")
        print(f"   Tier: {template.tier}")
        print(f"   Location: {self._get_template_path(template)}")

        # Check if deployed
        deployment_file = Path.cwd() / ".claude" / "agents" / f"{template.agent_id}.md"
        if deployment_file.exists():
            print(f"   Deployed: Yes ({deployment_file})")
        else:
            print("   Deployed: No")

        print("\nDelete options:")
        print("   [1] Delete template and deployment")
        print("   [2] Delete template only (keep deployment)")
        print("   [3] Cancel")

        option = input("\nSelect option [1-3]: ").strip()

        if option == "3":
            return False, "Deletion cancelled"

        delete_deployment = option == "1"

        # Confirmation
        print("\n⚠️  This will permanently delete:")
        print(f"   - Template: {self._get_template_path(template)}")
        if delete_deployment and deployment_file.exists():
            print(f"   - Deployment: {deployment_file}")

        # Ask about backup
        backup_choice = (
            input("\nCreate backup before deletion? [y/N]: ").strip().lower()
        )
        backup_first = backup_choice in ["y", "yes"]

        confirm = input("\nAre you sure? Type 'DELETE' to confirm: ").strip()

        if confirm != "DELETE":
            return False, "Deletion cancelled"

        # Perform deletion
        result = self.manager.delete_local_template(
            agent_id=template.agent_id,
            tier=template.tier,
            delete_deployment=delete_deployment,
            backup_first=backup_first,
        )

        if result["success"]:
            message = f"✅ Agent '{template.agent_id}' deleted successfully"
            if result["backup_location"]:
                message += f"\n   Backup saved to: {result['backup_location']}"
            message += f"\n   Removed {len(result['deleted_files'])} file(s)"
            return True, message
        errors = "\n".join(result["errors"])
        return False, f"Failed to delete agent:\n{errors}"

    def _export_single_agent(self, template: LocalAgentTemplate) -> Tuple[bool, str]:
        """Export a single agent."""
        output_dir = Path("./exported-agents")
        output_dir.mkdir(exist_ok=True)

        output_file = output_dir / f"{template.agent_id}.json"

        with output_file.open("w") as f:
            json.dump(template.to_json(), f, indent=2)

        return True, f"Agent exported to {output_file}"

    def _interactive_import(self) -> Tuple[bool, str]:
        """Interactive agent import."""
        input_dir = input("\nEnter directory path to import from: ").strip()

        if not input_dir:
            return False, "Import cancelled"

        input_path = Path(input_dir)
        if not input_path.exists():
            return False, f"Directory does not exist: {input_path}"

        # Select tier
        print("\nImport to which tier?")
        print("   [1] Project (recommended)")
        print("   [2] User")

        tier_choice = input("Select tier [1-2] [1]: ").strip() or "1"
        tier = "project" if tier_choice == "1" else "user"

        count = self.manager.import_local_templates(input_path, tier)
        return True, f"Imported {count} agents from {input_path}"

    def _interactive_export(self) -> Tuple[bool, str]:
        """Interactive agent export."""
        output_dir = input(
            "\nEnter directory path to export to [./exported-agents]: "
        ).strip()

        if not output_dir:
            output_dir = "./exported-agents"

        output_path = Path(output_dir)
        count = self.manager.export_local_templates(output_path)
        return True, f"Exported {count} agents to {output_path}"

    def _get_template_path(self, template: LocalAgentTemplate) -> Path:
        """Get the file path for a template."""
        if template.tier == "project":
            return self.manager.project_agents_dir / f"{template.agent_id}.json"
        return self.manager.user_agents_dir / f"{template.agent_id}.json"

    def _interactive_delete_menu(self, templates: list) -> Tuple[bool, str]:
        """Interactive deletion menu for multiple agents."""
        print("\n🗑️  Delete Agents")
        print("=" * 50)

        if not templates:
            return False, "No agents available to delete"

        print("\nAvailable agents:")
        for i, template in enumerate(templates, 1):
            tier_icon = "🏢" if template.tier == "project" else "👤"
            print(
                f"   [{i}] {tier_icon} {template.agent_id} - {template.metadata.get('name', template.agent_id)}"
            )

        print("\n[all] Select all agents")
        print("[0] Cancel")

        selection = input(
            "\nSelect agents to delete (comma-separated numbers or 'all'): "
        ).strip()

        if selection == "0" or not selection:
            return False, "Deletion cancelled"

        # Parse selection
        selected_templates = []
        if selection.lower() == "all":
            selected_templates = templates
        else:
            try:
                indices = [int(x.strip()) - 1 for x in selection.split(",")]
                for idx in indices:
                    if 0 <= idx < len(templates):
                        selected_templates.append(templates[idx])
                    else:
                        print(f"⚠️  Invalid selection: {idx + 1}")
            except ValueError:
                return False, "Invalid selection format"

        if not selected_templates:
            return False, "No valid agents selected"

        # Show what will be deleted
        print(f"\n📋 Selected {len(selected_templates)} agent(s) for deletion:")
        for template in selected_templates:
            tier_icon = "🏢" if template.tier == "project" else "👤"
            print(f"   - {tier_icon} {template.agent_id}")

        # Deletion options
        print("\nDelete options:")
        print("   [1] Delete templates and deployments")
        print("   [2] Delete templates only (keep deployments)")
        print("   [3] Cancel")

        option = input("\nSelect option [1-3]: ").strip()

        if option == "3":
            return False, "Deletion cancelled"

        delete_deployment = option == "1"

        # Ask about backup
        backup_choice = (
            input("\nCreate backups before deletion? [y/N]: ").strip().lower()
        )
        backup_first = backup_choice in ["y", "yes"]

        # Strong confirmation for multiple deletions
        if len(selected_templates) > 1:
            print(f"\n⚠️  WARNING: This will delete {len(selected_templates)} agents!")

        confirm = input("\nAre you sure? Type 'DELETE ALL' to confirm: ").strip()

        if confirm != "DELETE ALL":
            return False, "Deletion cancelled"

        # Perform bulk deletion
        agent_ids = [t.agent_id for t in selected_templates]
        results = self.manager.delete_multiple_templates(
            agent_ids=agent_ids,
            tier="all",  # Check all tiers since we have mixed selection
            delete_deployment=delete_deployment,
            backup_first=backup_first,
        )

        # Format results
        if results["successful"]:
            message = (
                f"✅ Successfully deleted {len(results['successful'])} agent(s):\n"
            )
            for agent_id in results["successful"]:
                message += f"   - {agent_id}\n"
        else:
            message = ""

        if results["failed"]:
            message += f"❌ Failed to delete {len(results['failed'])} agent(s):\n"
            for agent_id in results["failed"]:
                errors = results["details"][agent_id]["errors"]
                message += f"   - {agent_id}: {', '.join(errors)}\n"

        return len(results["successful"]) > 0, message.strip()

    def _show_agent_details(self, agent: Dict[str, Any]) -> None:
        """Show detailed information about an agent.

        Args:
            agent: Agent metadata dictionary
        """
        print("\n" + "=" * 60)
        print(f"📄 Agent Details: {agent['agent_id']}")
        print("=" * 60)
        print(f"Name:         {agent['name']}")
        print(f"Category:     {agent['category'] or 'N/A'}")
        print(f"Source:       [{agent['source_type']}] {agent['source_identifier']}")
        print(f"Status:       {'✓ Deployed' if agent['deployed'] else 'Available'}")
        print(f"Path:         {agent['path']}")

        if agent["description"]:
            print("\nDescription:")
            print(
                f"  {agent['description'][:200]}{'...' if len(agent['description']) > 200 else ''}"
            )

        input("\nPress Enter to continue...")

    def _deploy_agent_interactive(self, available_agents: List[Dict[str, Any]]):
        """Interactive agent deployment.

        Args:
            available_agents: List of all available agents
        """
        # Filter to non-deployed agents using improved detection (1M-502 Phase 1)
        # This checks both .claude-mpm/agents/ and .claude/agents/
        deployable = apply_all_filters(
            available_agents, filter_base=True, filter_deployed=True
        )

        if not deployable:
            print("\n✅ All agents are already deployed!")
            input("\nPress Enter to continue...")
            return

        print("\n" + "=" * 60)
        print("📦 Deploy Agent")
        print("=" * 60)
        print(f"\n{len(deployable)} agent(s) available to deploy:\n")

        # Build agent selection choices with arrow-key navigation
        agent_choices = [
            f"{i}. {agent['agent_id']} - {agent['description'][:60]}{'...' if len(agent['description']) > 60 else ''}"
            for i, agent in enumerate(deployable, 1)
        ]

        choice = questionary.select(
            "Select agent to deploy:", choices=agent_choices, style=QUESTIONARY_STYLE
        ).ask()

        if not choice:  # User pressed Esc
            return

        # Parse agent index from "N. agent_id - description" format
        idx = int(choice.split(".")[0]) - 1
        agent = deployable[idx]

        # Deploy agent using deployment service
        print(f"\n🚀 Deploying {agent['agent_id']}...")

        try:
            # Use SingleAgentDeployer for deployment
            from claude_mpm.services.agents.deployment.agent_template_builder import (
                AgentTemplateBuilder,
            )
            from claude_mpm.services.agents.deployment.agent_version_manager import (
                AgentVersionManager,
            )
            from claude_mpm.services.agents.deployment.deployment_results_manager import (
                DeploymentResultsManager,
            )
            from claude_mpm.services.agents.deployment.single_agent_deployer import (
                SingleAgentDeployer,
            )

            # Initialize deployment services
            template_builder = AgentTemplateBuilder()
            version_manager = AgentVersionManager()
            results_manager = DeploymentResultsManager(self.logger)
            deployer = SingleAgentDeployer(
                template_builder=template_builder,
                version_manager=version_manager,
                results_manager=results_manager,
                logger=self.logger,
            )

            # Prepare deployment parameters
            template_path = Path(agent["path"])
            target_dir = Path.cwd() / ".claude" / "agents"

            # Find base_agent.json in multiple possible locations
            base_agent_candidates = [
                Path.home()
                / ".claude-mpm"
                / "agents"
                / "templates"
                / "base_agent.json",
                Path.home() / ".claude-mpm" / "cache" / "base_agent.json",
                Path(__file__).parent.parent.parent
                / "agents"
                / "templates"
                / "base_agent.json",
            ]
            base_agent_path = None
            for candidate in base_agent_candidates:
                if candidate.exists():
                    base_agent_path = candidate
                    break

            if not base_agent_path:
                base_agent_path = base_agent_candidates[
                    0
                ]  # Use default even if not exists

            # Deploy the agent
            success = deployer.deploy_agent(
                agent_name=agent["agent_id"],
                templates_dir=template_path.parent,
                target_dir=target_dir,
                base_agent_path=base_agent_path,
                force_rebuild=True,
                working_directory=Path.cwd(),
            )

            if success:
                print(f"\n✅ Successfully deployed {agent['agent_id']}")
            else:
                print(f"\n❌ Failed to deploy {agent['agent_id']}")

        except Exception as e:
            self.logger.error(f"Deployment failed: {e}", exc_info=True)
            print(f"\n❌ Deployment error: {e}")

        input("\nPress Enter to continue...")

    def _browse_agents_interactive(self):
        """Interactive agent browsing with filters."""
        if not self.discovery_enabled or not self.source_manager:
            print("\n❌ Discovery service not available")
            input("\nPress Enter to continue...")
            return

        while True:
            print("\n" + "=" * 60)
            print("🔍 Browse & Filter Agents")
            print("=" * 60)

            # Show filter menu with arrow-key navigation
            print("\n[bold]Filter by:[/bold]")

            filter_choices = [
                "1. Category (engineer/backend, qa, ops, etc.)",
                "2. Language (python, typescript, rust, etc.)",
                "3. Framework (react, nextjs, flask, etc.)",
                "4. Show all agents",
                "← Back to main menu",
            ]

            choice = questionary.select(
                "Browse & Filter Agents:",
                choices=filter_choices,
                style=QUESTIONARY_STYLE,
            ).ask()

            if not choice or "Back" in choice:
                break

            # Parse choice number if it starts with a digit
            if choice[0].isdigit():
                choice_num = choice.split(".")[0]
            else:
                break

            filtered_agents = []
            filter_description = ""

            if choice_num == "1":
                # Category filtering with arrow-key navigation
                categories = [
                    "engineer/backend",
                    "engineer/frontend",
                    "qa",
                    "ops",
                    "documentation",
                    "universal",
                ]

                cat_choices = [f"{idx}. {cat}" for idx, cat in enumerate(categories, 1)]

                cat_choice = questionary.select(
                    "Select category:", choices=cat_choices, style=QUESTIONARY_STYLE
                ).ask()

                if not cat_choice:  # User pressed Esc
                    continue

                # Parse category from "N. category" format
                cat_idx = int(cat_choice.split(".")[0]) - 1
                category = categories[cat_idx]
                all_agents = self._merge_agent_sources()
                filtered_agents = [
                    a for a in all_agents if a.get("category", "").startswith(category)
                ]
                filter_description = f"Category: {category}"

            elif choice_num == "2":
                # Language filtering (using AUTO-DEPLOY-INDEX if available)
                language = input(
                    "\nEnter language (python, typescript, rust, go, etc.): "
                ).strip()

                try:
                    # Find AUTO-DEPLOY-INDEX.md in agent repository
                    from claude_mpm.services.agents.auto_deploy_index_parser import (
                        AutoDeployIndexParser,
                    )

                    index_path = (
                        Path.home()
                        / ".claude-mpm"
                        / "cache"
                        / "agents"
                        / "bobmatnyc"
                        / "claude-mpm-agents"
                        / "AUTO-DEPLOY-INDEX.md"
                    )
                    if not index_path.exists():
                        print(
                            f"[yellow]Could not find AUTO-DEPLOY-INDEX.md at: {index_path}[/yellow]"
                        )
                        input("\nPress Enter to continue...")
                        continue

                    parser = AutoDeployIndexParser(index_path)
                    lang_agents = parser.get_agents_by_language(language.lower())

                    # Get full agent details from discovery
                    all_agents = self._merge_agent_sources()
                    agent_ids = lang_agents.get("core", []) + lang_agents.get(
                        "optional", []
                    )
                    filtered_agents = [
                        a for a in all_agents if a["agent_id"] in agent_ids
                    ]
                    filter_description = f"Language: {language}"
                except Exception as e:
                    self.logger.error(f"Language filter error: {e}", exc_info=True)
                    print(f"[yellow]Could not filter by language: {e}[/yellow]")
                    input("\nPress Enter to continue...")
                    continue

            elif choice_num == "3":
                # Framework filtering
                framework = input(
                    "\nEnter framework (react, nextjs, flask, django, etc.): "
                ).strip()

                try:
                    from claude_mpm.services.agents.auto_deploy_index_parser import (
                        AutoDeployIndexParser,
                    )

                    index_path = (
                        Path.home()
                        / ".claude-mpm"
                        / "cache"
                        / "agents"
                        / "bobmatnyc"
                        / "claude-mpm-agents"
                        / "AUTO-DEPLOY-INDEX.md"
                    )
                    if not index_path.exists():
                        print(
                            f"[yellow]Could not find AUTO-DEPLOY-INDEX.md at: {index_path}[/yellow]"
                        )
                        input("\nPress Enter to continue...")
                        continue

                    parser = AutoDeployIndexParser(index_path)
                    framework_agent_ids = parser.get_agents_by_framework(
                        framework.lower()
                    )

                    all_agents = self._merge_agent_sources()
                    filtered_agents = [
                        a for a in all_agents if a["agent_id"] in framework_agent_ids
                    ]
                    filter_description = f"Framework: {framework}"
                except Exception as e:
                    self.logger.error(f"Framework filter error: {e}", exc_info=True)
                    print(f"[yellow]Could not filter by framework: {e}[/yellow]")
                    input("\nPress Enter to continue...")
                    continue

            elif choice_num == "4":
                # Show all agents
                filtered_agents = self._merge_agent_sources()
                filter_description = "All agents"
            else:
                print("❌ Invalid choice")
                input("\nPress Enter to continue...")
                continue

            # Display filtered results
            print("\n" + "=" * 60)
            print(f"📋 {filter_description} ({len(filtered_agents)} agents)")
            print("=" * 60)

            if not filtered_agents:
                print("\n[yellow]No agents found matching filter[/yellow]")
            else:
                print(f"\n{'#':<4} {'Agent ID':<40} {'Name':<25} {'Status':<12}")
                print("-" * 85)

                for idx, agent in enumerate(filtered_agents, 1):
                    agent_id = (
                        agent["agent_id"][:39]
                        if len(agent["agent_id"]) > 39
                        else agent["agent_id"]
                    )
                    name = (
                        agent["name"][:24] if len(agent["name"]) > 24 else agent["name"]
                    )
                    status = "✓ Deployed" if agent.get("deployed") else "Available"
                    print(f"{idx:<4} {agent_id:<40} {name:<25} {status:<12}")

            print("\n[bold]Actions:[/bold]")
            print("  [d] Deploy agent from this list")
            print("  [v] View agent details")
            print("  [n] New filter")
            print("  [b] Back to main menu")

            action = input("\nSelect action: ").strip()

            if action == "b":
                break
            if action == "n":
                continue
            if action == "d":
                self._deploy_from_filtered_list(filtered_agents)
            elif action == "v":
                self._view_from_filtered_list(filtered_agents)
            else:
                print("❌ Invalid choice")
                input("\nPress Enter to continue...")

    def _deploy_from_filtered_list(self, agents: List[Dict[str, Any]]):
        """Deploy an agent from a filtered list.

        Args:
            agents: List of agent dictionaries with metadata
        """
        if not agents:
            print("\n[yellow]No agents in list[/yellow]")
            input("\nPress Enter to continue...")
            return

        deployable = [a for a in agents if not a.get("deployed")]

        if not deployable:
            print("\n[yellow]All agents in this list are already deployed[/yellow]")
            input("\nPress Enter to continue...")
            return

        # Build agent selection choices
        agent_choices = [
            f"{i}. {agent['agent_id']}" for i, agent in enumerate(agents, 1)
        ]

        agent_choice = questionary.select(
            "Select agent to deploy:", choices=agent_choices, style=QUESTIONARY_STYLE
        ).ask()

        if not agent_choice:  # User pressed Esc
            return

        # Parse agent index from "N. agent_id" format
        idx = int(agent_choice.split(".")[0]) - 1
        agent = agents[idx]

        if agent.get("deployed"):
            print(f"\n[yellow]{agent['agent_id']} is already deployed[/yellow]")
        else:
            print(f"\n🚀 Deploying {agent['agent_id']}...")

            try:
                from claude_mpm.services.agents.deployment.agent_template_builder import (
                    AgentTemplateBuilder,
                )
                from claude_mpm.services.agents.deployment.agent_version_manager import (
                    AgentVersionManager,
                )
                from claude_mpm.services.agents.deployment.deployment_results_manager import (
                    DeploymentResultsManager,
                )
                from claude_mpm.services.agents.deployment.single_agent_deployer import (
                    SingleAgentDeployer,
                )

                # Initialize deployment services
                template_builder = AgentTemplateBuilder()
                version_manager = AgentVersionManager()
                results_manager = DeploymentResultsManager(self.logger)
                deployer = SingleAgentDeployer(
                    template_builder=template_builder,
                    version_manager=version_manager,
                    results_manager=results_manager,
                    logger=self.logger,
                )

                # Prepare deployment parameters
                template_path = Path(agent["path"])
                target_dir = Path.cwd() / ".claude" / "agents"

                # Find base_agent.json in multiple possible locations
                base_agent_candidates = [
                    Path.home()
                    / ".claude-mpm"
                    / "agents"
                    / "templates"
                    / "base_agent.json",
                    Path.home() / ".claude-mpm" / "cache" / "base_agent.json",
                    Path(__file__).parent.parent.parent
                    / "agents"
                    / "templates"
                    / "base_agent.json",
                ]
                base_agent_path = None
                for candidate in base_agent_candidates:
                    if candidate.exists():
                        base_agent_path = candidate
                        break

                if not base_agent_path:
                    base_agent_path = base_agent_candidates[
                        0
                    ]  # Use default even if not exists

                # Deploy the agent
                success = deployer.deploy_agent(
                    agent_name=agent["agent_id"],
                    templates_dir=template_path.parent,
                    target_dir=target_dir,
                    base_agent_path=base_agent_path,
                    force_rebuild=True,
                    working_directory=Path.cwd(),
                )

                if success:
                    print(f"[green]✓ Successfully deployed {agent['agent_id']}[/green]")
                else:
                    print(f"[red]✗ Failed to deploy {agent['agent_id']}[/red]")

            except Exception as e:
                self.logger.error(f"Deployment error: {e}", exc_info=True)
                print(f"❌ Deployment error: {e}")

        input("\nPress Enter to continue...")

    def _view_from_filtered_list(self, agents: List[Dict[str, Any]]):
        """View details of an agent from filtered list.

        Args:
            agents: List of agent dictionaries with metadata
        """
        if not agents:
            print("\n[yellow]No agents in list[/yellow]")
            input("\nPress Enter to continue...")
            return

        # Build agent selection choices
        agent_choices = [
            f"{i}. {agent['agent_id']}" for i, agent in enumerate(agents, 1)
        ]

        agent_choice = questionary.select(
            "Select agent to view:", choices=agent_choices, style=QUESTIONARY_STYLE
        ).ask()

        if not agent_choice:  # User pressed Esc
            return

        # Parse agent index from "N. agent_id" format
        idx = int(agent_choice.split(".")[0]) - 1
        agent = agents[idx]
        self._show_agent_details(agent)

    def _deploy_preset_interactive(self):
        """Interactive preset deployment with preview and confirmation."""
        from claude_mpm.services.agents.agent_preset_service import AgentPresetService

        if not self.source_manager:
            print("\n❌ Source manager not available")
            input("\nPress Enter to continue...")
            return

        preset_service = AgentPresetService(self.source_manager)

        while True:
            print("\n" + "=" * 60)
            print("📦 Deploy Agent Preset")
            print("=" * 60)

            # List available presets
            presets = preset_service.list_presets()

            print(f"\n{len(presets)} preset(s) available:\n")
            print(f"{'#':<4} {'Preset':<20} {'Agents':<10} {'Description':<50}")
            print("-" * 90)

            for idx, preset in enumerate(presets, 1):
                description = (
                    preset["description"][:48] + "..."
                    if len(preset["description"]) > 50
                    else preset["description"]
                )
                print(
                    f"{idx:<4} {preset['name']:<20} {len(preset.get('agents', [])):<10} {description:<50}"
                )

            print("\n[bold]Actions:[/bold]")
            print("  [1-11] Select preset number")
            print("  [b] Back to main menu")

            choice = input("\nSelect preset number or action: ").strip()

            if choice.lower() == "b":
                break

            try:
                idx = int(choice) - 1
                if idx < 0 or idx >= len(presets):
                    raise ValueError("Out of range")

                preset_name = presets[idx]["name"]

                # Show preset details
                print("\n" + "=" * 60)
                print(f"📦 Preset: {preset_name}")
                print("=" * 60)
                print(f"\n[bold]Description:[/bold] {presets[idx]['description']}\n")

                # Resolve preset
                print("🔍 Resolving preset agents...")
                resolution = preset_service.resolve_agents(
                    preset_name, validate_availability=True
                )

                if resolution.get("missing_agents"):
                    print(
                        f"\n⚠️  [red]Missing agents ({len(resolution['missing_agents'])}):[/red]"
                    )
                    for agent_id in resolution["missing_agents"]:
                        print(f"  • {agent_id}")
                    print("\n[yellow]Cannot deploy preset with missing agents[/yellow]")
                    input("\nPress Enter to continue...")
                    continue

                # Show agents to deploy
                agents = resolution.get("agents", [])
                print(f"\n[bold]Agents to deploy ({len(agents)}):[/bold]\n")

                print(f"{'Agent ID':<40} {'Name':<25} {'Source':<25}")
                print("-" * 95)

                for agent in agents:
                    # Get agent metadata
                    agent_metadata = agent.get("metadata", {})
                    agent_meta_data = agent_metadata.get("metadata", {})

                    agent_id = (
                        agent.get("agent_id", "")[:39]
                        if len(agent.get("agent_id", "")) > 39
                        else agent.get("agent_id", "")
                    )
                    name = (
                        agent_meta_data.get("name", "")[:24]
                        if len(agent_meta_data.get("name", "")) > 24
                        else agent_meta_data.get("name", "")
                    )
                    source = (
                        agent.get("source", "unknown")[:24]
                        if len(agent.get("source", "unknown")) > 24
                        else agent.get("source", "unknown")
                    )

                    print(f"{agent_id:<40} {name:<25} {source:<25}")

                # Confirm deployment
                print("\n[bold]Options:[/bold]")
                print("  [y] Deploy all agents")
                print("  [n] Cancel")

                confirm = input("\nProceed with deployment? ").strip()

                if confirm.lower() == "y":
                    print(f"\n🚀 Deploying preset '{preset_name}'...\n")

                    from claude_mpm.services.agents.deployment.agent_template_builder import (
                        AgentTemplateBuilder,
                    )
                    from claude_mpm.services.agents.deployment.agent_version_manager import (
                        AgentVersionManager,
                    )
                    from claude_mpm.services.agents.deployment.deployment_results_manager import (
                        DeploymentResultsManager,
                    )
                    from claude_mpm.services.agents.deployment.single_agent_deployer import (
                        SingleAgentDeployer,
                    )

                    # Initialize deployment services once for all agents
                    template_builder = AgentTemplateBuilder()
                    version_manager = AgentVersionManager()
                    results_manager = DeploymentResultsManager(self.logger)
                    deployer = SingleAgentDeployer(
                        template_builder=template_builder,
                        version_manager=version_manager,
                        results_manager=results_manager,
                        logger=self.logger,
                    )

                    target_dir = Path.cwd() / ".claude" / "agents"

                    # Find base_agent.json
                    base_agent_candidates = [
                        Path.home()
                        / ".claude-mpm"
                        / "agents"
                        / "templates"
                        / "base_agent.json",
                        Path.home() / ".claude-mpm" / "cache" / "base_agent.json",
                        Path(__file__).parent.parent.parent
                        / "agents"
                        / "templates"
                        / "base_agent.json",
                    ]
                    base_agent_path = None
                    for candidate in base_agent_candidates:
                        if candidate.exists():
                            base_agent_path = candidate
                            break

                    if not base_agent_path:
                        base_agent_path = base_agent_candidates[0]

                    deployed = 0
                    failed = 0

                    for agent in agents:
                        agent_id = agent["agent_id"]
                        agent_metadata = agent.get("metadata", {})
                        agent_path = agent_metadata.get(
                            "path", agent_metadata.get("source_file", "")
                        )

                        if not agent_path:
                            print(f"  Deploying {agent_id}... [red]✗ (no path)[/red]")
                            failed += 1
                            continue

                        print(f"  Deploying {agent_id}...", end=" ", flush=True)

                        try:
                            template_path = Path(agent_path)
                            success = deployer.deploy_agent(
                                agent_name=agent_id,
                                templates_dir=template_path.parent,
                                target_dir=target_dir,
                                base_agent_path=base_agent_path,
                                force_rebuild=True,
                                working_directory=Path.cwd(),
                            )

                            if success:
                                print("[green]✓[/green]")
                                deployed += 1
                            else:
                                print("[red]✗[/red]")
                                failed += 1
                        except Exception as e:
                            print(f"[red]✗ ({e})[/red]")
                            self.logger.error(
                                f"Failed to deploy {agent_id}: {e}", exc_info=True
                            )
                            failed += 1

                    print("\n[bold]Summary:[/bold]")
                    print(f"  • Deployed: {deployed}")
                    print(f"  • Failed: {failed}")
                    print(f"  • Total: {len(agents)}")

                    if failed == 0:
                        print(
                            f"\n[green]✓ Preset '{preset_name}' deployed successfully![/green]"
                        )
                    else:
                        print(
                            f"\n[yellow]⚠ Preset deployed with {failed} failures[/yellow]"
                        )

                input("\nPress Enter to continue...")
                break

            except (ValueError, IndexError):
                print("❌ Invalid preset selection")
                input("\nPress Enter to continue...")
            except Exception as e:
                self.logger.error(f"Preset deployment error: {e}", exc_info=True)
                print(f"❌ Error: {e}")
                input("\nPress Enter to continue...")

    def _manage_sources_interactive(self):
        """Interactive source management."""
        if not self.discovery_enabled or not self.source_manager:
            print("\n❌ Source manager not available")
            input("\nPress Enter to continue...")
            return

        print("\n" + "=" * 60)
        print("🔗 Manage Agent Sources")
        print("=" * 60)

        try:
            from claude_mpm.config.agent_sources import AgentSourceConfiguration

            config = AgentSourceConfiguration()
            sources = config.list_sources()

            if not sources:
                print("\n📭 No sources configured.")
            else:
                print(f"\n{len(sources)} source(s) configured:\n")
                print(f"{'Source':<40} {'Priority':<10} {'Status':<10}")
                print("-" * 60)

                for source in sources:
                    identifier = source.get("identifier", "unknown")[:39]
                    priority = str(source.get("priority", 100))
                    status = "✓ Active" if source.get("enabled", True) else "Disabled"
                    print(f"{identifier:<40} {priority:<10} {status:<10}")

            print("\n💡 Use 'claude-mpm agent-source' command to add/remove sources")
            print("💡 Use 'claude-mpm agents discover' command to refresh agent cache")

        except Exception as e:
            self.logger.error(f"Failed to list sources: {e}", exc_info=True)
            print(f"\n❌ Error: {e}")

        input("\nPress Enter to continue...")


def run_interactive_agent_wizard() -> int:
    """Entry point for interactive agent wizard.

    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    try:
        wizard = AgentWizard()
        success, message = wizard.run_interactive_create()

        if success:
            print(f"\n✅ {message}")
            return 0
        print(f"\n❌ {message}", file=sys.stderr)
        return 1

    except Exception as e:
        print(f"\n❌ Wizard error: {e}", file=sys.stderr)
        return 1


def run_interactive_agent_manager() -> int:
    """Entry point for interactive agent management.

    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    try:
        wizard = AgentWizard()
        success, message = wizard.run_interactive_manage()

        if success:
            print(f"\n✅ {message}")
            return 0
        print(f"\n❌ {message}", file=sys.stderr)
        return 1

    except Exception as e:
        print(f"\n❌ Management error: {e}", file=sys.stderr)
        return 1

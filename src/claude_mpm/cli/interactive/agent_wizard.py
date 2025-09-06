"""Interactive Agent Creation Wizard for Claude MPM.

This module provides a step-by-step interactive wizard for creating and managing
local agents with user-friendly prompts, intelligent defaults, and validation.
"""

import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from claude_mpm.core.logging_config import get_logger
from claude_mpm.services.agents.local_template_manager import (
    LocalAgentTemplate,
    LocalAgentTemplateManager,
)

logger = get_logger(__name__)


class AgentWizard:
    """Interactive wizard for agent creation and management."""

    def __init__(self):
        """Initialize the agent wizard."""
        self.manager = LocalAgentTemplateManager()
        self.logger = logger

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
            parent_agent, base_template = self._get_inheritance_option()

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

    def run_interactive_manage(self) -> Tuple[bool, str]:
        """Run interactive agent management menu.

        Returns:
            Tuple of (success, message)
        """
        try:
            while True:
                # List current local agents
                templates = self.manager.list_local_templates()

                print("\n" + "=" * 60)
                print("🔧  Agent Management Menu")
                print("=" * 60)

                if not templates:
                    print("\n📭 No local agents found.")
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
                # Show existing agents
                print(f"\n📋 Found {len(templates)} local agent(s):")
                for i, template in enumerate(templates, 1):
                    tier_icon = "🏢" if template.tier == "project" else "👤"
                    print(
                        f"   {i}. {tier_icon} {template.agent_id} - {template.metadata.get('name', template.agent_id)}"
                    )

                print(f"\n{len(templates) + 1}. Create new agent")
                print(f"{len(templates) + 2}. Delete agent(s)")
                print(f"{len(templates) + 3}. Import agents")
                print(f"{len(templates) + 4}. Export all agents")
                print(f"{len(templates) + 5}. Exit")

                max_choice = len(templates) + 5
                choice = input(f"\nSelect option [1-{max_choice}]: ").strip()

                try:
                    choice_num = int(choice)
                except ValueError:
                    print("❌ Invalid choice. Please enter a number.")
                    continue

                if 1 <= choice_num <= len(templates):
                    # Manage specific agent
                    selected_template = templates[choice_num - 1]
                    result = self._manage_single_agent(selected_template)
                    if not result[0]:
                        print(f"❌ {result[1]}")
                elif choice_num == len(templates) + 1:
                    success, message = self.run_interactive_create()
                    if message:
                        # Message already has emoji from the function
                        print(f"\n{message}")
                    continue  # Return to main menu
                elif choice_num == len(templates) + 2:
                    success, message = self._interactive_delete_menu(templates)
                    if message:
                        # Message already has emoji from the function
                        print(f"\n{message}")
                    continue  # Return to main menu
                elif choice_num == len(templates) + 3:
                    success, message = self._interactive_import()
                    if message:
                        # Message already has emoji from the function
                        print(f"\n{message}")
                    continue  # Return to main menu
                elif choice_num == len(templates) + 4:
                    success, message = self._interactive_export()
                    if message:
                        # Message already has emoji from the function
                        print(f"\n{message}")
                    continue  # Return to main menu
                elif choice_num == len(templates) + 5:
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

        for i, (type_id, name, desc) in enumerate(agent_types, 1):
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

        for i, (model_id, name, desc) in enumerate(models, 1):
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
        for i, (cap_id, desc) in enumerate(capabilities_options, 1):
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

        with open(output_file, "w") as f:
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

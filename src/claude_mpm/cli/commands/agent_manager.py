"""Agent Manager CLI command for comprehensive agent lifecycle management.

This module provides CLI interface for:
- Creating and customizing agents
- Managing agent variants
- Deploying agents across tiers
- Customizing PM instructions
- Discovering and listing agents
"""

import json
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from ...core.logging_config import get_logger
from ...services.agents.agent_builder import AgentBuilderService
from ...services.agents.deployment.agent_deployment import AgentDeploymentService
from ..shared import AgentCommand, CommandResult


class AgentManagerCommand(AgentCommand):
    """Agent Manager command for comprehensive agent management."""

    def __init__(self):
        super().__init__("agent-manager")
        self.builder_service = AgentBuilderService()
        self.deployment_service = None
        self.logger = get_logger(__name__)

    @property
    def deployment(self):
        """Lazy load deployment service."""
        if self.deployment_service is None:
            self.deployment_service = AgentDeploymentService()
        return self.deployment_service

    def run(self, args) -> CommandResult:
        """Execute agent manager command.

        Args:
            args: Command arguments

        Returns:
            CommandResult with operation status
        """
        if not hasattr(args, "agent_manager_command"):
            return self._show_help()

        command_map = {
            "list": self._list_agents,
            "create": self._create_agent,
            "variant": self._create_variant,
            "deploy": self._deploy_agent,
            "customize-pm": self._customize_pm,
            "show": self._show_agent,
            "test": self._test_agent,
            "templates": self._list_templates,
            "reset": self._reset_agents,
        }

        command = args.agent_manager_command
        if command in command_map:
            return command_map[command](args)
        return CommandResult.error_result(f"Unknown command: {command}")

    def _list_agents(self, args) -> CommandResult:
        """List all agents across tiers with hierarchy.

        Shows agents from:
        1. Project level (.claude/agents/)
        2. User level (~/.claude/agents/)
        3. System level (framework)
        """
        agents = {"project": [], "user": [], "system": []}

        # Check project level
        project_dir = Path.cwd() / ".claude" / "agents"
        if project_dir.exists():
            for agent_file in project_dir.glob("*.yaml"):
                agents["project"].append(
                    self._read_agent_summary(agent_file, "project")
                )

        # Check user level
        user_dir = Path.home() / ".claude" / "agents"
        if user_dir.exists():
            for agent_file in user_dir.glob("*.yaml"):
                agent_id = agent_file.stem
                # Skip if overridden by project
                if not any(a["id"] == agent_id for a in agents["project"]):
                    agents["user"].append(self._read_agent_summary(agent_file, "user"))

        # Get system agents
        templates = self.builder_service.list_available_templates()
        for template in templates:
            agent_id = template["id"]
            # Skip if overridden by project or user
            if not any(a["id"] == agent_id for a in agents["project"] + agents["user"]):
                agents["system"].append(
                    {
                        "id": agent_id,
                        "name": template["name"],
                        "tier": "system",
                        "description": template["description"],
                        "category": template.get("category", "custom"),
                    }
                )

        # Format output
        output_format = getattr(args, "format", "text")
        if output_format == "json":
            return CommandResult.success_result("Agents listed", data=agents)
        output = self._format_agent_list(agents)
        return CommandResult.success_result(output)

    def _create_agent(self, args) -> CommandResult:
        """Create a new agent interactively or from arguments."""
        try:
            # Interactive mode if no arguments
            if not hasattr(args, "agent_id"):
                return self._interactive_create()

            # Create from arguments
            config, instructions = self.builder_service.create_agent(
                agent_id=args.agent_id,
                name=getattr(args, "name", args.agent_id),
                description=getattr(
                    args, "description", f"Custom agent {args.agent_id}"
                ),
                model=getattr(args, "model", "sonnet"),
                tool_choice=getattr(args, "tool_choice", "auto"),
                base_template=getattr(args, "template", None),
            )

            # Save agent files
            result = self._save_agent(config, instructions, args.agent_id)

            if result:
                return CommandResult.success_result(
                    f"Agent '{args.agent_id}' created successfully"
                )
            return CommandResult.error_result("Failed to save agent files")

        except Exception as e:
            return CommandResult.error_result(f"Failed to create agent: {e}")

    def _create_variant(self, args) -> CommandResult:
        """Create an agent variant."""
        try:
            if not hasattr(args, "base_agent"):
                return CommandResult.error_result(
                    "Base agent ID required for variant creation"
                )

            modifications = {}
            if hasattr(args, "model"):
                modifications["model"] = args.model
            if hasattr(args, "tool_choice"):
                modifications["tool_choice"] = args.tool_choice

            config, instructions = self.builder_service.create_variant(
                base_agent_id=args.base_agent,
                variant_id=args.variant_id,
                variant_name=getattr(args, "name", f"{args.base_agent}-variant"),
                modifications=modifications,
                instructions_append=getattr(args, "instructions", None),
            )

            # Save variant
            result = self._save_agent(config, instructions, args.variant_id)

            if result:
                return CommandResult.success_result(
                    f"Variant '{args.variant_id}' created successfully"
                )
            return CommandResult.error_result("Failed to save variant files")

        except Exception as e:
            return CommandResult.error_result(f"Failed to create variant: {e}")

    def _deploy_agent(self, args) -> CommandResult:
        """Deploy an agent to specified tier."""
        try:
            agent_id = args.agent_id
            tier = getattr(
                args, "tier", "project"
            )  # Default to project (changed from 'user')

            # Always deploy to project directory
            # Regardless of tier, all agents go to project .claude/agents
            deploy_path = Path.cwd() / ".claude" / "agents"

            # Note: We're keeping the tier parameter for backward compatibility
            # but it no longer affects the deployment location
            if tier not in ["project", "user"]:
                return CommandResult.error_result(
                    "Invalid tier. Use 'project' or 'user'"
                )

            # Create directory if needed
            deploy_path.mkdir(parents=True, exist_ok=True)

            # Find agent files
            template_dir = Path(__file__).parent.parent.parent / "agents" / "templates"
            json_file = template_dir / f"{agent_id}.json"
            template_dir / f"{agent_id}.md"

            if not json_file.exists():
                return CommandResult.error_result(f"Agent '{agent_id}' not found")

            # Deploy using deployment service
            # Pass Path object, not string
            self.deployment.deploy_agent(agent_id, deploy_path)

            return CommandResult.success_result(
                f"Agent '{agent_id}' deployed to {tier} level"
            )

        except Exception as e:
            return CommandResult.error_result(f"Deployment failed: {e}")

    def _customize_pm(self, args) -> CommandResult:
        """Customize PM instructions via .claude-mpm/INSTRUCTIONS.md."""
        try:
            level = getattr(args, "level", "user")

            # Use .claude-mpm/INSTRUCTIONS.md for customization
            if level == "user":
                pm_file = Path.home() / ".claude-mpm" / "INSTRUCTIONS.md"
            elif level == "project":
                pm_file = Path.cwd() / ".claude-mpm" / "INSTRUCTIONS.md"
            else:
                return CommandResult.error_result(
                    "Invalid level. Use 'user' or 'project'"
                )

            # Create backup if file exists
            if pm_file.exists():
                backup_file = pm_file.with_suffix(".md.backup")
                shutil.copy(pm_file, backup_file)
                self.logger.info(f"Backup created: {backup_file}")

            # Generate or load instructions
            if hasattr(args, "template"):
                instructions = self._load_pm_template(args.template)
            else:
                instructions = self.builder_service.generate_pm_instructions(
                    delegation_patterns=getattr(args, "patterns", None),
                    workflow_overrides=getattr(args, "workflows", None),
                    custom_rules=getattr(args, "rules", None),
                )

            # Save instructions to .claude-mpm directory
            pm_file.parent.mkdir(parents=True, exist_ok=True)
            pm_file.write_text(instructions)

            return CommandResult.success_result(
                f"PM instructions customized at {level} level: {pm_file}\n"
                f"Note: These instructions will be loaded by the framework loader."
            )

        except Exception as e:
            return CommandResult.error_result(f"Failed to customize PM: {e}")

    def _show_agent(self, args) -> CommandResult:
        """Show detailed agent information."""
        try:
            agent_id = args.agent_id

            # Find agent across tiers
            agent_info = self._find_agent(agent_id)

            if not agent_info:
                return CommandResult.error_result(f"Agent '{agent_id}' not found")

            output_format = getattr(args, "format", "text")
            if output_format == "json":
                return CommandResult.success_result("Agent details", data=agent_info)
            output = self._format_agent_details(agent_info)
            return CommandResult.success_result(output)

        except Exception as e:
            return CommandResult.error_result(f"Failed to show agent: {e}")

    def _test_agent(self, args) -> CommandResult:
        """Test agent configuration."""
        try:
            agent_id = args.agent_id

            # Find agent configuration
            config = self._load_agent_config(agent_id)

            if not config:
                return CommandResult.error_result(f"Agent '{agent_id}' not found")

            # Validate configuration
            errors = self.builder_service.validate_configuration(config)

            if errors:
                return CommandResult.error_result(
                    "Validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
                )

            # Check for conflicts
            conflicts = self._check_conflicts(agent_id)

            warning = f"Warning: Agent overrides {conflicts}" if conflicts else ""

            return CommandResult.success_result(
                f"Agent '{agent_id}' configuration is valid. {warning}"
            )

        except Exception as e:
            return CommandResult.error_result(f"Test failed: {e}")

    def _list_templates(self, args) -> CommandResult:
        """List available agent templates."""
        templates = self.builder_service.list_available_templates()

        output_format = getattr(args, "format", "text")
        if output_format == "json":
            return CommandResult.success_result("Templates listed", data=templates)
        output = "Available Agent Templates:\n\n"
        for template in templates:
            template_id = template.get("id", "unknown")
            template_name = template.get("name", "Unnamed")
            output += f"  {template_id:<20} - {template_name}\n"
            if template.get("description"):
                output += f"    {template['description']}\n"
        return CommandResult.success_result(output)

    def _reset_agents(self, args) -> CommandResult:
        """Reset by removing claude-mpm authored agents from project and user directories.

        This command removes any agents with "author: claude-mpm" in their frontmatter,
        preserving user-created agents. This is useful for clean reinstalls or when
        wanting to get fresh versions of system agents.
        """
        try:
            # Determine which directories to clean
            clean_project = not getattr(args, "user_only", False)
            clean_user = not getattr(args, "project_only", False)
            dry_run = getattr(args, "dry_run", False)
            force = getattr(args, "force", False)
            output_format = getattr(args, "format", "text")

            # Track results
            results = {
                "project": {"checked": False, "removed": [], "preserved": []},
                "user": {"checked": False, "removed": [], "preserved": []},
                "dry_run": dry_run,
                "total_removed": 0,
                "total_preserved": 0,
            }

            # Check project directory - always scan first to see what's there
            if clean_project:
                project_dir = Path.cwd() / ".claude" / "agents"
                if project_dir.exists():
                    results["project"]["checked"] = True
                    # Always scan with dry_run=True first to see what's there
                    self._scan_and_clean_directory(
                        project_dir, results["project"], dry_run=True
                    )

            # Check user directory - always scan first to see what's there
            if clean_user:
                user_dir = Path.home() / ".claude" / "agents"
                if user_dir.exists():
                    results["user"]["checked"] = True
                    # Always scan with dry_run=True first to see what's there
                    self._scan_and_clean_directory(
                        user_dir, results["user"], dry_run=True
                    )

            # Calculate totals
            results["total_removed"] = len(results["project"]["removed"]) + len(
                results["user"]["removed"]
            )
            results["total_preserved"] = len(results["project"]["preserved"]) + len(
                results["user"]["preserved"]
            )

            # Handle output based on format
            if output_format == "json":
                return CommandResult.success_result("Reset completed", data=results)

            # Generate text output
            output = self._format_reset_results(results, dry_run, force)

            # If not dry-run, perform actual removal
            if not dry_run and results["total_removed"] > 0:
                # If force mode, remove immediately; otherwise get confirmation
                if not force:
                    # Get confirmation first
                    print(output)
                    print("\n⚠️  This will permanently remove the agents listed above.")

                    # Ensure stdout is flushed before reading input
                    sys.stdout.flush()

                    # Get confirmation
                    try:
                        response = input("Continue? [y/N]: ").strip().lower()
                        if response not in ["y", "yes"]:
                            return CommandResult.success_result(
                                "Reset cancelled by user"
                            )
                    except (KeyboardInterrupt, EOFError):
                        return CommandResult.success_result("\nReset cancelled")

                # Perform actual removal using the list we already have
                if clean_project and results["project"]["removed"]:
                    project_dir = Path.cwd() / ".claude" / "agents"
                    for agent in results["project"]["removed"]:
                        agent_file = project_dir / agent
                        try:
                            if agent_file.exists():
                                agent_file.unlink()
                                self.logger.info(
                                    f"Removed claude-mpm agent: {agent_file}"
                                )
                        except Exception as e:
                            self.logger.warning(f"Could not remove {agent_file}: {e}")

                if clean_user and results["user"]["removed"]:
                    user_dir = Path.home() / ".claude" / "agents"
                    for agent in results["user"]["removed"]:
                        agent_file = user_dir / agent
                        try:
                            if agent_file.exists():
                                agent_file.unlink()
                                self.logger.info(
                                    f"Removed claude-mpm agent: {agent_file}"
                                )
                        except Exception as e:
                            self.logger.warning(f"Could not remove {agent_file}: {e}")

                # Update output to show actual removal
                output = self._format_reset_results(results, dry_run=False, force=force)

            return CommandResult.success_result(output)

        except Exception as e:
            self.logger.error(f"Failed to reset agents: {e}", exc_info=True)
            return CommandResult.error_result(f"Failed to reset agents: {e}")

    def _scan_and_clean_directory(
        self, directory: Path, results: Dict[str, Any], dry_run: bool
    ) -> None:
        """Scan a directory for claude-mpm authored agents and optionally remove them.

        Args:
            directory: Directory to scan
            results: Results dictionary to update
            dry_run: If True, only scan without removing
        """
        for agent_file in directory.glob("*.md"):
            try:
                content = agent_file.read_text()
                # Check if this is a claude-mpm authored agent
                if "author: claude-mpm" in content.lower():
                    results["removed"].append(agent_file.name)
                    if not dry_run:
                        agent_file.unlink()
                        self.logger.info(f"Removed claude-mpm agent: {agent_file}")
                else:
                    results["preserved"].append(agent_file.name)
                    self.logger.debug(f"Preserved user agent: {agent_file}")
            except Exception as e:
                self.logger.warning(f"Could not process {agent_file}: {e}")

    def _format_reset_results(
        self, results: Dict[str, Any], dry_run: bool, force: bool
    ) -> str:
        """Format reset results for display.

        Args:
            results: Results dictionary
            dry_run: Whether this was a dry run
            force: Whether force mode was used

        Returns:
            Formatted output string
        """
        if dry_run:
            output = "🔍 DRY RUN - No changes will be made\n"
            output += "=" * 50 + "\n\n"
        else:
            output = "🧹 Agent Reset Complete\n"
            output += "=" * 50 + "\n\n"

        # Show project results
        if results["project"]["checked"]:
            output += "📁 Project Level (.claude/agents):\n"
            if results["project"]["removed"]:
                action = "Would remove" if dry_run else "Removed"
                output += f"   {action} {len(results['project']['removed'])} claude-mpm agent(s):\n"
                for agent in results["project"]["removed"][:5]:
                    output += f"      • {agent}\n"
                if len(results["project"]["removed"]) > 5:
                    output += (
                        f"      ... and {len(results['project']['removed']) - 5} more\n"
                    )
            else:
                output += "   No claude-mpm agents found\n"

            if results["project"]["preserved"]:
                output += f"   Preserved {len(results['project']['preserved'])} user-created agent(s)\n"
            output += "\n"

        # Show user results
        if results["user"]["checked"]:
            output += "📁 User Level (~/.claude/agents):\n"
            if results["user"]["removed"]:
                action = "Would remove" if dry_run else "Removed"
                output += f"   {action} {len(results['user']['removed'])} claude-mpm agent(s):\n"
                for agent in results["user"]["removed"][:5]:
                    output += f"      • {agent}\n"
                if len(results["user"]["removed"]) > 5:
                    output += (
                        f"      ... and {len(results['user']['removed']) - 5} more\n"
                    )
            else:
                output += "   No claude-mpm agents found\n"

            if results["user"]["preserved"]:
                output += f"   Preserved {len(results['user']['preserved'])} user-created agent(s)\n"
            output += "\n"

        # Show summary
        output += "📊 Summary:\n"
        if dry_run:
            output += f"   • Would remove: {results['total_removed']} agent(s)\n"
        else:
            output += f"   • Removed: {results['total_removed']} agent(s)\n"
        output += f"   • Preserved: {results['total_preserved']} user agent(s)\n"

        if dry_run and results["total_removed"] > 0:
            output += "\n💡 Run with --force to execute this cleanup immediately"

        return output

    def _interactive_create(self) -> CommandResult:
        """Interactive agent creation wizard."""
        print("\n=== Agent Creation Wizard ===\n")

        # Get agent ID
        agent_id = input("Agent ID (lowercase, hyphens only): ").strip()
        if not agent_id:
            return CommandResult.error_result("Agent ID is required")

        # Get name
        name = input(f"Display name [{agent_id}]: ").strip() or agent_id

        # Get description
        description = input("Description: ").strip()
        if not description:
            return CommandResult.error_result("Description is required")

        # Get model
        print("\nAvailable models: sonnet, opus, haiku")
        model = input("Model [sonnet]: ").strip() or "sonnet"

        # Get tool choice
        print("\nTool choices: auto, required, any, none")
        tool_choice = input("Tool choice [auto]: ").strip() or "auto"

        # Create agent
        try:
            config, instructions = self.builder_service.create_agent(
                agent_id=agent_id,
                name=name,
                description=description,
                model=model,
                tool_choice=tool_choice,
            )

            # Save agent
            if self._save_agent(config, instructions, agent_id):
                return CommandResult.success_result(
                    f"\nAgent '{agent_id}' created successfully!"
                )
            return CommandResult.error_result("Failed to save agent files")

        except Exception as e:
            return CommandResult.error_result(f"Creation failed: {e}")

    def _save_agent(
        self, config: Dict[str, Any], instructions: str, agent_id: str
    ) -> bool:
        """Save agent configuration and instructions.

        Args:
            config: Agent configuration dictionary
            instructions: Agent instructions markdown
            agent_id: Agent identifier

        Returns:
            True if saved successfully
        """
        try:
            template_dir = Path(__file__).parent.parent.parent / "agents" / "templates"
            template_dir.mkdir(parents=True, exist_ok=True)

            # Save JSON configuration
            json_file = template_dir / f"{agent_id}.json"
            with open(json_file, "w") as f:
                json.dump(config, f, indent=2)

            # Save instructions
            md_file = template_dir / f"{agent_id}.md"
            md_file.write_text(instructions)

            self.logger.info(f"Agent saved: {json_file} and {md_file}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to save agent: {e}")
            return False

    def _read_agent_summary(self, agent_file: Path, tier: str) -> Dict[str, Any]:
        """Read agent summary from file."""
        try:
            # For YAML files, extract basic info
            agent_id = agent_file.stem
            return {
                "id": agent_id,
                "name": agent_id.replace("-", " ").title(),
                "tier": tier,
                "file": str(agent_file),
            }
        except Exception:
            return {}

    def _format_agent_list(self, agents: Dict[str, List]) -> str:
        """Format agent list for display."""
        output = "=== Agent Hierarchy ===\n\n"

        # Project agents
        if agents["project"]:
            output += "[P] PROJECT LEVEL (Highest Priority)\n"
            for agent in agents["project"]:
                output += f"    {agent['id']:<20} - {agent.get('name', agent['id'])}\n"
            output += "\n"

        # User agents
        if agents["user"]:
            output += "[U] USER LEVEL\n"
            for agent in agents["user"]:
                output += f"    {agent['id']:<20} - {agent.get('name', agent['id'])}\n"
            output += "\n"

        # System agents
        if agents["system"]:
            output += "[S] SYSTEM LEVEL (Framework Defaults)\n"
            for agent in agents["system"]:
                output += f"    {agent['id']:<20} - {agent.get('name', agent['id'])}\n"

        return output

    def _find_agent(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Find agent across all tiers."""
        # Implementation would search across tiers
        # This is a simplified version
        return {"id": agent_id, "tier": "system"}

    def _load_agent_config(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Load agent configuration."""
        try:
            return self.builder_service._load_template(agent_id)
        except:
            return None

    def _check_conflicts(self, agent_id: str) -> Optional[str]:
        """Check for agent conflicts across tiers."""
        # Check if agent exists in multiple tiers
        # Return tier information if conflicts exist
        return None

    def _format_agent_details(self, agent_info: Dict[str, Any]) -> str:
        """Format agent details for display."""
        output = f"=== Agent: {agent_info['id']} ===\n\n"
        for key, value in agent_info.items():
            output += f"{key}: {value}\n"
        return output

    def _load_pm_template(self, template_name: str) -> str:
        """Load PM instruction template."""
        # Load predefined PM templates
        return "# PM Instructions Template\n"

    def _show_help(self) -> CommandResult:
        """Show help for agent manager."""
        help_text = """
Agent Manager - Comprehensive Agent Lifecycle Management

Commands:
  list          List all agents across tiers with hierarchy
  create        Create a new agent (interactive or with arguments)
  variant       Create an agent variant based on existing agent
  deploy        Deploy agent to project or user tier
  customize-pm  Customize PM instructions via .claude-mpm/INSTRUCTIONS.md
  show          Display detailed agent information
  test          Validate agent configuration
  templates     List available agent templates
  reset         Remove claude-mpm authored agents for clean install

Examples:
  claude-mpm agent-manager list
  claude-mpm agent-manager create --id my-agent --name "My Agent"
  claude-mpm agent-manager variant --base research --id research-v2
  claude-mpm agent-manager deploy --agent-id my-agent --tier user
  claude-mpm agent-manager customize-pm --level project
  claude-mpm agent-manager reset --dry-run
  claude-mpm agent-manager reset --force --project-only

Note: PM customization writes to .claude-mpm/INSTRUCTIONS.md, not CLAUDE.md
"""
        return CommandResult.success_result(help_text)


# Module-level function for CLI integration
def manage_agent_manager(args) -> int:
    """Entry point for agent-manager command from CLI.

    Args:
        args: Parsed command line arguments

    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    command = AgentManagerCommand()
    result = command.run(args)

    if result.success:
        # Handle JSON output format
        output_format = getattr(args, "format", "text")
        if output_format == "json" and result.data is not None:
            print(json.dumps(result.data, indent=2))
        elif result.message:
            print(result.message)
        return 0
    if result.message:
        print(f"Error: {result.message}", file=sys.stderr)
    return 1

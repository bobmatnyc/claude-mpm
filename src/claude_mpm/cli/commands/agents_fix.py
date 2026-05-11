"""
Fix / validate / view / clean handler for agents command.

WHY: Extracted from agents.py to keep the main command file focused on routing.
This handler manages clean, view, and fix (frontmatter validation) commands
plus all related text-output helpers.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ...core.enums import OutputFormat
from ..shared import CommandResult

if TYPE_CHECKING:
    from .agents import AgentsCommand


class AgentFixHandler:
    """Handles clean, view, and frontmatter-fix commands."""

    def __init__(self, cmd: AgentsCommand) -> None:
        self.cmd = cmd

    @property
    def _logger(self):
        return self.cmd.logger

    def clean_agents(self, args) -> CommandResult:
        """Clean deployed agents."""
        try:
            result = self.cmd.cleanup_service.clean_deployed_agents()

            output_format = self.cmd._get_output_format(args)
            dry_run = False  # Regular clean is not a dry run

            formatted = self.cmd._formatter.format_cleanup_result(
                result, output_format=output_format, dry_run=dry_run
            )
            print(formatted)

            cleaned_count = result.get("cleaned_count", 0)
            return CommandResult.success_result(
                f"Cleaned {cleaned_count} agents", data=result
            )

        except Exception as e:
            self._logger.error(f"Error cleaning agents: {e}", exc_info=True)
            return CommandResult.error_result(f"Error cleaning agents: {e}")

    def view_agent(self, args) -> CommandResult:
        """View details of a specific agent."""
        try:
            agent_name = getattr(args, "agent_name", None)
            if not agent_name:
                return CommandResult.error_result(
                    "Agent name is required for view command"
                )

            # Get agent details from listing service
            agent_details = self.cmd.listing_service.get_agent_details(agent_name)

            if not agent_details:
                # Try to find the agent to provide helpful error message
                agent = self.cmd.listing_service.find_agent(agent_name)
                if not agent:
                    return CommandResult.error_result(f"Agent '{agent_name}' not found")
                return CommandResult.error_result(
                    f"Could not retrieve details for agent '{agent_name}'"
                )

            output_format = self.cmd._get_output_format(args)
            verbose = getattr(args, "verbose", False)

            formatted = self.cmd._formatter.format_agent_details(
                agent_details, output_format=output_format, verbose=verbose
            )
            print(formatted)

            return CommandResult.success_result(
                f"Displayed details for {agent_name}", data=agent_details
            )

        except Exception as e:
            self._logger.error(f"Error viewing agent: {e}", exc_info=True)
            return CommandResult.error_result(f"Error viewing agent: {e}")

    def fix_agents(self, args) -> CommandResult:
        """Fix agent frontmatter issues using validation service."""
        try:
            dry_run = getattr(args, "dry_run", False)
            agent_name = getattr(args, "agent_name", None)
            fix_all = getattr(args, "all", False)
            output_format = self.cmd._get_output_format(args)

            # Route to appropriate handler based on input
            if fix_all:
                return self.fix_all_agents(dry_run, output_format)
            if agent_name:
                return self.fix_single_agent(agent_name, dry_run, output_format)
            return self.handle_no_agent_specified(output_format)

        except Exception as e:
            self._logger.error(f"Error fixing agents: {e}", exc_info=True)
            return CommandResult.error_result(f"Error fixing agents: {e}")

    def fix_all_agents(self, dry_run: bool, output_format: str) -> CommandResult:
        """Fix all agents' frontmatter issues."""
        result = self.cmd.validation_service.fix_all_agents(dry_run=dry_run)

        if self.cmd._is_structured_format(output_format):
            self.print_structured_output(result, output_format)
        else:
            self.print_all_agents_text_output(result, dry_run)

        msg = f"{'Would fix' if dry_run else 'Fixed'} {result.get('total_corrections_available' if dry_run else 'total_corrections_made', 0)} issues"
        return CommandResult.success_result(msg, data=result)

    def fix_single_agent(
        self, agent_name: str, dry_run: bool, output_format: str
    ) -> CommandResult:
        """Fix a single agent's frontmatter issues."""
        result = self.cmd.validation_service.fix_agent_frontmatter(
            agent_name, dry_run=dry_run
        )

        if not result.get("success"):
            return CommandResult.error_result(
                result.get("error", "Failed to fix agent")
            )

        if self.cmd._is_structured_format(output_format):
            self.print_structured_output(result, output_format)
        else:
            self.print_single_agent_text_output(agent_name, result, dry_run)

        msg = f"{'Would fix' if dry_run else 'Fixed'} agent '{agent_name}'"
        return CommandResult.success_result(msg, data=result)

    def handle_no_agent_specified(self, output_format: str) -> CommandResult:
        """Handle case where no agent is specified."""
        usage_msg = "Please specify an agent name or use --all to fix all agents\nUsage: claude-mpm agents fix [agent_name] [--dry-run] [--all]"
        if self.cmd._is_structured_format(output_format):
            return CommandResult.error_result(
                "No agent specified", data={"usage": usage_msg}
            )
        print(f"❌ {usage_msg}")
        return CommandResult.error_result("No agent specified")

    def print_structured_output(self, result: dict, output_format: str) -> None:
        """Print result in JSON or YAML format."""
        formatted = (
            self.cmd._formatter.format_as_json(result)
            if str(output_format).lower() == OutputFormat.JSON
            else self.cmd._formatter.format_as_yaml(result)
        )
        print(formatted)

    def print_all_agents_text_output(self, result: dict, dry_run: bool) -> None:
        """Print text output for all agents fix operation."""
        mode = "DRY RUN" if dry_run else "FIX"
        print(
            f"\n🔧 {mode}: Checking {result.get('total_agents', 0)} agent(s) for frontmatter issues...\n"
        )

        if result.get("results"):
            for agent_result in result["results"]:
                self.print_agent_result(agent_result, dry_run)

        self.print_all_agents_summary(result, dry_run)

    def print_agent_result(self, agent_result: dict, dry_run: bool) -> None:
        """Print result for a single agent."""
        print(f"📄 {agent_result['agent']}:")
        if agent_result.get("skipped"):
            print(f"  ⚠️  Skipped: {agent_result.get('reason', 'Unknown reason')}")
        elif agent_result.get("was_valid"):
            print("  ✓ No issues found")
        else:
            self.print_agent_issues(agent_result, dry_run)
        print()

    def print_agent_issues(self, agent_result: dict, dry_run: bool) -> None:
        """Print issues found for an agent."""
        if agent_result.get("errors_found", 0) > 0:
            print(f"  ❌ Errors found: {agent_result['errors_found']}")
        if agent_result.get("warnings_found", 0) > 0:
            print(f"  ⚠️  Warnings found: {agent_result['warnings_found']}")

        if dry_run:
            if agent_result.get("corrections_available", 0) > 0:
                print(f"  🔧 Would fix: {agent_result['corrections_available']} issues")
        elif agent_result.get("corrections_made", 0) > 0:
            print(f"  ✓ Fixed: {agent_result['corrections_made']} issues")

    def print_all_agents_summary(self, result: dict, dry_run: bool) -> None:
        """Print summary for all agents fix operation."""
        print("=" * 80)
        print("SUMMARY:")
        print(f"  Agents checked: {result.get('agents_checked', 0)}")
        print(f"  Total issues found: {result.get('total_issues_found', 0)}")

        if dry_run:
            print(
                f"  Issues that would be fixed: {result.get('total_corrections_available', 0)}"
            )
            print("\n💡 Run without --dry-run to apply fixes")
        else:
            print(f"  Issues fixed: {result.get('total_corrections_made', 0)}")
            if result.get("total_corrections_made", 0) > 0:
                print("\n✓ Frontmatter issues have been fixed!")
        print("=" * 80 + "\n")

    def print_single_agent_text_output(
        self, agent_name: str, result: dict, dry_run: bool
    ) -> None:
        """Print text output for single agent fix operation."""
        mode = "DRY RUN" if dry_run else "FIX"
        print(f"\n🔧 {mode}: Checking agent '{agent_name}' for frontmatter issues...\n")

        print(f"📄 {agent_name}:")
        if result.get("was_valid"):
            print("  ✓ No issues found")
        else:
            self.print_single_agent_issues(result, dry_run)
        print()

        self.print_single_agent_footer(result, dry_run)

    def print_single_agent_issues(self, result: dict, dry_run: bool) -> None:
        """Print issues for a single agent."""
        if result.get("errors_found"):
            print("  ❌ Errors:")
            for error in result["errors_found"]:
                print(f"    - {error}")

        if result.get("warnings_found"):
            print("  ⚠️  Warnings:")
            for warning in result["warnings_found"]:
                print(f"    - {warning}")

        if dry_run:
            if result.get("corrections_available"):
                print("  🔧 Would fix:")
                for correction in result["corrections_available"]:
                    print(f"    - {correction}")
        elif result.get("corrections_made"):
            print("  ✓ Fixed:")
            for correction in result["corrections_made"]:
                print(f"    - {correction}")

    def print_single_agent_footer(self, result: dict, dry_run: bool) -> None:
        """Print footer message for single agent fix."""
        if dry_run and result.get("corrections_available"):
            print("💡 Run without --dry-run to apply fixes\n")
        elif not dry_run and result.get("corrections_made"):
            print("✓ Frontmatter issues have been fixed!\n")

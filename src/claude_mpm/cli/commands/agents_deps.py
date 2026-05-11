"""
Dependency management handler for agents command.

WHY: Extracted from agents.py to keep the main command file focused on routing.
This handler manages agent Python/system dependency check/install/list/fix.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from ...core.enums import OutputFormat
from ..shared import CommandResult

if TYPE_CHECKING:
    from .agents import AgentsCommand


class AgentDepsHandler:
    """Handles agent dependency management commands."""

    def __init__(self, cmd: AgentsCommand) -> None:
        self.cmd = cmd

    @property
    def _logger(self):
        return self.cmd.logger

    def check_agent_dependencies(self, args) -> CommandResult:
        """Check agent dependencies."""
        try:
            agent_name = getattr(args, "agent", None)
            result = self.cmd.dependency_service.check_dependencies(
                agent_name=agent_name
            )

            if not result["success"]:
                if "available_agents" in result:
                    print(f"❌ Agent '{agent_name}' is not deployed")
                    print(
                        f"   Available agents: {', '.join(result['available_agents'])}"
                    )
                return CommandResult.error_result(
                    result.get("error", "Dependency check failed")
                )

            # Print the formatted report
            print(result["report"])

            return CommandResult.success_result(
                "Dependency check completed", data=result
            )

        except Exception as e:
            self._logger.error(f"Error checking dependencies: {e}", exc_info=True)
            return CommandResult.error_result(f"Error checking dependencies: {e}")

    def install_agent_dependencies(self, args) -> CommandResult:
        """Install agent dependencies."""
        try:
            agent_name = getattr(args, "agent", None)
            dry_run = getattr(args, "dry_run", False)
            result = self.cmd.dependency_service.install_dependencies(
                agent_name=agent_name, dry_run=dry_run
            )

            if not result["success"]:
                if "available_agents" in result:
                    print(f"❌ Agent '{agent_name}' is not deployed")
                    print(
                        f"   Available agents: {', '.join(result['available_agents'])}"
                    )
                return CommandResult.error_result(
                    result.get("error", "Installation failed")
                )

            if result.get("missing_count") == 0:
                print("✅ All Python dependencies are already installed")
            elif dry_run:
                print(
                    f"Found {len(result['missing_dependencies'])} missing dependencies:"
                )
                for dep in result["missing_dependencies"]:
                    print(f"  - {dep}")
                print("\n--dry-run specified, not installing anything")
                print(f"Would install: {result['install_command']}")
            else:
                print(
                    f"✅ Successfully installed {len(result.get('installed', []))} dependencies"
                )
                if result.get("still_missing"):
                    print(
                        f"⚠️  {len(result['still_missing'])} dependencies still missing after installation"
                    )
                elif result.get("fully_resolved"):
                    print("✅ All dependencies verified after installation")

            return CommandResult.success_result(
                "Dependency installation completed", data=result
            )

        except Exception as e:
            self._logger.error(f"Error installing dependencies: {e}", exc_info=True)
            return CommandResult.error_result(f"Error installing dependencies: {e}")

    def list_agent_dependencies(self, args) -> CommandResult:
        """List agent dependencies."""
        try:
            output_format = self.cmd._get_output_format(args)
            result = self.cmd.dependency_service.list_dependencies(
                format_type=output_format
            )

            if not result["success"]:
                return CommandResult.error_result(result.get("error", "Listing failed"))

            # Format output based on requested format
            if output_format == "pip":
                for dep in result["dependencies"]:
                    print(dep)
            elif str(output_format).lower() == OutputFormat.JSON:
                print(json.dumps(result["data"], indent=2))
            else:  # text format
                print("=" * 60)
                print("DEPENDENCIES FROM DEPLOYED AGENTS")
                print("=" * 60)
                print()

                if result["python_dependencies"]:
                    print(
                        f"Python Dependencies ({len(result['python_dependencies'])}):"
                    )
                    print("-" * 30)
                    for dep in result["python_dependencies"]:
                        print(f"  {dep}")
                    print()

                if result["system_dependencies"]:
                    print(
                        f"System Dependencies ({len(result['system_dependencies'])}):"
                    )
                    print("-" * 30)
                    for dep in result["system_dependencies"]:
                        print(f"  {dep}")
                    print()

                print("Per-Agent Dependencies:")
                print("-" * 30)
                for agent_id in sorted(result["per_agent"].keys()):
                    deps = result["per_agent"][agent_id]
                    python_count = len(deps.get("python", []))
                    system_count = len(deps.get("system", []))
                    if python_count or system_count:
                        print(
                            f"  {agent_id}: {python_count} Python, {system_count} System"
                        )

            return CommandResult.success_result(
                "Dependency listing completed", data=result
            )

        except Exception as e:
            self._logger.error(f"Error listing dependencies: {e}", exc_info=True)
            return CommandResult.error_result(f"Error listing dependencies: {e}")

    def fix_agent_dependencies(self, args) -> CommandResult:
        """Fix agent dependency issues."""
        try:
            max_retries = getattr(args, "max_retries", 3)
            agent_name = getattr(args, "agent", None)

            print("=" * 70)
            print("FIXING AGENT DEPENDENCIES WITH RETRY LOGIC")
            print("=" * 70)
            print()

            result = self.cmd.dependency_service.fix_dependencies(
                max_retries=max_retries, agent_name=agent_name
            )

            if not result["success"]:
                if "error" in result and "not deployed" in result["error"]:
                    print(f"❌ {result['error']}")
                return CommandResult.error_result(result.get("error", "Fix failed"))

            if result.get("message") == "No deployed agents found":
                print("No deployed agents found")
                return CommandResult.success_result("No agents to fix")

            if result.get("message") == "All dependencies are already satisfied":
                print("\n✅ All dependencies are already satisfied!")
                return CommandResult.success_result("All dependencies satisfied")

            # Show what's missing
            if result.get("missing_python"):
                print(f"\n❌ Missing Python packages: {len(result['missing_python'])}")
                for pkg in result["missing_python"][:10]:
                    print(f"   - {pkg}")
                if len(result["missing_python"]) > 10:
                    print(f"   ... and {len(result['missing_python']) - 10} more")

            if result.get("missing_system"):
                print(f"\n❌ Missing system commands: {len(result['missing_system'])}")
                for cmd in result["missing_system"]:
                    print(f"   - {cmd}")
                print("\n⚠️  System dependencies must be installed manually:")
                print(f"  macOS:  brew install {' '.join(result['missing_system'])}")
                print(f"  Ubuntu: apt-get install {' '.join(result['missing_system'])}")

            # Show incompatible packages
            if result.get("incompatible"):
                print(
                    f"\n⚠️  Skipping {len(result['incompatible'])} incompatible packages:"
                )
                for pkg in result["incompatible"][:5]:
                    print(f"   - {pkg}")
                if len(result["incompatible"]) > 5:
                    print(f"   ... and {len(result['incompatible']) - 5} more")

            # Show installation results
            if result.get("fixed_python") or result.get("failed_python"):
                print("\n" + "=" * 70)
                print("INSTALLATION RESULTS:")
                print("=" * 70)

                if result.get("fixed_python"):
                    print(
                        f"✅ Successfully installed: {len(result['fixed_python'])} packages"
                    )

                if result.get("failed_python"):
                    print(
                        f"❌ Failed to install: {len(result['failed_python'])} packages"
                    )
                    errors = result.get("errors", {})
                    for pkg in result["failed_python"]:
                        print(f"   - {pkg}: {errors.get(pkg, 'Unknown error')}")

                # Final verification
                if result.get("still_missing") is not None:
                    if not result["still_missing"]:
                        print("\n✅ All Python dependencies are now satisfied!")
                    else:
                        print(
                            f"\n⚠️  Still missing {len(result['still_missing'])} packages"
                        )
                        print("\nTry running again or install manually:")
                        missing_sample = result["still_missing"][:3]
                        print(f"  pip install {' '.join(missing_sample)}")

            print("\n" + "=" * 70)
            print("DONE")
            print("=" * 70)

            return CommandResult.success_result("Dependency fix completed", data=result)

        except Exception as e:
            self._logger.error(f"Error fixing dependencies: {e}", exc_info=True)
            return CommandResult.error_result(f"Error fixing dependencies: {e}")

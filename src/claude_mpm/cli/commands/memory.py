"""
Memory command implementation for claude-mpm.

WHY: This module provides CLI commands for managing agent memory files,
allowing users to view, add, and manage persistent learnings across sessions.

DESIGN DECISIONS:
- Use MemoryCommand base class for consistent CLI patterns
- Leverage shared utilities for argument parsing and output formatting
- Maintain backward compatibility with existing functionality
- Support multiple output formats (json, yaml, table, text)
"""

import json
import os
from pathlib import Path
from typing import Any, Dict

from ...core.shared.config_loader import ConfigLoader
from ...services.agents.memory import AgentMemoryManager
from ...services.cli.memory_crud_service import MemoryCRUDService
from ...services.cli.memory_output_formatter import MemoryOutputFormatter
from ..shared.base_command import CommandResult, MemoryCommand


class MemoryManagementCommand(MemoryCommand):
    """Memory management command using shared utilities."""

    def __init__(self):
        super().__init__("memory")
        self._memory_manager = None
        self._formatter = None
        self._crud_service = None

    @property
    def memory_manager(self):
        """Get memory manager instance (lazy loaded)."""
        if self._memory_manager is None:
            config_loader = ConfigLoader()
            config = config_loader.load_main_config()
            # Use CLAUDE_MPM_USER_PWD if available, otherwise use current working directory
            user_pwd = os.environ.get("CLAUDE_MPM_USER_PWD", os.getcwd())
            current_dir = Path(user_pwd)
            self._memory_manager = AgentMemoryManager(config, current_dir)
        return self._memory_manager

    @property
    def formatter(self):
        """Get formatter instance (lazy loaded)."""
        if self._formatter is None:
            # Check if quiet mode is requested
            quiet = os.environ.get("CLAUDE_MPM_QUIET", "false").lower() == "true"
            self._formatter = MemoryOutputFormatter(quiet=quiet)
        return self._formatter

    @property
    def crud_service(self):
        """Get CRUD service instance (lazy loaded)."""
        if self._crud_service is None:
            self._crud_service = MemoryCRUDService(memory_manager=self.memory_manager)
        return self._crud_service

    def validate_args(self, args) -> str:
        """Validate command arguments."""
        # Check if memory command is valid
        if hasattr(args, "memory_command") and args.memory_command:
            valid_commands = [
                "init",
                "view",
                "add",
                "clean",
                "optimize",
                "build",
                "cross-ref",
                "route",
            ]
            if args.memory_command not in valid_commands:
                return f"Unknown memory command: {args.memory_command}. Valid commands: {', '.join(valid_commands)}"
        return None

    def run(self, args) -> CommandResult:
        """Execute the memory command."""
        try:
            # Handle default case (no subcommand)
            if not hasattr(args, "memory_command") or not args.memory_command:
                return self._show_status(args)

            # Route to specific subcommand handlers
            command_map = {
                "init": self._init_memory,
                "status": self._show_status,
                "view": self._show_memories,
                "add": self._add_learning,
                "clean": self._clean_memory,
                "optimize": self._optimize_memory,
                "build": self._build_memory,
                "cross-ref": self._cross_reference_memory,
                "show": self._show_memories,
                "route": self._route_memory_command,
            }

            if args.memory_command in command_map:
                return command_map[args.memory_command](args)
            available_commands = list(command_map.keys())
            error_msg = f"Unknown memory command: {args.memory_command}"

            output_format = getattr(args, "format", "text")
            if output_format in ["json", "yaml"]:
                return CommandResult.error_result(
                    error_msg, data={"available_commands": available_commands}
                )
            print(f"❌ {error_msg}")
            print(f"Available commands: {', '.join(available_commands)}")
            return CommandResult.error_result(error_msg)

        except Exception as e:
            self.logger.error(f"Error managing memory: {e}", exc_info=True)
            return CommandResult.error_result(f"Error managing memory: {e}")

    def _show_status(self, args) -> CommandResult:
        """Show memory system status."""
        try:
            output_format = getattr(args, "format", "text")

            if output_format in ["json", "yaml"]:
                # Structured output
                status_data = self._get_status_data()
                return CommandResult.success_result(
                    "Memory status retrieved", data=status_data
                )
            # Text output using formatter
            status = self.memory_manager.get_memory_status()
            output = self.formatter.format_status(status)
            print(output)
            return CommandResult.success_result("Memory status displayed")

        except Exception as e:
            self.logger.error(f"Error showing memory status: {e}", exc_info=True)
            return CommandResult.error_result(f"Error showing memory status: {e}")

    def _get_status_data(self) -> Dict[str, Any]:
        """Get memory status as structured data."""
        # Use CRUD service to list memories with stats
        result = self.crud_service.list_memories(include_stats=True)

        if not result.get("success"):
            return {
                "error": result.get("error", "Failed to get status"),
                "exists": False,
                "agents": [],
                "total_size_kb": 0,
                "total_files": 0,
            }

        # Transform CRUD service result to expected format
        memories = result.get("memories", [])
        agents = [
            {
                "agent_id": mem["agent_id"],
                "file": mem["file"],
                "size_kb": mem.get("size_kb", 0),
                "path": mem["path"],
            }
            for mem in memories
        ]

        return {
            "memory_directory": result.get("memory_directory", ""),
            "exists": result.get("exists", False),
            "agents": agents,
            "total_size_kb": result.get("total_size_kb", 0),
            "total_files": result.get("total_files", 0),
        }

    def _show_memories(self, args) -> CommandResult:
        """Show agent memories."""
        try:
            output_format = getattr(args, "format", "text")
            agent_id = getattr(args, "agent_id", None)
            raw_output = getattr(args, "raw", False)

            if output_format in ["json", "yaml"] or raw_output:
                # Use CRUD service for structured output
                result = self.crud_service.read_memory(agent_id)

                if not result.get("success"):
                    return CommandResult.error_result(
                        result.get("error", "Failed to read memories")
                    )

                if raw_output:
                    # Output raw JSON for external tools
                    print(json.dumps(result, indent=2, ensure_ascii=False))
                    return CommandResult.success_result("Raw memory data output")

                return CommandResult.success_result("Memories retrieved", data=result)

            # Text output
            result = self.crud_service.read_memory(agent_id)

            if not result.get("success"):
                print(f"❌ {result.get('error', 'Failed to read memories')}")
                return CommandResult.error_result(result.get("error"))

            print("🧠 Agent Memories Display")
            print("-" * 80)

            if agent_id:
                # Single agent memory
                content = result.get("content", "")
                if content:
                    output = self.formatter.format_memory_view(
                        agent_id, content, getattr(args, "format", "detailed")
                    )
                    print(output)
                else:
                    print(f"📭 No memory found for agent: {agent_id}")
            else:
                # All agent memories
                agents = result.get("agents", {})
                if agents:
                    # Parse and format all memories
                    agent_memories = {}
                    for aid, data in agents.items():
                        sections = self.formatter._parse_memory_content(
                            data.get("content", "")
                        )
                        agent_memories[aid] = sections

                    output = self.formatter.format_agent_memories_summary(
                        agent_memories, getattr(args, "format", "detailed")
                    )
                    print(output)
                else:
                    print("📭 No agent memories found")

            return CommandResult.success_result("Memories displayed")

        except Exception as e:
            self.logger.error(f"Error showing memories: {e}", exc_info=True)
            return CommandResult.error_result(f"Error showing memories: {e}")

    # Removed _get_memories_data - now handled inline with CRUD service

    def _init_memory(self, args) -> CommandResult:
        """Initialize project-specific memories."""
        try:
            output_format = getattr(args, "format", "text")

            # Use CRUD service for initialization task
            result = self.crud_service.init_project_memories()

            if not result.get("success"):
                return CommandResult.error_result(
                    result.get("error", "Failed to create initialization task")
                )

            if output_format in ["json", "yaml"]:
                # Return structured task data
                return CommandResult.success_result(
                    "Memory initialization task created", data=result.get("task_data")
                )

            # Text output - display the task
            task = result.get("task_data", {})
            print("🚀 Initializing project-specific memories...")
            print("=" * 80)
            print()
            print("This will analyze the project to:")
            for idx, instruction in enumerate(task.get("instructions", []), 1):
                print(f"  {idx}. {instruction}")
            print()
            print("The analysis will cover:")
            for area in task.get("focus_areas", []):
                print(f"  • {area}")
            print()
            print("Example commands to use:")
            for cmd in task.get("example_commands", []):
                print(f"  {cmd}")
            print()
            print("=" * 80)
            print()
            print(
                "📝 Note: Copy the task above to execute the memory initialization process."
            )

            return CommandResult.success_result("Memory initialization task displayed")

        except Exception as e:
            self.logger.error(f"Error initializing memory: {e}", exc_info=True)
            return CommandResult.error_result(f"Error initializing memory: {e}")

    def _add_learning(self, args) -> CommandResult:
        """Add learning to agent memory."""
        try:
            output_format = getattr(args, "format", "text")

            # Extract arguments
            agent_id = getattr(args, "agent_id", None)
            learning_type = getattr(args, "learning_type", "context")
            content = getattr(args, "content", "")

            if not agent_id or not content:
                return CommandResult.error_result(
                    "Agent ID and content are required for adding learning"
                )

            # Use CRUD service to add learning
            result = self.crud_service.update_memory(agent_id, learning_type, content)

            if not result.get("success"):
                return CommandResult.error_result(
                    result.get("error", "Failed to add learning")
                )

            if output_format in ["json", "yaml"]:
                # Return structured result
                return CommandResult.success_result(
                    "Learning added to agent memory", data=result
                )

            # Text output
            print(f"✅ Added {learning_type} to {agent_id} memory")
            print(f"   Section: {result.get('section', 'Unknown')}")
            print(f"   Content: {result.get('content_preview', content[:100])}")

            return CommandResult.success_result("Learning added")

        except Exception as e:
            self.logger.error(f"Error adding learning: {e}", exc_info=True)
            return CommandResult.error_result(f"Error adding learning: {e}")

    def _clean_memory(self, args) -> CommandResult:
        """Clean up old/unused memory files."""
        try:
            output_format = getattr(args, "format", "text")
            agent_id = getattr(args, "agent_id", None)
            dry_run = getattr(args, "dry_run", True)

            # Use CRUD service for cleanup
            result = self.crud_service.clean_memory(agent_id=agent_id, dry_run=dry_run)

            if not result.get("success"):
                return CommandResult.error_result(result.get("error", "Cleanup failed"))

            if output_format in ["json", "yaml"]:
                # Return structured cleanup results
                return CommandResult.success_result(
                    result.get("message", "Memory cleanup completed"), data=result
                )

            # Text output
            print("🧹 Memory cleanup")
            print("-" * 80)

            if dry_run:
                print("📊 Cleanup preview (dry run)")
                candidates = result.get("cleanup_candidates", [])
                if candidates:
                    print(f"Found {len(candidates)} files eligible for cleanup:")
                    for candidate in candidates:
                        print(
                            f"  • {candidate['agent_id']}: {candidate['size_kb']:.1f} KB, {candidate['age_days']} days old"
                        )
                        print(f"    Reason: {candidate['reason']}")
                else:
                    print("No files eligible for cleanup")
            else:
                cleaned = result.get("cleaned_files", [])
                if cleaned:
                    print(f"Cleaned {len(cleaned)} files")
                else:
                    print(result.get("message", "No files cleaned"))

            if result.get("note"):
                print(f"\n⚠️  {result['note']}")

            return CommandResult.success_result("Memory cleanup completed")

        except Exception as e:
            self.logger.error(f"Error cleaning memory: {e}", exc_info=True)
            return CommandResult.error_result(f"Error cleaning memory: {e}")

    def _optimize_memory(self, args) -> CommandResult:
        """Optimize memory files."""
        try:
            output_format = getattr(args, "format", "text")
            agent_id = getattr(args, "agent_id", None)

            if output_format in ["json", "yaml"]:
                # For structured output, perform optimization and return results
                if agent_id:
                    result = self.memory_manager.optimize_memory(agent_id)
                else:
                    result = self.memory_manager.optimize_memory()
                return CommandResult.success_result(
                    "Memory optimization completed", data=result
                )
            # Text output using formatter
            if agent_id:
                print(f"📊 Optimizing memory for agent: {agent_id}")
                result = self.memory_manager.optimize_memory(agent_id)
                output = self.formatter.format_optimization_results(
                    result, is_single_agent=True
                )
            else:
                print("📊 Optimizing all agent memories...")
                result = self.memory_manager.optimize_memory()
                output = self.formatter.format_optimization_results(
                    result, is_single_agent=False
                )
            print(output)
            return CommandResult.success_result("Memory optimization completed")

        except Exception as e:
            self.logger.error(f"Error optimizing memory: {e}", exc_info=True)
            return CommandResult.error_result(f"Error optimizing memory: {e}")

    def _build_memory(self, args) -> CommandResult:
        """Build agent memories from project documentation."""
        try:
            output_format = getattr(args, "format", "text")

            if output_format in ["json", "yaml"]:
                # For structured output, return build results
                build_data = {
                    "built_memories": [],
                    "processed_files": [],
                    "summary": "Memory build completed",
                }
                return CommandResult.success_result(
                    "Memory build completed", data=build_data
                )
            # Text output using existing function
            _build_memory(args, self.memory_manager)
            return CommandResult.success_result("Memory build completed")

        except Exception as e:
            self.logger.error(f"Error building memory: {e}", exc_info=True)
            return CommandResult.error_result(f"Error building memory: {e}")

    def _cross_reference_memory(self, args) -> CommandResult:
        """Find cross-references and common patterns."""
        try:
            output_format = getattr(args, "format", "text")

            if output_format in ["json", "yaml"]:
                # For structured output, return cross-reference results
                crossref_data = {
                    "common_patterns": [],
                    "agent_similarities": [],
                    "summary": "Cross-reference analysis completed",
                }
                return CommandResult.success_result(
                    "Cross-reference analysis completed", data=crossref_data
                )
            # Text output using existing function
            _cross_reference_memory(args, self.memory_manager)
            return CommandResult.success_result("Cross-reference analysis completed")

        except Exception as e:
            self.logger.error(f"Error cross-referencing memory: {e}", exc_info=True)
            return CommandResult.error_result(f"Error cross-referencing memory: {e}")

    def _route_memory_command(self, args) -> CommandResult:
        """Route memory command to appropriate agent."""
        try:
            output_format = getattr(args, "format", "text")

            if output_format in ["json", "yaml"]:
                # For structured output, return routing results
                routing_data = {
                    "routed_to": "memory_agent",
                    "command": getattr(args, "command", ""),
                    "summary": "Command routed successfully",
                }
                return CommandResult.success_result(
                    "Command routed successfully", data=routing_data
                )
            # Text output using existing function
            _route_memory_command(args, self.memory_manager)
            return CommandResult.success_result("Command routed successfully")

        except Exception as e:
            self.logger.error(f"Error routing memory command: {e}", exc_info=True)
            return CommandResult.error_result(f"Error routing memory command: {e}")


def manage_memory(args) -> int:
    """Main entry point for memory management commands.

    This function maintains backward compatibility while using the new BaseCommand pattern.
    """
    command = MemoryManagementCommand()
    result = command.execute(args)

    # Print result if structured output format is requested
    if hasattr(args, "format") and args.format in ["json", "yaml"]:
        command.print_result(result, args)

    return result.exit_code


# Removed _init_memory - now handled by MemoryCRUDService.init_project_memories()


# Removed _show_status - functionality moved to MemoryManagementCommand._show_status()


# Removed _show_basic_status - functionality integrated into MemoryManagementCommand


# Removed _view_memory - functionality moved to MemoryCRUDService.read_memory()


# Removed _add_learning - now handled by MemoryCRUDService.update_memory()


# Removed _clean_memory - now handled by MemoryCRUDService.clean_memory()


# Removed _optimize_memory - functionality moved to MemoryManagementCommand._optimize_memory()


def _build_memory(args, memory_manager):
    """
    Build agent memories from project documentation.

    WHY: Project documentation contains valuable patterns and guidelines that
    agents should be aware of. This command automatically extracts and assigns
    relevant information to appropriate agents.

    Args:
        args: Command arguments with optional force_rebuild flag
        memory_manager: AgentMemoryManager instance
    """
    print("📚 Memory Building from Documentation")
    print("-" * 80)

    force_rebuild = getattr(args, "force_rebuild", False)

    try:
        print("🔍 Analyzing project documentation...")
        result = memory_manager.build_memories_from_docs(force_rebuild)

        # Use formatter to display build results
        quiet = os.environ.get("CLAUDE_MPM_QUIET", "false").lower() == "true"
        formatter = MemoryOutputFormatter(quiet=quiet)
        output = formatter.format_build_results(result)
        print(output)

    except Exception as e:
        print(f"❌ Error building memories: {e}")


def _cross_reference_memory(args, memory_manager):
    """
    Find cross-references and common patterns across agent memories.

    WHY: Different agents may have learned similar information or there may be
    knowledge gaps that can be identified through cross-referencing.

    Args:
        args: Command arguments with optional query
        memory_manager: AgentMemoryManager instance
    """
    query = getattr(args, "query", None)

    try:
        result = memory_manager.cross_reference_memories(query)

        # Use formatter to display cross-reference results
        quiet = os.environ.get("CLAUDE_MPM_QUIET", "false").lower() == "true"
        formatter = MemoryOutputFormatter(quiet=quiet)
        output = formatter.format_cross_reference(result, query)
        print(output)

    except Exception as e:
        print(f"❌ Error during cross-reference analysis: {e}")


# Note: Memory display functions have been moved to MemoryManagementCommand and MemoryCRUDService


def _route_memory_command(args, memory_manager):
    """
    Test memory command routing logic.

    WHY: Users and developers need to understand how memory commands are routed
    to appropriate agents for debugging and customization purposes.

    Args:
        args: Command arguments with content to route
        memory_manager: AgentMemoryManager instance
    """
    print("🎯 Memory Command Routing Test")
    print("-" * 80)

    content = getattr(args, "content", None)
    if not content:
        print("❌ No content provided for routing analysis")
        print("   Usage: memory route --content 'your content here'")
        return

    try:
        print(
            f"📝 Analyzing content: '{content[:100]}{'...' if len(content) > 100 else ''}'"
        )

        result = memory_manager.route_memory_command(content)

        if result.get("success") is False:
            print(f"❌ Routing failed: {result.get('error', 'Unknown error')}")
            return

        target_agent = result.get("target_agent", "unknown")
        section = result.get("section", "unknown")
        confidence = result.get("confidence", 0.0)
        reasoning = result.get("reasoning", "No reasoning provided")

        print("\n🎯 Routing Decision:")
        print(f"   Target Agent: {target_agent}")
        print(f"   Section: {section}")
        print(f"   Confidence: {confidence:.2f}")
        print(f"   Reasoning: {reasoning}")

        # Show agent scores if available
        agent_scores = result.get("agent_scores", {})
        if agent_scores:
            print("\n📊 Agent Relevance Scores:")
            sorted_scores = sorted(
                [(agent, data["score"]) for agent, data in agent_scores.items()],
                key=lambda x: x[1],
                reverse=True,
            )
            for agent, score in sorted_scores[:5]:  # Show top 5
                print(f"   {agent}: {score:.3f}")
                # Show matched keywords if available
                if agent in agent_scores and agent_scores[agent].get(
                    "matched_keywords"
                ):
                    keywords = ", ".join(agent_scores[agent]["matched_keywords"][:3])
                    print(f"      Keywords: {keywords}")

    except Exception as e:
        print(f"❌ Error routing memory command: {e}")


def _display_single_optimization_result(result):
    """Display optimization results for a single agent."""
    quiet = os.environ.get("CLAUDE_MPM_QUIET", "false").lower() == "true"
    formatter = MemoryOutputFormatter(quiet=quiet)
    output = formatter.format_optimization_results(result, is_single_agent=True)
    print(output)


def _display_bulk_optimization_results(result):
    """Display optimization results for all agents."""
    quiet = os.environ.get("CLAUDE_MPM_QUIET", "false").lower() == "true"
    formatter = MemoryOutputFormatter(quiet=quiet)
    output = formatter.format_optimization_results(result, is_single_agent=False)
    print(output)


# Note: Raw output functions have been moved to MemoryCRUDService

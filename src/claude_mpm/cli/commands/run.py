from pathlib import Path

"""
Run command implementation for claude-mpm.

WHY: This module handles the main 'run' command which starts Claude sessions.
It's the most commonly used command and handles both interactive and non-interactive modes.

DESIGN DECISIONS:
- Use BaseCommand for consistent CLI patterns
- Leverage shared utilities for argument parsing and output formatting
- Maintain backward compatibility with existing functionality
- Support multiple output formats (json, yaml, table, text)
"""

import subprocess
import sys
from datetime import datetime, timezone
from typing import Optional

from ...constants import LogLevel
from ...core.logger import get_logger
from ...core.unified_paths import get_scripts_dir
from ...services.cli.session_manager import SessionManager

# SocketIOManager functionality now provided by UnifiedDashboardManager
from ...services.cli.startup_checker import StartupCheckerService
from ...services.cli.unified_dashboard_manager import UnifiedDashboardManager
from ..shared import BaseCommand, CommandResult
from ..startup_logging import (
    cleanup_old_startup_logs,
    log_startup_status,
    setup_startup_logging,
)
from ..utils import get_user_input


def filter_claude_mpm_args(claude_args):
    """
    Filter out claude-mpm specific arguments from claude_args before passing to Claude CLI.

    WHY: The argparse.REMAINDER captures ALL remaining arguments, including claude-mpm
    specific flags like --monitor, etc. Claude CLI doesn't understand these
    flags and will error if they're passed through.

    DESIGN DECISION: We maintain a list of known claude-mpm flags to filter out,
    ensuring only genuine Claude CLI arguments are passed through. We also remove
    the '--' separator that argparse uses, as it's not needed by Claude CLI.

    Args:
        claude_args: List of arguments captured by argparse.REMAINDER

    Returns:
        Filtered list of arguments safe to pass to Claude CLI
    """
    if not claude_args:
        return []

    # Known claude-mpm specific flags that should NOT be passed to Claude CLI
    # This includes all MPM-specific arguments from the parser
    mpm_flags = {
        # Run-specific flags
        "--monitor",
        "--websocket-port",
        "--no-hooks",
        "--no-tickets",
        "--intercept-commands",
        "--no-native-agents",
        "--launch-method",
        "--mpm-resume",
        "--reload-agents",  # New flag to force rebuild system agents
        # Dependency checking flags (MPM-specific)
        "--no-check-dependencies",
        "--force-check-dependencies",
        "--no-prompt",
        "--force-prompt",
        # Input/output flags (these are MPM-specific, not Claude CLI flags)
        "--input",
        "--non-interactive",
        # Common logging flags (these are MPM-specific, not Claude CLI flags)
        "--debug",
        "--logging",
        "--log-dir",
        # Framework flags (these are MPM-specific)
        "--framework-path",
        "--agents-dir",
        # Version flag (handled by MPM)
        "--version",
        # Short flags (MPM-specific equivalents)
        "-i",  # --input (MPM-specific, not Claude CLI)
        "-d",  # --debug (MPM-specific, not Claude CLI)
    }

    filtered_args = []
    i = 0
    while i < len(claude_args):
        arg = claude_args[i]

        # Skip the '--' separator used by argparse - Claude doesn't need it
        if arg == "--":
            i += 1
            continue

        # Check if this is a claude-mpm flag
        if arg in mpm_flags:
            # Skip this flag
            i += 1
            # Also skip the next argument if this flag expects a value
            value_expecting_flags = {
                "--websocket-port",
                "--launch-method",
                "--logging",
                "--log-dir",
                "--framework-path",
                "--agents-dir",
                "-i",
                "--input",
            }
            optional_value_flags = {
                "--mpm-resume"
            }  # These flags can have optional values (nargs="?")

            if arg in value_expecting_flags and i < len(claude_args):
                i += 1  # Skip the value too
            elif arg in optional_value_flags and i < len(claude_args):
                # For optional value flags, only skip next arg if it doesn't start with --
                next_arg = claude_args[i]
                if not next_arg.startswith("--"):
                    i += 1  # Skip the value
        else:
            # This is not a claude-mpm flag, keep it
            filtered_args.append(arg)
            i += 1

    return filtered_args


def create_session_context(session_id, session_manager):
    """
    Create enhanced context for resumed sessions.

    WHY: When resuming a session, we want to provide Claude with context about
    the previous session including what agents were used and when it was created.
    This helps maintain continuity across session boundaries.

    Args:
        session_id: Session ID being resumed
        session_manager: SessionManager instance

    Returns:
        Enhanced context string with session information
    """
    try:
        from ...core.claude_runner import create_simple_context
    except ImportError:
        from claude_mpm.core.claude_runner import create_simple_context

    base_context = create_simple_context()

    session_data = session_manager.get_session_info(session_id)
    if not session_data:
        return base_context

    # Add session resumption information
    session_info = f"""

# Session Resumption

You are resuming session {session_id[:8]}... which was:
- Created: {session_data.get("created_at", "unknown")}
- Last used: {session_data.get("last_used", "unknown")}
- Context: {session_data.get("context", "default")}
- Use count: {session_data.get("use_count", 0)}
"""

    # Add information about agents previously run in this session
    agents_run = session_data.get("agents_run", [])
    if agents_run:
        session_info += "\n- Previous agent activity:\n"
        for agent_info in agents_run[-5:]:  # Show last 5 agents
            session_info += f"  • {agent_info.get('agent', 'unknown')}: {agent_info.get('task', 'no description')[:50]}...\n"
        if len(agents_run) > 5:
            session_info += f"  (and {len(agents_run) - 5} other agent interactions)\n"

    session_info += "\nContinue from where you left off in this session."

    return base_context + session_info


class RunCommand(BaseCommand):
    """Run command using shared utilities."""

    def __init__(self):
        super().__init__("run")

    def validate_args(self, args) -> Optional[str]:
        """Validate command arguments."""
        # Run command has minimal validation requirements
        # Most validation is handled by the ClaudeRunner and related services
        return None

    def run(self, args) -> CommandResult:
        """Execute the run command."""
        try:
            # Execute the main run logic
            success = self._execute_run_session(args)

            # Log memory stats at session completion
            from ..startup_logging import log_memory_stats

            log_memory_stats(self.logger, "Session End Memory")

            if success:
                return CommandResult.success_result(
                    "Claude session completed successfully"
                )
            return CommandResult.error_result("Claude session failed", exit_code=1)

        except KeyboardInterrupt:
            self.logger.info("Session interrupted by user")
            return CommandResult.error_result(
                "Session cancelled by user", exit_code=130
            )
        except Exception as e:
            self.logger.error(f"Error running Claude session: {e}", exc_info=True)
            return CommandResult.error_result(f"Error running Claude session: {e}")

    def _execute_run_session(self, args) -> bool:
        """Execute the main run session logic."""
        # For now, delegate to the legacy function to maintain compatibility
        # TODO: Gradually migrate logic into the individual helper methods
        try:
            run_session_legacy(args)
            return True
        except Exception as e:
            self.logger.error(f"Run session failed: {e}")
            return False

    def _execute_run_session_new(self, args) -> bool:
        """Execute the main run session logic using new pattern."""
        try:
            # Log session start
            if args.logging != LogLevel.OFF.value:
                self.logger.info("Starting Claude MPM session")

            # Log MCP and monitor startup status
            if args.logging != LogLevel.OFF.value:
                monitor_mode = getattr(args, "monitor", False)
                websocket_port = getattr(args, "websocket_port", 8765)
                log_startup_status(monitor_mode, websocket_port)

            # Perform startup checks
            self._check_configuration_health()
            self._check_claude_json_memory(args)

            # Handle session management
            session_manager, resume_session_id, resume_context = (
                self._setup_session_management(args)
            )

            # Handle dependency checking
            self._handle_dependency_checking(args)

            # Setup monitoring if requested
            monitor_mode, websocket_port = self._setup_monitoring(args)

            # Configure Claude runner
            runner = self._setup_claude_runner(args, monitor_mode, websocket_port)

            # Create context and run session
            context = self._create_session_context(
                args, session_manager, resume_session_id, resume_context
            )

            # Execute the session
            return self._execute_session(args, runner, context)

        except Exception as e:
            self.logger.error(f"Run session failed: {e}")
            return False

    def _check_configuration_health(self):
        """Check configuration health at startup."""
        # Use new StartupCheckerService
        from ...core.config import Config

        config_service = Config()
        checker = StartupCheckerService(config_service)
        warnings = checker.check_configuration()
        checker.display_warnings(warnings)

    def _check_claude_json_memory(self, args):
        """Check .claude.json file size and warn about memory issues."""
        # Use new StartupCheckerService
        from ...core.config import Config

        config_service = Config()
        checker = StartupCheckerService(config_service)
        resume_enabled = getattr(args, "mpm_resume", False)
        warning = checker.check_memory(resume_enabled)
        if warning:
            checker.display_warnings([warning])

    def _setup_session_management(self, args):
        """Setup session management and handle resumption."""
        # Use the new SessionManager service from the CLI services layer
        session_manager = SessionManager()
        resume_session_id = None
        resume_context = None

        if hasattr(args, "mpm_resume") and args.mpm_resume:
            if args.mpm_resume == "last":
                # Resume the last interactive session
                resume_session_id = session_manager.get_last_interactive_session()
                if resume_session_id:
                    session_data = session_manager.get_session_info(resume_session_id)
                    if session_data:
                        resume_context = session_data.get("context", "default")
                        self.logger.info(
                            f"Resuming session {resume_session_id} (context: {resume_context})"
                        )
                        print(
                            f"🔄 Resuming session {resume_session_id[:8]}... (created: {session_data.get('created_at', 'unknown')})"
                        )
                    else:
                        self.logger.warning(f"Session {resume_session_id} not found")
                else:
                    self.logger.info("No recent interactive sessions found")
                    print("[INFO]️  No recent interactive sessions found to resume")
            else:
                # Resume specific session by ID
                resume_session_id = args.mpm_resume
                session_data = session_manager.get_session_info(resume_session_id)
                if session_data:
                    resume_context = session_data.get("context", "default")
                    self.logger.info(
                        f"Resuming session {resume_session_id} (context: {resume_context})"
                    )
                    print(
                        f"🔄 Resuming session {resume_session_id[:8]}... (context: {resume_context})"
                    )
                else:
                    self.logger.error(f"Session {resume_session_id} not found")
                    print(f"❌ Session {resume_session_id} not found")
                    print("💡 Use 'claude-mpm sessions' to list available sessions")
                    raise RuntimeError(f"Session {resume_session_id} not found")

        return session_manager, resume_session_id, resume_context

    def _handle_dependency_checking(self, args):
        """Handle smart dependency checking."""
        # Smart dependency checking - only when needed
        if getattr(args, "check_dependencies", True):  # Default to checking
            try:
                from ...utils.agent_dependency_loader import AgentDependencyLoader
                from ...utils.dependency_cache import SmartDependencyChecker
                from ...utils.environment_context import should_prompt_for_dependencies

                # Initialize smart checker
                smart_checker = SmartDependencyChecker()
                loader = AgentDependencyLoader(auto_install=False)

                # Check if agents have changed
                _has_changed, deployment_hash = loader.has_agents_changed()

                # Determine if we should check dependencies
                should_check, check_reason = smart_checker.should_check_dependencies(
                    force_check=getattr(args, "force_check_dependencies", False),
                    deployment_hash=deployment_hash,
                )

                if should_check:
                    self.logger.info(f"Checking dependencies: {check_reason}")

                    # Check if we should prompt for dependencies
                    should_prompt = should_prompt_for_dependencies()

                    if should_prompt:
                        # Check dependencies and prompt for installation if needed
                        missing_deps = loader.check_dependencies()
                        if missing_deps:
                            self.logger.info(
                                f"Found {len(missing_deps)} missing dependencies"
                            )

                            # Prompt user for installation
                            print(
                                f"\n📦 Found {len(missing_deps)} missing dependencies:"
                            )
                            for dep in missing_deps[:5]:  # Show first 5
                                print(f"  • {dep}")
                            if len(missing_deps) > 5:
                                print(f"  ... and {len(missing_deps) - 5} more")

                            response = (
                                input("\nInstall missing dependencies? (y/N): ")
                                .strip()
                                .lower()
                            )
                            if response in ["y", "yes"]:
                                loader.auto_install = True
                                loader.install_dependencies(missing_deps)
                                print("✅ Dependencies installed successfully")
                            else:
                                print("⚠️  Continuing without installing dependencies")
                    else:
                        # Just check without prompting
                        missing_deps = loader.check_dependencies()
                        if missing_deps:
                            self.logger.warning(
                                f"Found {len(missing_deps)} missing dependencies"
                            )
                            print(
                                f"⚠️  Found {len(missing_deps)} missing dependencies. Use --force-check-dependencies to install."
                            )

                    # Update cache
                    smart_checker.update_cache(deployment_hash)
                else:
                    self.logger.debug(f"Skipping dependency check: {check_reason}")

            except ImportError as e:
                self.logger.warning(f"Dependency checking not available: {e}")
            except Exception as e:
                self.logger.warning(f"Dependency check failed: {e}")

    def _setup_monitoring(self, args):
        """Setup monitoring configuration using UnifiedDashboardManager."""
        monitor_mode = getattr(args, "monitor", False)
        websocket_port = 8765  # Default port

        if monitor_mode:
            # Use UnifiedDashboardManager for server management
            dashboard_manager = UnifiedDashboardManager(self.logger)

            # Check dependencies
            deps_ok, error_msg = dashboard_manager.ensure_dependencies()
            if not deps_ok:
                self.logger.warning(
                    f"Socket.IO dependencies not available: {error_msg}, disabling monitor mode"
                )
                monitor_mode = False
            else:
                # Find available port and start server
                websocket_port = dashboard_manager.find_available_port(8765)
                success, _server_info = dashboard_manager.start_server(
                    port=websocket_port
                )

                if not success:
                    self.logger.warning(
                        "Failed to start Socket.IO server, disabling monitor mode"
                    )
                    monitor_mode = False
                else:
                    # Use UnifiedDashboardManager for browser opening only
                    dashboard_manager = UnifiedDashboardManager(self.logger)
                    monitor_url = dashboard_manager.get_dashboard_url(websocket_port)

                    # Try to open browser
                    browser_opened = dashboard_manager.open_browser(monitor_url)
                    args._browser_opened_by_cli = browser_opened

                    if not browser_opened:
                        print(f"💡 Monitor interface available at: {monitor_url}")

        return monitor_mode, websocket_port

    def _setup_claude_runner(self, args, monitor_mode: bool, websocket_port: int):
        """Setup and configure the Claude runner."""
        try:
            from ...core.claude_runner import ClaudeRunner
        except ImportError:
            from claude_mpm.core.claude_runner import ClaudeRunner

        # Configure tickets
        enable_tickets = not getattr(args, "no_tickets", False)

        # Configure launch method
        launch_method = "exec"  # Default
        if getattr(args, "subprocess", False):
            launch_method = "subprocess"

        # Configure WebSocket
        enable_websocket = monitor_mode

        # Build Claude arguments
        claude_args = []
        if hasattr(args, "claude_args") and args.claude_args:
            claude_args.extend(args.claude_args)

        # Create runner
        runner = ClaudeRunner(
            enable_tickets=enable_tickets,
            log_level=args.logging,
            claude_args=claude_args,
            launch_method=launch_method,
            enable_websocket=enable_websocket,
            websocket_port=websocket_port,
        )

        # Set browser opening flag for monitor mode
        if monitor_mode:
            runner._should_open_monitor_browser = True
            runner._browser_opened_by_cli = getattr(
                args, "_browser_opened_by_cli", False
            )

        return runner

    def _create_session_context(
        self, args, session_manager, resume_session_id, resume_context
    ):
        """Create session context."""
        try:
            from ...core.claude_runner import create_simple_context
        except ImportError:
            from claude_mpm.core.claude_runner import create_simple_context

        if resume_session_id and resume_context:
            # For resumed sessions, create enhanced context with session information
            context = create_session_context(resume_session_id, session_manager)
            # Update session usage
            session = session_manager.load_session(resume_session_id)
            if session:
                session.last_used = datetime.now(timezone.utc).isoformat()
                session.use_count += 1
                session_manager.save_session(session)
        else:
            # Create a new session for tracking
            new_session = session_manager.create_session("default")
            context = create_simple_context()
            self.logger.info(f"Created new session {new_session.id}")

        return context

    def _execute_session(self, args, runner, context) -> bool:
        """Execute the Claude session."""
        try:
            # Run session based on mode
            non_interactive = getattr(args, "non_interactive", False)
            input_arg = getattr(args, "input", None)

            if non_interactive or input_arg:
                # Non-interactive mode
                user_input = get_user_input(input_arg, self.logger)
                success = runner.run_oneshot(user_input, context)
                if not success:
                    self.logger.error("Session failed")
                    return False
            # Interactive mode
            elif getattr(args, "intercept_commands", False):
                wrapper_path = get_scripts_dir() / "interactive_wrapper.py"
                if wrapper_path.exists():
                    print("Starting interactive session with command interception...")
                    subprocess.run([sys.executable, str(wrapper_path)], check=False)
                else:
                    self.logger.warning(
                        "Interactive wrapper not found, falling back to normal mode"
                    )
                    runner.run_interactive(context)
            else:
                runner.run_interactive(context)

            return True

        except Exception as e:
            self.logger.error(f"Session execution failed: {e}")
            return False


def _handle_reload_agents(logger):
    """
    Handle the --reload-agents flag by deleting all local claude-mpm system agents.

    This forces a fresh rebuild of system agents on the next deployment,
    while preserving user-created agents.

    Args:
        logger: Logger instance for output
    """
    try:
        logger.info("Reloading system agents - cleaning existing deployments...")

        # Import the cleanup service
        from ...services.agents.deployment.agent_deployment import (
            AgentDeploymentService,
        )
        from ...services.cli.agent_cleanup_service import AgentCleanupService

        # Create services
        deployment_service = AgentDeploymentService()
        cleanup_service = AgentCleanupService(deployment_service)

        # Determine the agents directory
        agents_dir = None  # Will auto-detect project or user directory

        # Clean deployed agents (preserves user agents)
        result = cleanup_service.clean_deployed_agents(agents_dir)

        # Check if cleanup was successful based on the result structure
        # The service returns a dict with 'removed', 'preserved', and possibly 'errors' keys
        # If it has 'success' key, use it; otherwise infer from the result
        success = (
            result.get("success", True)
            if "success" in result
            else not result.get("errors")
        )

        if success:
            removed_count = result.get("cleaned_count", len(result.get("removed", [])))
            removed_agents = result.get("removed", [])
            preserved_agents = result.get("preserved", [])

            if removed_count > 0:
                logger.info(f"✅ Successfully removed {removed_count} system agents")
                if removed_agents:
                    logger.debug(f"Removed agents: {', '.join(removed_agents)}")
                print(f"🔄 Cleaned {removed_count} claude-mpm system agents")
            else:
                logger.info("No system agents found to clean")
                print("[INFO]️  No system agents found - already clean")

            if preserved_agents:
                logger.info(f"Preserved {len(preserved_agents)} user-created agents")
                print(f"✅ Preserved {len(preserved_agents)} user-created agents")

            print("🚀 System agents will be rebuilt on next use")
        else:
            error = result.get("error", "Cleanup failed")
            if result.get("errors"):
                error = f"Cleanup errors: {', '.join(result['errors'])}"
            logger.error(f"Failed to clean system agents: {error}")
            print(f"❌ Error cleaning agents: {error}")

    except Exception as e:
        logger.error(f"Error handling --reload-agents: {e}", exc_info=True)
        print(f"❌ Failed to reload agents: {e}")
        # Don't fail the entire session, just log the error
        print("⚠️  Continuing with existing agents...")


def run_session(args):
    """
    Main entry point for run command.

    This function maintains backward compatibility while using the new BaseCommand pattern.
    """
    command = RunCommand()
    result = command.execute(args)

    # For run command, we don't typically need structured output
    # but we should respect the exit code
    return result.exit_code


def run_session_legacy(args):
    """
    Legacy run session implementation.

    WHY: This contains the original run_session logic, preserved during migration
    to BaseCommand pattern. Will be gradually refactored into the RunCommand class.

    DESIGN DECISION: We use ClaudeRunner to handle the complexity of
    subprocess management and hook integration, keeping this function focused
    on high-level orchestration.

    Args:
        args: Parsed command line arguments
    """
    # Only setup startup logging if user wants logging
    if args.logging != LogLevel.OFF.value:
        # Set up startup logging to file early in the process
        setup_startup_logging(Path.cwd())

    logger = get_logger("cli")
    if args.logging != LogLevel.OFF.value:
        logger.info("Starting Claude MPM session")
        # Log file already announced in startup_logging.py when created

    # Clean up old startup logs (using configured retention count)
    if args.logging != LogLevel.OFF.value:
        try:
            deleted_count = cleanup_old_startup_logs(Path.cwd())
            if deleted_count > 0:
                logger.debug(f"Cleaned up {deleted_count} old startup log files")
        except Exception as e:
            logger.debug(f"Failed to clean up old logs: {e}")

    # Log MCP and monitor startup status
    if args.logging != LogLevel.OFF.value:
        monitor_mode = getattr(args, "monitor", False)
        websocket_port = getattr(args, "websocket_port", 8765)
        log_startup_status(monitor_mode, websocket_port)

    # Perform startup configuration check
    _check_configuration_health(logger)

    # Check for memory usage issues with .claude.json
    _check_claude_json_memory(args, logger)

    # Handle --reload-agents flag if specified
    if getattr(args, "reload_agents", False):
        _handle_reload_agents(logger)

    # Trigger vector search indexing
    try:
        from ...cli.startup_logging import start_vector_search_indexing

        start_vector_search_indexing()
    except Exception as e:
        logger.debug(f"Failed to start vector search indexing: {e}")

    try:
        from ...core.claude_runner import ClaudeRunner, create_simple_context
    except ImportError:
        from claude_mpm.core.claude_runner import ClaudeRunner, create_simple_context

    # Handle session resumption using the new SessionManager service
    session_manager = SessionManager()
    resume_session_id = None
    resume_context = None

    if hasattr(args, "mpm_resume") and args.mpm_resume:
        if args.mpm_resume == "last":
            # Resume the last interactive session
            resume_session_id = session_manager.get_last_interactive_session()
            if resume_session_id:
                session_data = session_manager.get_session_info(resume_session_id)
                if session_data:
                    resume_context = session_data.get("context", "default")
                    logger.info(
                        f"Resuming session {resume_session_id} (context: {resume_context})"
                    )
                    print(
                        f"🔄 Resuming session {resume_session_id[:8]}... (created: {session_data.get('created_at', 'unknown')})"
                    )
                else:
                    logger.warning(f"Session {resume_session_id} not found")
            else:
                logger.info("No recent interactive sessions found")
                print("[INFO]️  No recent interactive sessions found to resume")
        else:
            # Resume specific session by ID
            resume_session_id = args.mpm_resume
            session_data = session_manager.get_session_info(resume_session_id)
            if session_data:
                resume_context = session_data.get("context", "default")
                logger.info(
                    f"Resuming session {resume_session_id} (context: {resume_context})"
                )
                print(
                    f"🔄 Resuming session {resume_session_id[:8]}... (context: {resume_context})"
                )
            else:
                logger.error(f"Session {resume_session_id} not found")
                print(f"❌ Session {resume_session_id} not found")
                print("💡 Use 'claude-mpm sessions' to list available sessions")
                return

    # Deploy MPM slash commands to user's Claude configuration
    try:
        from ...services.command_deployment_service import deploy_commands_on_startup

        deploy_commands_on_startup(force=False)
    except Exception as e:
        logger.debug(f"Failed to deploy MPM commands (non-critical): {e}")

    # Skip native agents if disabled
    if getattr(args, "no_native_agents", False):
        print("Native agents disabled")
    else:
        # Agent versions removed from startup display - use /mpm-agents to view
        # list_agent_versions_at_startup()
        pass

    # Smart dependency checking - only when needed
    if getattr(args, "check_dependencies", True):  # Default to checking
        try:
            from ...utils.agent_dependency_loader import AgentDependencyLoader
            from ...utils.dependency_cache import SmartDependencyChecker
            from ...utils.environment_context import should_prompt_for_dependencies

            # Initialize smart checker
            smart_checker = SmartDependencyChecker()
            loader = AgentDependencyLoader(auto_install=False)

            # Check if agents have changed
            _has_changed, deployment_hash = loader.has_agents_changed()

            # Determine if we should check dependencies
            should_check, check_reason = smart_checker.should_check_dependencies(
                force_check=getattr(args, "force_check_dependencies", False),
                deployment_hash=deployment_hash,
            )

            if should_check:
                # Check if we're in an environment where prompting makes sense
                can_prompt, prompt_reason = should_prompt_for_dependencies(
                    force_prompt=getattr(args, "force_prompt", False),
                    force_skip=getattr(args, "no_prompt", False),
                )

                logger.debug(f"Dependency check needed: {check_reason}")
                logger.debug(f"Interactive prompting: {can_prompt} ({prompt_reason})")

                # Get or check dependencies
                results, was_cached = smart_checker.get_or_check_dependencies(
                    loader=loader,
                    force_check=getattr(args, "force_check_dependencies", False),
                )

                # Show summary if there are missing dependencies
                if results["summary"]["missing_python"]:
                    missing_count = len(results["summary"]["missing_python"])
                    print(f"⚠️  {missing_count} agent dependencies missing")

                    if can_prompt and missing_count > 0:
                        # Interactive prompt for installation
                        print("\n📦 Missing dependencies detected:")
                        for dep in results["summary"]["missing_python"][:5]:
                            print(f"   - {dep}")
                        if missing_count > 5:
                            print(f"   ... and {missing_count - 5} more")

                        print("\nWould you like to install them now?")
                        print("  [y] Yes, install missing dependencies")
                        print("  [n] No, continue without installing")
                        print("  [q] Quit")

                        sys.stdout.flush()  # Ensure prompt is displayed before input

                        # Check if we're in a TTY environment for proper input handling
                        if not sys.stdin.isatty():
                            # In non-TTY environment (like pipes), use readline
                            print("\nChoice [y/n/q]: ", end="", flush=True)
                            try:
                                response = sys.stdin.readline().strip().lower()
                                # Handle various line endings and control characters
                                response = (
                                    response.replace("\r", "").replace("\n", "").strip()
                                )
                            except (EOFError, KeyboardInterrupt):
                                response = "q"
                        else:
                            # In TTY environment, use normal input()
                            try:
                                response = input("\nChoice [y/n/q]: ").strip().lower()
                            except (EOFError, KeyboardInterrupt):
                                response = "q"

                        try:
                            if response == "y":
                                print("\n🔧 Installing missing dependencies...")
                                loader.auto_install = True
                                (
                                    success,
                                    error,
                                ) = loader.install_missing_dependencies(
                                    results["summary"]["missing_python"]
                                )
                                if success:
                                    print("✅ Dependencies installed successfully")
                                    # Invalidate cache after installation
                                    smart_checker.cache.invalidate(deployment_hash)
                                else:
                                    print(f"❌ Installation failed: {error}")
                            elif response == "q":
                                print("👋 Exiting...")
                                return
                            else:
                                print("⏩ Continuing without installing dependencies")
                        except (EOFError, KeyboardInterrupt):
                            print("\n⏩ Continuing without installing dependencies")
                    else:
                        # Non-interactive environment or prompting disabled
                        print(
                            "   Run 'pip install \"claude-mpm[agents]\"' to install all agent dependencies"
                        )
                        if not can_prompt:
                            logger.debug(
                                f"Not prompting for installation: {prompt_reason}"
                            )
                elif was_cached:
                    logger.debug("Dependencies satisfied (cached result)")
                else:
                    logger.debug("All dependencies satisfied")
            else:
                logger.debug(f"Skipping dependency check: {check_reason}")

        except Exception as e:
            if args.logging != LogLevel.OFF.value:
                logger.debug(f"Could not check agent dependencies: {e}")
                # Continue anyway - don't block execution

    # Create simple runner
    enable_tickets = not args.no_tickets
    raw_claude_args = getattr(args, "claude_args", []) or []

    # Add --resume to claude_args if the flag is set
    resume_flag_present = getattr(args, "resume", False)
    if resume_flag_present:
        logger.info("📌 --resume flag detected in args")
        if "--resume" not in raw_claude_args:
            raw_claude_args = ["--resume", *raw_claude_args]
            logger.info("✅ Added --resume to claude_args")
        else:
            logger.info("[INFO]️ --resume already in claude_args")

    # Filter out claude-mpm specific flags before passing to Claude CLI
    logger.debug(f"Pre-filter claude_args: {raw_claude_args}")
    claude_args = filter_claude_mpm_args(raw_claude_args)
    monitor_mode = getattr(args, "monitor", False)

    # Enhanced debug logging for argument filtering
    if raw_claude_args != claude_args:
        filtered_out = list(set(raw_claude_args) - set(claude_args))
        logger.debug(f"Filtered out MPM-specific args: {filtered_out}")

    logger.info(f"Final claude_args being passed: {claude_args}")

    # Explicit verification of --resume flag
    if resume_flag_present:
        if "--resume" in claude_args:
            logger.info("✅ CONFIRMED: --resume flag will be passed to Claude CLI")
        else:
            logger.error("❌ WARNING: --resume flag was filtered out! This is a bug!")
            logger.error(f"   Original args: {raw_claude_args}")
            logger.error(f"   Filtered args: {claude_args}")

    # Use the specified launch method (default: exec)
    launch_method = getattr(args, "launch_method", "exec")

    enable_websocket = getattr(args, "monitor", False) or monitor_mode
    websocket_port = getattr(args, "websocket_port", 8765)

    # Display Socket.IO server info if enabled
    if enable_websocket:
        # Use UnifiedDashboardManager for server management
        dashboard_manager = UnifiedDashboardManager(logger)

        # Check dependencies
        print("🔧 Checking Socket.IO dependencies...")
        deps_ok, error_msg = dashboard_manager.ensure_dependencies()

        if not deps_ok:
            print(f"❌ Failed to install Socket.IO dependencies: {error_msg}")
            print(
                "  Please install manually: pip install python-socketio aiohttp python-engineio"
            )
            print("  Or install with extras: pip install claude-mpm[monitor]")
            # Continue anyway - some functionality might still work
        else:
            print("✓ Socket.IO dependencies ready")

            # Find available port and start server if in monitor mode
            if monitor_mode:
                websocket_port = dashboard_manager.find_available_port(websocket_port)
                success, server_info = dashboard_manager.start_server(
                    port=websocket_port
                )

                if success:
                    print(f"✓ Socket.IO server enabled at {server_info.url}")
                    if launch_method == "exec":
                        print(
                            "  Note: Socket.IO monitoring using exec mode with Claude Code hooks"
                        )

                    # Use UnifiedDashboardManager for browser opening
                    dashboard_manager = UnifiedDashboardManager(logger)
                    monitor_url = dashboard_manager.get_dashboard_url(websocket_port)
                    browser_opened = dashboard_manager.open_browser(monitor_url)
                    args._browser_opened_by_cli = browser_opened

                    if not browser_opened:
                        print(f"💡 Monitor interface available at: {monitor_url}")
                else:
                    print("⚠️  Failed to launch Socket.IO monitor")
                    print("Dashboard is not running. To enable monitoring:")
                    print("  1. Use the --monitor flag: claude-mpm run --monitor")
                    print(
                        "  2. Or start dashboard separately: claude-mpm dashboard start"
                    )
                    print(
                        f"  3. Dashboard will be available at: http://localhost:{websocket_port}"
                    )
                    args._browser_opened_by_cli = False
            else:
                print(f"✓ Socket.IO ready (port: {websocket_port})")

    runner = ClaudeRunner(
        enable_tickets=enable_tickets,
        log_level=args.logging,
        claude_args=claude_args,
        launch_method=launch_method,
        enable_websocket=enable_websocket,
        websocket_port=websocket_port,
    )

    # Agent deployment is handled by ClaudeRunner.setup_agents() and
    # ClaudeRunner.deploy_project_agents_to_claude() which are called
    # in both run_interactive() and run_oneshot() methods.
    # No need for redundant deployment here.

    # Set browser opening flag for monitor mode
    if monitor_mode:
        runner._should_open_monitor_browser = True
        # Pass information about whether we already opened the browser in run.py
        runner._browser_opened_by_cli = getattr(args, "_browser_opened_by_cli", False)

    # Create context - use resumed session context if available
    if resume_session_id and resume_context:
        # For resumed sessions, create enhanced context with session information
        context = create_session_context(resume_session_id, session_manager)
        # Update session usage
        session = session_manager.load_session(resume_session_id)
        if session:
            session.last_used = datetime.now(timezone.utc).isoformat()
            session.use_count += 1
            session_manager.save_session(session)
    else:
        # Create a new session for tracking
        new_session = session_manager.create_session("default")
        context = create_simple_context()
        logger.info(f"Created new session {new_session.id}")

    # For monitor mode, we handled everything in launch_socketio_monitor
    # No need for ClaudeRunner browser delegation
    if monitor_mode:
        # Clear any browser opening flags since we handled it completely
        runner._should_open_monitor_browser = False
        runner._browser_opened_by_cli = True  # Prevent duplicate opening

    # Run session based on mode
    if args.non_interactive or args.input:
        # Non-interactive mode
        user_input = get_user_input(args.input, logger)
        success = runner.run_oneshot(user_input, context)
        if not success:
            logger.error("Session failed")
    # Interactive mode
    elif getattr(args, "intercept_commands", False):
        wrapper_path = get_scripts_dir() / "interactive_wrapper.py"
        if wrapper_path.exists():
            print("Starting interactive session with command interception...")
            subprocess.run([sys.executable, str(wrapper_path)], check=False)
        else:
            logger.warning("Interactive wrapper not found, falling back to normal mode")
            runner.run_interactive(context)
    else:
        runner.run_interactive(context)


# Legacy helper functions - now delegating to UnifiedDashboardManager
def launch_socketio_monitor(port, logger):
    """Launch the Socket.IO monitoring dashboard (legacy compatibility)."""
    dashboard_manager = UnifiedDashboardManager(logger)
    success, server_info = dashboard_manager.start_server(port=port)

    if success:
        # Open browser using UnifiedDashboardManager
        browser_opened = dashboard_manager.open_browser(server_info.url)
        return success, browser_opened

    return False, False


def _check_socketio_server_running(port, logger):
    """Check if a Socket.IO server is running on the specified port (legacy compatibility)."""
    dashboard_manager = UnifiedDashboardManager(logger)
    return dashboard_manager.is_server_running(port)


def _start_standalone_socketio_server(port, logger):
    """Start a standalone Socket.IO server (legacy compatibility)."""
    dashboard_manager = UnifiedDashboardManager(logger)
    success, _ = dashboard_manager.start_server(port=port)
    return success


def open_in_browser_tab(url, logger):
    """Open URL in browser, attempting to reuse existing tabs when possible."""
    manager = UnifiedDashboardManager(logger)
    return manager.open_browser(url)


def _check_claude_json_memory(args, logger):
    """Check .claude.json file size and warn about memory issues."""
    # Use new StartupCheckerService
    from ...core.config import Config

    config_service = Config()
    checker = StartupCheckerService(config_service)
    resume_enabled = getattr(args, "mpm_resume", False)
    warning = checker.check_memory(resume_enabled)
    if warning:
        checker.display_warnings([warning])


def _check_configuration_health(logger):
    """Check configuration health at startup and warn about issues."""
    # Use new StartupCheckerService
    from ...core.config import Config

    config_service = Config()
    checker = StartupCheckerService(config_service)
    warnings = checker.check_configuration()
    checker.display_warnings(warnings)

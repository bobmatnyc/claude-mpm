"""
CLI Startup Functions
=====================

This module contains initialization functions that run on CLI startup,
including project registry, MCP configuration, and update checks.

Part of cli/__init__.py refactoring to reduce file size and improve modularity.
"""

import os
import sys


def setup_early_environment(argv):
    """
    Set up early environment variables and logging suppression.

    WHY: Some commands need special environment handling before any logging
    or service initialization occurs.

    Args:
        argv: Command line arguments

    Returns:
        Processed argv list
    """
    # Disable telemetry and set cleanup flags early
    os.environ.setdefault("DISABLE_TELEMETRY", "1")
    os.environ.setdefault("CLAUDE_MPM_SKIP_CLEANUP", "0")

    # EARLY CHECK: Suppress logging for configure command
    if argv is None:
        argv = sys.argv[1:]
    if "configure" in argv or (len(argv) > 0 and argv[0] == "configure"):
        import logging

        logging.getLogger("claude_mpm").setLevel(logging.WARNING)
        os.environ["CLAUDE_MPM_SKIP_CLEANUP"] = "1"

    return argv


def should_skip_background_services(args, processed_argv):
    """
    Determine if background services should be skipped for this command.

    WHY: Some commands (help, version, configure, doctor) don't need
    background services and should start faster.

    Args:
        args: Parsed arguments
        processed_argv: Processed command line arguments

    Returns:
        bool: True if background services should be skipped
    """
    skip_commands = ["--version", "-v", "--help", "-h"]
    return any(cmd in (processed_argv or sys.argv[1:]) for cmd in skip_commands) or (
        hasattr(args, "command")
        and args.command in ["info", "doctor", "config", "mcp", "configure"]
    )


def setup_configure_command_environment(args):
    """
    Set up special environment for configure command.

    WHY: Configure command needs clean state without background services
    and with suppressed logging.

    Args:
        args: Parsed arguments
    """
    if hasattr(args, "command") and args.command == "configure":
        os.environ["CLAUDE_MPM_SKIP_CLEANUP"] = "1"
        import logging

        logging.getLogger("claude_mpm").setLevel(logging.WARNING)


def deploy_bundled_skills():
    """
    Deploy bundled Claude Code skills on startup.

    WHY: Automatically deploy skills from the bundled/ directory to .claude/skills/
    to ensure skills are available for agents without manual intervention.

    DESIGN DECISION: Deployment happens silently on startup with logging only.
    Failures are logged but don't block startup to ensure claude-mpm remains
    functional even if skills deployment fails. Respects auto_deploy config setting.
    """
    try:
        # Check if auto-deploy is disabled in config
        from ..config.config_loader import ConfigLoader

        config_loader = ConfigLoader()
        try:
            config = config_loader.load_config()
            skills_config = config.get("skills", {})
            if not skills_config.get("auto_deploy", True):
                # Auto-deploy disabled, skip silently
                return
        except Exception:
            # If config loading fails, assume auto-deploy is enabled (default)
            pass

        # Import and run skills deployment
        from ..skills.skills_service import SkillsService

        skills_service = SkillsService()
        deployment_result = skills_service.deploy_bundled_skills()

        # Log results
        from ..core.logger import get_logger

        logger = get_logger("cli")

        if deployment_result.get("deployed"):
            logger.info(
                f"Skills: Deployed {len(deployment_result['deployed'])} skill(s)"
            )

        if deployment_result.get("errors"):
            logger.warning(
                f"Skills: {len(deployment_result['errors'])} skill(s) failed to deploy"
            )

    except Exception as e:
        # Import logger here to avoid circular imports
        from ..core.logger import get_logger

        logger = get_logger("cli")
        logger.debug(f"Failed to deploy bundled skills: {e}")
        # Continue execution - skills deployment failure shouldn't block startup


def discover_and_link_runtime_skills():
    """
    Discover and link runtime skills from user/project directories.

    WHY: Automatically discover and link skills added to .claude/skills/
    without requiring manual configuration.

    DESIGN DECISION: Failures are logged but don't block startup to ensure
    claude-mpm remains functional even if skills discovery fails.
    """
    try:
        from ..cli.interactive.skills_wizard import (
            discover_and_link_runtime_skills as discover_skills,
        )

        discover_skills()
    except Exception as e:
        # Import logger here to avoid circular imports
        from ..core.logger import get_logger

        logger = get_logger("cli")
        logger.debug(f"Failed to discover runtime skills: {e}")
        # Continue execution - skills discovery failure shouldn't block startup


def run_background_services():
    """
    Initialize all background services on startup.

    WHY: Centralizes all startup service initialization for cleaner main().
    """
    initialize_project_registry()
    check_mcp_auto_configuration()
    verify_mcp_gateway_startup()
    check_for_updates_async()
    deploy_bundled_skills()
    discover_and_link_runtime_skills()


def setup_mcp_server_logging(args):
    """
    Configure minimal logging for MCP server mode.

    WHY: MCP server needs minimal stderr-only logging to avoid interfering
    with stdout protocol communication.

    Args:
        args: Parsed arguments

    Returns:
        Configured logger
    """
    import logging

    from ..cli.utils import setup_logging
    from ..constants import CLICommands

    if (
        args.command == CLICommands.MCP.value
        and getattr(args, "mcp_command", None) == "start"
    ):
        if not getattr(args, "test", False) and not getattr(
            args, "instructions", False
        ):
            # Production MCP mode - minimal logging
            logging.basicConfig(
                level=logging.ERROR,
                format="%(message)s",
                stream=sys.stderr,
                force=True,
            )
            return logging.getLogger("claude_mpm")
        # Test or instructions mode - normal logging
        return setup_logging(args)
    # Normal logging for all other commands
    return setup_logging(args)


def initialize_project_registry():
    """
    Initialize or update the project registry for the current session.

    WHY: The project registry tracks all claude-mpm projects and their metadata
    across sessions. This function ensures the current project is properly
    registered and updates session information.

    DESIGN DECISION: Registry failures are logged but don't prevent startup
    to ensure claude-mpm remains functional even if registry operations fail.
    """
    try:
        from ..services.project.registry import ProjectRegistry

        registry = ProjectRegistry()
        registry.get_or_create_project_entry()
    except Exception as e:
        # Import logger here to avoid circular imports
        from ..core.logger import get_logger

        logger = get_logger("cli")
        logger.debug(f"Failed to initialize project registry: {e}")
        # Continue execution - registry failure shouldn't block startup


def check_mcp_auto_configuration():
    """
    Check and potentially auto-configure MCP for pipx installations.

    WHY: Users installing via pipx should have MCP work out-of-the-box with
    minimal friction. This function offers one-time auto-configuration with
    user consent.

    DESIGN DECISION: This is blocking but quick - it only runs once and has
    a 10-second timeout. We want to catch users on first run for the best
    experience.
    """
    try:
        from ..services.mcp_gateway.auto_configure import check_and_configure_mcp

        # This function handles all the logic:
        # - Checks if already configured
        # - Checks if pipx installation
        # - Checks if already asked before
        # - Prompts user if needed
        # - Configures if user agrees
        check_and_configure_mcp()

    except Exception as e:
        # Non-critical - log but don't fail
        from ..core.logger import get_logger

        logger = get_logger("cli")
        logger.debug(f"MCP auto-configuration check failed: {e}")

    # Skip MCP service fixes for the doctor and configure commands
    # The doctor command performs its own comprehensive MCP service check
    # The configure command allows users to configure which services to enable
    # Running both would cause duplicate checks and log messages (9 seconds apart)
    if len(sys.argv) > 1 and sys.argv[1] in ("doctor", "configure"):
        return

    # Also ensure MCP services are properly configured in ~/.claude.json
    # This fixes incorrect paths and adds missing services
    try:
        from ..core.logger import get_logger
        from ..services.mcp_config_manager import MCPConfigManager

        logger = get_logger("cli")
        mcp_manager = MCPConfigManager()

        # Fix any corrupted installations first
        fix_success, fix_message = mcp_manager.fix_mcp_service_issues()
        if fix_message and "Fixed:" in fix_message:
            logger.info(f"MCP service fixes applied: {fix_message}")

        # Ensure all services are configured correctly
        config_success, config_message = mcp_manager.ensure_mcp_services_configured()
        if config_message and "Added MCP services" in config_message:
            logger.info(f"MCP services configured: {config_message}")

    except Exception as e:
        # Non-critical - log but don't fail
        from ..core.logger import get_logger

        logger = get_logger("cli")
        logger.debug(f"MCP services configuration update failed: {e}")


def verify_mcp_gateway_startup():
    """
    Verify MCP Gateway configuration on startup and pre-warm MCP services.

    WHY: The MCP gateway should be automatically configured and verified on startup
    to provide a seamless experience with diagnostic tools, file summarizer, and
    ticket service. Pre-warming MCP services eliminates the 11.9s delay on first use.

    DESIGN DECISION: This is non-blocking - failures are logged but don't prevent
    startup to ensure claude-mpm remains functional even if MCP gateway has issues.
    """
    # Quick verification of MCP services installation
    try:
        from ..core.logger import get_logger
        from ..services.mcp_service_verifier import verify_mcp_services_on_startup

        logger = get_logger("mcp_verify")
        all_ok, message = verify_mcp_services_on_startup()
        if not all_ok:
            logger.warning(message)
    except Exception:
        # Non-critical - continue with startup
        pass

    try:
        import asyncio
        import time

        from ..core.logger import get_logger
        from ..services.mcp_gateway.core.startup_verification import (
            is_mcp_gateway_configured,
            verify_mcp_gateway_on_startup,
        )

        logger = get_logger("mcp_prewarm")

        # Quick check first - if already configured, skip detailed verification
        gateway_configured = is_mcp_gateway_configured()

        # DISABLED: Pre-warming MCP servers can interfere with Claude Code's MCP management
        # This was causing issues with MCP server initialization and stderr handling
        # def run_pre_warming():
        #     loop = None
        #     try:
        #         start_time = time.time()
        #         loop = asyncio.new_event_loop()
        #         asyncio.set_event_loop(loop)
        #
        #         # Pre-warm MCP servers (especially vector search)
        #         logger.info("Pre-warming MCP servers to eliminate startup delay...")
        #         loop.run_until_complete(pre_warm_mcp_servers())
        #
        #         pre_warm_time = time.time() - start_time
        #         if pre_warm_time > 1.0:
        #             logger.info(f"MCP servers pre-warmed in {pre_warm_time:.2f}s")

        # Dummy function to maintain structure
        def run_pre_warming():
            loop = None
            try:
                time.time()
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

                # Also run gateway verification if needed
                if not gateway_configured:
                    loop.run_until_complete(verify_mcp_gateway_on_startup())

            except Exception as e:
                # Non-blocking - log but don't fail
                logger.debug(f"MCP pre-warming error (non-critical): {e}")
            finally:
                # Properly clean up event loop to prevent kqueue warnings
                if loop is not None:
                    try:
                        # Cancel all running tasks
                        pending = asyncio.all_tasks(loop)
                        for task in pending:
                            task.cancel()
                        # Wait for tasks to complete cancellation
                        if pending:
                            loop.run_until_complete(
                                asyncio.gather(*pending, return_exceptions=True)
                            )
                    except Exception:
                        pass  # Ignore cleanup errors
                    finally:
                        loop.close()
                        # Clear the event loop reference to help with cleanup
                        asyncio.set_event_loop(None)

        # Run pre-warming in background thread
        import threading

        pre_warm_thread = threading.Thread(target=run_pre_warming, daemon=True)
        pre_warm_thread.start()

        return

        # Run detailed verification in background if not configured
        if not gateway_configured:
            # Note: We don't await this to avoid blocking startup
            def run_verification():
                loop = None
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    results = loop.run_until_complete(verify_mcp_gateway_on_startup())

                    # Log results but don't block
                    from ..core.logger import get_logger

                    logger = get_logger("cli")

                    if results.get("gateway_configured"):
                        logger.debug("MCP Gateway verification completed successfully")
                    else:
                        logger.debug("MCP Gateway verification completed with warnings")

                except Exception as e:
                    from ..core.logger import get_logger

                    logger = get_logger("cli")
                    logger.debug(f"MCP Gateway verification failed: {e}")
                finally:
                    # Properly clean up event loop to prevent kqueue warnings
                    if loop is not None:
                        try:
                            # Cancel all running tasks
                            pending = asyncio.all_tasks(loop)
                            for task in pending:
                                task.cancel()
                            # Wait for tasks to complete cancellation
                            if pending:
                                loop.run_until_complete(
                                    asyncio.gather(*pending, return_exceptions=True)
                                )
                        except Exception:
                            pass  # Ignore cleanup errors
                        finally:
                            loop.close()
                            # Clear the event loop reference to help with cleanup
                            asyncio.set_event_loop(None)

            # Run in background thread to avoid blocking startup
            import threading

            verification_thread = threading.Thread(target=run_verification, daemon=True)
            verification_thread.start()

    except Exception as e:
        # Import logger here to avoid circular imports
        from ..core.logger import get_logger

        logger = get_logger("cli")
        logger.debug(f"Failed to start MCP Gateway verification: {e}")
        # Continue execution - MCP gateway issues shouldn't block startup


def check_for_updates_async():
    """
    Check for updates in background thread (non-blocking).

    WHY: Users should be notified of new versions and have an easy way to upgrade
    without manually checking PyPI/npm. This runs asynchronously on startup to avoid
    blocking the CLI.

    DESIGN DECISION: This is non-blocking and non-critical - failures are logged
    but don't prevent startup. Only runs for pip/pipx/npm installations, skips
    editable/development installations. Respects user configuration settings.
    """

    def run_update_check():
        """Inner function to run in background thread."""
        loop = None
        try:
            import asyncio

            from ..core.config import Config
            from ..core.logger import get_logger
            from ..services.self_upgrade_service import SelfUpgradeService

            logger = get_logger("upgrade_check")

            # Load configuration
            config = Config()
            updates_config = config.get("updates", {})

            # Check if update checking is enabled
            if not updates_config.get("check_enabled", True):
                logger.debug("Update checking disabled in configuration")
                return

            # Check frequency setting
            frequency = updates_config.get("check_frequency", "daily")
            if frequency == "never":
                logger.debug("Update checking frequency set to 'never'")
                return

            # Create new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            # Create upgrade service and check for updates
            upgrade_service = SelfUpgradeService()

            # Skip for editable installs (development mode)
            from ..services.self_upgrade_service import InstallationMethod

            if upgrade_service.installation_method == InstallationMethod.EDITABLE:
                logger.debug("Skipping version check for editable installation")
                return

            # Get configuration values
            check_claude_code = updates_config.get("check_claude_code", True)
            auto_upgrade = updates_config.get("auto_upgrade", False)

            # Check and prompt for upgrade if available (non-blocking)
            loop.run_until_complete(
                upgrade_service.check_and_prompt_on_startup(
                    auto_upgrade=auto_upgrade, check_claude_code=check_claude_code
                )
            )

        except Exception as e:
            # Non-critical - log but don't fail startup
            try:
                from ..core.logger import get_logger

                logger = get_logger("upgrade_check")
                logger.debug(f"Update check failed (non-critical): {e}")
            except Exception:
                pass  # Avoid any errors in error handling
        finally:
            # Properly clean up event loop
            if loop is not None:
                try:
                    # Cancel all running tasks
                    pending = asyncio.all_tasks(loop)
                    for task in pending:
                        task.cancel()
                    # Wait for tasks to complete cancellation
                    if pending:
                        loop.run_until_complete(
                            asyncio.gather(*pending, return_exceptions=True)
                        )
                except Exception:
                    pass  # Ignore cleanup errors
                finally:
                    loop.close()
                    # Clear the event loop reference to help with cleanup
                    asyncio.set_event_loop(None)

    # Run update check in background thread to avoid blocking startup
    import threading

    update_check_thread = threading.Thread(target=run_update_check, daemon=True)
    update_check_thread.start()

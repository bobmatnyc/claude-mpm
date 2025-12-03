"""
CLI Startup Functions
=====================

This module contains initialization functions that run on CLI startup,
including project registry, MCP configuration, and update checks.

Part of cli/__init__.py refactoring to reduce file size and improve modularity.
"""

import os
import sys
import warnings
from pathlib import Path


def check_legacy_cache() -> None:
    """Check for legacy cache/agents/ directory and warn user.

    WHY: cache/agents/ is deprecated in favor of cache/remote-agents/.
    Research confirmed that cache/remote-agents/ is the canonical location
    with 26 active code references, while cache/agents/ has only 7 legacy references.

    DESIGN DECISIONS:
    - Non-blocking warning: Doesn't stop execution, just informs user
    - Migration guidance: Provides clear path to migrate
    - One-time check: Only warns if legacy cache contains files
    """
    home = Path.home()
    legacy_cache = home / ".claude-mpm" / "cache" / "agents"
    canonical_cache = home / ".claude-mpm" / "cache" / "remote-agents"
    migration_marker = home / ".claude-mpm" / "cache" / ".migrated_to_remote_agents"

    # Skip if already migrated or no legacy cache
    if migration_marker.exists() or not legacy_cache.exists():
        return

    # Check if legacy cache has actual agent files
    legacy_files = list(legacy_cache.glob("*.md")) + list(legacy_cache.glob("*.json"))
    if not legacy_files:
        return

    # Only warn if canonical cache doesn't exist (indicating unmigrated system)
    if not canonical_cache.exists():
        warnings.warn(
            f"\n⚠️  DEPRECATION: Legacy cache directory detected\n"
            f"   Location: {legacy_cache}\n"
            f"   Files found: {len(legacy_files)}\n\n"
            f"The 'cache/agents/' directory is deprecated. Please migrate to 'cache/remote-agents/'.\n"
            f"Run: python scripts/migrate_cache_to_remote_agents.py\n",
            DeprecationWarning,
            stacklevel=2
        )


def setup_early_environment(argv):
    """
    Set up early environment variables and logging suppression.

    WHY: Some commands need special environment handling before any logging
    or service initialization occurs.

    CRITICAL: Suppress ALL logging by default until setup_mcp_server_logging()
    configures the user's preference. This prevents early loggers (like
    ProjectInitializer and service.* loggers) from logging at INFO level before
    we know the user's logging preference.

    Args:
        argv: Command line arguments

    Returns:
        Processed argv list
    """
    import logging

    # Disable telemetry and set cleanup flags early
    os.environ.setdefault("DISABLE_TELEMETRY", "1")
    os.environ.setdefault("CLAUDE_MPM_SKIP_CLEANUP", "0")

    # CRITICAL: Suppress ALL logging by default
    # This catches all loggers (claude_mpm.*, service.*, framework_loader, etc.)
    # This will be overridden by setup_mcp_server_logging() based on user preference
    logging.getLogger().setLevel(logging.CRITICAL + 1)  # Root logger catches everything

    # Process argv
    if argv is None:
        argv = sys.argv[1:]

    # EARLY CHECK: Additional suppression for configure command
    if "configure" in argv or (len(argv) > 0 and argv[0] == "configure"):
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

    DESIGN DECISION: Deployment happens with minimal feedback (checkmark on success).
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
            # Show simple feedback for deployed skills
            deployed_count = len(deployment_result["deployed"])
            print(f"✓ Bundled skills ready ({deployed_count} deployed)", flush=True)
            logger.info(f"Skills: Deployed {deployed_count} skill(s)")
        elif not deployment_result.get("errors"):
            # No deployment needed, skills already present
            print("✓ Bundled skills ready", flush=True)

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

    DESIGN DECISION: Provides simple feedback on completion.
    Failures are logged but don't block startup to ensure
    claude-mpm remains functional even if skills discovery fails.
    """
    try:
        from ..cli.interactive.skills_wizard import (
            discover_and_link_runtime_skills as discover_skills,
        )

        discover_skills()
        # Show simple success feedback
        print("✓ Runtime skills linked", flush=True)
    except Exception as e:
        # Import logger here to avoid circular imports
        from ..core.logger import get_logger

        logger = get_logger("cli")
        logger.debug(f"Failed to discover runtime skills: {e}")
        # Continue execution - skills discovery failure shouldn't block startup


def deploy_output_style_on_startup():
    """
    Deploy claude-mpm output style to Claude Code on CLI startup.

    WHY: Automatically deploy and activate the output style to ensure consistent,
    professional communication without emojis and exclamation points. This ensures
    the style is available even when using Claude Code directly (not via chat command).

    DESIGN DECISION: This is non-blocking and idempotent. It uses OutputStyleManager
    which handles version detection, file deployment, and settings activation.
    Only works for Claude Code >= 1.0.83.
    """
    try:
        from pathlib import Path

        from ..core.output_style_manager import OutputStyleManager

        # Create OutputStyleManager instance
        output_style_manager = OutputStyleManager()

        # Check if Claude Code supports output styles
        if not output_style_manager.supports_output_styles():
            # Silently skip - version too old or Claude not installed
            return

        # Check if already deployed and active
        settings_file = Path.home() / ".claude" / "settings.json"
        output_style_file = Path.home() / ".claude" / "output-styles" / "claude-mpm.md"

        already_configured = False
        if settings_file.exists() and output_style_file.exists():
            try:
                import json

                # Check if file has content (bug fix: was skipping empty files)
                if output_style_file.stat().st_size == 0:
                    # File is empty, need to redeploy with content
                    pass  # Fall through to deployment below
                else:
                    # File has content, check if already active
                    settings = json.loads(settings_file.read_text())
                    if settings.get("activeOutputStyle") == "claude-mpm":
                        # Already deployed and active with content
                        already_configured = True
            except Exception:
                pass  # Continue with deployment if we can't read settings

        if already_configured:
            # Show feedback that output style is ready
            print("✓ Output style configured", flush=True)
            return

        # Read OUTPUT_STYLE.md content
        output_style_path = Path(__file__).parent.parent / "agents" / "OUTPUT_STYLE.md"

        if not output_style_path.exists():
            # No output style file to deploy
            return

        output_style_content = output_style_path.read_text()

        # Deploy the output style (deploys file and activates it)
        output_style_manager.deploy_output_style(output_style_content)
        print("✓ Output style configured", flush=True)

    except Exception as e:
        # Non-critical - log but don't fail startup
        from ..core.logger import get_logger

        logger = get_logger("cli")
        logger.debug(f"Failed to deploy output style: {e}")
        # Continue execution - output style deployment shouldn't block startup


def sync_remote_agents_on_startup():
    """
    Synchronize agent templates from remote sources on startup.

    WHY: Ensures agents are up-to-date from remote Git sources (GitHub)
    without manual intervention. Uses ETag-based caching for efficient
    updates (95%+ bandwidth reduction).

    DESIGN DECISION: Non-blocking synchronization that doesn't prevent
    startup if network is unavailable. Failures are logged but don't
    block startup to ensure claude-mpm remains functional.

    Workflow:
    1. Sync all enabled Git sources (download/cache files) - Phase 1 progress bar
    2. Deploy agents to ~/.claude/agents/ - Phase 2 progress bar
    3. Log deployment results
    """
    # Check for legacy cache and warn user if found
    check_legacy_cache()

    try:
        from ..services.agents.deployment.agent_deployment import AgentDeploymentService
        from ..services.agents.startup_sync import sync_agents_on_startup
        from ..utils.progress import ProgressBar

        # Phase 1: Sync files from Git sources
        result = sync_agents_on_startup()

        # Only proceed with deployment if sync was enabled and ran
        if result.get("enabled") and result.get("sources_synced", 0) > 0:
            from ..core.logger import get_logger

            logger = get_logger("cli")

            downloaded = result.get("total_downloaded", 0)
            cached = result.get("cache_hits", 0)
            duration = result.get("duration_ms", 0)

            if downloaded > 0 or cached > 0:
                logger.debug(
                    f"Agent sync: {downloaded} updated, {cached} cached ({duration}ms)"
                )

            # Log errors if any
            errors = result.get("errors", [])
            if errors:
                logger.warning(f"Agent sync completed with {len(errors)} errors")

            # Phase 2: Deploy agents from cache to ~/.claude/agents/
            # This mirrors the skills deployment pattern (lines 371-407)
            try:
                # Initialize deployment service
                deployment_service = AgentDeploymentService()

                # Count agents in cache to show accurate progress
                from pathlib import Path

                cache_dir = Path.home() / ".claude-mpm" / "cache" / "remote-agents"
                agent_count = 0

                if cache_dir.exists():
                    # Count MD files in cache (agent markdown files from Git)
                    # BUGFIX: Use rglob to support nested directory structure
                    # (bobmatnyc/claude-mpm-agents/agents/*.md)
                    # Exclude PM templates and BASE-AGENT - only count deployable agents
                    pm_templates = {
                        "base-agent.md",
                        "circuit_breakers.md",
                        "pm_examples.md",
                        "pm_red_flags.md",
                        "research_gate_examples.md",
                        "response_format.md",
                        "ticket_completeness_examples.md",
                        "validation_templates.md",
                        "git_file_tracking.md",
                        "readme.md",  # Exclude READMEs from nested directories
                        "auto-deploy-index.md",  # Exclude index files
                    }
                    # Use rglob("**/*.md") to find agents in nested structure
                    agent_files = [
                        f
                        for f in cache_dir.rglob("*.md")
                        if f.name.lower() not in pm_templates
                    ]
                    agent_count = len(agent_files)

                if agent_count > 0:
                    # Create progress bar for deployment phase
                    deploy_progress = ProgressBar(
                        total=agent_count,
                        prefix="Deploying agents",
                        show_percentage=True,
                        show_counter=True,
                    )

                    # Deploy agents with progress callback
                    deploy_target = Path.home() / ".claude" / "agents"
                    deployment_result = deployment_service.deploy_agents(
                        target_dir=deploy_target,
                        force_rebuild=False,  # Only deploy if versions differ
                        deployment_mode="update",  # Version-aware updates
                    )

                    # Update progress bar (single increment since deploy_agents is batch)
                    deploy_progress.update(agent_count)

                    # Finish deployment progress bar
                    deployed = len(deployment_result.get("deployed", []))
                    updated = len(deployment_result.get("updated", []))
                    skipped = len(deployment_result.get("skipped", []))
                    total_available = deployed + updated + skipped

                    # Show total available agents (deployed + updated + already existing)
                    if deployed > 0 or updated > 0:
                        deploy_progress.finish(
                            f"Complete: {deployed} deployed, {updated} updated, {skipped} already present ({total_available} total)"
                        )
                    else:
                        deploy_progress.finish(
                            f"Complete: {total_available} agents ready (all up-to-date)"
                        )

                    # Display deployment errors to user (not just logs)
                    deploy_errors = deployment_result.get("errors", [])
                    if deploy_errors:
                        # Log for debugging
                        logger.warning(
                            f"Agent deployment completed with {len(deploy_errors)} errors: {deploy_errors}"
                        )

                        # Display errors to user with clear formatting
                        print("\n⚠️  Agent Deployment Errors:")

                        # Show first 10 errors to avoid overwhelming output
                        max_errors_to_show = 10
                        errors_to_display = deploy_errors[:max_errors_to_show]

                        for error in errors_to_display:
                            # Format error message for readability
                            # Errors typically come as strings like "agent.md: Error message"
                            print(f"   - {error}")

                        # If more errors exist, show count
                        if len(deploy_errors) > max_errors_to_show:
                            remaining = len(deploy_errors) - max_errors_to_show
                            print(f"   ... and {remaining} more error(s)")

                        # Show summary message
                        print(
                            f"\n❌ Failed to deploy {len(deploy_errors)} agent(s). Please check the error messages above."
                        )
                        print("   Run with --verbose for detailed error information.\n")

            except Exception as e:
                # Deployment failure shouldn't block startup
                from ..core.logger import get_logger

                logger = get_logger("cli")
                logger.warning(f"Failed to deploy agents from cache: {e}")

    except Exception as e:
        # Non-critical - log but don't fail startup
        from ..core.logger import get_logger

        logger = get_logger("cli")
        logger.debug(f"Failed to sync remote agents: {e}")
        # Continue execution - agent sync failure shouldn't block startup


def sync_remote_skills_on_startup():
    """
    Synchronize skill templates from remote sources on startup.

    WHY: Ensures skills are up-to-date from remote Git sources (GitHub)
    without manual intervention. Provides consistency with agent syncing.

    DESIGN DECISION: Non-blocking synchronization that doesn't prevent
    startup if network is unavailable. Failures are logged but don't
    block startup to ensure claude-mpm remains functional.

    Workflow:
    1. Sync all enabled Git sources (download/cache files) - Phase 1 progress bar
    2. Deploy skills to ~/.claude/skills/ with flat structure - Phase 2 progress bar
    3. Log deployment results
    """
    try:
        from pathlib import Path

        from ..config.skill_sources import SkillSourceConfiguration
        from ..services.skills.git_skill_source_manager import GitSkillSourceManager
        from ..utils.progress import ProgressBar

        config = SkillSourceConfiguration()
        manager = GitSkillSourceManager(config)

        # Get enabled sources
        enabled_sources = config.get_enabled_sources()
        if not enabled_sources:
            return  # No sources enabled, nothing to sync

        # Phase 1: Sync files from Git sources
        # We need to discover file count first to show accurate progress
        # This requires pre-scanning repositories via GitHub API
        from ..core.logger import get_logger

        logger = get_logger("cli")

        # Discover total file count across all sources
        total_file_count = 0
        for source in enabled_sources:
            try:
                # Parse GitHub URL
                url_parts = (
                    source.url.rstrip("/").replace(".git", "").split("github.com/")
                )
                if len(url_parts) == 2:
                    repo_path = url_parts[1].strip("/")
                    owner_repo = "/".join(repo_path.split("/")[:2])

                    # Use Tree API to discover all files
                    all_files = manager._discover_repository_files_via_tree_api(
                        owner_repo, source.branch
                    )

                    # Count relevant files (markdown, JSON)
                    relevant_files = [
                        f
                        for f in all_files
                        if f.endswith(".md") or f.endswith(".json") or f == ".gitignore"
                    ]
                    total_file_count += len(relevant_files)

            except Exception as e:
                logger.debug(f"Failed to discover files for {source.id}: {e}")
                # Use estimate if discovery fails
                total_file_count += 150

        # Create progress bar for sync phase with actual file count
        sync_progress = ProgressBar(
            total=total_file_count if total_file_count > 0 else 1,
            prefix="Syncing skills",
            show_percentage=True,
            show_counter=True,
        )

        # Sync all sources with progress callback
        results = manager.sync_all_sources(
            force=False, progress_callback=sync_progress.update
        )

        # Finish sync progress bar with clear breakdown
        downloaded = results["total_files_updated"]
        cached = results["total_files_cached"]
        total_files = downloaded + cached

        if cached > 0:
            sync_progress.finish(
                f"Complete: {downloaded} downloaded, {cached} cached ({total_files} total)"
            )
        else:
            # All new downloads (first sync)
            sync_progress.finish(f"Complete: {downloaded} files downloaded")

        # Phase 2: Deploy skills to ~/.claude/skills/
        # This flattens nested Git structure (e.g., collaboration/parallel-agents/SKILL.md)
        # into flat deployment (e.g., collaboration-dispatching-parallel-agents/SKILL.md)
        if results["synced_count"] > 0:
            # Get all skills to determine deployment count
            all_skills = manager.get_all_skills()
            skill_count = len(all_skills)

            if skill_count > 0:
                # Create progress bar for deployment phase
                deploy_progress = ProgressBar(
                    total=skill_count,
                    prefix="Deploying skill directories",
                    show_percentage=True,
                    show_counter=True,
                )

                # Deploy skills with progress callback
                # Deploy to project directory (like agents), not user directory
                deployment_result = manager.deploy_skills(
                    target_dir=Path.cwd() / ".claude" / "skills",
                    force=False,
                    progress_callback=deploy_progress.update,
                )

                # Finish deployment progress bar
                deployed = deployment_result.get("deployed_count", 0)
                skipped = deployment_result.get("skipped_count", 0)
                total_available = deployed + skipped

                # Show total available skills (deployed + already existing)
                # This is more user-friendly than just showing newly deployed count
                if deployed > 0:
                    deploy_progress.finish(
                        f"Complete: {deployed} deployed, {skipped} already present ({total_available} total)"
                    )
                else:
                    deploy_progress.finish(
                        f"Complete: {total_available} skills ready (all up-to-date)"
                    )

                # Log deployment errors if any
                from ..core.logger import get_logger

                logger = get_logger("cli")

                errors = deployment_result.get("errors", [])
                if errors:
                    logger.warning(
                        f"Skill deployment completed with {len(errors)} errors: {errors}"
                    )

                # Log sync errors if any
                if results["failed_count"] > 0:
                    logger.warning(
                        f"Skill sync completed with {results['failed_count']} failures"
                    )

    except Exception as e:
        # Non-critical - log but don't fail startup
        from ..core.logger import get_logger

        logger = get_logger("cli")
        logger.debug(f"Failed to sync remote skills: {e}")
        # Continue execution - skill sync failure shouldn't block startup


def run_background_services():
    """
    Initialize all background services on startup.

    WHY: Centralizes all startup service initialization for cleaner main().

    NOTE: System instructions (PM_INSTRUCTIONS.md, WORKFLOW.md, MEMORY.md) and
    templates do NOT deploy automatically on startup. They only deploy when user
    explicitly requests them via agent-manager commands. This prevents unwanted
    file creation in project .claude/ directories.
    See: SystemInstructionsDeployer and agent_deployment.py line 504-509
    """
    initialize_project_registry()
    check_mcp_auto_configuration()
    verify_mcp_gateway_startup()
    check_for_updates_async()
    sync_remote_agents_on_startup()  # Sync agents from remote sources

    # Skills deployment order (precedence: remote > bundled)
    # 1. Deploy bundled skills first (base layer from package)
    # 2. Sync and deploy remote skills (Git sources, can override bundled)
    # 3. Discover and link runtime skills (user-added skills)
    # This ensures remote skills take precedence over bundled skills when names conflict
    deploy_bundled_skills()  # Base layer: package-bundled skills
    sync_remote_skills_on_startup()  # Override layer: Git-based skills (takes precedence)
    discover_and_link_runtime_skills()  # Discovery: user-added skills

    deploy_output_style_on_startup()


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
    a 10-second timeout. Shows progress feedback during checks to avoid
    appearing frozen.

    OPTIMIZATION: Skip ALL MCP checks for doctor and configure commands to avoid
    duplicate checks (doctor performs its own comprehensive check, configure
    allows users to select services).
    """
    # Skip MCP service checks for the doctor and configure commands
    # The doctor command performs its own comprehensive MCP service check
    # The configure command allows users to configure which services to enable
    # Running both would cause duplicate checks and log messages (9 seconds apart)
    if len(sys.argv) > 1 and sys.argv[1] in ("doctor", "configure"):
        return

    try:
        from ..services.mcp_gateway.auto_configure import check_and_configure_mcp

        # Show progress feedback - this operation can take 10+ seconds
        print("Checking MCP configuration...", end="", flush=True)

        # This function handles all the logic:
        # - Checks if already configured
        # - Checks if pipx installation
        # - Checks if already asked before
        # - Prompts user if needed
        # - Configures if user agrees
        check_and_configure_mcp()

        # Clear the "Checking..." message by overwriting with spaces
        print("\r" + " " * 30 + "\r", end="", flush=True)

    except Exception as e:
        # Clear progress message on error
        print("\r" + " " * 30 + "\r", end="", flush=True)

        # Non-critical - log but don't fail
        from ..core.logger import get_logger

        logger = get_logger("cli")
        logger.debug(f"MCP auto-configuration check failed: {e}")

    # Also ensure MCP services are properly configured in ~/.claude.json
    # This fixes incorrect paths and adds missing services
    try:
        from ..core.logger import get_logger
        from ..services.mcp_config_manager import MCPConfigManager

        logger = get_logger("cli")
        mcp_manager = MCPConfigManager()

        # Fix any corrupted installations first
        _fix_success, fix_message = mcp_manager.fix_mcp_service_issues()
        if fix_message and "Fixed:" in fix_message:
            logger.info(f"MCP service fixes applied: {fix_message}")
            print("✓ MCP services fixed", flush=True)

        # Ensure all services are configured correctly
        _config_success, config_message = mcp_manager.ensure_mcp_services_configured()
        if config_message and "Added MCP services" in config_message:
            logger.info(f"MCP services configured: {config_message}")
            print("✓ MCP services configured", flush=True)

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
        # Pre-warming functionality has been removed. Gateway verification only runs
        # if MCP gateway is not already configured.

        # Run gateway verification in background if not configured
        if not gateway_configured:

            def run_verification():
                """Background thread to verify MCP gateway configuration."""
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

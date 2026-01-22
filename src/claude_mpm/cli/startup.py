"""
CLI Startup Functions
=====================

This module contains initialization functions that run on CLI startup,
including project registry, MCP configuration, and update checks.

Part of cli/__init__.py refactoring to reduce file size and improve modularity.
"""

import os
import sys
from pathlib import Path


def cleanup_user_level_hooks() -> bool:
    """Remove stale user-level hooks directory.

    WHY: claude-mpm previously deployed hooks to ~/.claude/hooks/claude-mpm/
    (user-level). This is now deprecated in favor of project-level hooks
    configured in .claude/settings.local.json. Stale user-level hooks can
    cause conflicts and confusion.

    DESIGN DECISION: Runs early in startup, before project hook sync.
    Non-blocking - failures are logged at debug level but don't prevent startup.

    Returns:
        bool: True if hooks were cleaned up, False if none found or cleanup failed
    """
    import shutil

    user_hooks_dir = Path.home() / ".claude" / "hooks" / "claude-mpm"

    if not user_hooks_dir.exists():
        return False

    try:
        from ..core.logger import get_logger

        logger = get_logger("startup")
        logger.debug(f"Removing stale user-level hooks directory: {user_hooks_dir}")

        shutil.rmtree(user_hooks_dir)

        logger.debug("User-level hooks cleanup complete")
        return True
    except Exception as e:
        # Non-critical - log but don't fail startup
        try:
            from ..core.logger import get_logger

            logger = get_logger("startup")
            logger.debug(f"Failed to cleanup user-level hooks (non-fatal): {e}")
        except Exception:  # nosec B110
            pass  # Avoid any errors in error handling
        return False


def sync_hooks_on_startup(quiet: bool = False) -> bool:
    """Ensure hooks are up-to-date on startup.

    WHY: Users can have stale hook configurations in settings.json that cause errors.
    Reinstalling hooks ensures the hook format matches the current code.

    DESIGN DECISION: Shows brief status message on success for user awareness.
    Failures are logged but don't prevent startup to ensure claude-mpm
    remains functional.

    Workflow:
    1. Cleanup stale user-level hooks (~/.claude/hooks/claude-mpm/)
    2. Reinstall project-level hooks to .claude/settings.local.json

    Args:
        quiet: If True, suppress all output (used internally)

    Returns:
        bool: True if hooks were synced successfully, False otherwise
    """
    is_tty = not quiet and sys.stdout.isatty()

    # Step 1: Cleanup stale user-level hooks first
    if is_tty:
        print("Cleaning user-level hooks...", end=" ", flush=True)

    cleaned = cleanup_user_level_hooks()

    if is_tty:
        if cleaned:
            print("✓")
        else:
            print("(none found)")

    # Step 2: Install project-level hooks
    try:
        from ..hooks.claude_hooks.installer import HookInstaller

        installer = HookInstaller()

        # Show brief status (hooks sync is fast)
        if is_tty:
            print("Installing project hooks...", end=" ", flush=True)

        # Reinstall hooks (force=True ensures update)
        success = installer.install_hooks(force=True)

        if is_tty:
            if success:
                # Count hooks from settings file
                hook_count = _count_installed_hooks(installer.settings_file)
                print(f"{hook_count} hooks configured ✓")
            else:
                print("(skipped)")

        return success

    except Exception as e:
        if is_tty:
            print("(error)")
        # Log but don't fail startup
        from ..core.logger import get_logger

        logger = get_logger("startup")
        logger.warning(f"Hook sync failed (non-fatal): {e}")
        return False


def _count_installed_hooks(settings_file: Path) -> int:
    """Count the number of hook event types configured in settings.

    Args:
        settings_file: Path to the settings.local.json file

    Returns:
        int: Number of hook event types configured (e.g., 7 for all events)
    """
    import json

    try:
        if not settings_file.exists():
            return 0

        with settings_file.open() as f:
            settings = json.load(f)

        hooks = settings.get("hooks", {})
        return len(hooks)
    except Exception:
        return 0


def cleanup_legacy_agent_cache() -> None:
    """Remove legacy hierarchical agent cache directories.

    WHY: Old agent cache used category-based directory structure directly in cache.
    New structure uses remote source paths. This cleanup prevents confusion from
    stale cache directories.

    Old structure (removed):
        ~/.claude-mpm/cache/agents/engineer/
        ~/.claude-mpm/cache/agents/ops/
        ~/.claude-mpm/cache/agents/qa/
        ...

    New structure (kept):
        ~/.claude-mpm/cache/agents/bobmatnyc/claude-mpm-agents/agents/...

    DESIGN DECISION: Runs early in startup before agent deployment to ensure
    clean cache state. Removes only known legacy directories to avoid deleting
    user data.
    """
    import shutil
    from pathlib import Path

    from ..core.logger import get_logger

    logger = get_logger("startup")

    cache_dir = Path.home() / ".claude-mpm" / "cache" / "agents"
    if not cache_dir.exists():
        return

    # Known legacy category directories (from old hierarchical structure)
    legacy_dirs = [
        "claude-mpm",
        "documentation",
        "engineer",
        "ops",
        "qa",
        "security",
        "universal",
    ]

    removed = []

    # Remove legacy category directories
    for dir_name in legacy_dirs:
        legacy_path = cache_dir / dir_name
        if legacy_path.exists() and legacy_path.is_dir():
            try:
                shutil.rmtree(legacy_path)
                removed.append(dir_name)
            except Exception as e:
                logger.debug(f"Failed to remove legacy directory {dir_name}: {e}")

    # Also remove stray BASE-AGENT.md in cache root
    base_agent = cache_dir / "BASE-AGENT.md"
    if base_agent.exists():
        try:
            base_agent.unlink()
            removed.append("BASE-AGENT.md")
        except Exception as e:
            logger.debug(f"Failed to remove BASE-AGENT.md: {e}")

    if removed:
        logger.info(f"Cleaned up legacy agent cache: {', '.join(removed)}")


def check_legacy_cache() -> None:
    """Deprecated: Legacy cache checking is no longer needed.

    This function is kept for backward compatibility but does nothing.
    All agent cache operations now use the standardized cache/agents/ directory.
    """


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
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.CRITICAL + 1)  # Root logger catches everything
    root_logger.handlers = []  # Remove any handlers

    # Also suppress common module loggers explicitly to prevent handler leakage
    for logger_name in [
        "claude_mpm",
        "path_resolver",
        "file_loader",
        "framework_loader",
        "service",
        "instruction_loader",
        "agent_loader",
        "startup",
    ]:
        module_logger = logging.getLogger(logger_name)
        module_logger.setLevel(logging.CRITICAL + 1)
        module_logger.handlers = []
        module_logger.propagate = False

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

    WHY: Some commands (help, version, configure, doctor, headless) don't need
    background services and should start faster.

    Args:
        args: Parsed arguments
        processed_argv: Processed command line arguments

    Returns:
        bool: True if background services should be skipped
    """
    # Skip for headless mode - no Rich output allowed
    if getattr(args, "headless", False):
        return True

    skip_commands = ["--version", "-v", "--help", "-h"]
    return any(cmd in (processed_argv or sys.argv[1:]) for cmd in skip_commands) or (
        hasattr(args, "command")
        and args.command
        in [
            "info",
            "doctor",
            "config",
            "mcp",
            "configure",
            "hook-errors",
            "autotodos",
            "commander",
        ]
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
        except Exception:  # nosec B110
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
            if sys.stdout.isatty():
                print(f"✓ Bundled skills ready ({deployed_count} deployed)", flush=True)
            logger.info(f"Skills: Deployed {deployed_count} skill(s)")
        elif not deployment_result.get("errors"):
            # No deployment needed, skills already present
            if sys.stdout.isatty():
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
        if sys.stdout.isatty():
            print("✓ Runtime skills linked", flush=True)
    except Exception as e:
        # Import logger here to avoid circular imports
        from ..core.logger import get_logger

        logger = get_logger("cli")
        logger.debug(f"Failed to discover runtime skills: {e}")
        # Continue execution - skills discovery failure shouldn't block startup


def deploy_output_style_on_startup():
    """
    Deploy claude-mpm output styles to PROJECT-LEVEL directory on CLI startup.

    WHY: Automatically deploy output styles to ensure consistent, professional
    communication without emojis and exclamation points. Styles are project-specific
    to allow different projects to have different communication styles.

    DESIGN DECISION: This is non-blocking and idempotent. Deploys to user-level
    directory (~/.claude/output-styles/) which is the official Claude Code location
    for custom output styles.

    Deploys all styles:
    - claude-mpm.md (professional mode)
    - claude-mpm-teacher.md (teaching mode)
    - claude-mpm-research.md (research mode - for codebase analysis)
    """
    try:
        from ..core.output_style_manager import OutputStyleManager

        # Initialize the output style manager
        manager = OutputStyleManager()

        # Check if Claude Code version supports output styles (>= 1.0.83)
        if not manager.supports_output_styles():
            # Skip deployment for older versions
            # The manager will fall back to injecting content directly
            return

        # Check if all styles are already deployed and up-to-date
        all_up_to_date = True
        for style_config in manager.styles.values():
            source_path = style_config["source"]
            target_path = style_config["target"]

            if not (
                target_path.exists()
                and source_path.exists()
                and target_path.stat().st_size == source_path.stat().st_size
            ):
                all_up_to_date = False
                break

        if all_up_to_date:
            # Show feedback that output styles are ready
            if sys.stdout.isatty():
                print("✓ Output styles ready", flush=True)
            return

        # Deploy all styles using the manager
        results = manager.deploy_all_styles(activate_default=True)

        # Count successful deployments
        deployed_count = sum(1 for success in results.values() if success)

        if deployed_count > 0:
            if sys.stdout.isatty():
                print(f"✓ Output styles deployed ({deployed_count} styles)", flush=True)
        else:
            # Deployment failed - log but don't fail startup
            from ..core.logger import get_logger

            logger = get_logger("cli")
            logger.debug("Failed to deploy any output styles")

    except Exception as e:
        # Non-critical - log but don't fail startup
        from ..core.logger import get_logger

        logger = get_logger("cli")
        logger.debug(f"Failed to deploy output styles: {e}")
        # Continue execution - output style deployment shouldn't block startup


def _cleanup_orphaned_agents(deploy_target: Path, deployed_agents: list[str]) -> int:
    """Remove agents that are managed by claude-mpm but no longer deployed.

    WHY: When agent configurations change, old agents should be removed to avoid
    confusion and stale agent references. Only removes claude-mpm managed agents,
    leaving user-created agents untouched.

    SAFETY: Only removes files with claude-mpm ownership markers in frontmatter.
    Files without frontmatter or without ownership indicators are preserved.

    Args:
        deploy_target: Path to .claude/agents/ directory
        deployed_agents: List of agent filenames that should remain

    Returns:
        Number of agents removed
    """
    import re

    import yaml

    from ..core.logger import get_logger

    logger = get_logger("cli")
    removed_count = 0
    deployed_set = set(deployed_agents)

    if not deploy_target.exists():
        return 0

    # Scan all .md files in agents directory
    for agent_file in deploy_target.glob("*.md"):
        # Skip hidden files
        if agent_file.name.startswith("."):
            continue

        # Skip if this agent should remain deployed
        if agent_file.name in deployed_set:
            continue

        # Check if this is a claude-mpm managed agent
        try:
            content = agent_file.read_text(encoding="utf-8")

            # Parse YAML frontmatter
            if content.startswith("---"):
                match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
                if match:
                    frontmatter = yaml.safe_load(match.group(1))

                    # Check ownership indicators
                    is_ours = False
                    if frontmatter:
                        author = frontmatter.get("author", "")
                        source = frontmatter.get("source", "")
                        agent_id = frontmatter.get("agent_id", "")

                        # It's ours if it has any of these markers
                        if (
                            "Claude MPM" in str(author)
                            or source == "remote"
                            or agent_id
                        ):
                            is_ours = True

                    if is_ours:
                        # Safe to remove - it's our agent but not deployed
                        agent_file.unlink()
                        removed_count += 1
                        logger.info(f"Removed orphaned agent: {agent_file.name}")

        except Exception as e:
            logger.debug(f"Could not check agent {agent_file.name}: {e}")
            # Don't remove if we can't verify ownership

    return removed_count


def _save_deployment_state_after_reconciliation(
    agent_result, project_path: Path
) -> None:
    """Save deployment state after reconciliation to prevent duplicate deployment.

    WHY: After perform_startup_reconciliation() deploys agents to .claude/agents/,
    we need to save a deployment state file so that ClaudeRunner.setup_agents()
    can detect agents are already deployed and skip redundant deployment.

    This prevents the "✓ Deployed 31 native agents" duplicate deployment that
    occurs when setup_agents() doesn't know reconciliation already ran.

    Args:
        agent_result: DeploymentResult from perform_startup_reconciliation()
        project_path: Project root directory

    DESIGN DECISION: Use same state file format as ClaudeRunner._save_deployment_state()
    Located at: .claude-mpm/cache/deployment_state.json

    State file format:
    {
        "version": "5.6.13",
        "agent_count": 15,
        "deployment_hash": "sha256:...",
        "deployed_at": 1234567890.123
    }
    """
    import hashlib
    import json
    import time

    from ..core.logger import get_logger

    logger = get_logger("cli")

    try:
        # Get version from package
        from claude_mpm import __version__

        # Path to state file (matches ClaudeRunner._get_deployment_state_path())
        state_file = project_path / ".claude-mpm" / "cache" / "deployment_state.json"
        agents_dir = project_path / ".claude" / "agents"

        # Count deployed agents
        if agents_dir.exists():
            agent_count = len(list(agents_dir.glob("*.md")))
        else:
            agent_count = 0

        # Calculate deployment hash (matches ClaudeRunner._calculate_deployment_hash())
        # CRITICAL: Must match exact hash algorithm used in ClaudeRunner
        # Hashes filename + file content (not mtime) for consistency
        deployment_hash = ""
        if agents_dir.exists():
            agent_files = sorted(agents_dir.glob("*.md"))
            hash_obj = hashlib.sha256()
            for agent_file in agent_files:
                # Include filename and content in hash (matches ClaudeRunner)
                hash_obj.update(agent_file.name.encode())
                try:
                    hash_obj.update(agent_file.read_bytes())
                except Exception as e:
                    logger.debug(f"Error reading {agent_file} for hash: {e}")

            deployment_hash = hash_obj.hexdigest()

        # Create state data
        state_data = {
            "version": __version__,
            "agent_count": agent_count,
            "deployment_hash": deployment_hash,
            "deployed_at": time.time(),
        }

        # Ensure directory exists
        state_file.parent.mkdir(parents=True, exist_ok=True)

        # Write state file
        state_file.write_text(json.dumps(state_data, indent=2))
        logger.debug(
            f"Saved deployment state after reconciliation: {agent_count} agents"
        )

    except Exception as e:
        # Non-critical error - log but don't fail startup
        logger.debug(f"Failed to save deployment state: {e}")


def sync_remote_agents_on_startup(force_sync: bool = False):
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
    3. Cleanup orphaned agents (ours but no longer deployed) - Phase 3
    4. Cleanup legacy agent cache directories (after sync/deployment) - Phase 4
    5. Log deployment results

    Args:
        force_sync: Force download even if cache is fresh (bypasses ETag).
    """
    # DEPRECATED: Legacy warning - no-op function, kept for compatibility
    check_legacy_cache()

    try:
        # Load active profile if configured
        # Get project root (where .claude-mpm exists)
        from pathlib import Path

        from ..core.shared.config_loader import ConfigLoader
        from ..services.agents.startup_sync import sync_agents_on_startup
        from ..services.profile_manager import ProfileManager
        from ..utils.progress import ProgressBar

        project_root = Path.cwd()

        profile_manager = ProfileManager(project_dir=project_root)
        config_loader = ConfigLoader()
        main_config = config_loader.load_main_config()
        active_profile = main_config.get("active_profile")

        if active_profile:
            success = profile_manager.load_profile(active_profile)
            if success:
                summary = profile_manager.get_filtering_summary()
                from ..core.logger import get_logger

                logger = get_logger("cli")
                logger.info(
                    f"Profile '{active_profile}' active: "
                    f"{summary['enabled_agents_count']} agents enabled"
                )

        # Phase 1: Sync files from Git sources
        result = sync_agents_on_startup(force_refresh=force_sync)

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
            # Use reconciliation service to respect configuration.yaml settings
            try:
                from pathlib import Path

                from ..core.unified_config import UnifiedConfig
                from ..services.agents.deployment.startup_reconciliation import (
                    perform_startup_reconciliation,
                )

                # Load configuration
                unified_config = UnifiedConfig()

                # Override with profile settings if active
                if active_profile and profile_manager.active_profile:
                    # Get enabled agents from profile (returns Set[str])
                    profile_enabled_agents = (
                        profile_manager.active_profile.get_enabled_agents()
                    )
                    # Update config with profile's enabled list (convert Set to List)
                    unified_config.agents.enabled = list(profile_enabled_agents)
                    logger.info(
                        f"Profile '{active_profile}': Using {len(profile_enabled_agents)} enabled agents"
                    )

                # Perform reconciliation to deploy configured agents
                project_path = Path.cwd()
                agent_result, _skill_result = perform_startup_reconciliation(
                    project_path=project_path, config=unified_config, silent=False
                )

                # Display results with progress bar
                total_operations = (
                    len(agent_result.deployed)
                    + len(agent_result.removed)
                    + len(agent_result.unchanged)
                )

                if total_operations > 0:
                    deploy_progress = ProgressBar(
                        total=total_operations,
                        prefix="Deploying agents",
                        show_percentage=True,
                        show_counter=True,
                    )
                    deploy_progress.update(total_operations)

                    # Build summary message
                    deployed = len(agent_result.deployed)
                    removed = len(agent_result.removed)
                    unchanged = len(agent_result.unchanged)

                    summary_parts = []
                    if deployed > 0:
                        summary_parts.append(f"{deployed} new")
                    if removed > 0:
                        summary_parts.append(f"{removed} removed")
                    if unchanged > 0:
                        summary_parts.append(f"{unchanged} unchanged")

                    summary = f"Complete: {', '.join(summary_parts)}"
                    deploy_progress.finish(summary)

                # Display errors if any
                if agent_result.errors:
                    logger.warning(
                        f"Agent deployment completed with {len(agent_result.errors)} errors"
                    )
                    print("\n⚠️  Agent Deployment Errors:")
                    max_errors_to_show = 10
                    errors_to_display = agent_result.errors[:max_errors_to_show]

                    for error in errors_to_display:
                        print(f"   - {error}")

                    if len(agent_result.errors) > max_errors_to_show:
                        remaining = len(agent_result.errors) - max_errors_to_show
                        print(f"   ... and {remaining} more error(s)")

                    print(
                        f"\n❌ Failed to deploy {len(agent_result.errors)} agent(s). "
                        "Please check the error messages above."
                    )
                    print("   Run with --verbose for detailed error information.\n")

                # Save deployment state to prevent duplicate deployment in ClaudeRunner
                # This ensures setup_agents() skips deployment since we already reconciled
                _save_deployment_state_after_reconciliation(
                    agent_result=agent_result, project_path=project_path
                )

            except Exception as e:
                # Deployment failure shouldn't block startup
                from ..core.logger import get_logger

                logger = get_logger("cli")
                logger.warning(f"Failed to deploy agents from cache: {e}")

        # Phase 4: Cleanup legacy agent cache directories (after sync/deployment)
        # CRITICAL: This must run AFTER sync completes because sync may recreate
        # legacy directories. Running cleanup here ensures they're removed.
        cleanup_legacy_agent_cache()

    except Exception as e:
        # Non-critical - log but don't fail startup
        from ..core.logger import get_logger

        logger = get_logger("cli")
        logger.debug(f"Failed to sync remote agents: {e}")
        # Continue execution - agent sync failure shouldn't block startup

        # Cleanup legacy cache even if sync failed
        try:
            cleanup_legacy_agent_cache()
        except Exception:  # nosec B110
            pass  # Ignore cleanup errors


def sync_remote_skills_on_startup(force_sync: bool = False):
    """
    Synchronize skill templates from remote sources on startup.

    WHY: Ensures skills are up-to-date from remote Git sources (GitHub)
    without manual intervention. Provides consistency with agent syncing.

    DESIGN DECISION: Non-blocking synchronization that doesn't prevent
    startup if network is unavailable. Failures are logged but don't
    block startup to ensure claude-mpm remains functional.

    Workflow:
    1. Sync all enabled Git sources (download/cache files) - Phase 1 progress bar
    2. Scan deployed agents for skill requirements → save to configuration.yaml
    3. Resolve which skills to deploy (user_defined vs agent_referenced)
    4. Apply profile filtering if active
    5. Deploy resolved skills to ~/.claude/skills/ - Phase 2 progress bar
    6. Log deployment results with source indication

    Args:
        force_sync: Force download even if cache is fresh (bypasses ETag).
    """
    try:
        from pathlib import Path

        from ..config.skill_sources import SkillSourceConfiguration
        from ..core.shared.config_loader import ConfigLoader
        from ..services.profile_manager import ProfileManager
        from ..services.skills.git_skill_source_manager import GitSkillSourceManager
        from ..services.skills.selective_skill_deployer import (
            get_required_skills_from_agents,
            get_skills_to_deploy,
            save_agent_skills_to_config,
        )
        from ..utils.progress import ProgressBar

        # Load active profile if configured
        # Get project root (where .claude-mpm exists)
        project_root = Path.cwd()

        profile_manager = ProfileManager(project_dir=project_root)
        config_loader = ConfigLoader()
        main_config = config_loader.load_main_config()
        active_profile = main_config.get("active_profile")

        if active_profile:
            success = profile_manager.load_profile(active_profile)
            if success:
                from ..core.logger import get_logger

                logger = get_logger("cli")
                summary = profile_manager.get_filtering_summary()
                logger.info(
                    f"Profile '{active_profile}' active: "
                    f"{summary['enabled_skills_count']} skills enabled, "
                    f"{summary['disabled_patterns_count']} patterns disabled"
                )

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
        total_skill_dirs = 0  # Count actual skill directories (folders with SKILL.md)

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

                    # Count skill directories (unique directories containing SKILL.md)
                    skill_dirs = set()
                    for f in all_files:
                        if f.endswith("/SKILL.md"):
                            # Extract directory path
                            skill_dir = "/".join(f.split("/")[:-1])
                            skill_dirs.add(skill_dir)
                    total_skill_dirs += len(skill_dirs)

            except Exception as e:
                logger.debug(f"Failed to discover files for {source.id}: {e}")
                # Use estimate if discovery fails
                total_file_count += 150
                total_skill_dirs += 50  # Estimate ~50 skills

        # Create progress bar for sync phase with actual file count
        # Note: We sync files (md, json, etc.), but will deploy skill directories
        sync_progress = ProgressBar(
            total=total_file_count if total_file_count > 0 else 1,
            prefix="Syncing skill files",
            show_percentage=True,
            show_counter=True,
        )

        # Sync all sources with progress callback
        results = manager.sync_all_sources(
            force=force_sync, progress_callback=sync_progress.update
        )

        # Finish sync progress bar with clear breakdown
        downloaded = results["total_files_updated"]
        cached = results["total_files_cached"]
        total_files = downloaded + cached

        if cached > 0:
            sync_progress.finish(
                f"Complete: {downloaded} downloaded, {cached} cached ({total_files} files, {total_skill_dirs} skills)"
            )
        else:
            # All new downloads (first sync)
            sync_progress.finish(
                f"Complete: {downloaded} files downloaded ({total_skill_dirs} skills)"
            )

        # Phase 2: Scan agents and save to configuration.yaml
        # This step populates configuration.yaml with agent-referenced skills
        # CRITICAL: Always scan agents to populate agent_referenced, even when using cached skills.
        # Without this, skill_filter=None causes ALL skills to deploy and NO cleanup to run.
        agents_dir = Path.cwd() / ".claude" / "agents"

        # Scan agents for skill requirements (ALWAYS run to ensure cleanup works)
        agent_skills = get_required_skills_from_agents(agents_dir)
        logger.info(
            f"Agent scan found {len(agent_skills)} unique skills across deployed agents"
        )

        # Save to project-level configuration.yaml
        project_config_path = Path.cwd() / ".claude-mpm" / "configuration.yaml"
        save_agent_skills_to_config(list(agent_skills), project_config_path)
        logger.debug(
            f"Saved {len(agent_skills)} agent-referenced skills to {project_config_path}"
        )

        # Phase 3: Resolve which skills to deploy (user_defined or agent_referenced)
        skills_to_deploy, skill_source = get_skills_to_deploy(project_config_path)

        # CRITICAL DEBUG: Log deployment resolution to diagnose cleanup issues
        if skills_to_deploy:
            logger.info(
                f"Resolved {len(skills_to_deploy)} skills from {skill_source} (cleanup will run)"
            )
        else:
            logger.warning(
                f"No skills resolved from {skill_source} - will deploy ALL skills WITHOUT cleanup! "
                f"This may indicate agent_referenced is empty in configuration.yaml."
            )

        # Phase 4: Apply profile filtering if active
        if active_profile and profile_manager.active_profile:
            # Filter skills based on profile
            if skills_to_deploy:
                # Filter the resolved skill list
                original_count = len(skills_to_deploy)
                filtered_skills = [
                    skill
                    for skill in skills_to_deploy
                    if profile_manager.is_skill_enabled(skill)
                ]
                filtered_count = original_count - len(filtered_skills)

                # SAFEGUARD: Warn if all skills were filtered out (misconfiguration)
                if not filtered_skills and original_count > 0:
                    logger.warning(
                        f"Profile '{active_profile}' filtered ALL {original_count} skills. "
                        f"This may indicate a naming mismatch in the profile."
                    )
                elif filtered_count > 0:
                    logger.info(
                        f"Profile '{active_profile}' filtered {filtered_count} skills "
                        f"({len(filtered_skills)} remaining)"
                    )

                skills_to_deploy = filtered_skills
                skill_source = f"{skill_source} + profile filtered"
            else:
                # No explicit skill list - filter from all available
                all_skills = manager.get_all_skills()
                filtered_skills = [
                    skill["name"]
                    for skill in all_skills
                    if profile_manager.is_skill_enabled(skill["name"])
                ]
                skills_to_deploy = filtered_skills
                skill_source = "profile filtered"
                logger.info(
                    f"Profile '{active_profile}': "
                    f"{len(filtered_skills)} skills enabled from {len(all_skills)} available"
                )

        # Get all skills to determine counts
        all_skills = manager.get_all_skills()
        total_skill_count = len(all_skills)

        # Determine skill count based on resolution
        skill_count = len(skills_to_deploy) if skills_to_deploy else total_skill_count

        if skill_count > 0:
            # Deploy skills with resolved filter
            # Deploy ONLY to project directory (not user-level)
            # DESIGN DECISION: Project-level deployment keeps skills isolated per project,
            # avoiding pollution of user's global ~/.claude/skills/ directory.

            # Deploy to project-local directory with cleanup
            deployment_result = manager.deploy_skills(
                target_dir=Path.cwd() / ".claude" / "skills",
                force=force_sync,
                # CRITICAL FIX: Empty list should mean "deploy no skills", not "deploy all"
                # When skills_to_deploy is [], we want skill_filter=set() NOT skill_filter=None
                # None means "no filtering" (deploy all), empty set means "filter to nothing"
                skill_filter=set(skills_to_deploy)
                if skills_to_deploy is not None
                else None,
            )

            # REMOVED: User-level deployment (lines 1068-1074)
            # Reason: Skills should be project-specific, not user-global.
            # Claude Code can read from project-level .claude/skills/ directory.

            # Get actual counts from deployment result (use project-local for display)
            deployed = deployment_result.get("deployed_count", 0)
            skipped = deployment_result.get("skipped_count", 0)
            filtered = deployment_result.get("filtered_count", 0)
            removed = deployment_result.get("removed_count", 0)
            total_available = deployed + skipped

            # Only show progress bar if there are skills to deploy
            if total_available > 0:
                deploy_progress = ProgressBar(
                    total=total_available,
                    prefix="Deploying skill directories",
                    show_percentage=True,
                    show_counter=True,
                )
                # Update progress bar to completion
                deploy_progress.update(total_available)
            else:
                # No skills to deploy - create dummy progress for message only
                deploy_progress = ProgressBar(
                    total=1,
                    prefix="Deploying skill directories",
                    show_percentage=False,
                    show_counter=False,
                )
                deploy_progress.update(1)

            # Show total available skills (deployed + already existing)
            # Include source indication (user_defined vs agent_referenced)
            # Note: total_skill_count is from cache, total_available is what's deployed/needed
            source_label = (
                "user override" if skill_source == "user_defined" else "from agents"
            )

            # Build finish message with cleanup info
            if deployed > 0 or removed > 0:
                parts = []
                if deployed > 0:
                    parts.append(f"{deployed} new")
                if skipped > 0:
                    parts.append(f"{skipped} unchanged")
                if removed > 0:
                    parts.append(f"{removed} removed")

                status = ", ".join(parts)

                if filtered > 0:
                    deploy_progress.finish(
                        f"Complete: {status} ({total_available} {source_label}, {filtered} files in cache)"
                    )
                else:
                    deploy_progress.finish(
                        f"Complete: {status} ({total_available} skills {source_label} from {total_skill_count} files in cache)"
                    )
            elif filtered > 0:
                # Skills filtered means agents require fewer skills than available
                deploy_progress.finish(
                    f"No skills needed ({source_label}, {total_skill_count} files in cache)"
                )
            else:
                # No changes - all skills already deployed
                msg = f"Complete: {total_available} skills {source_label}"
                if removed > 0:
                    msg += f", {removed} removed"
                msg += f" ({total_skill_count} files in cache)"
                deploy_progress.finish(msg)

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


def show_agent_summary():
    """
    Display agent availability summary on startup.

    WHY: Users should see at a glance how many agents are available and installed
    without having to run /mpm-agents list.

    DESIGN DECISION: Fast, non-blocking check that counts agents from the deployment
    directory. Shows simple "X installed / Y available" format. Failures are silent
    to avoid blocking startup.
    """
    try:
        from pathlib import Path

        # Count deployed agents (installed)
        deploy_target = Path.cwd() / ".claude" / "agents"
        installed_count = 0
        if deploy_target.exists():
            # Count .md files, excluding README and other docs
            agent_files = [
                f
                for f in deploy_target.glob("*.md")
                if not f.name.startswith(("README", "INSTRUCTIONS", "."))
            ]
            installed_count = len(agent_files)

        # Count available agents in cache (from remote sources)
        cache_dir = Path.home() / ".claude-mpm" / "cache" / "agents"
        available_count = 0
        if cache_dir.exists():
            # Use same filtering logic as agent deployment (lines 486-533 in startup.py)
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
            }
            doc_files = {
                "readme.md",
                "changelog.md",
                "contributing.md",
                "implementation-summary.md",
                "reorganization-plan.md",
                "auto-deploy-index.md",
            }

            # Find all markdown files in agents/ directories
            all_md_files = list(cache_dir.rglob("*.md"))
            agent_files = [
                f
                for f in all_md_files
                if (
                    "/agents/" in str(f)
                    and f.name.lower() not in pm_templates
                    and f.name.lower() not in doc_files
                    and f.name.lower() != "base-agent.md"
                    and not any(
                        part in str(f).split("/")
                        for part in ["dist", "build", ".cache"]
                    )
                )
            ]
            available_count = len(agent_files)

        # Display summary if we have agents
        if installed_count > 0 or available_count > 0:
            print(
                f"✓ Agents: {installed_count} deployed / {max(0, available_count - installed_count)} cached",
                flush=True,
            )

    except Exception as e:
        # Silent failure - agent summary is informational only
        from ..core.logger import get_logger

        logger = get_logger("cli")
        logger.debug(f"Failed to generate agent summary: {e}")


def show_skill_summary():
    """
    Display skill availability summary on startup.

    WHY: Users should see at a glance how many skills are deployed and available
    from cache, similar to the agent summary showing "X deployed / Y cached".

    DESIGN DECISION: Fast, non-blocking check that counts skills from:
    - Deployed skills: PROJECT-level .claude/skills/ directory
    - Cached skills: ~/.claude-mpm/cache/skills/ directory (from remote sources)

    Shows format: "✓ Skills: X deployed / Y cached"
    Failures are silent to avoid blocking startup.
    """
    try:
        from pathlib import Path

        # Count deployed skills (PROJECT-level, not user-level)
        project_skills_dir = Path.cwd() / ".claude" / "skills"
        deployed_count = 0
        if project_skills_dir.exists():
            # Count directories with SKILL.md (excludes collection repos)
            # Exclude collection directories (obra-superpowers, etc.)
            skill_dirs = [
                d
                for d in project_skills_dir.iterdir()
                if d.is_dir()
                and (d / "SKILL.md").exists()
                and not (d / ".git").exists()  # Exclude collection repos
            ]
            deployed_count = len(skill_dirs)

        # Count cached skills (from remote sources, not deployed yet)
        # This matches the agent summary pattern: deployed vs cached
        cache_dir = Path.home() / ".claude-mpm" / "cache" / "skills"
        cached_count = 0
        if cache_dir.exists():
            # Scan all repository directories in cache
            # Cache structure: ~/.claude-mpm/cache/skills/{owner}/{repo}/...
            for repo_dir in cache_dir.rglob("*"):
                if not repo_dir.is_dir():
                    continue

                # Count skill directories (those with SKILL.md)
                # Skills can be nested in: skills/category/skill-name/SKILL.md
                # or in flat structure: skill-name/SKILL.md
                for root, dirs, files in os.walk(repo_dir):
                    if "SKILL.md" in files:
                        # Exclude build artifacts and hidden directories
                        root_path = Path(root)
                        if not any(
                            part.startswith(".")
                            or part in ["dist", "build", "__pycache__"]
                            for part in root_path.parts
                        ):
                            cached_count += 1

        # Display summary using agent summary format: "X deployed / Y cached"
        # Only show non-deployed cached skills (subtract deployed from cached)
        non_deployed_cached = max(0, cached_count - deployed_count)
        if deployed_count > 0 or non_deployed_cached > 0:
            print(
                f"✓ Skills: {deployed_count} deployed / {non_deployed_cached} cached",
                flush=True,
            )

    except Exception as e:
        # Silent failure - skill summary is informational only
        from ..core.logger import get_logger

        logger = get_logger("cli")
        logger.debug(f"Failed to generate skill summary: {e}")


def verify_and_show_pm_skills():
    """Verify PM skills and display status with enhanced validation.

    WHY: PM skills are CRITICAL for PM agent operation. PM must KNOW if
    framework knowledge is unavailable at startup. Enhanced validation
    checks all required skills exist, are not corrupted, and auto-repairs
    if needed.

    Shows deployment status:
    - "✓ PM skills: 8/8 verified" if all required skills are valid
    - "⚠ PM skills: 2 missing, auto-repairing..." if issues detected
    - Non-blocking but visible warning if auto-repair fails
    """
    try:
        from pathlib import Path

        from ..services.pm_skills_deployer import (
            REQUIRED_PM_SKILLS,
            PMSkillsDeployerService,
        )

        deployer = PMSkillsDeployerService()
        project_dir = Path.cwd()

        # Verify with auto-repair enabled
        result = deployer.verify_pm_skills(project_dir, auto_repair=True)

        if result.verified:
            # Show verified status with count
            total_required = len(REQUIRED_PM_SKILLS)
            if sys.stdout.isatty():
                print(
                    f"✓ PM skills: {total_required}/{total_required} verified",
                    flush=True,
                )
        else:
            # Show warning with details
            missing_count = len(result.missing_skills)
            corrupted_count = len(result.corrupted_skills)

            # Build status message
            issues = []
            if missing_count > 0:
                issues.append(f"{missing_count} missing")
            if corrupted_count > 0:
                issues.append(f"{corrupted_count} corrupted")

            status = ", ".join(issues)

            # Check if auto-repair was attempted
            if "Auto-repaired" in result.message:
                # Auto-repair succeeded
                total_required = len(REQUIRED_PM_SKILLS)
                if sys.stdout.isatty():
                    print(
                        f"✓ PM skills: {total_required}/{total_required} verified (auto-repaired)",
                        flush=True,
                    )
            else:
                # Auto-repair failed or not attempted
                if sys.stdout.isatty():
                    print(f"⚠ PM skills: {status}", flush=True)

                # Log warnings for debugging
                from ..core.logger import get_logger

                logger = get_logger("cli")
                for warning in result.warnings:
                    logger.warning(f"PM skills: {warning}")

    except ImportError:
        # PM skills deployer not available - skip silently
        pass
    except Exception as e:
        from ..core.logger import get_logger

        logger = get_logger("cli")
        logger.debug(f"PM skills verification failed: {e}")


def auto_install_chrome_devtools_on_startup():
    """
    Automatically install chrome-devtools-mcp on startup if enabled.

    WHY: Browser automation capabilities should be available out-of-the-box without
    manual MCP server configuration. chrome-devtools-mcp provides powerful browser
    interaction tools for Claude Code.

    DESIGN DECISION: Non-blocking installation that doesn't prevent startup if it fails.
    Respects user configuration setting (enabled by default). Only installs if not
    already configured in Claude.
    """
    try:
        # Check if auto-install is disabled in config
        from ..config.config_loader import ConfigLoader

        config_loader = ConfigLoader()
        try:
            config = config_loader.load_main_config()
            chrome_devtools_config = config.get("chrome_devtools", {})
            if not chrome_devtools_config.get("auto_install", True):
                # Auto-install disabled, skip silently
                return
        except Exception:  # nosec B110
            # If config loading fails, assume auto-install is enabled (default)
            pass

        # Import and run chrome-devtools installation
        from ..cli.chrome_devtools_installer import auto_install_chrome_devtools

        auto_install_chrome_devtools(quiet=False)

    except Exception as e:
        # Import logger here to avoid circular imports
        from ..core.logger import get_logger

        logger = get_logger("cli")
        logger.debug(f"Failed to auto-install chrome-devtools-mcp: {e}")
        # Continue execution - chrome-devtools installation failure shouldn't block startup


def sync_deployment_on_startup(force_sync: bool = False) -> None:
    """Consolidated deployment block: hooks + agents.

    WHY: Groups all deployment tasks into a single logical block for clarity.
    This ensures hooks and agents are deployed together before other services.

    Order:
    1. Hook cleanup (remove ~/.claude/hooks/claude-mpm/)
    2. Hook reinstall (update .claude/settings.local.json)
    3. Agent sync from remote Git sources

    Args:
        force_sync: Force download even if cache is fresh (bypasses ETag).
    """
    # Step 1-2: Hooks (cleanup + reinstall handled by sync_hooks_on_startup)
    sync_hooks_on_startup()  # Shows "Syncing Claude Code hooks... ✓"

    # Step 3: Agents from remote sources
    sync_remote_agents_on_startup(force_sync=force_sync)
    show_agent_summary()  # Display agent counts after deployment


def run_background_services(force_sync: bool = False):
    """
    Initialize all background services on startup.

    WHY: Centralizes all startup service initialization for cleaner main().

    NOTE: System instructions (PM_INSTRUCTIONS.md, WORKFLOW.md, MEMORY.md) and
    templates do NOT deploy automatically on startup. They only deploy when user
    explicitly requests them via agent-manager commands. This prevents unwanted
    file creation in project .claude/ directories.
    See: SystemInstructionsDeployer and agent_deployment.py line 504-509

    Args:
        force_sync: Force download even if cache is fresh (bypasses ETag).
    """
    # Consolidated deployment block: hooks + agents
    # RATIONALE: Hooks and agents are deployed together before other services
    # This ensures the deployment phase is complete before configuration checks
    sync_deployment_on_startup(force_sync=force_sync)

    initialize_project_registry()
    check_mcp_auto_configuration()
    verify_mcp_gateway_startup()
    check_for_updates_async()

    # Skills deployment order (precedence: remote > bundled)
    # 1. Deploy bundled skills first (base layer from package)
    # 2. Sync and deploy remote skills (Git sources, can override bundled)
    # 3. Discover and link runtime skills (user-added skills)
    # This ensures remote skills take precedence over bundled skills when names conflict
    deploy_bundled_skills()  # Base layer: package-bundled skills
    sync_remote_skills_on_startup(
        force_sync=force_sync
    )  # Override layer: Git-based skills (takes precedence)
    discover_and_link_runtime_skills()  # Discovery: user-added skills
    show_skill_summary()  # Display skill counts after deployment
    verify_and_show_pm_skills()  # PM skills verification and status

    deploy_output_style_on_startup()

    # Auto-install chrome-devtools-mcp for browser automation
    auto_install_chrome_devtools_on_startup()


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
        # Only show progress message in TTY mode to avoid interfering with Claude Code's status display
        if sys.stdout.isatty():
            print("Checking MCP configuration...", end="", flush=True)

        # This function handles all the logic:
        # - Checks if already configured
        # - Checks if pipx installation
        # - Checks if already asked before
        # - Prompts user if needed
        # - Configures if user agrees
        check_and_configure_mcp()

        # Clear the "Checking..." message by overwriting with spaces
        # Only use carriage return clearing if stdout is a real TTY
        if sys.stdout.isatty():
            print("\r" + " " * 30 + "\r", end="", flush=True)
        # In non-TTY mode, don't print anything - the "Checking..." message will just remain on its line

    except Exception as e:
        # Clear progress message on error
        # Only use carriage return clearing if stdout is a real TTY
        if sys.stdout.isatty():
            print("\r" + " " * 30 + "\r", end="", flush=True)
        # In non-TTY mode, don't print anything - the "Checking..." message will just remain on its line

        # Non-critical - log but don't fail
        from ..core.logger import get_logger

        logger = get_logger("cli")
        logger.debug(f"MCP auto-configuration check failed: {e}")


def verify_mcp_gateway_startup():
    """
    Verify MCP Gateway configuration on startup and pre-warm MCP services.

    WHY: The MCP gateway should be automatically configured and verified on startup
    to provide a seamless experience with diagnostic tools, file summarizer, and
    ticket service. Pre-warming MCP services eliminates the 11.9s delay on first use.

    DESIGN DECISION: This is non-blocking - failures are logged but don't prevent
    startup to ensure claude-mpm remains functional even if MCP gateway has issues.
    """
    # DISABLED: MCP service verification removed - Claude Code handles MCP natively
    # The previous check warned about missing MCP services, but users should configure
    # MCP servers through Claude Code's native MCP management, not through claude-mpm.
    # See: https://docs.anthropic.com/en/docs/claude-code/mcp

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
                        except Exception:  # nosec B110
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
            except Exception:  # nosec B110
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
                except Exception:  # nosec B110
                    pass  # Ignore cleanup errors
                finally:
                    loop.close()
                    # Clear the event loop reference to help with cleanup
                    asyncio.set_event_loop(None)

    # Run update check in background thread to avoid blocking startup
    import threading

    update_check_thread = threading.Thread(target=run_update_check, daemon=True)
    update_check_thread.start()

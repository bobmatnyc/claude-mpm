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


def sync_hooks_on_startup(quiet: bool = False) -> bool:
    """Ensure hooks are up-to-date on startup.

    WHY: Users can have stale hook configurations in settings.json that cause errors.
    Reinstalling hooks ensures the hook format matches the current code.

    DESIGN DECISION: Shows brief status message on success for user awareness.
    Failures are logged but don't prevent startup to ensure claude-mpm remains functional.

    Args:
        quiet: If True, suppress all output (used internally)

    Returns:
        bool: True if hooks were synced successfully, False otherwise
    """
    try:
        from ..hooks.claude_hooks.installer import HookInstaller

        installer = HookInstaller()

        # Show brief status (hooks sync is fast)
        if not quiet:
            print("Syncing Claude Code hooks...", end=" ", flush=True)

        # Reinstall hooks (force=True ensures update)
        success = installer.install_hooks(force=True)

        if not quiet:
            if success:
                print("✓")
            else:
                print("(skipped)")

        return success

    except Exception as e:
        if not quiet:
            print("(error)")
        # Log but don't fail startup
        from ..core.logger import get_logger

        logger = get_logger("startup")
        logger.warning(f"Hook sync failed (non-fatal): {e}")
        return False


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
    Deploy claude-mpm output styles to PROJECT-LEVEL directory on CLI startup.

    WHY: Automatically deploy output styles to ensure consistent, professional
    communication without emojis and exclamation points. Styles are project-specific
    to allow different projects to have different communication styles.

    DESIGN DECISION: This is non-blocking and idempotent. Deploys to project-level
    directory (.claude/settings/output-styles/) instead of user-level to maintain
    project isolation.

    Deploys two styles:
    - claude-mpm-style.md (professional mode)
    - claude-mpm-teacher.md (teaching mode)
    """
    try:
        import shutil
        from pathlib import Path

        # Source files (in framework package)
        package_dir = Path(__file__).parent.parent / "agents"
        professional_source = package_dir / "CLAUDE_MPM_OUTPUT_STYLE.md"
        teacher_source = package_dir / "CLAUDE_MPM_TEACHER_OUTPUT_STYLE.md"

        # Target directory (PROJECT-LEVEL, not user-level)
        project_dir = Path.cwd()
        output_styles_dir = project_dir / ".claude" / "settings" / "output-styles"
        professional_target = output_styles_dir / "claude-mpm-style.md"
        teacher_target = output_styles_dir / "claude-mpm-teacher.md"

        # Create directory if it doesn't exist
        output_styles_dir.mkdir(parents=True, exist_ok=True)

        # Check if already deployed (both files exist and have content)
        already_deployed = (
            professional_target.exists()
            and teacher_target.exists()
            and professional_target.stat().st_size > 0
            and teacher_target.stat().st_size > 0
        )

        if already_deployed:
            # Show feedback that output styles are ready
            print("✓ Output styles ready", flush=True)
            return

        # Deploy both styles
        deployed_count = 0
        if professional_source.exists():
            shutil.copy2(professional_source, professional_target)
            deployed_count += 1

        if teacher_source.exists():
            shutil.copy2(teacher_source, teacher_target)
            deployed_count += 1

        if deployed_count > 0:
            print(f"✓ Output styles deployed ({deployed_count} styles)", flush=True)
        else:
            # Source files missing - log but don't fail
            from ..core.logger import get_logger

            logger = get_logger("cli")
            logger.debug("Output style source files not found")

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
    1. Cleanup legacy agent cache directories (if any)
    2. Sync all enabled Git sources (download/cache files) - Phase 1 progress bar
    3. Deploy agents to ~/.claude/agents/ - Phase 2 progress bar
    4. Cleanup orphaned agents (ours but no longer deployed) - Phase 3
    5. Log deployment results
    """
    # Cleanup legacy cache directories first (before syncing)
    cleanup_legacy_agent_cache()

    # DEPRECATED: Legacy warning - replaced by automatic cleanup above
    check_legacy_cache()

    try:
        # Load active profile if configured
        # Get project root (where .claude-mpm exists)
        from pathlib import Path

        from ..core.shared.config_loader import ConfigLoader
        from ..services.agents.deployment.agent_deployment import AgentDeploymentService
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
                # Initialize deployment service with profile-filtered configuration
                from ..core.config import Config

                deploy_config = None
                if active_profile and profile_manager.active_profile:
                    # Create config with excluded agents based on profile
                    # Get all agents that should be excluded (not in enabled list)
                    from pathlib import Path

                    cache_dir = Path.home() / ".claude-mpm" / "cache" / "agents"
                    if cache_dir.exists():
                        # Find all agent files
                        # Supports both flat cache and {owner}/{repo}/agents/ structure
                        all_agent_files = [
                            f
                            for f in cache_dir.rglob("*.md")
                            if "/agents/" in str(f)
                            and f.stem.lower() != "base-agent"
                            and f.name.lower()
                            not in {"readme.md", "changelog.md", "contributing.md"}
                        ]

                        # Build exclusion list for agents not in profile
                        excluded_agents = []
                        for agent_file in all_agent_files:
                            agent_name = agent_file.stem
                            if not profile_manager.is_agent_enabled(agent_name):
                                excluded_agents.append(agent_name)

                        if excluded_agents:
                            # Get singleton config and update with profile settings
                            # BUGFIX: Config is a singleton that ignores dict parameter if already initialized.
                            # Creating Config({...}) doesn't store excluded_agents - use set() instead.
                            deploy_config = Config()
                            deploy_config.set(
                                "agent_deployment.excluded_agents", excluded_agents
                            )
                            deploy_config.set(
                                "agent_deployment.filter_non_mpm_agents", False
                            )
                            deploy_config.set("agent_deployment.case_sensitive", False)
                            deploy_config.set(
                                "agent_deployment.exclude_dependencies", False
                            )
                            logger.info(
                                f"Profile '{active_profile}': Excluding {len(excluded_agents)} agents from deployment"
                            )

                deployment_service = AgentDeploymentService(config=deploy_config)

                # Count agents in cache to show accurate progress
                from pathlib import Path

                cache_dir = Path.home() / ".claude-mpm" / "cache" / "agents"
                agent_count = 0

                if cache_dir.exists():
                    # BUGFIX (cache-count-inflation): Clean up stale cache files
                    # from old repositories before counting to prevent inflated counts.
                    # Issue: Old caches like bobmatnyc/claude-mpm-agents/agents/
                    # were counted alongside current agents, inflating count
                    # from 44 to 85.
                    #
                    # Solution: Remove files with nested /agents/ paths
                    # (e.g., cache/agents/user/repo/agents/...)
                    # Keep only current agents (e.g., cache/agents/engineer/...)
                    removed_count = 0
                    stale_dirs = set()

                    for md_file in cache_dir.rglob("*.md"):
                        # Stale cache files have multiple /agents/ in their path RELATIVE to cache_dir
                        # Current: cache/agents/bobmatnyc/claude-mpm-agents/agents/engineer/...
                        #          (1 occurrence in relative path: /agents/)
                        # Old flat: cache/agents/engineer/...
                        #           (0 occurrences in relative path - no repo structure)
                        # The issue: str(md_file).count("/agents/") counts BOTH cache/agents/ AND repo/agents/
                        # Fix: Count /agents/ in path RELATIVE to cache_dir (after cache/agents/)
                        relative_path = str(md_file.relative_to(cache_dir))
                        if relative_path.count("/agents/") > 1:
                            # Track parent directory for cleanup
                            # Extract subdirectory under cache/agents/
                            # (e.g., "bobmatnyc")
                            parts = md_file.parts
                            cache_agents_idx = parts.index("agents")
                            if cache_agents_idx + 1 < len(parts):
                                stale_subdir = parts[cache_agents_idx + 1]
                                # Only remove if it's not a known category directory
                                if stale_subdir not in [
                                    "engineer",
                                    "ops",
                                    "qa",
                                    "universal",
                                    "documentation",
                                    "claude-mpm",
                                    "security",
                                ]:
                                    stale_dirs.add(cache_dir / stale_subdir)

                            md_file.unlink()
                            removed_count += 1

                    # Remove empty stale directories
                    for stale_dir in stale_dirs:
                        if stale_dir.exists() and stale_dir.is_dir():
                            try:
                                # Remove directory and all contents
                                import shutil

                                shutil.rmtree(stale_dir)
                            except Exception:
                                pass  # Ignore cleanup errors

                    if removed_count > 0:
                        from loguru import logger

                        logger.info(
                            f"Cleaned up {removed_count} stale cache files "
                            f"from old repositories"
                        )

                    # Count MD files in cache (agent markdown files from
                    # current repos)
                    # BUGFIX: Only count files in agent directories,
                    # not docs/templates/READMEs
                    # Valid agent paths must contain "/agents/" exactly ONCE
                    # (current structure)
                    # Exclude PM templates, BASE-AGENT, and documentation files
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
                    # Documentation files to exclude (by filename)
                    doc_files = {
                        "readme.md",
                        "changelog.md",
                        "contributing.md",
                        "implementation-summary.md",
                        "reorganization-plan.md",
                        "auto-deploy-index.md",
                    }

                    # Find all markdown files (after cleanup)
                    all_md_files = list(cache_dir.rglob("*.md"))

                    # Filter to only agent files:
                    # 1. Must have "/agents/" in path (current structure supports
                    #    both flat and {owner}/{repo}/agents/ patterns)
                    # 2. Must not be in PM templates or doc files
                    # 3. Exclude BASE-AGENT.md which is not a deployable agent
                    # 4. Exclude build artifacts (dist/, build/, .cache/)
                    #    to prevent double-counting
                    agent_files = [
                        f
                        for f in all_md_files
                        if (
                            # Must be in an agent directory
                            # Supports: cache/agents/{category}/... (flat)
                            # Supports: cache/agents/{owner}/{repo}/agents/{category}/... (GitHub sync)
                            "/agents/" in str(f)
                            # Exclude PM templates, doc files, and BASE-AGENT
                            and f.name.lower() not in pm_templates
                            and f.name.lower() not in doc_files
                            and f.name.lower() != "base-agent.md"
                            # Exclude build artifacts (prevents double-counting
                            # source + built files)
                            and not any(
                                part in str(f).split("/")
                                for part in ["dist", "build", ".cache"]
                            )
                        )
                    ]
                    agent_count = len(agent_files)

                if agent_count > 0:
                    # Deploy agents to project-level directory where Claude Code expects them
                    deploy_target = Path.cwd() / ".claude" / "agents"
                    deployment_result = deployment_service.deploy_agents(
                        target_dir=deploy_target,
                        force_rebuild=False,  # Only deploy if versions differ
                        deployment_mode="update",  # Version-aware updates
                        config=deploy_config,  # Pass config to respect profile filtering
                    )

                    # Get actual counts from deployment result (reflects configured agents)
                    deployed = len(deployment_result.get("deployed", []))
                    updated = len(deployment_result.get("updated", []))
                    skipped = len(deployment_result.get("skipped", []))
                    total_configured = deployed + updated + skipped

                    # FALLBACK: If deployment result doesn't track skipped agents (async path),
                    # count existing agents in target directory as "already deployed"
                    # This ensures accurate reporting when agents are already up-to-date
                    if total_configured == 0 and deploy_target.exists():
                        existing_agents = list(deploy_target.glob("*.md"))
                        # Filter out non-agent files (e.g., README.md, INSTRUCTIONS.md)
                        agent_count_in_target = len(
                            [
                                f
                                for f in existing_agents
                                if not f.name.startswith(("README", "INSTRUCTIONS"))
                            ]
                        )
                        if agent_count_in_target > 0:
                            # All agents already deployed - count them as skipped
                            skipped = agent_count_in_target
                            total_configured = agent_count_in_target

                    # Create progress bar with actual configured agent count (not raw file count)
                    deploy_progress = ProgressBar(
                        total=total_configured if total_configured > 0 else 1,
                        prefix="Deploying agents",
                        show_percentage=True,
                        show_counter=True,
                    )

                    # Update progress bar to completion
                    deploy_progress.update(
                        total_configured if total_configured > 0 else 1
                    )

                    # Cleanup orphaned agents (ours but no longer deployed)
                    # Get list of deployed agent filenames (what should remain)
                    deployed_filenames = []
                    for agent_name in deployment_result.get("deployed", []):
                        deployed_filenames.append(f"{agent_name}.md")
                    for agent_name in deployment_result.get("updated", []):
                        deployed_filenames.append(f"{agent_name}.md")
                    for agent_name in deployment_result.get("skipped", []):
                        deployed_filenames.append(f"{agent_name}.md")

                    # Run cleanup and get count of removed agents
                    removed = _cleanup_orphaned_agents(
                        deploy_target, deployed_filenames
                    )

                    # Show total configured agents (deployed + updated + already existing)
                    # Include cache count for context and removed count if any
                    if deployed > 0 or updated > 0:
                        if removed > 0:
                            deploy_progress.finish(
                                f"Complete: {deployed} new, {updated} updated, {skipped} unchanged, "
                                f"{removed} removed ({total_configured} configured from {agent_count} files in cache)"
                            )
                        else:
                            deploy_progress.finish(
                                f"Complete: {deployed} new, {updated} updated, {skipped} unchanged "
                                f"({total_configured} configured from {agent_count} files in cache)"
                            )
                    elif removed > 0:
                        deploy_progress.finish(
                            f"Complete: {total_configured} agents deployed, "
                            f"{removed} removed ({agent_count} files in cache)"
                        )
                    else:
                        deploy_progress.finish(
                            f"Complete: {total_configured} agents deployed "
                            f"({agent_count} files in cache)"
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
    2. Scan deployed agents for skill requirements → save to configuration.yaml
    3. Resolve which skills to deploy (user_defined vs agent_referenced)
    4. Apply profile filtering if active
    5. Deploy resolved skills to ~/.claude/skills/ - Phase 2 progress bar
    6. Log deployment results with source indication
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
            force=False, progress_callback=sync_progress.update
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
        # BUGFIX: Removed `if results["synced_count"] > 0` condition to ensure
        # agent_referenced is always populated, even when using cached skills.
        # Previous behavior: If skills were cached, agent scan was skipped,
        # leaving agent_referenced: [] empty, which prevented cleanup.
        agents_dir = Path.cwd() / ".claude" / "agents"

        # Scan agents for skill requirements (always run, not just on sync)
        agent_skills = get_required_skills_from_agents(agents_dir)

        # Save to project-level configuration.yaml
        project_config_path = Path.cwd() / ".claude-mpm" / "configuration.yaml"
        save_agent_skills_to_config(list(agent_skills), project_config_path)

        # Phase 3: Resolve which skills to deploy (user_defined or agent_referenced)
        skills_to_deploy, skill_source = get_skills_to_deploy(project_config_path)

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
        skill_count = (
            len(skills_to_deploy) if skills_to_deploy else total_skill_count
        )

        if skill_count > 0:
            # Deploy skills with resolved filter
            # Deploy ONLY to project directory (not user-level)
            # DESIGN DECISION: Project-level deployment keeps skills isolated per project,
            # avoiding pollution of user's global ~/.claude/skills/ directory.

            # Deploy to project-local directory with cleanup
            deployment_result = manager.deploy_skills(
                target_dir=Path.cwd() / ".claude" / "skills",
                force=False,
                skill_filter=set(skills_to_deploy) if skills_to_deploy else None,
            )

            # REMOVED: User-level deployment (lines 1068-1074)
            # Reason: Skills should be project-specific, not user-global.
            # Claude Code can read from project-level .claude/skills/ directory.

            # Get actual counts from deployment result (use project-local for display)
            deployed = deployment_result.get("deployed_count", 0)
            skipped = deployment_result.get("skipped_count", 0)
            filtered = deployment_result.get("filtered_count", 0)
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

            if deployed > 0:
                if filtered > 0:
                    deploy_progress.finish(
                        f"Complete: {deployed} new, {skipped} unchanged "
                        f"({total_available} {source_label}, {filtered} files in cache)"
                    )
                else:
                    deploy_progress.finish(
                        f"Complete: {deployed} new, {skipped} unchanged "
                        f"({total_available} skills {source_label} from {total_skill_count} files in cache)"
                    )
            elif filtered > 0:
                # Skills filtered means agents require fewer skills than available
                deploy_progress.finish(
                    f"No skills needed ({source_label}, {total_skill_count} files in cache)"
                )
            else:
                deploy_progress.finish(
                    f"Complete: {total_available} skills {source_label} "
                    f"({total_skill_count} files in cache)"
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
    from collections, similar to the agent summary.

    DESIGN DECISION: Fast, non-blocking check that counts skills from deployment
    directory and collection repos. Shows "X installed (Y available)" format.
    Failures are silent to avoid blocking startup.
    """
    try:
        from pathlib import Path

        # Count deployed skills (installed)
        skills_dir = Path.home() / ".claude" / "skills"
        installed_count = 0
        if skills_dir.exists():
            # Count directories with SKILL.md (excludes collection repos)
            # Exclude collection directories (obra-superpowers, etc.)
            skill_dirs = [
                d
                for d in skills_dir.iterdir()
                if d.is_dir()
                and (d / "SKILL.md").exists()
                and not (d / ".git").exists()  # Exclude collection repos
            ]
            installed_count = len(skill_dirs)

        # Count available skills in collections
        available_count = 0
        if skills_dir.exists():
            # Scan all collection directories (those with .git)
            for collection_dir in skills_dir.iterdir():
                if (
                    not collection_dir.is_dir()
                    or not (collection_dir / ".git").exists()
                ):
                    continue

                # Count skill directories in this collection
                # Skills can be nested in: skills/category/skill-name/SKILL.md
                # or in flat structure: skill-name/SKILL.md
                for root, dirs, files in os.walk(collection_dir):
                    if "SKILL.md" in files:
                        # Exclude build artifacts and hidden directories (within the collection)
                        # Get relative path from collection_dir to avoid excluding based on .claude parent
                        root_path = Path(root)
                        relative_parts = root_path.relative_to(collection_dir).parts
                        if not any(
                            part.startswith(".")
                            or part in ["dist", "build", "__pycache__"]
                            for part in relative_parts
                        ):
                            available_count += 1

        # Display summary if we have skills
        if installed_count > 0 or available_count > 0:
            print(
                f"✓ Skills: {installed_count} installed ({available_count} available)",
                flush=True,
            )

    except Exception as e:
        # Silent failure - skill summary is informational only
        from ..core.logger import get_logger

        logger = get_logger("cli")
        logger.debug(f"Failed to generate skill summary: {e}")


def verify_and_show_pm_skills():
    """Verify PM skills and display status.

    WHY: PM skills are essential for PM agent operation.
    Shows deployment status and auto-deploys if missing.
    """
    try:
        from pathlib import Path

        from ..services.pm_skills_deployer import PMSkillsDeployerService

        deployer = PMSkillsDeployerService()
        project_dir = Path.cwd()

        result = deployer.verify_pm_skills(project_dir)

        if result.verified:
            # Show verified status
            print(f"✓ PM skills: {result.skill_count} verified", flush=True)
        else:
            # Auto-deploy if missing
            print("Deploying PM skills...", end="", flush=True)
            deploy_result = deployer.deploy_pm_skills(project_dir)
            if deploy_result.success:
                total = len(deploy_result.deployed) + len(deploy_result.skipped)
                print(f"\r✓ PM skills: {total} deployed" + " " * 20, flush=True)
            else:
                print("\r⚠ PM skills: deployment failed" + " " * 20, flush=True)

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
        except Exception:
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
    # Sync hooks early to ensure up-to-date configuration
    # RATIONALE: Hooks should be synced before other services to fix stale configs
    # This is fast (<100ms) and non-blocking, so it doesn't delay startup
    sync_hooks_on_startup()  # Shows "Syncing Claude Code hooks... ✓"

    initialize_project_registry()
    check_mcp_auto_configuration()
    verify_mcp_gateway_startup()
    check_for_updates_async()
    sync_remote_agents_on_startup()  # Sync agents from remote sources
    show_agent_summary()  # Display agent counts after deployment

    # Skills deployment order (precedence: remote > bundled)
    # 1. Deploy bundled skills first (base layer from package)
    # 2. Sync and deploy remote skills (Git sources, can override bundled)
    # 3. Discover and link runtime skills (user-added skills)
    # This ensures remote skills take precedence over bundled skills when names conflict
    deploy_bundled_skills()  # Base layer: package-bundled skills
    sync_remote_skills_on_startup()  # Override layer: Git-based skills (takes precedence)
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

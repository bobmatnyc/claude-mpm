"""Skill source command handlers for managing Git-based skill repositories.

WHY: This module implements CLI commands for managing skill source repositories
(Git repositories containing skill JSON files). Provides add, remove, list, update,
enable, disable, and show commands with user-friendly output.

DESIGN DECISION: Uses SkillSourceConfiguration for persistent storage and
GitSkillSourceManager for Git operations. Provides clear, emoji-enhanced feedback
for better UX. Handles errors gracefully with actionable messages.
"""

import json
import logging
import re

from ...config.skill_sources import SkillSource, SkillSourceConfiguration
from ...services.skills.git_skill_source_manager import GitSkillSourceManager
from ...services.skills.skill_discovery_service import SkillDiscoveryService

logger = logging.getLogger(__name__)


def _test_skill_repository_access(source: SkillSource) -> dict:
    """Test if skill repository is accessible via GitHub API.

    Design Decision: Test via GitHub API, not Git clone

    Rationale: GitHub API is faster and less resource-intensive than
    cloning the repository. We can validate access and existence without
    downloading any files.

    Args:
        source: SkillSource to test

    Returns:
        Dictionary with:
        - accessible: bool (True if repo can be reached)
        - error: str (error message if not accessible)

    Example:
        >>> source = SkillSource(id="custom", type="git", url="https://github.com/owner/repo")
        >>> result = _test_skill_repository_access(source)
        >>> print(result["accessible"])
        True
    """
    import requests

    try:
        # Parse GitHub URL
        url = source.url.rstrip("/").replace(".git", "")
        parts = url.split("github.com/")
        if len(parts) != 2:
            return {"accessible": False, "error": "Invalid GitHub URL format"}

        repo_path = parts[1].strip("/")
        owner_repo = "/".join(repo_path.split("/")[:2])

        # Test GitHub API access
        api_url = f"https://api.github.com/repos/{owner_repo}"

        response = requests.get(api_url, timeout=10)

        if response.status_code == 200:
            return {"accessible": True, "error": None}
        if response.status_code == 404:
            return {
                "accessible": False,
                "error": f"Repository not found: {owner_repo}",
            }
        if response.status_code == 403:
            return {
                "accessible": False,
                "error": "Access denied (private repository or rate limit)",
            }
        return {
            "accessible": False,
            "error": f"HTTP {response.status_code}: {response.reason}",
        }

    except Exception as e:
        return {"accessible": False, "error": str(e)}


def _test_skill_repository_sync(source: SkillSource) -> dict:
    """Test syncing skill repository and discovering skills.

    Design Decision: Use temporary cache for testing

    Rationale: We want to test sync without polluting the main cache.
    Use a temporary directory that gets cleaned up after testing.

    Args:
        source: SkillSource to test sync

    Returns:
        Dictionary with:
        - synced: bool (True if sync successful)
        - skills_discovered: int (number of skills found)
        - error: str (error message if sync failed)

    Example:
        >>> source = SkillSource(id="custom", type="git", url="https://github.com/owner/repo")
        >>> result = _test_skill_repository_sync(source)
        >>> print(result["synced"])
        True
        >>> print(result["skills_discovered"])
        5
    """
    import tempfile
    from pathlib import Path

    try:
        # Create temporary cache directory
        with tempfile.TemporaryDirectory() as temp_cache:
            temp_cache_path = Path(temp_cache)

            # Create temporary config with just this source
            temp_config_path = temp_cache_path / "skill_sources.yaml"
            temp_config = SkillSourceConfiguration(config_path=temp_config_path)

            # Save source to temp config
            temp_config.save([source])

            # Sync repository
            manager = GitSkillSourceManager(
                config=temp_config, cache_dir=temp_cache_path
            )
            sync_result = manager.sync_source(source.id, force=True)

            if not sync_result.get("synced"):
                return {
                    "synced": False,
                    "skills_discovered": 0,
                    "error": sync_result.get("error", "Unknown sync error"),
                }

            return {
                "synced": True,
                "skills_discovered": sync_result.get("skills_discovered", 0),
                "error": None,
            }

    except Exception as e:
        return {"synced": False, "skills_discovered": 0, "error": str(e)}


def _generate_source_id(url: str) -> str:
    """Generate source ID from Git URL.

    Extracts repository name from various Git URL formats and sanitizes
    it to create a valid identifier.

    Args:
        url: Git repository URL

    Returns:
        Source ID (sanitized repository name)

    Examples:
        https://github.com/owner/repo.git -> repo
        https://github.com/owner/repo -> repo
        git@github.com:owner/repo.git -> repo
    """
    # Remove .git suffix
    url_clean = url.rstrip("/").removesuffix(".git")

    # Extract last path component (repo name)
    if "://" in url_clean:
        # HTTPS URL: https://github.com/owner/repo
        repo_name = url_clean.split("/")[-1]
    elif "@" in url_clean and ":" in url_clean:
        # SSH URL: git@github.com:owner/repo
        repo_name = url_clean.split(":")[-1].split("/")[-1]
    else:
        # Fallback: use last path component
        repo_name = url_clean.split("/")[-1]

    # Sanitize: only alphanumeric, dash, underscore
    sanitized = re.sub(r"[^a-zA-Z0-9_-]", "-", repo_name)

    # Remove leading/trailing dashes
    sanitized = sanitized.strip("-")

    return sanitized or "unnamed-repo"


def skill_source_command(args) -> int:
    """Main entry point for skill-source commands.

    Routes to appropriate handler based on subcommand.

    Args:
        args: Parsed command arguments

    Returns:
        Exit code (0 = success, non-zero = error)
    """
    handlers = {
        "add": handle_add_skill_source,
        "list": handle_list_skill_sources,
        "remove": handle_remove_skill_source,
        "update": handle_update_skill_sources,
        "enable": handle_enable_skill_source,
        "disable": handle_disable_skill_source,
        "show": handle_show_skill_source,
    }

    handler = handlers.get(getattr(args, "skill_source_command", None))
    if not handler:
        print(f"❌ Unknown command: {getattr(args, 'skill_source_command', 'none')}")
        print()
        print("💡 Run 'claude-mpm skill-source --help' for available commands")
        return 1

    try:
        return handler(args)
    except Exception as e:
        logger.error(f"Command failed: {e}", exc_info=True)
        print(f"❌ Command failed: {e}")
        return 1


def handle_add_skill_source(args) -> int:
    """Add a new skill source with immediate testing.

    Args:
        args: Parsed arguments with url, priority, branch, disabled, test, skip_test

    Returns:
        Exit code

    Design Decision: Immediate testing on add (fail-fast approach)

    Rationale: Adding a repository that can't be accessed or synced leads to
    broken state at startup. By testing immediately, we provide instant feedback
    and prevent configuration pollution.

    Test Mode Behavior:
    - --test: Test only, don't save to configuration
    - --no-test: Skip testing entirely (not recommended)
    - Default: Test and save if successful
    """
    try:
        # Load configuration
        config = SkillSourceConfiguration()

        # Generate source ID from URL
        source_id = _generate_source_id(args.url)

        # Check if already exists
        existing = config.get_source(source_id)
        if existing:
            print(f"❌ Source '{source_id}' already exists")
            print(f"   URL: {existing.url}")
            print()
            print(f"💡 Remove it first: claude-mpm skill-source remove {source_id}")
            return 1

        # Validate priority range
        if args.priority < 0 or args.priority > 1000:
            print("❌ Priority must be between 0 and 1000")
            return 1

        # Create new source
        enabled = not args.disabled
        source = SkillSource(
            id=source_id,
            type="git",
            url=args.url,
            branch=args.branch,
            priority=args.priority,
            enabled=enabled,
        )

        # Determine if we should test
        test_mode = getattr(args, "test", False)
        skip_test = getattr(args, "skip_test", False)

        # Test repository access unless explicitly skipped
        if not skip_test:
            print(f"🔍 Testing repository access: {args.url}")
            print()

            test_result = _test_skill_repository_access(source)

            if not test_result["accessible"]:
                print(f"❌ Repository not accessible: {test_result['error']}")
                print()
                print("💡 Check the URL and try again")
                return 1

            print("✅ Repository accessible")

            # Test sync and discovery
            print("🔍 Testing sync and skill discovery...")
            print()

            sync_result = _test_skill_repository_sync(source)

            if not sync_result["synced"]:
                print(f"❌ Sync failed: {sync_result['error']}")
                print()
                print("💡 Repository may be valid but sync failed")
                print(
                    "   You can still add it with --no-test if you want to troubleshoot later"
                )
                return 1

            skills_count = sync_result.get("skills_discovered", 0)
            print("✅ Sync successful")
            print(f"   Discovered {skills_count} skills")
            print()

        # If test mode, stop here
        if test_mode:
            print("✅ Test complete - repository is valid and accessible")
            print()
            print("💡 To add this repository, run without --test flag:")
            print(f"   claude-mpm skill-source add {args.url}")
            return 0

        # Check for priority conflicts
        warnings = config.validate_priority_conflicts()
        if warnings:
            print("⚠️  Priority conflicts detected:")
            for warning in warnings:
                print(f"   {warning}")
            print()
            print("💡 Lower priority number = higher precedence")

        # Add source
        config.add_source(source)

        # Success message
        status_emoji = "✅" if enabled else "⚠️ "
        status_text = "enabled" if enabled else "disabled"
        print(f"{status_emoji} Added skill source: {source_id}")
        print(f"   URL: {args.url}")
        print(f"   Branch: {args.branch}")
        print(f"   Priority: {args.priority}")
        print(f"   Status: {status_text}")
        print()

        if enabled:
            print("💡 Repository configured and tested successfully")
            print("   Skills from this source will be available on next startup")
        else:
            print(f"💡 Enable it: claude-mpm skill-source enable {source_id}")

        return 0

    except Exception as e:
        logger.error(f"Failed to add skill source: {e}", exc_info=True)
        print(f"❌ Failed to add skill source: {e}")
        return 1


def handle_list_skill_sources(args) -> int:
    """List configured skill sources.

    Args:
        args: Parsed arguments with by_priority, enabled_only, json

    Returns:
        Exit code
    """
    try:
        config = SkillSourceConfiguration()
        sources = config.load()

        # Filter if requested
        if args.enabled_only:
            sources = [s for s in sources if s.enabled]

        # Sort if requested
        if args.by_priority:
            sources = sorted(sources, key=lambda s: s.priority)

        # Output format
        if args.json:
            # JSON output
            output = [
                {
                    "id": s.id,
                    "type": s.type,
                    "url": s.url,
                    "branch": s.branch,
                    "priority": s.priority,
                    "enabled": s.enabled,
                }
                for s in sources
            ]
            print(json.dumps(output, indent=2))
        else:
            # Human-readable output
            if not sources:
                print("📚 No skill sources configured")
                print()
                print("💡 Add a source: claude-mpm skill-source add <git-url>")
                return 0

            filter_text = " (enabled only)" if args.enabled_only else ""
            print(f"📚 Configured Skill Sources ({len(sources)} total{filter_text}):")
            print()

            for source in sources:
                status = "✅" if source.enabled else "❌"
                status_text = "Enabled" if source.enabled else "Disabled"
                print(f"  {status} {source.id} ({status_text})")
                print(f"     URL: {source.url}")
                print(f"     Branch: {source.branch}")
                print(f"     Priority: {source.priority}")
                print()

        return 0

    except Exception as e:
        logger.error(f"Failed to list skill sources: {e}", exc_info=True)
        print(f"❌ Failed to list skill sources: {e}")
        return 1


def handle_remove_skill_source(args) -> int:
    """Remove a skill source.

    Args:
        args: Parsed arguments with source_id, force

    Returns:
        Exit code
    """
    try:
        config = SkillSourceConfiguration()
        source = config.get_source(args.source_id)

        if not source:
            print(f"❌ Source not found: {args.source_id}")
            print()
            print("💡 List sources: claude-mpm skill-source list")
            return 1

        # Confirmation prompt unless --force
        if not args.force:
            print(f"⚠️  Remove skill source: {args.source_id}")
            print(f"   URL: {source.url}")
            print()
            response = input("   Continue? (y/N): ").strip().lower()
            if response not in ("y", "yes"):
                print()
                print("❌ Cancelled")
                return 0

        # Remove source
        config.remove_source(args.source_id)

        print()
        print(f"✅ Removed skill source: {args.source_id}")

        return 0

    except Exception as e:
        logger.error(f"Failed to remove skill source: {e}", exc_info=True)
        print(f"❌ Failed to remove skill source: {e}")
        return 1


def handle_update_skill_sources(args) -> int:
    """Update (sync) skill sources.

    Args:
        args: Parsed arguments with source_id (optional), force

    Returns:
        Exit code
    """
    try:
        config = SkillSourceConfiguration()
        manager = GitSkillSourceManager(config)

        if args.source_id:
            # Update specific source
            print(f"🔄 Updating skill source: {args.source_id}")

            # Verify source exists
            source = config.get_source(args.source_id)
            if not source:
                print(f"❌ Source not found: {args.source_id}")
                print()
                print("💡 List sources: claude-mpm skill-source list")
                return 1

            # Sync source
            result = manager.sync_source(args.source_id, force=args.force)

            if result.get("synced"):
                print(f"✅ Successfully updated {args.source_id}")
                skills_count = result.get("skills_discovered", 0)
                print(f"   Skills discovered: {skills_count}")

                if skills_count > 0:
                    print()
                    print(
                        f"💡 View skills: claude-mpm skill-source show {args.source_id} --skills"
                    )
            else:
                print(f"❌ Failed to update {args.source_id}")
                error_msg = result.get("error", "Unknown error")
                print(f"   Error: {error_msg}")
                return 1
        else:
            # Update all sources
            print("🔄 Updating all skill sources...")
            results = manager.sync_all_sources(force=args.force)

            success_count = results["synced_count"]
            total_count = success_count + results["failed_count"]

            print()
            print(f"✅ Updated {success_count}/{total_count} sources")
            print()

            for source_id, result in results["sources"].items():
                if result.get("synced"):
                    skills_count = result.get("skills_discovered", 0)
                    print(f"   ✅ {source_id}: {skills_count} skills")
                else:
                    error_msg = result.get("error", "Unknown error")
                    print(f"   ❌ {source_id}: {error_msg}")

            if success_count > 0:
                print()
                print("💡 List all skills: claude-mpm skills list")

        return 0

    except Exception as e:
        logger.error(f"Failed to update skill sources: {e}", exc_info=True)
        print(f"❌ Failed to update skill sources: {e}")
        return 1


def handle_enable_skill_source(args) -> int:
    """Enable a skill source.

    Args:
        args: Parsed arguments with source_id

    Returns:
        Exit code
    """
    try:
        config = SkillSourceConfiguration()
        source = config.get_source(args.source_id)

        if not source:
            print(f"❌ Source not found: {args.source_id}")
            print()
            print("💡 List sources: claude-mpm skill-source list")
            return 1

        if source.enabled:
            print(f"⚠️  Source '{args.source_id}' is already enabled")
            return 0

        # Enable source
        source.enabled = True
        config.update_source(source)

        print(f"✅ Enabled skill source: {args.source_id}")
        print()
        print(f"💡 Sync skills: claude-mpm skill-source update {args.source_id}")

        return 0

    except Exception as e:
        logger.error(f"Failed to enable skill source: {e}", exc_info=True)
        print(f"❌ Failed to enable skill source: {e}")
        return 1


def handle_disable_skill_source(args) -> int:
    """Disable a skill source.

    Args:
        args: Parsed arguments with source_id

    Returns:
        Exit code
    """
    try:
        config = SkillSourceConfiguration()
        source = config.get_source(args.source_id)

        if not source:
            print(f"❌ Source not found: {args.source_id}")
            print()
            print("💡 List sources: claude-mpm skill-source list")
            return 1

        if not source.enabled:
            print(f"⚠️  Source '{args.source_id}' is already disabled")
            return 0

        # Disable source
        source.enabled = False
        config.update_source(source)

        print(f"✅ Disabled skill source: {args.source_id}")
        print("   Skills from this source will not be available")
        print()
        print(f"💡 Re-enable: claude-mpm skill-source enable {args.source_id}")

        return 0

    except Exception as e:
        logger.error(f"Failed to disable skill source: {e}", exc_info=True)
        print(f"❌ Failed to disable skill source: {e}")
        return 1


def handle_show_skill_source(args) -> int:
    """Show detailed information about a skill source.

    Args:
        args: Parsed arguments with source_id, skills

    Returns:
        Exit code
    """
    try:
        config = SkillSourceConfiguration()
        source = config.get_source(args.source_id)

        if not source:
            print(f"❌ Source not found: {args.source_id}")
            print()
            print("💡 List sources: claude-mpm skill-source list")
            return 1

        # Display source details
        status_emoji = "✅" if source.enabled else "❌"
        status_text = "Enabled" if source.enabled else "Disabled"

        print()
        print(f"📚 Skill Source: {source.id}")
        print()
        print(f"  Status: {status_emoji} {status_text}")
        print(f"  URL: {source.url}")
        print(f"  Branch: {source.branch}")
        print(f"  Priority: {source.priority}")
        print()

        # Optionally list skills from this source
        if args.skills:
            try:
                discovery = SkillDiscoveryService(config)
                all_skills = discovery.discover_skills()

                # Filter skills by source
                source_skills = [
                    skill
                    for skill in all_skills
                    if skill.get("source_id") == args.source_id
                ]

                if source_skills:
                    print(f"  Skills ({len(source_skills)}):")
                    print()
                    for skill in source_skills:
                        print(f"    - {skill['name']}")
                        if skill.get("description"):
                            desc = skill["description"]
                            # Truncate long descriptions
                            if len(desc) > 70:
                                desc = desc[:70] + "..."
                            print(f"      {desc}")
                    print()
                else:
                    print("  No skills found in this source")
                    print()
                    print(
                        f"💡 Sync source: claude-mpm skill-source update {args.source_id}"
                    )
            except Exception as e:
                logger.warning(f"Failed to load skills: {e}")
                print(f"  ⚠️  Could not load skills: {e}")
                print()

        return 0

    except Exception as e:
        logger.error(f"Failed to show skill source: {e}", exc_info=True)
        print(f"❌ Failed to show skill source: {e}")
        return 1

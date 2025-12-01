"""Agent source command handlers for managing Git-based agent repositories.

WHY: This module implements CLI commands for managing agent source repositories
(Git repositories containing agent markdown files). Provides add, remove, list, update,
enable, disable, and show commands with user-friendly output.

DESIGN DECISION: Uses AgentSourceConfiguration for persistent storage and
GitSourceManager for Git operations. Provides clear, emoji-enhanced feedback
for better UX. Handles errors gracefully with actionable messages.

IMPLEMENTATION NOTE: This module is adapted from skill_source.py, following
the same proven patterns but for agent repositories instead of skills.
"""

import json
import logging
import re

from ...config.agent_sources import AgentSourceConfiguration
from ...models.git_repository import GitRepository
from ...services.agents.git_source_manager import GitSourceManager

logger = logging.getLogger(__name__)


def _test_repository_access(repo: GitRepository) -> dict:
    """Test if repository is accessible via GitHub API.

    Design Decision: Test via GitHub API, not Git clone

    Rationale: GitHub API is faster and less resource-intensive than
    cloning the repository. We can validate access and existence without
    downloading any files.

    Args:
        repo: GitRepository to test

    Returns:
        Dictionary with:
        - accessible: bool (True if repo can be reached)
        - error: str (error message if not accessible)

    Example:
        >>> repo = GitRepository(url="https://github.com/owner/repo")
        >>> result = _test_repository_access(repo)
        >>> print(result["accessible"])
        True
    """
    import requests

    try:
        # Parse GitHub URL to extract owner/repo
        owner, repo_name = repo._parse_github_url(repo.url)

        # Test GitHub API access
        api_url = f"https://api.github.com/repos/{owner}/{repo_name}"

        response = requests.get(api_url, timeout=10)

        if response.status_code == 200:
            return {"accessible": True, "error": None}
        if response.status_code == 404:
            return {
                "accessible": False,
                "error": f"Repository not found: {owner}/{repo_name}",
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


def _test_repository_sync(repo: GitRepository) -> dict:
    """Test syncing repository and discovering agents.

    Design Decision: Use temporary cache for testing

    Rationale: We want to test sync without polluting the main cache.
    Use a temporary directory that gets cleaned up after testing.

    Args:
        repo: GitRepository to test sync

    Returns:
        Dictionary with:
        - synced: bool (True if sync successful)
        - agents_discovered: list[str] (agent names found)
        - error: str (error message if sync failed)

    Example:
        >>> repo = GitRepository(url="https://github.com/owner/repo")
        >>> result = _test_repository_sync(repo)
        >>> print(result["synced"])
        True
        >>> print(result["agents_discovered"])
        ['engineer', 'pm', 'research']
    """
    import tempfile
    from pathlib import Path

    try:
        # Create temporary cache directory
        with tempfile.TemporaryDirectory() as temp_cache:
            temp_cache_path = Path(temp_cache)

            # Override cache path for testing
            original_cache_path = repo.cache_path
            repo.cache_path = temp_cache_path / repo.identifier

            # Sync repository
            manager = GitSourceManager(cache_root=temp_cache_path)
            sync_result = manager.sync_repository(repo, force=True, show_progress=False)

            # Restore original cache path
            repo.cache_path = original_cache_path

            if not sync_result.get("synced"):
                return {
                    "synced": False,
                    "agents_discovered": [],
                    "error": sync_result.get("error", "Unknown sync error"),
                }

            return {
                "synced": True,
                "agents_discovered": sync_result.get("agents_discovered", []),
                "error": None,
            }

    except Exception as e:
        return {"synced": False, "agents_discovered": [], "error": str(e)}


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


def agent_source_command(args) -> int:
    """Main entry point for agent-source commands.

    Routes to appropriate handler based on subcommand.

    Args:
        args: Parsed command arguments

    Returns:
        Exit code (0 = success, non-zero = error)
    """
    handlers = {
        "add": handle_add_agent_source,
        "list": handle_list_agent_sources,
        "remove": handle_remove_agent_source,
        "update": handle_update_agent_sources,
        "enable": handle_enable_agent_source,
        "disable": handle_disable_agent_source,
        "show": handle_show_agent_source,
    }

    handler = handlers.get(getattr(args, "agent_source_command", None))
    if not handler:
        print(f"❌ Unknown command: {getattr(args, 'agent_source_command', 'none')}")
        print()
        print("💡 Run 'claude-mpm agent-source --help' for available commands")
        return 1

    try:
        return handler(args)
    except Exception as e:
        logger.error(f"Command failed: {e}", exc_info=True)
        print(f"❌ Command failed: {e}")
        return 1


def handle_add_agent_source(args) -> int:
    """Add a new agent source with immediate testing.

    Args:
        args: Parsed arguments with url, priority, branch, subdirectory, disabled, test, skip_test

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

    Testing Steps:
    1. Validate repository URL format
    2. Test Git access (can we reach the repository?)
    3. Test sync (can we clone and discover agents?)
    4. Report results with clear feedback
    5. Save to configuration only if tests pass
    """
    try:
        # Load configuration
        config = AgentSourceConfiguration.load()

        # Generate source ID from URL
        source_id = _generate_source_id(args.url)

        # Check if already exists (by identifier)
        for repo in config.repositories:
            if repo.identifier == source_id or repo.url == args.url:
                print(f"❌ Source '{repo.identifier}' already exists")
                print(f"   URL: {repo.url}")
                print()
                print(
                    f"💡 Remove it first: claude-mpm agent-source remove {repo.identifier}"
                )
                return 1

        # Validate priority range
        if args.priority < 0 or args.priority > 1000:
            print("❌ Priority must be between 0 and 1000")
            return 1

        # Create new repository
        enabled = not args.disabled
        repo = GitRepository(
            url=args.url,
            subdirectory=args.subdirectory,
            priority=args.priority,
            enabled=enabled,
        )

        # Validate repository
        errors = repo.validate()
        if errors:
            print("❌ Invalid repository configuration:")
            for error in errors:
                print(f"   - {error}")
            return 1

        # Determine if we should test
        test_mode = getattr(args, "test", False)
        skip_test = getattr(args, "skip_test", False)

        # Test repository access unless explicitly skipped
        if not skip_test:
            print(f"🔍 Testing repository access: {args.url}")
            print()

            test_result = _test_repository_access(repo)

            if not test_result["accessible"]:
                print(f"❌ Repository not accessible: {test_result['error']}")
                print()
                print("💡 Check the URL and try again")
                return 1

            print("✅ Repository accessible")

            # Test sync and discovery
            print("🔍 Testing sync and agent discovery...")
            print()

            sync_result = _test_repository_sync(repo)

            if not sync_result["synced"]:
                print(f"❌ Sync failed: {sync_result['error']}")
                print()
                print("💡 Repository may be valid but sync failed")
                print(
                    "   You can still add it with --no-test if you want to troubleshoot later"
                )
                return 1

            agents_count = len(sync_result.get("agents_discovered", []))
            print("✅ Sync successful")
            print(f"   Discovered {agents_count} agents")

            if agents_count > 0:
                print()
                print("   Agents found:")
                for agent_name in sync_result["agents_discovered"][:5]:
                    print(f"     - {agent_name}")
                if agents_count > 5:
                    print(f"     ... and {agents_count - 5} more")

            print()

        # If test mode, stop here
        if test_mode:
            print("✅ Test complete - repository is valid and accessible")
            print()
            print("💡 To add this repository, run without --test flag:")
            print(f"   claude-mpm agent-source add {args.url}")
            return 0

        # Check for priority conflicts
        conflicts = [r for r in config.repositories if r.priority == args.priority]
        if conflicts:
            print("⚠️  Priority conflict detected:")
            for conflict_repo in conflicts:
                print(
                    f"   Repository '{conflict_repo.identifier}' has the same priority"
                )
            print()
            print("💡 Lower priority number = higher precedence")

        # Add repository
        config.add_repository(repo)
        config.save()

        # Success message
        status_emoji = "✅" if enabled else "⚠️ "
        status_text = "enabled" if enabled else "disabled"
        print(f"{status_emoji} Added agent source: {repo.identifier}")
        print(f"   URL: {args.url}")
        if args.subdirectory:
            print(f"   Subdirectory: {args.subdirectory}")
        print(f"   Priority: {args.priority}")
        print(f"   Status: {status_text}")
        print()

        if enabled:
            print("💡 Repository configured and tested successfully")
            print("   Agents from this source will be available on next startup")
        else:
            print(f"💡 Enable it: claude-mpm agent-source enable {repo.identifier}")

        return 0

    except Exception as e:
        logger.error(f"Failed to add agent source: {e}", exc_info=True)
        print(f"❌ Failed to add agent source: {e}")
        return 1


def handle_list_agent_sources(args) -> int:
    """List configured agent sources.

    Args:
        args: Parsed arguments with by_priority, enabled_only, json

    Returns:
        Exit code
    """
    try:
        config = AgentSourceConfiguration.load()
        repositories = config.repositories.copy()

        # Add system repository if not disabled
        system_repo = config.get_system_repo()
        all_repos = []
        if system_repo:
            all_repos.append(system_repo)
        all_repos.extend(repositories)

        # Filter if requested
        if args.enabled_only:
            all_repos = [r for r in all_repos if r.enabled]

        # Sort if requested
        if args.by_priority:
            all_repos = sorted(all_repos, key=lambda r: r.priority)

        # Output format
        if args.json:
            # JSON output
            output = [
                {
                    "identifier": r.identifier,
                    "url": r.url,
                    "subdirectory": r.subdirectory,
                    "priority": r.priority,
                    "enabled": r.enabled,
                }
                for r in all_repos
            ]
            print(json.dumps(output, indent=2))
        else:
            # Human-readable output
            if not all_repos:
                print("📚 No agent sources configured")
                print()
                print("💡 Add a source: claude-mpm agent-source add <git-url>")
                return 0

            filter_text = " (enabled only)" if args.enabled_only else ""
            print(f"📚 Configured Agent Sources ({len(all_repos)} total{filter_text}):")
            print()

            for repo in all_repos:
                status = "✅" if repo.enabled else "❌"
                status_text = "Enabled" if repo.enabled else "Disabled"
                is_system = repo.url == "https://github.com/bobmatnyc/claude-mpm-agents"
                system_tag = " [System]" if is_system else ""

                print(f"  {status} {repo.identifier}{system_tag} ({status_text})")
                print(f"     URL: {repo.url}")
                if repo.subdirectory:
                    print(f"     Subdirectory: {repo.subdirectory}")
                print(f"     Priority: {repo.priority}")
                print()

        return 0

    except Exception as e:
        logger.error(f"Failed to list agent sources: {e}", exc_info=True)
        print(f"❌ Failed to list agent sources: {e}")
        return 1


def handle_remove_agent_source(args) -> int:
    """Remove an agent source.

    Args:
        args: Parsed arguments with source_id, force

    Returns:
        Exit code
    """
    try:
        config = AgentSourceConfiguration.load()

        # Find repository by identifier
        repo_to_remove = None
        for repo in config.repositories:
            if repo.identifier == args.source_id:
                repo_to_remove = repo
                break

        if not repo_to_remove:
            print(f"❌ Source not found: {args.source_id}")
            print()
            print("💡 List sources: claude-mpm agent-source list")
            return 1

        # Confirmation prompt unless --force
        if not args.force:
            print(f"⚠️  Remove agent source: {args.source_id}")
            print(f"   URL: {repo_to_remove.url}")
            print()
            response = input("   Continue? (y/N): ").strip().lower()
            if response not in ("y", "yes"):
                print()
                print("❌ Cancelled")
                return 0

        # Remove repository
        config.remove_repository(args.source_id)
        config.save()

        print()
        print(f"✅ Removed agent source: {args.source_id}")

        return 0

    except Exception as e:
        logger.error(f"Failed to remove agent source: {e}", exc_info=True)
        print(f"❌ Failed to remove agent source: {e}")
        return 1


def handle_update_agent_sources(args) -> int:
    """Update (sync) agent sources.

    Args:
        args: Parsed arguments with source_id (optional), force

    Returns:
        Exit code
    """
    try:
        config = AgentSourceConfiguration.load()
        manager = GitSourceManager()

        if args.source_id:
            # Update specific source
            print(f"🔄 Updating agent source: {args.source_id}")

            # Find repository
            repo_to_sync = None
            for repo in config.repositories:
                if repo.identifier == args.source_id:
                    repo_to_sync = repo
                    break

            # Check system repo
            if not repo_to_sync:
                system_repo = config.get_system_repo()
                if system_repo and system_repo.identifier == args.source_id:
                    repo_to_sync = system_repo

            if not repo_to_sync:
                print(f"❌ Source not found: {args.source_id}")
                print()
                print("💡 List sources: claude-mpm agent-source list")
                return 1

            # Sync repository
            result = manager.sync_repository(repo_to_sync, force=args.force)

            if result.get("synced"):
                print(f"✅ Successfully updated {args.source_id}")
                agents_count = len(result.get("agents_discovered", []))
                print(f"   Agents discovered: {agents_count}")

                if agents_count > 0:
                    print()
                    print(
                        f"💡 View agents: claude-mpm agent-source show {args.source_id} --agents"
                    )
            else:
                print(f"❌ Failed to update {args.source_id}")
                error_msg = result.get("error", "Unknown error")
                print(f"   Error: {error_msg}")
                return 1
        else:
            # Update all enabled sources
            print("🔄 Updating all agent sources...")
            enabled_repos = config.get_enabled_repositories()

            if not enabled_repos:
                print("⚠️  No enabled agent sources to update")
                print()
                print("💡 Add a source: claude-mpm agent-source add <git-url>")
                return 0

            results = manager.sync_all_repositories(enabled_repos, force=args.force)

            success_count = sum(1 for r in results.values() if r.get("synced"))
            total_count = len(results)

            print()
            print(f"✅ Updated {success_count}/{total_count} sources")
            print()

            for repo_id, result in results.items():
                if result.get("synced"):
                    agents_count = len(result.get("agents_discovered", []))
                    print(f"   ✅ {repo_id}: {agents_count} agents")
                else:
                    error_msg = result.get("error", "Unknown error")
                    print(f"   ❌ {repo_id}: {error_msg}")

            if success_count > 0:
                print()
                print("💡 List agents: claude-mpm agents list --remote")

        return 0

    except Exception as e:
        logger.error(f"Failed to update agent sources: {e}", exc_info=True)
        print(f"❌ Failed to update agent sources: {e}")
        return 1


def handle_enable_agent_source(args) -> int:
    """Enable an agent source.

    Args:
        args: Parsed arguments with source_id

    Returns:
        Exit code
    """
    try:
        config = AgentSourceConfiguration.load()

        # Find repository
        repo_to_enable = None
        for repo in config.repositories:
            if repo.identifier == args.source_id:
                repo_to_enable = repo
                break

        if not repo_to_enable:
            print(f"❌ Source not found: {args.source_id}")
            print()
            print("💡 List sources: claude-mpm agent-source list")
            return 1

        if repo_to_enable.enabled:
            print(f"⚠️  Source '{args.source_id}' is already enabled")
            return 0

        # Enable repository
        repo_to_enable.enabled = True
        config.save()

        print(f"✅ Enabled agent source: {args.source_id}")
        print()
        print(f"💡 Sync agents: claude-mpm agent-source update {args.source_id}")

        return 0

    except Exception as e:
        logger.error(f"Failed to enable agent source: {e}", exc_info=True)
        print(f"❌ Failed to enable agent source: {e}")
        return 1


def handle_disable_agent_source(args) -> int:
    """Disable an agent source.

    Args:
        args: Parsed arguments with source_id

    Returns:
        Exit code
    """
    try:
        config = AgentSourceConfiguration.load()

        # Find repository
        repo_to_disable = None
        for repo in config.repositories:
            if repo.identifier == args.source_id:
                repo_to_disable = repo
                break

        if not repo_to_disable:
            print(f"❌ Source not found: {args.source_id}")
            print()
            print("💡 List sources: claude-mpm agent-source list")
            return 1

        if not repo_to_disable.enabled:
            print(f"⚠️  Source '{args.source_id}' is already disabled")
            return 0

        # Disable repository
        repo_to_disable.enabled = False
        config.save()

        print(f"✅ Disabled agent source: {args.source_id}")
        print("   Agents from this source will not be available")
        print()
        print(f"💡 Re-enable: claude-mpm agent-source enable {args.source_id}")

        return 0

    except Exception as e:
        logger.error(f"Failed to disable agent source: {e}", exc_info=True)
        print(f"❌ Failed to disable agent source: {e}")
        return 1


def handle_show_agent_source(args) -> int:
    """Show detailed information about an agent source.

    Args:
        args: Parsed arguments with source_id, agents

    Returns:
        Exit code
    """
    try:
        config = AgentSourceConfiguration.load()

        # Find repository
        repo_to_show = None
        for repo in config.repositories:
            if repo.identifier == args.source_id:
                repo_to_show = repo
                break

        # Check system repo
        if not repo_to_show:
            system_repo = config.get_system_repo()
            if system_repo and system_repo.identifier == args.source_id:
                repo_to_show = system_repo

        if not repo_to_show:
            print(f"❌ Source not found: {args.source_id}")
            print()
            print("💡 List sources: claude-mpm agent-source list")
            return 1

        # Display repository details
        status_emoji = "✅" if repo_to_show.enabled else "❌"
        status_text = "Enabled" if repo_to_show.enabled else "Disabled"
        is_system = repo_to_show.url == "https://github.com/bobmatnyc/claude-mpm-agents"

        print()
        print(f"📚 Agent Source: {repo_to_show.identifier}")
        if is_system:
            print("   [System Repository]")
        print()
        print(f"  Status: {status_emoji} {status_text}")
        print(f"  URL: {repo_to_show.url}")
        if repo_to_show.subdirectory:
            print(f"  Subdirectory: {repo_to_show.subdirectory}")
        print(f"  Priority: {repo_to_show.priority}")
        print()

        # Optionally list agents from this source
        if args.agents:
            try:
                manager = GitSourceManager()
                all_agents = manager.list_cached_agents(repo_identifier=args.source_id)

                if all_agents:
                    print(f"  Agents ({len(all_agents)}):")
                    print()
                    for agent in all_agents:
                        name = agent.get("metadata", {}).get(
                            "name", agent.get("agent_id", "unknown")
                        )
                        print(f"    - {name}")
                        version = agent.get("metadata", {}).get("version")
                        if version:
                            print(f"      Version: {version}")
                    print()
                else:
                    print("  No agents found in this source")
                    print()
                    print(
                        f"💡 Sync source: claude-mpm agent-source update {args.source_id}"
                    )
            except Exception as e:
                logger.warning(f"Failed to load agents: {e}")
                print(f"  ⚠️  Could not load agents: {e}")
                print()

        return 0

    except Exception as e:
        logger.error(f"Failed to show agent source: {e}", exc_info=True)
        print(f"❌ Failed to show agent source: {e}")
        return 1

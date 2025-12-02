"""Agent cleanup command for syncing, installing, and removing old underscore-named agents.

WHY: After standardizing template filenames from underscores to dashes, users need
a way to sync the latest agents, install them with correct names, and remove old
underscore-named duplicates.

DESIGN DECISION: Three-phase cleanup process:
1. Sync agents from remote repository (download latest)
2. Deploy synced agents to target directory (force overwrite)
3. Remove old underscore-named agents that have dash equivalents

IMPLEMENTATION NOTE: Uses name similarity matching to identify old agents that
should be removed (e.g., python_engineer.md → python-engineer.md).
"""

import logging
from pathlib import Path
from typing import List

from ...config.agent_sources import AgentSourceConfiguration
from ...services.agents.sources.git_source_sync_service import GitSourceSyncService

logger = logging.getLogger(__name__)


def _normalize_agent_name(name: str) -> str:
    """Normalize agent name by removing extensions and converting to lowercase.

    Args:
        name: Agent filename (e.g., "python_engineer.md" or "python-engineer.md")

    Returns:
        Normalized name (e.g., "pythonengineer")
    """
    # Remove file extension
    name = name.replace(".md", "").replace(".json", "")
    # Remove dashes and underscores for comparison
    name = name.replace("-", "").replace("_", "")
    return name.lower()


def _find_old_underscore_agents(
    deployed_agents: List[Path], new_agents: List[str]
) -> List[Path]:
    """Find old underscore-named agents that have dash-named equivalents.

    Args:
        deployed_agents: List of paths to deployed agent files
        new_agents: List of new agent filenames (with dashes)

    Returns:
        List of paths to old agents that should be removed
    """
    # Normalize new agent names for comparison
    normalized_new = {_normalize_agent_name(agent) for agent in new_agents}

    old_agents = []
    for agent_path in deployed_agents:
        agent_name = agent_path.name

        # Check if this is an underscore-named agent
        if "_" in agent_name and "-" not in agent_name:
            normalized = _normalize_agent_name(agent_name)

            # If we have a dash-named equivalent, mark for removal
            if normalized in normalized_new:
                old_agents.append(agent_path)

    return old_agents


def handle_agents_cleanup(args) -> int:
    """Handle the 'claude-mpm agents cleanup' command.

    This command performs a complete agent cleanup:
    1. Syncs agents from remote repository
    2. Deploys agents with new naming convention (force overwrite)
    3. Removes old underscore-named agents that have dash equivalents

    Args:
        args: Parsed command-line arguments with:
            - dry_run: Show what would be done without doing it
            - target: Target directory for deployment
            - global_deployment: Deploy to global ~/.claude/agents/

    Returns:
        Exit code (0 for success, 1 for error)
    """
    try:
        dry_run = args.dry_run

        # Determine target directory
        if args.global_deployment:
            target_dir = Path.home() / ".claude" / "agents"
        elif args.target:
            target_dir = args.target
        else:
            target_dir = Path.cwd() / ".claude-mpm" / "agents"

        print("\n🧹 Agent Cleanup")
        print(f"{'=' * 60}")

        if dry_run:
            print("🔍 DRY RUN MODE - No changes will be made\n")

        # Phase 1: Sync agents from remote
        print("📥 Phase 1: Syncing agents from remote repository...")

        config = AgentSourceConfiguration.load()
        repositories = config.get_enabled_repositories()

        if not repositories:
            print(
                "⚠️  No agent sources configured. Run 'claude-mpm agent-source add' first."
            )
            return 1

        sync_service = GitSourceSyncService()
        synced_count = 0

        for repo in repositories:
            print(f"  Syncing from {repo.url}...")
            try:
                result = sync_service.sync_agents(show_progress=False)
                synced_count += result.get("total_downloaded", 0)
                print(f"  ✓ Synced {result.get('total_downloaded', 0)} agents")
            except Exception as e:
                print(f"  ✗ Failed to sync: {e}")
                continue

        if synced_count == 0:
            print(
                "⚠️  No agents synced. Check your network connection or agent sources."
            )
            return 1

        print(f"\n✓ Synced {synced_count} agents total")

        # Phase 2: Deploy agents (force overwrite)
        print(f"\n📦 Phase 2: Deploying agents to {target_dir}...")

        if not dry_run:
            target_dir.mkdir(parents=True, exist_ok=True)

        # Get list of agents from cache
        cache_dir = sync_service.get_cached_agents_dir()
        cached_agents = list(cache_dir.glob("*.md"))
        new_agent_names = [agent.name for agent in cached_agents]

        if not dry_run:
            result = sync_service.deploy_agents_to_project(Path.cwd(), force=True)
            deployed_count = len(result.get("deployed", [])) + len(
                result.get("updated", [])
            )
            print(f"✓ Deployed {deployed_count} agents")
        else:
            print(f"  Would deploy {len(cached_agents)} agents:")
            for agent in cached_agents[:10]:  # Show first 10
                print(f"    - {agent.name}")
            if len(cached_agents) > 10:
                print(f"    ... and {len(cached_agents) - 10} more")

        # Phase 3: Remove old underscore-named agents
        print("\n🗑️  Phase 3: Removing old underscore-named agents...")

        # Find deployed agents
        deployed_agents = list(target_dir.glob("*.md"))
        old_agents = _find_old_underscore_agents(deployed_agents, new_agent_names)

        if not old_agents:
            print("✓ No old underscore-named agents found")
        else:
            print(f"  Found {len(old_agents)} old agents to remove:")
            for agent in old_agents:
                # Find the new equivalent name
                normalized = _normalize_agent_name(agent.name)
                dash_equiv = [
                    name
                    for name in new_agent_names
                    if _normalize_agent_name(name) == normalized
                ]
                equiv_str = f" → {dash_equiv[0]}" if dash_equiv else ""

                print(f"    - {agent.name}{equiv_str}")

                if not dry_run:
                    agent.unlink()

            if not dry_run:
                print(f"✓ Removed {len(old_agents)} old agents")
            else:
                print(f"  Would remove {len(old_agents)} old agents")

        # Summary
        print(f"\n{'=' * 60}")
        print("✅ Cleanup complete!")
        print("\nSummary:")
        print(f"  • Synced: {synced_count} agents")
        print(f"  • Deployed: {len(cached_agents)} agents")
        print(f"  • Removed: {len(old_agents)} old agents")

        if dry_run:
            print("\n💡 Run without --dry-run to apply changes")

        return 0

    except Exception as e:
        logger.exception("Agent cleanup failed")
        print(f"\n❌ Error: {e}")
        return 1

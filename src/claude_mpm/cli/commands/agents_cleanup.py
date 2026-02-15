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
Also detects -agent suffix duplicates and content-identical files.
"""

import hashlib
import logging
from pathlib import Path
from typing import Dict, List, Set, Tuple

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


def _strip_agent_suffix(name: str) -> str:
    """Strip -agent or _agent suffix from a filename (without extension).

    Args:
        name: Agent filename without extension (e.g., "research-agent" or "research_agent")

    Returns:
        Name with suffix removed (e.g., "research")
    """
    # Remove extension first if present
    base_name = name.replace(".md", "").replace(".json", "")

    # Strip common suffixes
    for suffix in ("-agent", "_agent"):
        if base_name.endswith(suffix):
            return base_name[: -len(suffix)]

    return base_name


def _get_file_hash(file_path: Path) -> str:
    """Calculate SHA256 hash of file contents.

    Args:
        file_path: Path to the file

    Returns:
        Hex-encoded SHA256 hash string
    """
    return hashlib.sha256(file_path.read_bytes()).hexdigest()


def _find_duplicate_agents_by_content(
    deployed_agents: List[Path],
) -> Dict[str, List[Path]]:
    """Find agents with identical content (byte-for-byte duplicates).

    Args:
        deployed_agents: List of paths to deployed agent files

    Returns:
        Dictionary mapping content hash to list of files with that content
        (only includes hashes with 2+ files)
    """
    hash_to_files: Dict[str, List[Path]] = {}

    for agent_path in deployed_agents:
        try:
            file_hash = _get_file_hash(agent_path)
            if file_hash not in hash_to_files:
                hash_to_files[file_hash] = []
            hash_to_files[file_hash].append(agent_path)
        except Exception as e:
            logger.warning(f"Could not hash file {agent_path}: {e}")

    # Return only hashes with duplicates
    return {h: files for h, files in hash_to_files.items() if len(files) > 1}


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


def _find_agent_suffix_duplicates(
    deployed_agents: List[Path], new_agents: List[str]
) -> List[Path]:
    """Find agents with -agent suffix that have non-suffixed equivalents.

    For example, if both "research.md" and "research-agent.md" exist,
    flag "research-agent.md" for removal.

    Args:
        deployed_agents: List of paths to deployed agent files
        new_agents: List of new agent filenames

    Returns:
        List of paths to -agent suffixed files that should be removed
    """
    # Build set of base names (without -agent suffix) from new agents
    new_base_names: Set[str] = set()
    for agent in new_agents:
        base = agent.replace(".md", "").replace(".json", "")
        new_base_names.add(base.lower())
        # Also add the stripped version
        stripped = _strip_agent_suffix(base)
        if stripped != base:
            new_base_names.add(stripped.lower())

    # Build set of deployed agent base names
    deployed_base_names: Set[str] = set()
    for agent_path in deployed_agents:
        base = agent_path.stem.lower()
        deployed_base_names.add(base)

    duplicates = []
    for agent_path in deployed_agents:
        agent_name = agent_path.name
        base = agent_path.stem.lower()

        # Check if this file has -agent or _agent suffix
        if base.endswith("-agent") or base.endswith("_agent"):
            stripped = _strip_agent_suffix(base).lower()

            # If the non-suffixed version exists (in deployed or new agents), mark for removal
            if stripped in deployed_base_names or stripped in new_base_names:
                duplicates.append(agent_path)
                logger.info(
                    f"Found -agent suffix duplicate: {agent_name} (base: {stripped})"
                )

    return duplicates


def _select_preferred_duplicate(files: List[Path]) -> Tuple[Path, List[Path]]:
    """Select which file to keep among content-identical duplicates.

    Prefers:
    1. Dash-named files over underscore-named
    2. Shorter names (no suffix) over longer names (with -agent suffix)
    3. Alphabetically first if all else equal

    Args:
        files: List of file paths with identical content

    Returns:
        Tuple of (file_to_keep, files_to_remove)
    """
    if len(files) < 2:
        return files[0], []

    def score(path: Path) -> Tuple[int, int, str]:
        """Lower score is better."""
        name = path.stem.lower()
        # Prefer dash-named (score 0) over underscore-named (score 1)
        dash_score = 1 if "_" in name and "-" not in name else 0
        # Prefer shorter names (no -agent suffix)
        suffix_score = 1 if name.endswith("-agent") or name.endswith("_agent") else 0
        return (dash_score, suffix_score, name)

    sorted_files = sorted(files, key=score)
    return sorted_files[0], sorted_files[1:]


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
        print("\n🗑️  Phase 3: Removing duplicate and old agents...")

        # Find deployed agents
        deployed_agents = list(target_dir.glob("*.md"))
        agents_to_remove: List[Path] = []
        removal_reasons: Dict[Path, str] = {}

        # 3a. Find old underscore-named agents
        print("  Checking for underscore-named duplicates...")
        old_underscore = _find_old_underscore_agents(deployed_agents, new_agent_names)
        for agent in old_underscore:
            if agent not in agents_to_remove:
                agents_to_remove.append(agent)
                normalized = _normalize_agent_name(agent.name)
                dash_equiv = [
                    name
                    for name in new_agent_names
                    if _normalize_agent_name(name) == normalized
                ]
                equiv_str = f" (dash equivalent: {dash_equiv[0]})" if dash_equiv else ""
                removal_reasons[agent] = f"underscore naming{equiv_str}"

        # 3b. Find -agent suffix duplicates
        print("  Checking for -agent suffix duplicates...")
        suffix_duplicates = _find_agent_suffix_duplicates(
            deployed_agents, new_agent_names
        )
        for agent in suffix_duplicates:
            if agent not in agents_to_remove:
                agents_to_remove.append(agent)
                stripped = _strip_agent_suffix(agent.stem)
                removal_reasons[agent] = f"-agent suffix (base: {stripped})"

        # 3c. Find content-identical duplicates
        print("  Checking for content-identical files...")
        content_duplicates = _find_duplicate_agents_by_content(deployed_agents)
        content_removal_count = 0
        for file_hash, files in content_duplicates.items():
            keep, remove = _select_preferred_duplicate(files)
            for agent in remove:
                if agent not in agents_to_remove:
                    agents_to_remove.append(agent)
                    removal_reasons[agent] = f"content duplicate of {keep.name}"
                    content_removal_count += 1

        # Report and remove
        if not agents_to_remove:
            print("✓ No duplicate or old agents found")
        else:
            print(f"  Found {len(agents_to_remove)} agents to remove:")
            for agent in agents_to_remove:
                reason = removal_reasons.get(agent, "unknown reason")
                print(f"    - {agent.name} ({reason})")

                if not dry_run:
                    agent.unlink()

            if not dry_run:
                print(f"✓ Removed {len(agents_to_remove)} duplicate/old agents")
            else:
                print(f"  Would remove {len(agents_to_remove)} duplicate/old agents")

        # Summary
        print(f"\n{'=' * 60}")
        print("Cleanup complete!")
        print("\nSummary:")
        print(f"  - Synced: {synced_count} agents")
        print(f"  - Deployed: {len(cached_agents)} agents")
        print(f"  - Removed: {len(agents_to_remove)} duplicate/old agents")
        if agents_to_remove:
            underscore_count = len(old_underscore)
            suffix_count = len(
                [a for a in suffix_duplicates if a not in old_underscore]
            )
            print(f"    - Underscore-named: {underscore_count}")
            print(f"    - Agent-suffix: {suffix_count}")
            print(f"    - Content duplicates: {content_removal_count}")

        if dry_run:
            print("\n💡 Run without --dry-run to apply changes")

        return 0

    except Exception as e:
        logger.exception("Agent cleanup failed")
        print(f"\n❌ Error: {e}")
        return 1

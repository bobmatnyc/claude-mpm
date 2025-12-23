"""Single-tier agent deployment service using Git sources.

This service replaces the multi-tier deployment system with a simpler,
Git-source-based approach. All agents come from Git repositories with
priority-based conflict resolution.

WHY: The multi-tier system (PROJECT > USER > SYSTEM) added complexity
without providing clear value. Single-tier with Git sources provides:
- Simpler mental model (Git repos with priorities)
- Better version control and collaboration
- Easier testing and debugging
- More flexible agent distribution

Design Decision: Composition over Inheritance

This service composes Phase 1 components (GitSourceManager,
RemoteAgentDiscoveryService) rather than inheriting. This provides
better separation of concerns and makes it easier to test each
component independently.

Trade-offs:
- Flexibility: Easy to swap implementations or mock for testing
- Complexity: Slightly more code than inheritance
- Maintainability: Clear boundaries between sync, discovery, and deployment
"""

import logging
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.claude_mpm.config.agent_sources import AgentSourceConfiguration
from src.claude_mpm.models.git_repository import GitRepository
from src.claude_mpm.services.agents.deployment.remote_agent_discovery_service import (
    RemoteAgentDiscoveryService,
)
from src.claude_mpm.services.agents.git_source_manager import GitSourceManager

logger = logging.getLogger(__name__)


class SingleTierDeploymentService:
    """Single-tier agent deployment service using Git sources.

    This service manages agent deployment from Git repositories with
    priority-based conflict resolution. It coordinates:
    - Git repository syncing (via GitSourceManager)
    - Agent discovery from cached repositories
    - Priority-based agent resolution
    - Deployment to .claude/agents/ directory

    Architecture:
    - Phase 1 GitSourceManager handles repository sync
    - Phase 1 RemoteAgentDiscoveryService discovers agents
    - This service orchestrates deployment workflow
    - Priority system resolves conflicts (lower priority = higher precedence)

    Example:
        >>> config = AgentSourceConfiguration.load()
        >>> service = SingleTierDeploymentService(
        ...     config=config,
        ...     deployment_dir=Path.home() / ".claude" / "agents"
        ... )
        >>> result = service.deploy_all_agents(force_sync=True)
        >>> print(f"Deployed {result['deployed_agents']} agents")
    """

    def __init__(
        self,
        config: AgentSourceConfiguration,
        deployment_dir: Path,
        cache_root: Optional[Path] = None,
    ):
        """Initialize single-tier deployment service.

        Args:
            config: Agent source configuration with repositories
            deployment_dir: Target deployment directory (.claude/agents/)
            cache_root: Cache root for repositories
                       (defaults to ~/.claude-mpm/cache/agents/)
        """
        self.config = config
        self.deployment_dir = deployment_dir
        self.deployment_dir.mkdir(parents=True, exist_ok=True)

        if cache_root is None:
            cache_root = Path.home() / ".claude-mpm" / "cache" / "agents"

        self.cache_root = cache_root
        self.git_source_manager = GitSourceManager(cache_root)

        logger.info(
            f"SingleTierDeploymentService initialized: "
            f"deployment={deployment_dir}, cache={cache_root}"
        )

    def deploy_all_agents(
        self, force_sync: bool = False, dry_run: bool = False
    ) -> Dict[str, Any]:
        """Deploy all agents from configured Git sources.

        Workflow:
        1. Get all enabled repositories from configuration
        2. Sync repositories (unless cached and not force_sync)
        3. Discover all agents from all repositories
        4. Resolve conflicts using priority system (lower = higher precedence)
        5. Deploy agents to .claude/agents/
        6. Return deployment report

        Args:
            force_sync: Force repository sync even if cache is fresh
            dry_run: Show what would be deployed without actually deploying

        Returns:
            Deployment report dictionary:
            {
                "synced_repos": int,           # Repositories successfully synced
                "discovered_agents": int,      # Total agents discovered
                "deployed_agents": int,        # Agents actually deployed
                "skipped_agents": int,         # Agents skipped (dry run or errors)
                "conflicts_resolved": int,     # Agent name conflicts resolved
                "timestamp": str,              # ISO timestamp
                "agents": [                    # Per-agent details
                    {
                        "name": "engineer",
                        "source": "bobmatnyc/claude-mpm-agents",
                        "priority": 100,
                        "deployed": true
                    }
                ]
            }

        Error Handling:
        - Individual repository sync failures don't stop overall deployment
        - Failed deployments are logged and counted as skipped
        - Returns partial success with error details
        """
        logger.info(
            f"Starting deploy_all_agents (force_sync={force_sync}, dry_run={dry_run})"
        )

        # Step 1: Get enabled repositories
        repos = self.config.get_enabled_repositories()
        logger.info(f"Found {len(repos)} enabled repositories")

        if not repos:
            logger.warning("No enabled repositories found")
            return {
                "synced_repos": 0,
                "discovered_agents": 0,
                "deployed_agents": 0,
                "skipped_agents": 0,
                "conflicts_resolved": 0,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "agents": [],
            }

        # Step 2: Sync all repositories
        sync_results = self.git_source_manager.sync_all_repositories(repos, force_sync)
        synced_count = sum(1 for r in sync_results.values() if r.get("synced"))
        logger.info(f"Synced {synced_count}/{len(repos)} repositories")

        # Step 3: Discover all agents from all repositories
        all_agents = []
        for repo in repos:
            try:
                # Discover agents in this repository's cache
                agents = self._discover_agents_in_repo(repo)
                all_agents.extend(agents)
                logger.debug(f"Discovered {len(agents)} agents from {repo.identifier}")
            except Exception as e:
                logger.error(f"Failed to discover agents in {repo.identifier}: {e}")

        logger.info(f"Discovered {len(all_agents)} total agents")

        # Step 4: Resolve conflicts (lower priority = higher precedence)
        resolved_agents, conflicts_count = self._resolve_conflicts(all_agents)
        logger.info(
            f"Resolved {conflicts_count} conflicts, {len(resolved_agents)} unique agents"
        )

        # Step 5: Deploy agents
        deployed_count = 0
        skipped_count = 0
        agent_details = []

        for agent in resolved_agents:
            agent_name = agent.get("metadata", {}).get("name", "unknown")
            source_repo = agent.get("repository", "unknown")
            priority = agent.get("priority", 100)

            try:
                if dry_run:
                    logger.info(
                        f"[DRY RUN] Would deploy {agent_name} from {source_repo}"
                    )
                    agent_details.append(
                        {
                            "name": agent_name,
                            "source": source_repo,
                            "priority": priority,
                            "deployed": False,
                            "dry_run": True,
                        }
                    )
                    skipped_count += 1
                else:
                    # Deploy agent to .claude/agents/
                    success = self._deploy_agent_file(agent)
                    if success:
                        logger.info(f"Deployed {agent_name} from {source_repo}")
                        deployed_count += 1
                        agent_details.append(
                            {
                                "name": agent_name,
                                "source": source_repo,
                                "priority": priority,
                                "deployed": True,
                            }
                        )
                    else:
                        logger.warning(f"Failed to deploy {agent_name}")
                        skipped_count += 1
                        agent_details.append(
                            {
                                "name": agent_name,
                                "source": source_repo,
                                "priority": priority,
                                "deployed": False,
                                "error": "deployment_failed",
                            }
                        )
            except Exception as e:
                logger.error(f"Error deploying {agent_name}: {e}")
                skipped_count += 1
                agent_details.append(
                    {
                        "name": agent_name,
                        "source": source_repo,
                        "priority": priority,
                        "deployed": False,
                        "error": str(e),
                    }
                )

        # Step 6: Build and return report
        report = {
            "synced_repos": synced_count,
            "discovered_agents": len(all_agents),
            "deployed_agents": deployed_count,
            "skipped_agents": skipped_count,
            "conflicts_resolved": conflicts_count,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agents": agent_details,
        }

        logger.info(
            f"Deployment complete: {deployed_count} deployed, "
            f"{skipped_count} skipped, {conflicts_count} conflicts resolved"
        )

        return report

    def deploy_agent(
        self, agent_name: str, source_repo: Optional[str] = None, dry_run: bool = False
    ) -> Dict[str, Any]:
        """Deploy a specific agent.

        Args:
            agent_name: Name of agent to deploy (e.g., "engineer", "research")
            source_repo: Optional specific repository identifier
                        (e.g., "owner/repo/subdirectory")
            dry_run: Show what would be deployed without actually deploying

        Returns:
            Deployment result:
            {
                "deployed": bool,
                "agent_name": str,
                "source": str,
                "priority": int,
                "path": str,  # Deployment path (if successful)
                "error": str  # Error message (if failed)
            }

        Error Handling:
        - Returns deployed=False with error message if agent not found
        - Returns deployed=False with error message if deployment fails
        """
        logger.info(f"Deploying agent: {agent_name} (source={source_repo})")

        # Discover agents (filtered by source_repo if specified)
        if source_repo:
            # Find specific repository
            repos = [
                r
                for r in self.config.get_enabled_repositories()
                if r.identifier == source_repo
            ]
            if not repos:
                return {
                    "deployed": False,
                    "agent_name": agent_name,
                    "error": f"Source repository not found: {source_repo}",
                }
        else:
            repos = self.config.get_enabled_repositories()

        # Discover agents from repositories
        all_agents = []
        for repo in repos:
            try:
                agents = self._discover_agents_in_repo(repo)
                all_agents.extend(agents)
            except Exception as e:
                logger.warning(f"Failed to discover agents in {repo.identifier}: {e}")

        # Find matching agent
        matching_agents = [
            a
            for a in all_agents
            if a.get("metadata", {}).get("name", "").lower().replace(" ", "-")
            == agent_name.lower()
            or a.get("agent_id", "") == agent_name.lower()
        ]

        if not matching_agents:
            return {
                "deployed": False,
                "agent_name": agent_name,
                "error": f"Agent not found: {agent_name}",
            }

        # Resolve conflicts if multiple sources have same agent
        if len(matching_agents) > 1:
            # Sort by priority (lower = higher precedence)
            matching_agents.sort(key=lambda a: a.get("priority", 100))
            logger.info(
                f"Multiple sources for {agent_name}, using highest priority "
                f"(priority={matching_agents[0].get('priority')})"
            )

        # Deploy the highest priority agent
        agent = matching_agents[0]
        agent_name_display = agent.get("metadata", {}).get("name", agent_name)
        source = agent.get("repository", "unknown")
        priority = agent.get("priority", 100)

        if dry_run:
            logger.info(f"[DRY RUN] Would deploy {agent_name_display} from {source}")
            return {
                "deployed": False,
                "agent_name": agent_name_display,
                "source": source,
                "priority": priority,
                "dry_run": True,
            }

        # Deploy agent
        try:
            success = self._deploy_agent_file(agent)
            if success:
                deployed_path = (
                    self.deployment_dir
                    / f"{agent.get('agent_id', agent_name.lower())}.md"
                )
                logger.info(f"Deployed {agent_name_display} to {deployed_path}")
                return {
                    "deployed": True,
                    "agent_name": agent_name_display,
                    "source": source,
                    "priority": priority,
                    "path": str(deployed_path),
                }
            return {
                "deployed": False,
                "agent_name": agent_name_display,
                "source": source,
                "priority": priority,
                "error": "Deployment failed",
            }
        except Exception as e:
            logger.error(f"Error deploying {agent_name_display}: {e}")
            return {
                "deployed": False,
                "agent_name": agent_name_display,
                "source": source,
                "priority": priority,
                "error": str(e),
            }

    def list_available_agents(
        self, source_repo: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List all agents available from configured sources.

        Args:
            source_repo: Optional repository filter (e.g., "owner/repo/subdirectory")

        Returns:
            List of agent metadata dictionaries:
            [
                {
                    "name": "Engineer",
                    "agent_id": "engineer",
                    "description": "Python specialist...",
                    "source": "bobmatnyc/claude-mpm-agents",
                    "priority": 100,
                    "version": "abc123...",
                    "model": "sonnet"
                }
            ]
        """
        logger.debug(f"Listing available agents (source={source_repo})")

        # Get repositories
        if source_repo:
            repos = [
                r
                for r in self.config.get_enabled_repositories()
                if r.identifier == source_repo
            ]
        else:
            repos = self.config.get_enabled_repositories()

        # Discover all agents
        all_agents = []
        for repo in repos:
            try:
                agents = self._discover_agents_in_repo(repo)
                all_agents.extend(agents)
            except Exception as e:
                logger.warning(f"Failed to discover agents in {repo.identifier}: {e}")

        # Format for return
        formatted_agents = []
        for agent in all_agents:
            metadata = agent.get("metadata", {})
            formatted_agents.append(
                {
                    "name": metadata.get("name", "Unknown"),
                    "agent_id": agent.get("agent_id", "unknown"),
                    "description": metadata.get("description", ""),
                    "source": agent.get("repository", "unknown"),
                    "priority": agent.get("priority", 100),
                    "version": agent.get("version", "unknown"),
                    "model": agent.get("model", "sonnet"),
                }
            )

        logger.debug(f"Found {len(formatted_agents)} available agents")
        return formatted_agents

    def get_deployed_agents(self) -> List[Dict[str, Any]]:
        """List currently deployed agents.

        Scans .claude/agents/ directory for deployed agent files.

        Returns:
            List of deployed agent metadata:
            [
                {
                    "name": "Engineer",
                    "agent_id": "engineer",
                    "path": "/Users/user/.claude/agents/engineer.md",
                    "size": 12345
                }
            ]
        """
        logger.debug(f"Listing deployed agents from {self.deployment_dir}")

        if not self.deployment_dir.exists():
            return []

        deployed = []
        for md_file in self.deployment_dir.glob("*.md"):
            try:
                # Extract agent_id from filename
                agent_id = md_file.stem

                # Read first line to get agent name
                with open(md_file) as f:
                    first_line = f.readline().strip()
                    # Extract name from markdown heading
                    name = (
                        first_line.lstrip("#").strip()
                        if first_line.startswith("#")
                        else agent_id
                    )

                deployed.append(
                    {
                        "name": name,
                        "agent_id": agent_id,
                        "path": str(md_file),
                        "size": md_file.stat().st_size,
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to read deployed agent {md_file.name}: {e}")

        logger.debug(f"Found {len(deployed)} deployed agents")
        return deployed

    def remove_agent(self, agent_name: str) -> bool:
        """Remove a deployed agent.

        Args:
            agent_name: Agent ID to remove (e.g., "engineer")

        Returns:
            True if agent was removed, False if not found
        """
        logger.info(f"Removing agent: {agent_name}")

        # Find deployed agent file
        agent_file = self.deployment_dir / f"{agent_name.lower()}.md"

        if not agent_file.exists():
            logger.warning(f"Agent not found: {agent_name}")
            return False

        try:
            agent_file.unlink()
            logger.info(f"Removed agent: {agent_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to remove agent {agent_name}: {e}")
            return False

    def sync_sources(
        self, force: bool = False, repo_identifier: Optional[str] = None
    ) -> Dict[str, Any]:
        """Sync Git sources.

        Wrapper for GitSourceManager.sync_all_repositories() with filtering.

        Args:
            force: Force sync even if cache is fresh (bypasses ETag)
            repo_identifier: Optional repository identifier to sync
                           (e.g., "owner/repo/subdirectory")

        Returns:
            Sync results dictionary:
            {
                "owner/repo": {
                    "synced": bool,
                    "files_updated": int,
                    ...
                }
            }
        """
        logger.info(f"Syncing sources (force={force}, repo={repo_identifier})")

        repos = self.config.get_enabled_repositories()

        if repo_identifier:
            repos = [r for r in repos if r.identifier == repo_identifier]
            if not repos:
                return {
                    repo_identifier: {
                        "synced": False,
                        "error": "Repository not found",
                    }
                }

        return self.git_source_manager.sync_all_repositories(repos, force)

    def _discover_agents_in_repo(self, repo: GitRepository) -> List[Dict[str, Any]]:
        """Discover agents in a specific repository's cache.

        Args:
            repo: Repository to discover agents from

        Returns:
            List of agent dictionaries with repository and priority metadata
        """
        try:
            discovery_service = RemoteAgentDiscoveryService(repo.cache_path)
            agents = discovery_service.discover_remote_agents()

            # Add repository identifier and priority to each agent
            for agent in agents:
                agent["repository"] = repo.identifier
                agent["priority"] = repo.priority

            return agents

        except Exception as e:
            logger.error(f"Failed to discover agents in {repo.identifier}: {e}")
            return []

    def _resolve_conflicts(
        self, agents: List[Dict[str, Any]]
    ) -> tuple[List[Dict[str, Any]], int]:
        """Resolve agent name conflicts using priority system.

        When multiple repositories provide the same agent, choose the one
        with the lowest priority number (highest precedence).

        Args:
            agents: List of all discovered agents from all repositories

        Returns:
            Tuple of (resolved_agents, conflict_count):
            - resolved_agents: List with one agent per name (highest priority)
            - conflict_count: Number of conflicts resolved

        Algorithm:
        1. Group agents by name
        2. For each group, sort by priority (ascending)
        3. Take the first agent (lowest priority number = highest precedence)
        4. Count groups with multiple agents as conflicts
        """
        # Group agents by name
        agents_by_name: Dict[str, List[Dict[str, Any]]] = {}

        for agent in agents:
            name = agent.get("metadata", {}).get("name", "").lower().replace(" ", "-")
            if not name:
                # Skip agents without valid names
                continue

            if name not in agents_by_name:
                agents_by_name[name] = []

            agents_by_name[name].append(agent)

        # Resolve conflicts
        resolved = []
        conflict_count = 0

        for name, agent_list in agents_by_name.items():
            if len(agent_list) > 1:
                # Conflict detected
                conflict_count += 1

                # Sort by priority (ascending - lower number = higher precedence)
                agent_list.sort(key=lambda a: a.get("priority", 100))

                logger.info(
                    f"Conflict for '{name}': {len(agent_list)} sources, "
                    f"using {agent_list[0].get('repository')} "
                    f"(priority {agent_list[0].get('priority')})"
                )

            # Use highest priority agent (first after sort)
            resolved.append(agent_list[0])

        return resolved, conflict_count

    def _deploy_agent_file(self, agent: Dict[str, Any]) -> bool:
        """Deploy a single agent file to deployment directory.

        Copies the agent Markdown file from cache to .claude/agents/

        Args:
            agent: Agent dictionary with source_file path

        Returns:
            True if deployment succeeded, False otherwise

        Error Handling:
        - Returns False if source file doesn't exist
        - Returns False if copy operation fails
        - Logs all errors for debugging
        """
        try:
            # Get source file path
            source_file = Path(agent.get("source_file", ""))
            if not source_file.exists():
                logger.error(f"Source file does not exist: {source_file}")
                return False

            # Build target filename using agent_id
            agent_id = agent.get("agent_id", "unknown")
            target_file = self.deployment_dir / f"{agent_id}.md"

            # Copy file
            shutil.copy2(source_file, target_file)

            logger.debug(f"Deployed {source_file.name} to {target_file}")
            return True

        except Exception as e:
            logger.error(f"Failed to deploy agent file: {e}")
            return False

    def __repr__(self) -> str:
        """Return string representation."""
        return (
            f"SingleTierDeploymentService("
            f"deployment_dir='{self.deployment_dir}', "
            f"repositories={len(self.config.get_enabled_repositories())})"
        )

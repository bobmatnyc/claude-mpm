"""Agent review service for comparing project agents with managed agents.

WHY: This service helps users maintain a clean agent directory by:
1. Identifying which agents are managed vs custom
2. Detecting outdated versions of managed agents
3. Finding unused agents that don't match the detected toolchain
4. Safely archiving unnecessary agents instead of deleting them

DESIGN DECISIONS:
- Archive to .claude/agents/unused/ instead of deleting (safe, recoverable)
- Add timestamps to archived files to prevent conflicts
- Preserve custom user agents (not in managed set)
- Compare versions to detect outdated managed agents
"""

import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Set

from claude_mpm.core.logging_config import get_logger

logger = get_logger(__name__)


class AgentReviewService:
    """Service for reviewing and managing project agents.

    This service analyzes the relationship between project agents and managed
    agents from the claude-mpm-agents repository, categorizing them as:
    - Managed: In sync with managed agents
    - Outdated: Older version of managed agent exists
    - Custom: User-created agents not in managed set
    - Unused: Not recommended for this project's toolchain
    """

    def __init__(self):
        """Initialize the agent review service."""
        self.logger = get_logger(__name__)

    def review_project_agents(
        self,
        project_agents_dir: Path,
        managed_agents: List[Dict[str, Any]],
        recommended_agent_ids: Set[str],
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Review existing project agents and categorize them.

        Args:
            project_agents_dir: Directory containing project agents (.claude/agents/)
            managed_agents: List of managed agent dicts from cache
            recommended_agent_ids: Set of agent IDs recommended for this toolchain

        Returns:
            Dictionary with categorized agents:
            {
                "managed": [...],      # In sync with managed
                "outdated": [...],     # Older version exists
                "custom": [...],       # User-created
                "unused": [...],       # Not needed for this toolchain
            }
        """
        results = {
            "managed": [],
            "outdated": [],
            "custom": [],
            "unused": [],
        }

        if not project_agents_dir.exists():
            self.logger.debug(
                f"Project agents directory does not exist: {project_agents_dir}"
            )
            return results

        # Build lookup map of managed agents by ID
        managed_by_id = {agent["agent_id"]: agent for agent in managed_agents}

        # Scan project agents
        for agent_file in project_agents_dir.glob("*.md"):
            # Skip the unused directory itself
            if agent_file.name == "unused":
                continue

            agent_name = agent_file.stem

            # Parse agent to get version and metadata
            project_agent_info = self._parse_project_agent(agent_file)

            # Check if this is a managed agent
            if agent_name in managed_by_id:
                managed_agent = managed_by_id[agent_name]

                # Compare versions
                project_version = project_agent_info.get("version", "unknown")
                managed_version = managed_agent.get("version", "unknown")

                if self._is_outdated(project_version, managed_version):
                    # Outdated version of managed agent
                    results["outdated"].append(
                        {
                            "name": agent_name,
                            "path": agent_file,
                            "current_version": project_version,
                            "available_version": managed_version,
                            "recommended": agent_name in recommended_agent_ids,
                        }
                    )
                else:
                    # Up-to-date managed agent
                    results["managed"].append(
                        {
                            "name": agent_name,
                            "path": agent_file,
                            "version": project_version,
                            "recommended": agent_name in recommended_agent_ids,
                        }
                    )
            else:
                # Custom user agent (not in managed set)
                results["custom"].append(
                    {
                        "name": agent_name,
                        "path": agent_file,
                        "version": project_agent_info.get("version", "unknown"),
                    }
                )

        # Identify unused agents (managed or outdated but not recommended)
        for category in ["managed", "outdated"]:
            for agent in results[category][:]:  # Copy list to modify during iteration
                if not agent.get("recommended", False):
                    # This managed/outdated agent is not recommended for this toolchain
                    results["unused"].append(agent)
                    results[category].remove(agent)

        self.logger.info(
            f"Agent review complete: "
            f"{len(results['managed'])} managed, "
            f"{len(results['outdated'])} outdated, "
            f"{len(results['custom'])} custom, "
            f"{len(results['unused'])} unused"
        )

        return results

    def archive_agents(
        self, agents_to_archive: List[Dict[str, Any]], project_agents_dir: Path
    ) -> Dict[str, Any]:
        """Archive agents by moving them to .claude/agents/unused/.

        Args:
            agents_to_archive: List of agent dicts with 'name' and 'path' keys
            project_agents_dir: Base agents directory (.claude/agents/)

        Returns:
            Dictionary with archival results:
            {
                "archived": [...],  # Successfully archived
                "errors": [...],    # Archival errors
            }
        """
        results = {"archived": [], "errors": []}

        if not agents_to_archive:
            return results

        # Create unused directory
        unused_dir = project_agents_dir / "unused"
        unused_dir.mkdir(exist_ok=True)

        for agent in agents_to_archive:
            agent_path = agent["path"]
            agent_name = agent["name"]

            try:
                # Generate timestamped filename to avoid conflicts
                timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
                archived_name = f"{agent_name}_{timestamp}.md"
                archived_path = unused_dir / archived_name

                # Move the file
                shutil.move(str(agent_path), str(archived_path))

                results["archived"].append(
                    {
                        "name": agent_name,
                        "original_path": str(agent_path),
                        "archived_path": str(archived_path),
                    }
                )

                self.logger.debug(f"Archived {agent_name} to {archived_path}")

            except Exception as e:
                error_msg = f"Failed to archive {agent_name}: {e}"
                self.logger.error(error_msg)
                results["errors"].append(error_msg)

        self.logger.info(
            f"Archived {len(results['archived'])} agents, "
            f"{len(results['errors'])} errors"
        )

        return results

    def _parse_project_agent(self, agent_file: Path) -> Dict[str, Any]:
        """Parse a project agent file to extract metadata.

        Args:
            agent_file: Path to agent Markdown file

        Returns:
            Dictionary with agent metadata (version, name, etc.)
        """
        try:
            content = agent_file.read_text(encoding="utf-8")

            # Extract version from YAML frontmatter
            import re

            version_match = re.search(
                r'^version:\s*["\']?(.+?)["\']?$', content, re.MULTILINE
            )
            version = version_match.group(1) if version_match else "unknown"

            return {
                "version": version,
                "name": agent_file.stem,
            }

        except Exception as e:
            self.logger.warning(f"Failed to parse agent {agent_file.name}: {e}")
            return {"version": "unknown", "name": agent_file.stem}

    def _is_outdated(self, current_version: str, available_version: str) -> bool:
        """Check if current version is outdated compared to available version.

        Args:
            current_version: Currently deployed version
            available_version: Available version from managed agents

        Returns:
            True if current version is outdated
        """
        # Handle unknown versions
        if current_version == "unknown" or available_version == "unknown":
            return False

        # Simple string comparison for now
        # TODO: Implement semantic version comparison (1.2.3 vs 1.2.4)
        return current_version != available_version

    def get_archive_summary(self, project_agents_dir: Path) -> Dict[str, Any]:
        """Get summary of archived agents.

        Args:
            project_agents_dir: Base agents directory (.claude/agents/)

        Returns:
            Dictionary with archive statistics
        """
        unused_dir = project_agents_dir / "unused"

        if not unused_dir.exists():
            return {"count": 0, "agents": []}

        archived_files = list(unused_dir.glob("*.md"))

        return {
            "count": len(archived_files),
            "agents": [
                {
                    "name": f.stem,
                    "path": str(f),
                    "size_bytes": f.stat().st_size,
                }
                for f in archived_files
            ],
        }

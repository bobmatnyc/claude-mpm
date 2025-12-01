"""Service for discovering and converting remote Markdown agents to JSON format.

This service handles the 4th tier of agent discovery: remote agents cached from GitHub.
Remote agents are stored as Markdown files with YAML frontmatter and need to be converted
to the JSON template format expected by the deployment system.

WHY: Remote agents from GitHub are cached as Markdown but the deployment system expects
JSON templates. This service bridges that gap and integrates remote agents into the
multi-tier discovery system.
"""

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from claude_mpm.core.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class RemoteAgentMetadata:
    """Metadata extracted from remote agent Markdown file."""

    name: str
    description: str
    model: str
    routing_keywords: List[str]
    routing_paths: List[str]
    routing_priority: int
    source_file: Path
    version: str  # SHA-256 hash from cache metadata


class RemoteAgentDiscoveryService:
    """Discovers and converts remote Markdown agents to JSON format.

    Remote agents are discovered from the cache directory (~/.claude-mpm/cache/remote-agents/)
    where they are stored as Markdown files. This service:
    1. Discovers all *.md files in the remote agents cache
    2. Parses Markdown frontmatter and content to extract metadata
    3. Converts to JSON template format for deployment
    4. Retrieves version (SHA-256 hash) from cache metadata

    Design Decision: Markdown Parsing Strategy
    - Use regex for simple frontmatter extraction (fast, no dependencies)
    - Parse key-value pairs from Configuration section
    - Extract routing info from Routing section
    - Fallback to sensible defaults when sections are missing

    Trade-offs:
    - Performance: Regex parsing is fast for our simple format
    - Maintainability: Clear regex patterns are easy to understand
    - Flexibility: Supports optional sections with defaults
    """

    def __init__(self, remote_agents_dir: Path):
        """Initialize the remote agent discovery service.

        Args:
            remote_agents_dir: Directory containing cached remote agent Markdown files
        """
        self.remote_agents_dir = remote_agents_dir
        self.logger = get_logger(__name__)

    def discover_remote_agents(self) -> List[Dict[str, Any]]:
        """Discover all remote agents from cache directory.

        Scans the remote agents directory for *.md files and converts each
        to JSON template format. Skips files that can't be parsed.

        Returns:
            List of agent dictionaries in JSON template format

        Example:
            >>> service = RemoteAgentDiscoveryService(Path("~/.claude-mpm/cache/remote-agents"))
            >>> agents = service.discover_remote_agents()
            >>> len(agents)
            5
            >>> agents[0]['name']
            'Security Scanner Agent'
        """
        agents = []

        if not self.remote_agents_dir.exists():
            self.logger.debug(
                f"Remote agents directory does not exist: {self.remote_agents_dir}"
            )
            return agents

        # Find all Markdown files
        md_files = list(self.remote_agents_dir.glob("*.md"))
        self.logger.debug(
            f"Found {len(md_files)} Markdown files in {self.remote_agents_dir}"
        )

        for md_file in md_files:
            try:
                agent_dict = self._parse_markdown_agent(md_file)
                if agent_dict:
                    agents.append(agent_dict)
                    self.logger.debug(
                        f"Successfully parsed remote agent: {md_file.name}"
                    )
                else:
                    self.logger.warning(
                        f"Failed to parse remote agent (no name found): {md_file.name}"
                    )
            except Exception as e:
                self.logger.warning(f"Failed to parse remote agent {md_file.name}: {e}")

        self.logger.info(
            f"Discovered {len(agents)} remote agents from {self.remote_agents_dir.name}"
        )
        return agents

    def _parse_markdown_agent(self, md_file: Path) -> Optional[Dict[str, Any]]:
        """Parse Markdown agent file and convert to JSON template format.

        Expected Markdown format:
        ```markdown
        # Agent Name

        Description paragraph (first paragraph after heading)

        ## Configuration
        - Model: sonnet
        - Priority: 100

        ## Routing
        - Keywords: keyword1, keyword2
        - Paths: /path1/, /path2/
        ```

        Args:
            md_file: Path to Markdown agent file

        Returns:
            Agent dictionary in JSON template format, or None if parsing fails

        Error Handling:
        - Returns None if agent name (first heading) is missing
        - Uses defaults for missing sections (model=sonnet, priority=50)
        - Empty routing keywords/paths if Routing section missing
        """
        try:
            content = md_file.read_text(encoding="utf-8")
        except Exception as e:
            self.logger.error(f"Failed to read file {md_file}: {e}")
            return None

        # Extract agent name from first heading
        name_match = re.search(r"^#\s+(.+?)$", content, re.MULTILINE)
        if not name_match:
            self.logger.debug(f"No agent name heading found in {md_file.name}")
            return None
        name = name_match.group(1).strip()

        # Extract description (first paragraph after heading, before next heading)
        desc_match = re.search(
            r"^#.+?\n\n(.+?)(?:\n\n##|\Z)", content, re.DOTALL | re.MULTILINE
        )
        description = desc_match.group(1).strip() if desc_match else ""

        # Extract model from Configuration section
        model_match = re.search(r"Model:\s*(\w+)", content, re.IGNORECASE)
        model = model_match.group(1) if model_match else "sonnet"

        # Extract priority from Configuration section
        priority_match = re.search(r"Priority:\s*(\d+)", content, re.IGNORECASE)
        priority = int(priority_match.group(1)) if priority_match else 50

        # Extract routing keywords
        keywords_match = re.search(r"Keywords:\s*(.+?)(?:\n|$)", content, re.IGNORECASE)
        keywords = []
        if keywords_match:
            keywords = [k.strip() for k in keywords_match.group(1).split(",")]

        # Extract routing paths
        paths_match = re.search(r"Paths:\s*(.+?)(?:\n|$)", content, re.IGNORECASE)
        paths = []
        if paths_match:
            paths = [p.strip() for p in paths_match.group(1).split(",")]

        # Get version (SHA-256 hash) from cache metadata
        version = self._get_agent_version(md_file)

        # Generate agent_id from name (lowercase, replace spaces/underscores with hyphens)
        # 1. Convert to lowercase
        # 2. Replace spaces and underscores with hyphens
        # 3. Remove any characters that aren't alphanumeric or hyphens
        # 4. Collapse multiple consecutive hyphens into one
        agent_id = name.lower()
        agent_id = agent_id.replace(" ", "-").replace("_", "-")
        agent_id = re.sub(r"[^a-z0-9-]+", "", agent_id)
        agent_id = re.sub(r"-+", "-", agent_id)  # Collapse multiple hyphens

        # Convert to JSON template format and return
        # IMPORTANT: Include 'path' field for compatibility with deployment validation (ticket 1M-480)
        # Git-sourced agents must have 'path' field to match structure from AgentDiscoveryService
        return {
            "agent_id": agent_id,
            "metadata": {
                "name": name,
                "description": description,
                "version": version,
                "author": "remote",  # Mark as remote agent
                "category": "agent",
            },
            "model": model,
            "source": "remote",  # Mark as remote agent
            "source_file": str(md_file),
            "path": str(
                md_file
            ),  # Add 'path' field for deployment compatibility (1M-480)
            "file_path": str(md_file),  # Keep for backward compatibility
            "version": version,  # Include at root level for version comparison
            "routing": {"keywords": keywords, "paths": paths, "priority": priority},
        }

    def _get_agent_version(self, md_file: Path) -> str:
        """Get version (SHA-256 hash) from cache metadata.

        Looks for corresponding .meta.json file in cache directory that contains
        the SHA-256 hash of the agent content.

        Args:
            md_file: Path to Markdown agent file

        Returns:
            SHA-256 hash from metadata, or 'unknown' if not found

        Example metadata file:
            {
                "content_hash": "abc123...",
                "etag": "W/\"abc123\"",
                "last_modified": "2025-11-30T10:00:00Z"
            }
        """
        # Look for .meta.json file
        meta_file = md_file.with_suffix(".md.meta.json")

        if not meta_file.exists():
            self.logger.debug(f"No metadata file found for {md_file.name}")
            return "unknown"

        try:
            meta_data = json.loads(meta_file.read_text(encoding="utf-8"))
            content_hash = meta_data.get("content_hash", "unknown")
            self.logger.debug(
                f"Retrieved version {content_hash[:8]}... for {md_file.name}"
            )
            return content_hash
        except Exception as e:
            self.logger.warning(f"Failed to read metadata for {md_file.name}: {e}")
            return "unknown"

    def get_remote_agent_metadata(
        self, agent_name: str
    ) -> Optional[RemoteAgentMetadata]:
        """Get metadata for a specific remote agent.

        Args:
            agent_name: Name of the agent to retrieve

        Returns:
            RemoteAgentMetadata if found, None otherwise
        """
        for md_file in self.remote_agents_dir.glob("*.md"):
            agent_dict = self._parse_markdown_agent(md_file)
            if agent_dict and agent_dict["metadata"]["name"] == agent_name:
                return RemoteAgentMetadata(
                    name=agent_dict["metadata"]["name"],
                    description=agent_dict["metadata"]["description"],
                    model=agent_dict["model"],
                    routing_keywords=agent_dict["routing"]["keywords"],
                    routing_paths=agent_dict["routing"]["paths"],
                    routing_priority=agent_dict["routing"]["priority"],
                    source_file=Path(agent_dict["source_file"]),
                    version=agent_dict["version"],
                )
        return None

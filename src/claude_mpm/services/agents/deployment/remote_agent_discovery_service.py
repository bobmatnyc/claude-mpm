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

import yaml

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
    collection_id: Optional[str] = None  # Format: owner/repo-name
    source_path: Optional[str] = None  # Relative path in repo
    canonical_id: Optional[str] = None  # Format: collection_id:agent_id


class RemoteAgentDiscoveryService:
    """Discovers and converts remote Markdown agents to JSON format.

    Remote agents are discovered from the cache directory (~/.claude-mpm/cache/agents/)
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

    def __init__(self, agents_cache_dir: Path):
        """Initialize the remote agent discovery service.

        Args:
            agents_cache_dir: Directory containing cached agent Markdown files
        """
        self.agents_cache_dir = agents_cache_dir
        self.logger = get_logger(__name__)

    def _extract_collection_id_from_path(self, file_path: Path) -> Optional[str]:
        """Extract collection_id from repository path structure.

        Collection ID is derived from the repository path structure:
        ~/.claude-mpm/cache/agents/{owner}/{repo}/agents/...

        Args:
            file_path: Absolute path to agent Markdown file

        Returns:
            Collection ID in format "owner/repo-name" or None if not found

        Example:
            Input:  ~/.claude-mpm/cache/agents/bobmatnyc/claude-mpm-agents/agents/pm.md
            Output: "bobmatnyc/claude-mpm-agents"
        """
        try:
            # Find "agents" cache directory in the path (looking for .claude-mpm/cache/agents)
            path_parts = file_path.parts
            agents_cache_idx = -1

            for i, part in enumerate(path_parts):
                # Look for cache/agents pattern
                if part == "agents" and i > 0 and path_parts[i - 1] == "cache":
                    agents_cache_idx = i
                    break

            if agents_cache_idx == -1 or agents_cache_idx + 2 >= len(path_parts):
                self.logger.debug(
                    f"Could not extract collection_id from path: {file_path}"
                )
                return None

            # Extract owner and repo (next two parts after "cache/agents")
            owner = path_parts[agents_cache_idx + 1]
            repo = path_parts[agents_cache_idx + 2]

            collection_id = f"{owner}/{repo}"
            self.logger.debug(f"Extracted collection_id: {collection_id}")
            return collection_id

        except Exception as e:
            self.logger.warning(
                f"Failed to extract collection_id from {file_path}: {e}"
            )
            return None

    def _extract_source_path_from_file(self, file_path: Path) -> Optional[str]:
        """Extract relative source path within repository.

        Source path is relative to the repository root (not the agents subdirectory).

        Args:
            file_path: Absolute path to agent Markdown file

        Returns:
            Relative path from repo root, or None if not found

        Example:
            Input:  ~/.claude-mpm/cache/agents/bobmatnyc/claude-mpm-agents/agents/pm.md
            Output: "agents/pm.md"
        """
        try:
            # Find "agents" cache directory in the path
            path_parts = file_path.parts
            agents_cache_idx = -1

            for i, part in enumerate(path_parts):
                # Look for cache/agents pattern
                if part == "agents" and i > 0 and path_parts[i - 1] == "cache":
                    agents_cache_idx = i
                    break

            if agents_cache_idx == -1 or agents_cache_idx + 3 >= len(path_parts):
                return None

            # Path after owner/repo is the source path
            # cache/agents/{owner}/{repo}/{source_path}
            repo_root_idx = agents_cache_idx + 3
            source_parts = path_parts[repo_root_idx:]

            return "/".join(source_parts)

        except Exception as e:
            self.logger.warning(f"Failed to extract source_path from {file_path}: {e}")
            return None

    def _parse_yaml_frontmatter(self, content: str) -> Optional[Dict[str, Any]]:
        """Parse YAML frontmatter from Markdown content.

        Extracts YAML frontmatter delimited by --- markers at the start of the file.
        Uses a tolerant approach: attempts full YAML parsing first, falls back to
        simple key-value extraction for malformed YAML.

        Design Decision: Tolerant YAML Parsing

        Rationale: Some agent markdown files have malformed YAML (incorrect indentation
        in nested structures). Rather than failing completely, we:
        1. Try full YAML parsing first (handles well-formed YAML)
        2. Fall back to regex extraction for critical fields (agent_id, name, etc.)
        3. Log warnings but continue processing

        This ensures we can still extract agent_id even if complex nested structures
        (like template_changelog) have indentation issues.

        Args:
            content: Full Markdown file content

        Returns:
            Dictionary of parsed YAML frontmatter, or None if not found

        Example:
            Input:
                ---
                agent_id: python-engineer
                name: Python Engineer
                version: 2.3.0
                ---
                # Agent content...

            Output:
                {"agent_id": "python-engineer", "name": "Python Engineer", "version": "2.3.0"}
        """
        try:
            # Check if content starts with YAML frontmatter
            if not content.startswith("---"):
                self.logger.debug("No YAML frontmatter found (doesn't start with ---)")
                return None

            # Extract frontmatter content between --- markers
            frontmatter_match = re.match(r"^---\n(.*?)\n---\s*\n", content, re.DOTALL)
            if not frontmatter_match:
                self.logger.debug("No closing --- marker found for YAML frontmatter")
                return None

            yaml_content = frontmatter_match.group(1)

            # Try full YAML parsing first
            try:
                parsed = yaml.safe_load(yaml_content)
                if isinstance(parsed, dict):
                    return parsed
                self.logger.warning(
                    f"YAML frontmatter is not a dictionary: {type(parsed)}"
                )
            except yaml.YAMLError as e:
                # Malformed YAML (e.g., indentation errors) - fall back to regex extraction
                self.logger.debug(
                    f"Full YAML parse failed, using fallback extraction: {e}"
                )

                # Extract key fields using regex (tolerant of malformed nested structures)
                result = {}

                # Extract simple key-value pairs (no nested structures)
                simple_keys = [
                    "agent_id",
                    "name",
                    "description",
                    "version",
                    "model",
                    "agent_type",
                    "category",
                    "author",
                    "schema_version",
                ]

                for key in simple_keys:
                    # Match key: value on a line (not indented, so it's top-level)
                    pattern = rf"^{key}:\s*(.+?)$"
                    match = re.search(pattern, yaml_content, re.MULTILINE)
                    if match:
                        value = match.group(1).strip()
                        # Remove quotes if present
                        if value.startswith(("'", '"')) and value.endswith(("'", '"')):
                            value = value[1:-1]
                        result[key] = value

                if result:
                    self.logger.debug(
                        f"Extracted {len(result)} fields using fallback method"
                    )
                    return result
                return None

        except Exception as e:
            self.logger.warning(f"Unexpected error parsing frontmatter: {e}")
            return None

        return None

    def _generate_hierarchical_id(self, file_path: Path) -> str:
        """Generate hierarchical agent ID from file path.

        Converts file path relative to agents subdirectory into hierarchical ID.

        Design Decision: Path-based IDs for hierarchy preservation

        Rationale: Agent IDs must reflect directory hierarchy to enable:
        - Category-based filtering (engineer/backend/python-engineer)
        - Preset matching against AUTO-DEPLOY-INDEX.md
        - Multi-level organization without name collisions

        Supports both cache structures:
        1. Git repo: Calculate relative to /agents/ subdirectory
        2. Flattened cache: Calculate relative to agents_cache_dir directly

        Example (Git repo):
            Input:  /cache/bobmatnyc/claude-mpm-agents/agents/engineer/backend/python-engineer.md
            Root:   /cache/bobmatnyc/claude-mpm-agents/agents
            Output: engineer/backend/python-engineer

        Example (Flattened cache):
            Input:  /cache/agents/engineer/python-engineer.md
            Root:   /cache/agents
            Output: engineer/python-engineer

        Args:
            file_path: Absolute path to agent Markdown file

        Returns:
            Hierarchical agent ID with forward slashes
        """
        try:
            # Try git repo structure first: /agents/ subdirectory
            agents_dir = self.agents_cache_dir / "agents"
            if agents_dir.exists():
                try:
                    relative_path = file_path.relative_to(agents_dir)
                    return str(relative_path.with_suffix("")).replace("\\", "/")
                except ValueError:
                    pass  # Not under agents_dir, try flattened structure

            # Try flattened cache structure: calculate relative to agents_cache_dir
            try:
                relative_path = file_path.relative_to(self.agents_cache_dir)
                return str(relative_path.with_suffix("")).replace("\\", "/")
            except ValueError:
                pass  # Not under agents_cache_dir either

            # Fall back to filename
            self.logger.warning(
                f"File {file_path} not under expected directories, using filename"
            )
            return file_path.stem
        except Exception as e:
            self.logger.warning(
                f"Error generating hierarchical ID for {file_path}: {e}"
            )
            return file_path.stem

    def _detect_category_from_path(self, file_path: Path) -> str:
        """Detect category from file path hierarchy.

        Extracts category from directory structure. Category is the path
        from agents subdirectory to the file, excluding the filename.

        Supports both cache structures:
        1. Git repo: Calculate relative to /agents/ subdirectory
        2. Flattened cache: Calculate relative to agents_cache_dir directly

        Example (Git repo):
            Input:  /cache/bobmatnyc/claude-mpm-agents/agents/engineer/backend/python-engineer.md
            Root:   /cache/bobmatnyc/claude-mpm-agents/agents
            Output: engineer/backend

        Example (Flattened cache):
            Input:  /cache/agents/engineer/python-engineer.md
            Root:   /cache/agents
            Output: engineer

        Args:
            file_path: Absolute path to agent Markdown file

        Returns:
            Category path with forward slashes, or "universal" if in root
        """
        try:
            # Try git repo structure first: /agents/ subdirectory
            agents_dir = self.agents_cache_dir / "agents"
            if agents_dir.exists():
                try:
                    relative_path = file_path.relative_to(agents_dir)
                    parts = relative_path.parts[:-1]  # Exclude filename
                    return "/".join(parts) if parts else "universal"
                except ValueError:
                    pass  # Not under agents_dir, try flattened structure

            # Try flattened cache structure: calculate relative to agents_cache_dir
            try:
                relative_path = file_path.relative_to(self.agents_cache_dir)
                parts = relative_path.parts[:-1]  # Exclude filename
                return "/".join(parts) if parts else "universal"
            except ValueError:
                pass  # Not under agents_cache_dir either

            return "universal"
        except Exception:
            return "universal"

    def discover_remote_agents(self) -> List[Dict[str, Any]]:
        """Discover all remote agents from cache directory.

        Scans the remote agents directory for *.md files recursively and converts each
        to JSON template format. Skips files that can't be parsed.

        Supports two cache structures:
        1. Git repo path: {path}/agents/ - has /agents/ subdirectory
        2. Flattened cache: {path}/ - directly contains category directories

        Bug #4 Fix: Only scan /agents/ subdirectory when it exists to prevent
        README.md, CHANGELOG.md, etc. from being treated as agents.

        Returns:
            List of agent dictionaries in JSON template format

        Example:
            >>> service = RemoteAgentDiscoveryService(Path("~/.claude-mpm/cache/agents"))
            >>> agents = service.discover_remote_agents()
            >>> len(agents)
            5
            >>> agents[0]['name']
            'Security Scanner Agent'
        """
        agents = []

        if not self.agents_cache_dir.exists():
            self.logger.debug(
                f"Agents cache directory does not exist: {self.agents_cache_dir}"
            )
            return agents

        # Support four cache structures (PRIORITY ORDER):
        # 1. Built output: {path}/dist/agents/ - PREFERRED (built with BASE-AGENT composition)
        # 2. Git repo path: {path}/agents/ - source files (fallback)
        # 3. Owner/repo structure: {path}/{owner}/{repo}/agents/ - GitHub sync structure
        # 4. Flattened cache: {path}/ - directly contains category directories (legacy)

        # Priority 1: Check for dist/agents/ (built output with BASE-AGENT composition)
        dist_agents_dir = self.agents_cache_dir / "dist" / "agents"
        agents_dir = self.agents_cache_dir / "agents"

        if dist_agents_dir.exists():
            # PREFERRED: Use built agents from dist/agents/
            # These have BASE-AGENT.md files properly composed by build-agent.py
            self.logger.debug(f"Using built agents from dist: {dist_agents_dir}")
            scan_dir = dist_agents_dir
        elif agents_dir.exists():
            # FALLBACK: Git repo structure - scan /agents/ subdirectory (source files)
            # This path is used when dist/agents/ hasn't been built yet
            self.logger.debug(f"Using source agents (no dist/ found): {agents_dir}")
            scan_dir = agents_dir
        else:
            # Priority 3: Check for {owner}/{repo}/agents/ structure (GitHub sync)
            # e.g., ~/.claude-mpm/cache/agents/bobmatnyc/claude-mpm-agents/agents/
            owner_repo_agents_dir = None
            for owner_dir in self.agents_cache_dir.iterdir():
                if owner_dir.is_dir() and not owner_dir.name.startswith("."):
                    for repo_dir in owner_dir.iterdir():
                        if repo_dir.is_dir():
                            potential_agents = repo_dir / "agents"
                            if potential_agents.exists():
                                owner_repo_agents_dir = potential_agents
                                self.logger.debug(
                                    f"Using GitHub sync structure: {owner_repo_agents_dir}"
                                )
                                break
                    if owner_repo_agents_dir:
                        break

            if owner_repo_agents_dir:
                scan_dir = owner_repo_agents_dir
            else:
                # LEGACY: Flattened cache structure - scan root directly
                # Check if this looks like the flattened cache (has category subdirectories)
                category_dirs = [
                    "universal",
                    "engineer",
                    "ops",
                    "qa",
                    "security",
                    "documentation",
                ]
                has_categories = any(
                    (self.agents_cache_dir / cat).exists() for cat in category_dirs
                )

                if has_categories:
                    self.logger.debug(
                        f"Using flattened cache structure: {self.agents_cache_dir}"
                    )
                    scan_dir = self.agents_cache_dir
                else:
                    self.logger.warning(
                        f"No agent directories found. Checked: {dist_agents_dir}, {agents_dir}, "
                        f"owner/repo/agents/ structure, and category directories in {self.agents_cache_dir}. "
                        "Expected agents in /dist/agents/, /agents/, owner/repo/agents/, or category directories."
                    )
                    return agents

        # Find all Markdown files recursively
        md_files = list(scan_dir.rglob("*.md"))

        # Filter out non-agent files and git repository files
        excluded_files = {
            "README.md",
            "CHANGELOG.md",
            "CONTRIBUTING.md",
            "LICENSE.md",
            "BASE-AGENT.md",
            "SUMMARY.md",
            "IMPLEMENTATION-SUMMARY.md",
            "REFACTORING_REPORT.md",
            "REORGANIZATION-PLAN.md",
            "AUTO-DEPLOY-INDEX.md",
            "PHASE1_COMPLETE.md",
            "AGENTS.md",
            # Skill-related files (should not be treated as agents)
            "SKILL.md",
            "SKILLS.md",
            "skill-template.md",
        }
        md_files = [f for f in md_files if f.name not in excluded_files]

        # Filter out files from skills-related directories
        # Skills are not agents and should not be discovered here
        excluded_directory_patterns = {"references", "examples", "claude-mpm-skills"}
        md_files = [
            f
            for f in md_files
            if not any(excluded in f.parts for excluded in excluded_directory_patterns)
        ]

        # In flattened cache mode, also exclude files from git repository subdirectories
        # (files under directories that contain .git folder)
        if scan_dir == self.agents_cache_dir:
            filtered_files = []
            for f in md_files:
                # Check if this file is inside a git repository (has .git in path)
                # Git repos are at {agents_cache_dir}/{owner}/{repo}/.git
                path_parts = f.relative_to(self.agents_cache_dir).parts
                if len(path_parts) >= 2:
                    # Check if this looks like a git repo path (owner/repo)
                    potential_repo = (
                        self.agents_cache_dir / path_parts[0] / path_parts[1]
                    )
                    if (potential_repo / ".git").exists():
                        # This file is in a git repo, skip it (we'll handle git repos separately)
                        self.logger.debug(f"Skipping file in git repo: {f}")
                        continue
                filtered_files.append(f)
            md_files = filtered_files

        self.logger.debug(f"Found {len(md_files)} Markdown files in {scan_dir}")

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
            f"Discovered {len(agents)} remote agents from {self.agents_cache_dir.name}"
        )
        return agents

    def _parse_markdown_agent(self, md_file: Path) -> Optional[Dict[str, Any]]:
        """Parse Markdown agent file and convert to JSON template format.

        Expected Markdown format with YAML frontmatter:
        ```markdown
        ---
        agent_id: python-engineer
        name: Python Engineer
        version: 2.3.0
        model: sonnet
        ---
        # Agent Name

        Description paragraph (first paragraph after heading)

        ## Configuration
        - Model: sonnet
        - Priority: 100

        ## Routing
        - Keywords: keyword1, keyword2
        - Paths: /path1/, /path2/
        ```

        Agent ID Priority (Mismatch Fix):
        1. Use agent_id from YAML frontmatter if present (e.g., "python-engineer")
        2. Fall back to leaf filename if no YAML frontmatter (e.g., "python-engineer.md" -> "python-engineer")
        3. Store hierarchical path separately as category_path for categorization

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

        # MISMATCH FIX: Parse YAML frontmatter to extract agent_id
        frontmatter = self._parse_yaml_frontmatter(content)

        # MISMATCH FIX: Use agent_id from YAML frontmatter if present, otherwise fall back to filename
        if frontmatter and "agent_id" in frontmatter:
            agent_id = frontmatter["agent_id"]
            self.logger.debug(f"Using agent_id from YAML frontmatter: {agent_id}")
        else:
            # Fallback: Use leaf filename without extension
            agent_id = md_file.stem
            self.logger.debug(f"No agent_id in YAML, using filename: {agent_id}")

        # Store hierarchical path separately for categorization (not as primary ID)
        hierarchical_path = self._generate_hierarchical_id(md_file)

        # Extract agent name - prioritize frontmatter over markdown heading
        # Frontmatter is intentional metadata, headings may be arbitrary content
        if frontmatter and "name" in frontmatter:
            name = frontmatter["name"]
        else:
            # Fallback to first heading or filename
            name_match = re.search(r"^#\s+(.+?)$", content, re.MULTILINE)
            if name_match:
                name = name_match.group(1).strip()
            else:
                # Last resort: derive from filename
                name = md_file.stem.replace("-", " ").replace("_", " ").title()

        # Extract description - prioritize frontmatter over markdown content
        # Frontmatter is intentional metadata, paragraphs may be arbitrary content
        if frontmatter and "description" in frontmatter:
            description = frontmatter["description"]
        else:
            # Fallback to first paragraph after heading
            desc_match = re.search(
                r"^#.+?\n\n(.+?)(?:\n\n##|\Z)", content, re.DOTALL | re.MULTILINE
            )
            if desc_match:
                description = desc_match.group(1).strip()
            else:
                description = ""

        # Extract model from YAML frontmatter or Configuration section
        if frontmatter and "model" in frontmatter:
            model = frontmatter["model"]
        else:
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

        # Get version (SHA-256 hash) from cache metadata or YAML frontmatter
        if frontmatter and "version" in frontmatter:
            version = frontmatter["version"]
        else:
            version = self._get_agent_version(md_file)

        # Bug #1 fix: Detect category from directory path
        category = self._detect_category_from_path(md_file)

        # NEW: Extract collection metadata from path
        collection_id = self._extract_collection_id_from_path(md_file)
        source_path = self._extract_source_path_from_file(md_file)

        # NEW: Generate canonical_id (collection_id:agent_id)
        # Use leaf agent_id (not hierarchical path) for canonical_id
        if collection_id:
            canonical_id = f"{collection_id}:{agent_id}"
        else:
            # Fallback for legacy agents without collection
            canonical_id = f"legacy:{agent_id}"

        # Convert to JSON template format and return
        # IMPORTANT: Include 'path' field for compatibility with deployment validation (ticket 1M-480)
        # Git-sourced agents must have 'path' field to match structure from AgentDiscoveryService
        return {
            "agent_id": agent_id,  # MISMATCH FIX: Use leaf name from YAML, not hierarchical path
            "hierarchical_path": hierarchical_path,  # Store hierarchical path separately
            "canonical_id": canonical_id,  # NEW: Primary matching key (uses leaf agent_id)
            "collection_id": collection_id,  # NEW: Collection identifier
            "source_path": source_path,  # NEW: Path within repository
            "metadata": {
                "name": name,
                "description": description,
                "version": version,
                "author": "remote",  # Mark as remote agent
                "category": category,  # Use detected category from path
                "hierarchical_path": hierarchical_path,  # For categorization/filtering
                "collection_id": collection_id,  # NEW: Also in metadata
                "source_path": source_path,  # NEW: Also in metadata
                "canonical_id": canonical_id,  # NEW: Also in metadata
            },
            "model": model,
            "source": "remote",  # Mark as remote agent
            "source_file": str(md_file),
            "path": str(
                md_file
            ),  # Add 'path' field for deployment compatibility (1M-480)
            "file_path": str(md_file),  # Keep for backward compatibility
            "version": version,  # Include at root level for version comparison
            "category": category,  # Add category at root level for filtering
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
        # Bug #4 fix: Search in /agents/ subdirectory, not root directory
        agents_dir = self.agents_cache_dir / "agents"
        if not agents_dir.exists():
            return None

        for md_file in agents_dir.rglob("*.md"):
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
                    collection_id=agent_dict.get("collection_id"),
                    source_path=agent_dict.get("source_path"),
                    canonical_id=agent_dict.get("canonical_id"),
                )
        return None

    def get_agents_by_collection(self, collection_id: str) -> List[Dict[str, Any]]:
        """Get all agents belonging to a specific collection.

        Args:
            collection_id: Collection identifier in format "owner/repo-name"

        Returns:
            List of agent dictionaries from the specified collection

        Example:
            >>> service = RemoteAgentDiscoveryService(Path("~/.claude-mpm/cache/agents"))
            >>> agents = service.get_agents_by_collection("bobmatnyc/claude-mpm-agents")
            >>> len(agents)
            45
        """
        all_agents = self.discover_remote_agents()

        # Filter by collection_id
        collection_agents = [
            agent for agent in all_agents if agent.get("collection_id") == collection_id
        ]

        self.logger.info(
            f"Found {len(collection_agents)} agents in collection '{collection_id}'"
        )

        return collection_agents

    def list_collections(self) -> List[Dict[str, Any]]:
        """List all available collections with agent counts.

        Returns:
            List of collection info dictionaries with:
            - collection_id: Collection identifier
            - agent_count: Number of agents in collection
            - agents: List of agent IDs in collection

        Example:
            >>> service = RemoteAgentDiscoveryService(Path("~/.claude-mpm/cache/agents"))
            >>> collections = service.list_collections()
            >>> collections
            [
                {
                    "collection_id": "bobmatnyc/claude-mpm-agents",
                    "agent_count": 45,
                    "agents": ["pm", "engineer", "qa", ...]
                }
            ]
        """
        all_agents = self.discover_remote_agents()

        # Group by collection_id
        collections_map: Dict[str, List[str]] = {}

        for agent in all_agents:
            collection_id = agent.get("collection_id")
            if not collection_id:
                # Skip agents without collection (legacy)
                continue

            if collection_id not in collections_map:
                collections_map[collection_id] = []

            agent_id = agent.get("agent_id", agent.get("metadata", {}).get("name"))
            if agent_id:
                collections_map[collection_id].append(agent_id)

        # Convert to list format
        collections = [
            {
                "collection_id": coll_id,
                "agent_count": len(agent_ids),
                "agents": sorted(agent_ids),
            }
            for coll_id, agent_ids in collections_map.items()
        ]

        self.logger.info(f"Found {len(collections)} collections")

        return collections

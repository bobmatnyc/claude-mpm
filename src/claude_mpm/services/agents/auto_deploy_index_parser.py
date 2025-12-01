"""Auto-Deploy Index Parser for agent categorization and filtering.

WHY: This module parses AUTO-DEPLOY-INDEX.md to extract category mappings,
language/framework detection rules, and agent relationships. This enables
rich filtering and discovery of agents from configured sources.

DESIGN DECISION: Parse at runtime, cache results for performance

Rationale: AUTO-DEPLOY-INDEX.md is the single source of truth for agent
categorization. Parsing at runtime allows updates without code changes,
and caching ensures performance isn't impacted by repeated parsing.

Trade-offs:
- Performance: Cache provides ~O(1) lookups after initial parse (~50ms)
- Flexibility: Changes to AUTO-DEPLOY-INDEX.md don't require code deployment
- Complexity: Parser must handle variations in markdown format gracefully

Example:
    >>> parser = AutoDeployIndexParser(index_path)
    >>> categories = parser.get_categories()
    >>> ['universal', 'engineer/backend', 'engineer/frontend', ...]

    >>> agents = parser.get_agents_by_language('python')
    >>> {'core': ['engineer/backend/python-engineer', ...], 'optional': [...]}
"""

import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class AutoDeployIndexParser:
    """Parser for AUTO-DEPLOY-INDEX.md agent categorization.

    This service parses the AUTO-DEPLOY-INDEX.md markdown file to extract:
    - Universal agents (always deployed)
    - Language-specific detection rules and agents
    - Framework-specific detection rules and agents
    - Platform-specific detection rules and agents
    - Specialized detection rules and agents

    Design Decision: Regex-based Markdown Parsing

    Rationale: AUTO-DEPLOY-INDEX.md has consistent structure using markdown
    headers and bullet lists. Regex parsing is sufficient and avoids adding
    a markdown parsing library dependency.

    Trade-offs:
    - Simplicity: No external dependencies, straightforward patterns
    - Fragility: Changes to markdown structure may require parser updates
    - Performance: Regex is fast for this file size (~400 lines)

    Error Handling:
    - Graceful degradation: Returns empty results if file missing or malformed
    - Logging: Warns about parsing issues for debugging
    - No exceptions: Parser never crashes, always returns valid (possibly empty) data

    Caching:
    - Parse results cached in instance after first parse
    - Cache invalidated only by creating new instance
    - For long-running processes, recreate parser periodically
    """

    def __init__(self, index_file_path: Path):
        """Initialize parser with path to AUTO-DEPLOY-INDEX.md.

        Args:
            index_file_path: Path to AUTO-DEPLOY-INDEX.md file
        """
        self.index_file_path = Path(index_file_path)
        self._cache: Optional[Dict[str, Any]] = None
        self._content: Optional[str] = None

        logger.debug(f"AutoDeployIndexParser initialized with: {self.index_file_path}")

    def parse(self) -> Dict[str, Any]:
        """Parse AUTO-DEPLOY-INDEX.md and return structured data.

        Returns:
            Dictionary with structure:
            {
                "universal_agents": List[str],
                "language_mappings": Dict[str, Dict[str, List[str]]],  # lang -> {core, optional}
                "framework_mappings": Dict[str, List[str]],  # framework -> agents
                "platform_mappings": Dict[str, List[str]],  # platform -> agents
                "specialization_mappings": Dict[str, List[str]]  # spec -> agents
            }

        Example:
            >>> result = parser.parse()
            >>> result['universal_agents']
            ['universal/memory-manager', 'universal/research', ...]

            >>> result['language_mappings']['python']
            {
                'core': ['engineer/backend/python-engineer', 'qa/qa', ...],
                'optional': ['engineer/backend/data-engineer']
            }
        """
        if self._cache is not None:
            return self._cache

        # Load file content
        if not self.index_file_path.exists():
            logger.warning(f"AUTO-DEPLOY-INDEX.md not found at: {self.index_file_path}")
            return self._empty_result()

        try:
            self._content = self.index_file_path.read_text(encoding="utf-8")
        except Exception as e:
            logger.error(f"Failed to read AUTO-DEPLOY-INDEX.md: {e}")
            return self._empty_result()

        # Parse sections
        result = {
            "universal_agents": self._parse_universal_agents(),
            "language_mappings": self._parse_language_mappings(),
            "framework_mappings": self._parse_framework_mappings(),
            "platform_mappings": self._parse_platform_mappings(),
            "specialization_mappings": self._parse_specialization_mappings(),
        }

        self._cache = result
        logger.info(
            f"Parsed AUTO-DEPLOY-INDEX.md: "
            f"{len(result['universal_agents'])} universal agents, "
            f"{len(result['language_mappings'])} languages, "
            f"{len(result['framework_mappings'])} frameworks, "
            f"{len(result['platform_mappings'])} platforms"
        )

        return result

    def _empty_result(self) -> Dict[str, Any]:
        """Return empty result structure when parsing fails."""
        return {
            "universal_agents": [],
            "language_mappings": {},
            "framework_mappings": {},
            "platform_mappings": {},
            "specialization_mappings": {},
        }

    def _parse_universal_agents(self) -> List[str]:
        """Extract universal agents (always deployed).

        Looks for the "Universal Agents (Always Deployed)" section
        and extracts agent IDs from bullet points.

        Returns:
            List of agent IDs (e.g., ['universal/memory-manager', ...])
        """
        if not self._content:
            return []

        agents = []

        # Find Universal Agents section
        universal_section = re.search(
            r"## Universal Agents \(Always Deployed\)(.*?)(?=##|\Z)",
            self._content,
            re.DOTALL,
        )

        if not universal_section:
            return agents

        section_text = universal_section.group(1)

        # Extract agent IDs from backticks (e.g., `universal/memory-manager`)
        agent_pattern = r"`([a-z0-9\-/]+/[a-z0-9\-]+)`"
        matches = re.findall(agent_pattern, section_text)
        agents.extend(matches)

        logger.debug(f"Found {len(agents)} universal agents")
        return agents

    def _parse_language_mappings(self) -> Dict[str, Dict[str, List[str]]]:
        """Extract language-specific agent mappings.

        Parses sections like "### Python Projects" to extract:
        - Indicator files (for detection)
        - Auto-deploy agents (core)
        - Optional agents (conditional)

        Returns:
            Dict mapping language name to {core: [...], optional: [...]}
        """
        if not self._content:
            return {}

        mappings = {}

        # Find Project Type Detection section
        detection_section = re.search(
            r"## Project Type Detection(.*?)(?=## Platform-Specific Detection|\Z)",
            self._content,
            re.DOTALL,
        )

        if not detection_section:
            return mappings

        section_text = detection_section.group(1)

        # Find all language subsections (### Python Projects, ### JavaScript/TypeScript Projects, etc.)
        language_sections = re.finditer(
            r"### ([A-Za-z/]+) Projects\n+(.*?)(?=###|\Z)", section_text, re.DOTALL
        )

        for match in language_sections:
            lang_name = match.group(1).strip()
            lang_content = match.group(2)

            # Extract language key (lowercase, first word)
            lang_key = lang_name.split("/")[0].lower()

            # Extract auto-deploy agents
            core_agents = self._extract_agents_from_section(
                lang_content, "Auto-Deploy Agents"
            )

            # Extract optional agents
            optional_agents = self._extract_agents_from_section(
                lang_content, "Optional Agents"
            )

            if core_agents or optional_agents:
                mappings[lang_key] = {"core": core_agents, "optional": optional_agents}
                logger.debug(
                    f"Language '{lang_key}': {len(core_agents)} core, {len(optional_agents)} optional agents"
                )

        return mappings

    def _parse_framework_mappings(self) -> Dict[str, List[str]]:
        """Extract framework-specific agent mappings.

        Parses conditional deployment sections like "#### React Projects"
        within JavaScript/TypeScript sections.

        Returns:
            Dict mapping framework name to list of agent IDs
        """
        if not self._content:
            return {}

        mappings = {}

        # Find JavaScript/TypeScript section (contains framework mappings)
        js_section = re.search(
            r"### JavaScript/TypeScript Projects(.*?)(?=###|\Z)",
            self._content,
            re.DOTALL,
        )

        if not js_section:
            return mappings

        js_content = js_section.group(1)

        # Find framework subsections (#### React Projects, etc.)
        framework_sections = re.finditer(
            r"#### ([A-Za-z./]+)(?: Projects)?\n+(.*?)(?=####|\n\n###|\Z)",
            js_content,
            re.DOTALL,
        )

        for match in framework_sections:
            framework_name = match.group(1).strip()
            framework_content = match.group(2)

            # Extract framework key (lowercase)
            framework_key = framework_name.lower().replace(" ", "-")

            # Extract agent IDs from lines starting with `-`
            agents = self._extract_agent_ids(framework_content)

            if agents:
                mappings[framework_key] = agents
                logger.debug(f"Framework '{framework_key}': {len(agents)} agents")

        return mappings

    def _parse_platform_mappings(self) -> Dict[str, List[str]]:
        """Extract platform-specific agent mappings.

        Parses "## Platform-Specific Detection" section to extract
        deployment platform agents (Vercel, GCP, Docker, etc.).

        Returns:
            Dict mapping platform name to list of agent IDs
        """
        if not self._content:
            return {}

        mappings = {}

        # Find Platform-Specific Detection section
        platform_section = re.search(
            r"## Platform-Specific Detection(.*?)(?=##|\Z)", self._content, re.DOTALL
        )

        if not platform_section:
            return mappings

        section_text = platform_section.group(1)

        # Find platform subsections (### Vercel, ### Google Cloud Platform, etc.)
        platform_subsections = re.finditer(
            r"### ([A-Za-z0-9 ./()]+)\n+(.*?)(?=###|\Z)", section_text, re.DOTALL
        )

        for match in platform_subsections:
            platform_name = match.group(1).strip()
            platform_content = match.group(2)

            # Extract platform key (lowercase, simplified)
            platform_key = platform_name.lower().replace(" ", "-")

            # Special case mappings
            if "google cloud" in platform_key:
                platform_key = "gcp"
            elif "docker" in platform_key or "container" in platform_key:
                platform_key = "docker"

            # Extract agent IDs
            agents = self._extract_agent_ids(platform_content)

            if agents:
                mappings[platform_key] = agents
                logger.debug(f"Platform '{platform_key}': {len(agents)} agents")

        return mappings

    def _parse_specialization_mappings(self) -> Dict[str, List[str]]:
        """Extract specialization-specific agent mappings.

        Parses "## Specialized Detection" section to extract agents
        for data engineering, image processing, build optimization, etc.

        Returns:
            Dict mapping specialization name to list of agent IDs
        """
        if not self._content:
            return {}

        mappings = {}

        # Find Specialized Detection section
        specialized_section = re.search(
            r"## Specialized Detection(.*?)(?=##|\Z)", self._content, re.DOTALL
        )

        if not specialized_section:
            return mappings

        section_text = specialized_section.group(1)

        # Find specialization subsections
        spec_subsections = re.finditer(
            r"### ([A-Za-z0-9 ]+)\n+(.*?)(?=###|\Z)", section_text, re.DOTALL
        )

        for match in spec_subsections:
            spec_name = match.group(1).strip()
            spec_content = match.group(2)

            # Extract specialization key (lowercase, simplified)
            spec_key = spec_name.lower().replace(" ", "-")

            # Extract agent IDs
            agents = self._extract_agent_ids(spec_content)

            if agents:
                mappings[spec_key] = agents
                logger.debug(f"Specialization '{spec_key}': {len(agents)} agents")

        return mappings

    def _extract_agents_from_section(
        self, content: str, section_name: str
    ) -> List[str]:
        """Extract agent IDs from a named section within content.

        Args:
            content: Text content to search
            section_name: Name of section (e.g., "Auto-Deploy Agents")

        Returns:
            List of agent IDs found in section
        """
        # Find section by name
        section_match = re.search(
            rf"\*\*{re.escape(section_name)}\*\*:(.*?)(?=\n\*\*|\Z)", content, re.DOTALL
        )

        if not section_match:
            return []

        section_text = section_match.group(1)
        return self._extract_agent_ids(section_text)

    def _extract_agent_ids(self, content: str) -> List[str]:
        """Extract agent IDs from content (looks for backtick-wrapped IDs).

        Args:
            content: Text content to search

        Returns:
            List of agent IDs (e.g., ['engineer/backend/python-engineer', ...])
        """
        agent_pattern = r"`([a-z0-9\-]+/[a-z0-9\-/]+)`"
        return re.findall(agent_pattern, content)

    def get_categories(self) -> List[str]:
        """Get all available agent categories.

        Categories are derived from agent IDs by extracting the path prefix.
        For example: 'engineer/backend/python-engineer' -> 'engineer/backend'

        Returns:
            List of category strings

        Example:
            >>> parser.get_categories()
            ['universal', 'documentation', 'engineer/backend', 'engineer/frontend',
             'qa', 'ops/core', 'ops/platform', 'security']
        """
        data = self.parse()
        categories = set()

        # Extract categories from all agent IDs
        all_agents = []
        all_agents.extend(data["universal_agents"])

        for lang_data in data["language_mappings"].values():
            all_agents.extend(lang_data["core"])
            all_agents.extend(lang_data["optional"])

        for agents in data["framework_mappings"].values():
            all_agents.extend(agents)

        for agents in data["platform_mappings"].values():
            all_agents.extend(agents)

        for agents in data["specialization_mappings"].values():
            all_agents.extend(agents)

        # Extract category from each agent ID
        for agent_id in all_agents:
            # Extract everything before the last '/'
            if "/" in agent_id:
                parts = agent_id.rsplit("/", 1)
                categories.add(parts[0])

        return sorted(categories)

    def get_agents_by_category(self, category: str) -> List[str]:
        """Get all agents matching a specific category.

        Args:
            category: Category string (e.g., 'engineer/backend', 'qa')

        Returns:
            List of agent IDs matching category

        Example:
            >>> parser.get_agents_by_category('engineer/backend')
            ['engineer/backend/python-engineer', 'engineer/backend/rust-engineer', ...]
        """
        data = self.parse()
        matching_agents = []

        # Collect all agents
        all_agents = []
        all_agents.extend(data["universal_agents"])

        for lang_data in data["language_mappings"].values():
            all_agents.extend(lang_data["core"])
            all_agents.extend(lang_data["optional"])

        for agents in data["framework_mappings"].values():
            all_agents.extend(agents)

        for agents in data["platform_mappings"].values():
            all_agents.extend(agents)

        for agents in data["specialization_mappings"].values():
            all_agents.extend(agents)

        # Filter by category
        for agent_id in all_agents:
            if agent_id.startswith(category + "/") or agent_id == category:
                matching_agents.append(agent_id)

        return sorted(set(matching_agents))

    def get_agents_by_language(self, language: str) -> Dict[str, List[str]]:
        """Get core and optional agents for a specific language.

        Args:
            language: Language key (e.g., 'python', 'javascript', 'rust')

        Returns:
            Dictionary with 'core' and 'optional' agent lists

        Example:
            >>> parser.get_agents_by_language('python')
            {
                'core': ['engineer/backend/python-engineer', 'qa/qa', 'ops/core/ops', 'security/security'],
                'optional': ['engineer/backend/data-engineer']
            }
        """
        data = self.parse()
        return data["language_mappings"].get(
            language.lower(), {"core": [], "optional": []}
        )

    def get_agents_by_framework(self, framework: str) -> List[str]:
        """Get agents for a specific framework.

        Args:
            framework: Framework key (e.g., 'react', 'nextjs', 'svelte')

        Returns:
            List of agent IDs for framework

        Example:
            >>> parser.get_agents_by_framework('react')
            ['engineer/frontend/react-engineer', 'qa/web-qa']
        """
        data = self.parse()
        return data["framework_mappings"].get(framework.lower(), [])

    def get_agents_by_platform(self, platform: str) -> List[str]:
        """Get agents for a specific platform.

        Args:
            platform: Platform key (e.g., 'vercel', 'gcp', 'docker')

        Returns:
            List of agent IDs for platform

        Example:
            >>> parser.get_agents_by_platform('vercel')
            ['ops/platform/vercel-ops']
        """
        data = self.parse()
        return data["platform_mappings"].get(platform.lower(), [])

    def get_agents_by_specialization(self, specialization: str) -> List[str]:
        """Get agents for a specific specialization.

        Args:
            specialization: Specialization key (e.g., 'data-engineering', 'image-processing')

        Returns:
            List of agent IDs for specialization

        Example:
            >>> parser.get_agents_by_specialization('data-engineering')
            ['engineer/data/data-engineer']
        """
        data = self.parse()
        return data["specialization_mappings"].get(specialization.lower(), [])

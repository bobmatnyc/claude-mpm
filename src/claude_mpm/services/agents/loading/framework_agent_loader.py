"""
Framework Agent Loader Service

Implements agent profile loading logic based on directory hierarchy:
1. Project .claude-mpm (in project root): project agents - HIGHEST PRECEDENCE
2. User .claude-mpm (~/.claude-mpm): user agents - MEDIUM PRECEDENCE
3. Framework/System agents: built-in agents - LOWEST PRECEDENCE

Loading precedence: Project → User → System

This service integrates with the main agent_loader.py to provide
markdown-based agent profiles alongside JSON-based templates.
"""

import logging
from pathlib import Path
from typing import Any, Dict, Optional

from claude_mpm.agents.agent_loader import (
    AgentTier,
    list_agents_by_tier,
)
from claude_mpm.core.unified_paths import get_path_manager

logger = logging.getLogger(__name__)


class FrameworkAgentLoader:
    """Loads agent profiles from project, user, and system directories with proper precedence"""

    def __init__(self):
        self.project_agents_dir = None
        self.user_agents_dir = None
        self.system_agents_dir = None
        self._profile_cache = {}
        self._tier_mapping = {
            AgentTier.PROJECT: "project",
            AgentTier.USER: "user",
            AgentTier.SYSTEM: "system",
        }

    def initialize(self, framework_claude_md_path: Optional[str] = None):
        """
        Initialize loader with project, user, and system directory detection

        Args:
            framework_claude_md_path: Optional explicit path to agents/INSTRUCTIONS.md or CLAUDE.md
        """
        # Find project .claude-mpm directory (highest precedence)
        project_dir = self._find_project_directory()
        if project_dir:
            self.project_agents_dir = (
                project_dir / get_path_manager().CONFIG_DIR / "agents"
            )
            logger.info(f"Project agents directory: {self.project_agents_dir}")

        # Find user .claude-mpm directory (medium precedence)
        user_config_dir = get_path_manager().get_user_config_dir()
        if user_config_dir:
            self.user_agents_dir = user_config_dir / "agents"
            if self.user_agents_dir.exists():
                logger.info(f"User agents directory: {self.user_agents_dir}")
            else:
                self.user_agents_dir = None

        # Find system/framework agents directory (lowest precedence)
        if framework_claude_md_path:
            framework_dir = Path(framework_claude_md_path).parent.parent
        else:
            framework_dir = self._find_framework_directory()

        if framework_dir:
            self.system_agents_dir = (
                framework_dir / get_path_manager().CONFIG_DIR / "agents"
            )
            logger.info(f"System agents directory: {self.system_agents_dir}")

    def _find_framework_directory(self) -> Optional[Path]:
        """Find directory containing agents/INSTRUCTIONS.md (or legacy CLAUDE.md)"""
        # Check if we're running from a wheel installation
        try:
            import claude_pm

            package_path = Path(claude_pm.__file__).parent
            path_str = str(package_path.resolve())
            if "site-packages" in path_str or "dist-packages" in path_str:
                # For wheel installations, check data directory
                data_instructions = package_path / "data" / "agents" / "INSTRUCTIONS.md"
                data_claude = package_path / "data" / "agents" / "CLAUDE.md"
                if data_instructions.exists() or data_claude.exists():
                    return package_path / "data"
        except Exception:
            pass

        current = Path.cwd()

        # Check current directory and parents
        for path in [current, *list(current.parents)]:
            framework_instructions = path / "agents" / "INSTRUCTIONS.md"
            framework_claude = path / "agents" / "CLAUDE.md"  # Legacy
            if framework_instructions.exists() or framework_claude.exists():
                return path

        return None

    def _find_project_directory(self) -> Optional[Path]:
        """Find project directory containing .claude-mpm"""
        current = Path.cwd()

        # Check current directory and parents for .claude-mpm
        for path in [current, *list(current.parents)]:
            claude_pm_dir = path / get_path_manager().CONFIG_DIR
            if claude_pm_dir.exists():
                return path

        return None

    def load_agent_profile(self, agent_type: str) -> Optional[Dict[str, Any]]:
        """
        Load agent profile with precedence: Project → User → System

        This method now properly integrates with the main agent_loader.py
        tier system for consistent precedence handling.

        Args:
            agent_type: Agent type (Engineer, Documenter, QA, etc.)

        Returns:
            Agent profile dictionary or None if not found
        """
        # Check cache first
        cache_key = agent_type.lower()
        if cache_key in self._profile_cache:
            return self._profile_cache[cache_key]

        profile = None
        loaded_tier = None

        # 1. Try project agents first (highest precedence)
        if self.project_agents_dir:
            # Check both 'project' subdirectory and direct directory
            profile = self._load_profile_from_directory(
                self.project_agents_dir / "project", agent_type
            )
            if not profile:
                profile = self._load_profile_from_directory(
                    self.project_agents_dir, agent_type
                )
            if profile:
                loaded_tier = AgentTier.PROJECT

        # 2. Try user agents (medium precedence)
        if not profile and self.user_agents_dir:
            # Check both 'user' subdirectory and direct directory
            profile = self._load_profile_from_directory(
                self.user_agents_dir / "user", agent_type
            )
            if not profile:
                profile = self._load_profile_from_directory(
                    self.user_agents_dir, agent_type
                )
            if profile:
                loaded_tier = AgentTier.USER

        # 3. Try system agents (lowest precedence)
        if not profile and self.system_agents_dir:
            # Check subdirectories in order: trained → system
            for subdir in ["trained", "system"]:
                profile = self._load_profile_from_directory(
                    self.system_agents_dir / subdir, agent_type
                )
                if profile:
                    loaded_tier = AgentTier.SYSTEM
                    break

            # Also check root system directory
            if not profile:
                profile = self._load_profile_from_directory(
                    self.system_agents_dir, agent_type
                )
                if profile:
                    loaded_tier = AgentTier.SYSTEM

        # Add tier information to profile
        if profile and loaded_tier:
            profile["_tier"] = loaded_tier.value
            logger.debug(f"Loaded {agent_type} profile from {loaded_tier.value} tier")

        # Cache result
        if profile:
            self._profile_cache[cache_key] = profile

        return profile

    def _load_profile_from_directory(
        self, directory: Path, agent_type: str
    ) -> Optional[Dict[str, Any]]:
        """Load agent profile from specific directory"""
        if not directory.exists():
            return None

        profile_file = directory / f"{agent_type}.md"
        if not profile_file.exists():
            return None

        try:
            content = profile_file.read_text(encoding="utf-8")
            return self._parse_agent_profile(content, str(profile_file))
        except Exception as e:
            logger.error(f"Error loading profile {profile_file}: {e}")
            return None

    def _parse_agent_profile(self, content: str, source_path: str) -> Dict[str, Any]:
        """Parse agent profile markdown into structured data"""
        profile = {
            "source_path": source_path,
            "raw_content": content,
            "role": "",
            "capabilities": [],
            "context_preferences": {},
            "authority_scope": [],
            "quality_standards": [],
            "escalation_criteria": [],
            "integration_patterns": {},
        }

        lines = content.split("\n")
        current_section = None
        current_content = []

        for line in lines:
            line = line.strip()

            # Detect sections
            if line.startswith("## Role"):
                # Process previous section
                if current_section and current_content:
                    self._process_section(profile, current_section, current_content)
                current_section = "role"
                current_content = []
            elif line.startswith("## Capabilities"):
                if current_section and current_content:
                    self._process_section(profile, current_section, current_content)
                current_section = "capabilities"
                current_content = []
            elif line.startswith("## Context Preferences"):
                if current_section and current_content:
                    self._process_section(profile, current_section, current_content)
                current_section = "context_preferences"
                current_content = []
            elif line.startswith("## Authority Scope"):
                if current_section and current_content:
                    self._process_section(profile, current_section, current_content)
                current_section = "authority_scope"
                current_content = []
            elif line.startswith("## Quality Standards"):
                if current_section and current_content:
                    self._process_section(profile, current_section, current_content)
                current_section = "quality_standards"
                current_content = []
            elif line.startswith("## Escalation Criteria"):
                if current_section and current_content:
                    self._process_section(profile, current_section, current_content)
                current_section = "escalation_criteria"
                current_content = []
            elif line.startswith("## Integration Patterns"):
                if current_section and current_content:
                    self._process_section(profile, current_section, current_content)
                current_section = "integration_patterns"
                current_content = []
            elif line.startswith("#"):
                # Process previous section before starting new one
                if current_section and current_content:
                    self._process_section(profile, current_section, current_content)
                current_section = None
                current_content = []
            elif current_section and line:
                current_content.append(line)

        # Process final section
        if current_section and current_content:
            self._process_section(profile, current_section, current_content)

        return profile

    def _process_section(self, profile: Dict[str, Any], section: str, content: list):
        """Process section content into profile structure"""
        text = "\n".join(content).strip()

        if section == "role":
            profile["role"] = text
        elif section == "capabilities":
            # Extract bullet points
            capabilities = []
            for line in content:
                if line.startswith("- **") and "**:" in line:
                    cap = line.split("**:")[0].replace("- **", "").strip()
                    capabilities.append(cap)
            profile["capabilities"] = capabilities
        elif section == "context_preferences":
            # Extract Include/Exclude/Focus
            prefs = {}
            for line in content:
                if line.startswith("- **Include**:"):
                    prefs["include"] = line.replace("- **Include**:", "").strip()
                elif line.startswith("- **Exclude**:"):
                    prefs["exclude"] = line.replace("- **Exclude**:", "").strip()
                elif line.startswith("- **Focus**:"):
                    prefs["focus"] = line.replace("- **Focus**:", "").strip()
            profile["context_preferences"] = prefs
        elif section in ["authority_scope", "quality_standards", "escalation_criteria"]:
            # Extract bullet points
            items = []
            for line in content:
                if line.startswith("- **") and "**:" in line:
                    item = line.split("**:")[0].replace("- **", "").strip()
                    items.append(item)
            profile[section] = items
        elif section == "integration_patterns":
            # Extract With X: patterns
            patterns = {}
            for line in content:
                if line.startswith("- **With ") and "**:" in line:
                    agent = (
                        line.split("**:")[0]
                        .replace("- **With ", "")
                        .replace("**", "")
                        .strip()
                    )
                    desc = line.split("**:")[1].strip()
                    patterns[agent] = desc
            profile["integration_patterns"] = patterns

    def get_available_agents(self) -> Dict[str, list]:
        """Get list of available agents by tier"""
        agents = {"project": [], "user": [], "system": []}

        # Project agents
        if self.project_agents_dir:
            # Check both project subdirectory and root
            for search_dir in [
                self.project_agents_dir / "project",
                self.project_agents_dir,
            ]:
                if search_dir.exists():
                    md_files = [f.stem for f in search_dir.glob("*.md")]
                    agents["project"].extend(
                        [f for f in md_files if f not in agents["project"]]
                    )

        # User agents
        if self.user_agents_dir:
            # Check both user subdirectory and root
            for search_dir in [self.user_agents_dir / "user", self.user_agents_dir]:
                if search_dir.exists():
                    md_files = [f.stem for f in search_dir.glob("*.md")]
                    agents["user"].extend(
                        [f for f in md_files if f not in agents["user"]]
                    )

        # System agents
        if self.system_agents_dir:
            # Check subdirectories and root
            for subdir in ["trained", "system", ""]:
                search_dir = (
                    self.system_agents_dir / subdir
                    if subdir
                    else self.system_agents_dir
                )
                if search_dir.exists():
                    md_files = [f.stem for f in search_dir.glob("*.md")]
                    agents["system"].extend(
                        [f for f in md_files if f not in agents["system"]]
                    )

        # Also integrate with main agent_loader to get JSON-based agents
        try:
            json_agents = list_agents_by_tier()
            for tier, agent_list in json_agents.items():
                if tier in agents:
                    # Merge lists, avoiding duplicates
                    for agent in agent_list:
                        # Remove _agent suffix for consistency
                        agent_name = agent.replace("_agent", "")
                        if agent_name not in agents[tier]:
                            agents[tier].append(agent_name)
        except Exception as e:
            logger.debug(f"Could not integrate with agent_loader: {e}")

        return agents

    def generate_profile_loading_instruction(self, agent_type: str) -> str:
        """Generate instruction for subprocess to load its own profile"""
        profile = self.load_agent_profile(agent_type)

        if not profile:
            return f"""
**{agent_type} Agent**: No profile found. Operating with basic capabilities.

**Task Context**: Please proceed with the assigned task using standard practices.
"""

        instruction = f"""
**{agent_type} Agent Profile Loaded**

**Agent Identity**: {agent_type} Agent
**Profile Source**: {profile.get('source_path', 'Unknown')}
**Primary Role**: {profile.get('role', 'Not specified')}

**Core Capabilities**:
"""

        for capability in profile.get("capabilities", [])[:5]:  # Top 5 capabilities
            instruction += f"- **{capability}**: Primary capability area\n"

        instruction += f"""
**Context Preferences**:
- **Include**: {profile.get('context_preferences', {}).get('include', 'Not specified')}
- **Exclude**: {profile.get('context_preferences', {}).get('exclude', 'Not specified')}
- **Focus**: {profile.get('context_preferences', {}).get('focus', 'Not specified')}

**Authority Scope**:
"""

        for authority in profile.get("authority_scope", [])[:3]:  # Top 3 authorities
            instruction += f"- **{authority}**: Authorized operation area\n"

        instruction += f"""
**Quality Standards**: {len(profile.get('quality_standards', []))} standards defined
**Escalation Triggers**: {len(profile.get('escalation_criteria', []))} criteria defined
**Integration Partners**: {len(profile.get('integration_patterns', {}))} agent coordination patterns

Please operate according to your profile specifications and maintain quality standards.
"""

        return instruction.strip()

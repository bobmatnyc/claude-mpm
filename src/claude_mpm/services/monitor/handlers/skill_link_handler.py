"""Skill-to-Agent linking handler.

Builds a bidirectional index of skill-agent relationships from:
1. Agent frontmatter (skills: field in deployed .claude/agents/*.md)
2. Content body markers ([SKILL: ...] in agent markdown)
3. User-defined skill deployments (deployment index)

Provides the SkillToAgentMapper service and HTTP handler functions.
"""

import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import yaml

logger = logging.getLogger(__name__)


class SkillToAgentMapper:
    """In-memory bidirectional index of skill-agent relationships.

    Sources:
    - Frontmatter: skills field in agent .md files
    - Content markers: [SKILL: skill-name] patterns in agent .md content
    - User defined: deployment index tracking user-requested skills

    Thread-safe after initialization (read-only in-memory data).
    """

    def __init__(self) -> None:
        self._agent_to_skills: Dict[str, Dict[str, Set[str]]] = {}
        self._skill_to_agents: Dict[str, Dict[str, Any]] = {}
        self._deployed_skill_names: Set[str] = set()
        self._initialized = False

    def _build_index(self) -> None:
        """Build the bidirectional index from disk sources."""
        agents_dir = Path.cwd() / ".claude" / "agents"
        if not agents_dir.exists():
            logger.warning(f"Agents directory not found: {agents_dir}")
            self._initialized = True
            return

        agent_files = list(agents_dir.glob("*.md"))
        logger.debug(f"Scanning {len(agent_files)} agent files for skill links")

        # Load deployed skills set for is_deployed flag
        self._load_deployed_skills()

        for agent_file in agent_files:
            agent_name = agent_file.stem
            self._process_agent_file(agent_name, agent_file)

        self._initialized = True
        logger.info(
            f"Built skill-agent index: {len(self._agent_to_skills)} agents, "
            f"{len(self._skill_to_agents)} skills"
        )

    def _load_deployed_skills(self) -> None:
        """Load the set of currently deployed skill names."""
        try:
            from claude_mpm.services.skills_deployer import SkillsDeployerService

            svc = SkillsDeployerService()
            project_skills_dir = Path.cwd() / ".claude" / "skills"
            deployed = svc.check_deployed_skills(skills_dir=project_skills_dir)
            self._deployed_skill_names = {
                s.get("name", "") for s in deployed.get("skills", [])
            }
        except Exception as e:
            logger.warning(f"Could not load deployed skills: {e}")
            self._deployed_skill_names = set()

    def _process_agent_file(self, agent_name: str, agent_file: Path) -> None:
        """Extract skill references from a single agent file."""
        try:
            content = agent_file.read_text(encoding="utf-8")
        except Exception as e:
            logger.warning(f"Failed to read {agent_file}: {e}")
            return

        frontmatter_skills: Set[str] = set()
        content_marker_skills: Set[str] = set()

        # Parse frontmatter skills
        match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
        if match:
            try:
                fm = yaml.safe_load(match.group(1))
                if fm:
                    skills_field = fm.get("skills")
                    if isinstance(skills_field, list):
                        frontmatter_skills = {str(s) for s in skills_field}
                    elif isinstance(skills_field, dict):
                        req = skills_field.get("required") or []
                        opt = skills_field.get("optional") or []
                        if isinstance(req, list):
                            frontmatter_skills.update(str(s) for s in req)
                        if isinstance(opt, list):
                            frontmatter_skills.update(str(s) for s in opt)
            except yaml.YAMLError as e:
                logger.warning(f"YAML parse error in {agent_file}: {e}")

        # Parse content body markers: [SKILL: skill-name]
        pattern = r"\*{0,2}\[SKILL:\s*([a-zA-Z0-9_-]+)\s*\]\*{0,2}"
        matches = re.findall(pattern, content, re.IGNORECASE)
        content_marker_skills.update(matches)

        # Store in agent-to-skills index
        self._agent_to_skills[agent_name] = {
            "frontmatter": frontmatter_skills,
            "content_markers": content_marker_skills,
        }

        # Build reverse index (skill -> agents)
        all_skills = frontmatter_skills | content_marker_skills
        for skill_name in all_skills:
            if skill_name not in self._skill_to_agents:
                self._skill_to_agents[skill_name] = {
                    "agents": set(),
                    "sources": set(),
                }
            self._skill_to_agents[skill_name]["agents"].add(agent_name)
            if skill_name in frontmatter_skills:
                self._skill_to_agents[skill_name]["sources"].add("frontmatter")
            if skill_name in content_marker_skills:
                self._skill_to_agents[skill_name]["sources"].add("content_marker")

    def _is_skill_deployed(self, skill_name: str) -> bool:
        """Check if a skill name matches any deployed skill, with suffix matching.

        Agent frontmatter may reference skills by short name (e.g., "daisyui")
        while deployed directory names are path-normalized (e.g.,
        "toolchains-ui-components-daisyui"). This checks exact match first,
        then suffix-based matching using "-" as segment boundary.

        Args:
            skill_name: Skill name from agent frontmatter (short or long).

        Returns:
            True if the skill name matches any deployed skill.
        """
        if not skill_name:
            return False
        # Exact match
        if skill_name in self._deployed_skill_names:
            return True
        # Segment suffix match: deployed name ends with "-{skill_name}"
        suffix = f"-{skill_name}"
        return any(dn.endswith(suffix) for dn in self._deployed_skill_names)

    def _ensure_initialized(self) -> None:
        """Lazy-initialize the index on first access."""
        if not self._initialized:
            self._build_index()

    def get_all_links(self) -> Dict[str, Any]:
        """Get the full bidirectional mapping.

        Returns:
            Dict with 'by_agent' and 'by_skill' mappings.
        """
        self._ensure_initialized()

        by_agent: Dict[str, Any] = {}
        for agent_name, sources in self._agent_to_skills.items():
            fm = sorted(sources["frontmatter"])
            cm = sorted(sources["content_markers"])
            by_agent[agent_name] = {
                "frontmatter_skills": fm,
                "content_marker_skills": cm,
                "total": len(set(fm) | set(cm)),
            }

        by_skill: Dict[str, Any] = {}
        for skill_name, info in self._skill_to_agents.items():
            by_skill[skill_name] = {
                "agents": sorted(info["agents"]),
                "sources": sorted(info["sources"]),
                "is_deployed": self._is_skill_deployed(skill_name),
            }

        return {"by_agent": by_agent, "by_skill": by_skill}

    def get_agent_skills(self, agent_name: str) -> Optional[Dict[str, Any]]:
        """Get skills for a specific agent.

        Args:
            agent_name: Agent identifier (stem of .md file).

        Returns:
            Dict with categorized skills, or None if agent not found.
        """
        self._ensure_initialized()

        sources = self._agent_to_skills.get(agent_name)
        if sources is None:
            return None

        fm = sorted(sources["frontmatter"])
        cm = sorted(sources["content_markers"])
        all_skills = sorted(set(fm) | set(cm))

        # Categorize skills with deployment status
        skills_detail: List[Dict[str, Any]] = []
        for skill in all_skills:
            source = "frontmatter"
            if (
                skill in sources["content_markers"]
                and skill not in sources["frontmatter"]
            ):
                source = "content_marker"
            elif (
                skill in sources["content_markers"] and skill in sources["frontmatter"]
            ):
                source = "both"

            skills_detail.append(
                {
                    "name": skill,
                    "source": source,
                    "is_deployed": self._is_skill_deployed(skill),
                }
            )

        return {
            "agent_name": agent_name,
            "skills": skills_detail,
            "frontmatter_skills": fm,
            "content_marker_skills": cm,
            "total": len(all_skills),
        }

    def get_skill_agents(self, skill_name: str) -> Optional[Dict[str, Any]]:
        """Get agents that reference a specific skill.

        Args:
            skill_name: Skill identifier.

        Returns:
            Dict with agent list and metadata, or None if skill not found.
        """
        self._ensure_initialized()

        info = self._skill_to_agents.get(skill_name)
        if info is None:
            return None

        return {
            "skill_name": skill_name,
            "agents": sorted(info["agents"]),
            "sources": sorted(info["sources"]),
            "is_deployed": self._is_skill_deployed(skill_name),
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get aggregate statistics about skill-agent links.

        Returns:
            Dict with totals and averages.
        """
        self._ensure_initialized()

        total_agents = len(self._agent_to_skills)
        total_skills = len(self._skill_to_agents)

        if total_skills > 0:
            agents_per_skill = [
                len(info["agents"]) for info in self._skill_to_agents.values()
            ]
            avg_agents_per_skill = round(
                sum(agents_per_skill) / len(agents_per_skill), 2
            )
        else:
            avg_agents_per_skill = 0.0

        if total_agents > 0:
            skills_per_agent = []
            for sources in self._agent_to_skills.values():
                count = len(sources["frontmatter"] | sources["content_markers"])
                skills_per_agent.append(count)
            avg_skills_per_agent = round(
                sum(skills_per_agent) / len(skills_per_agent), 2
            )
        else:
            avg_skills_per_agent = 0.0

        deployed_count = sum(
            1
            for skill_name in self._skill_to_agents
            if self._is_skill_deployed(skill_name)
        )

        return {
            "total_agents": total_agents,
            "total_skills": total_skills,
            "deployed_skills": deployed_count,
            "avg_agents_per_skill": avg_agents_per_skill,
            "avg_skills_per_agent": avg_skills_per_agent,
        }

    def invalidate(self) -> None:
        """Invalidate the cache, forcing rebuild on next access."""
        self._agent_to_skills.clear()
        self._skill_to_agents.clear()
        self._deployed_skill_names.clear()
        self._initialized = False

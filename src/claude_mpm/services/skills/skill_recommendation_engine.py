"""Skill Recommendation Engine for Technology Stack Matching.

This service recommends skills based on detected project technology stack.
It scores skills by relevance, prioritizes core vs optional, and filters
out already deployed skills.

Author: Claude MPM Team
Created: 2026-02-12
"""

import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set

from claude_mpm.core.logging_utils import get_logger

from .project_inspector import TechnologyStack

logger = get_logger(__name__)


class SkillPriority(str, Enum):
    """Priority levels for skill recommendations."""

    CRITICAL = "critical"  # Core skills for detected stack
    HIGH = "high"  # Highly recommended
    MEDIUM = "medium"  # Nice-to-have
    LOW = "low"  # Optional/situational


@dataclass
class SkillRecommendation:
    """A skill recommendation with justification and score."""

    skill_name: str
    skill_id: str
    priority: SkillPriority
    relevance_score: float
    category: str
    toolchain: Optional[str]
    framework: Optional[str]
    tags: List[str]
    justification: str
    matched_technologies: List[str]

    def __str__(self) -> str:
        """String representation for display."""
        return (
            f"{self.skill_name} ({self.priority.value}, "
            f"score: {self.relevance_score:.2f}, "
            f"matched: {', '.join(self.matched_technologies)})"
        )


class SkillRecommendationEngine:
    """Recommends skills based on technology stack."""

    # Priority mappings for different technology combinations
    CRITICAL_PATTERNS = {
        # Core language skills
        "python": [
            "toolchains-python-core",
            "universal-testing-test-driven-development",
        ],
        "typescript": [
            "toolchains-typescript-core",
            "universal-testing-test-driven-development",
        ],
        "javascript": [
            "toolchains-javascript-core",
            "universal-testing-test-driven-development",
        ],
        "rust": ["toolchains-rust-core"],
        "go": ["toolchains-go-core"],
        # Framework-specific
        "fastapi": ["toolchains-python-frameworks-fastapi"],
        "django": ["toolchains-python-frameworks-django"],
        "flask": ["toolchains-python-frameworks-flask"],
        "react": ["toolchains-javascript-frameworks-react"],
        "nextjs": ["toolchains-nextjs-core"],
        "vue": ["toolchains-javascript-frameworks-vue"],
        # Testing frameworks
        "pytest": ["toolchains-python-testing-pytest"],
        "jest": ["toolchains-typescript-testing-jest"],
        "vitest": ["toolchains-typescript-testing-vitest"],
    }

    HIGH_PRIORITY_PATTERNS = {
        # Infrastructure
        "docker": ["universal-infrastructure-docker"],
        "kubernetes": ["universal-infrastructure-kubernetes"],
        # Databases
        "postgresql": ["toolchains-python-database-postgresql"],
        "mongodb": ["toolchains-python-database-mongodb"],
        # Security
        "jwt": ["universal-security-jwt"],
        # Debugging
        "debugging": ["universal-debugging-systematic-debugging"],
    }

    def __init__(self, manifest_path: Optional[Path] = None):
        """Initialize engine with skills manifest."""
        self.manifest_path = manifest_path or self._get_default_manifest_path()
        self.skills_manifest = self._load_manifest()

    def _get_default_manifest_path(self) -> Path:
        """Get default path to skills manifest."""
        # Try ~/.claude-mpm/cache/skills/system/manifest.json first
        cache_path = (
            Path.home()
            / ".claude-mpm"
            / "cache"
            / "skills"
            / "system"
            / "manifest.json"
        )
        if cache_path.exists():
            return cache_path

        # Fallback to direct claude-mpm-skills repo if in development
        dev_path = Path.home() / "Projects" / "claude-mpm-skills" / "manifest.json"
        if dev_path.exists():
            return dev_path

        logger.warning("Could not find skills manifest in standard locations")
        return cache_path  # Return cache path anyway, will fail later if doesn't exist

    def _load_manifest(self) -> Dict:
        """Load skills manifest from JSON file."""
        try:
            with open(self.manifest_path) as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(
                f"Failed to load skills manifest from {self.manifest_path}: {e}"
            )
            return {"skills": {}}

    def recommend_skills(
        self,
        tech_stack: TechnologyStack,
        already_deployed: Optional[Set[str]] = None,
        max_recommendations: int = 10,
    ) -> List[SkillRecommendation]:
        """Recommend skills based on technology stack.

        Args:
            tech_stack: Detected technology stack
            already_deployed: Set of already deployed skill IDs
            max_recommendations: Maximum number of recommendations to return

        Returns:
            List of skill recommendations, sorted by priority and relevance
        """
        if already_deployed is None:
            already_deployed = set()

        recommendations = []

        # Flatten all skills from manifest
        all_skills = []
        skills_by_category = self.skills_manifest.get("skills", {})

        for category, category_data in skills_by_category.items():
            if isinstance(category_data, list):
                # Simple list (e.g., universal, examples)
                all_skills.extend(category_data)
            elif isinstance(category_data, dict):
                # Nested dict (e.g., toolchains -> {python: [...], typescript: [...]})
                for subcategory_skills in category_data.values():
                    if isinstance(subcategory_skills, list):
                        all_skills.extend(subcategory_skills)

        logger.debug(f"Evaluating {len(all_skills)} skills against detected stack")

        # Score each skill
        for skill in all_skills:
            skill_id = skill.get("name", "")

            # Skip already deployed skills
            if skill_id in already_deployed:
                logger.debug(f"Skipping {skill_id}: already deployed")
                continue

            recommendation = self._evaluate_skill(skill, tech_stack)
            if recommendation:
                recommendations.append(recommendation)

        # Sort by priority (critical first) and then by relevance score
        priority_order = {
            SkillPriority.CRITICAL: 0,
            SkillPriority.HIGH: 1,
            SkillPriority.MEDIUM: 2,
            SkillPriority.LOW: 3,
        }

        recommendations.sort(
            key=lambda r: (priority_order[r.priority], -r.relevance_score)
        )

        # Limit to max recommendations
        return recommendations[:max_recommendations]

    def _evaluate_skill(
        self, skill: Dict, tech_stack: TechnologyStack
    ) -> Optional[SkillRecommendation]:
        """Evaluate if skill is relevant to technology stack."""
        skill_id = skill.get("name", "")
        skill_tags = set(skill.get("tags", []))
        toolchain = skill.get("toolchain")
        framework = skill.get("framework")
        category = skill.get("category", "unknown")

        # Calculate relevance score
        score = 0.0
        matched_tech = []

        # Match against languages
        for lang, confidence in tech_stack.languages.items():
            if lang in skill_tags or toolchain == lang:
                score += confidence * 0.4
                matched_tech.append(lang)

        # Match against frameworks
        for fw, confidence in tech_stack.frameworks.items():
            if fw in skill_tags or framework == fw:
                score += confidence * 0.5
                matched_tech.append(fw)

        # Match against tools
        for tool, confidence in tech_stack.tools.items():
            if tool in skill_tags:
                score += confidence * 0.3
                matched_tech.append(tool)

        # Match against databases
        for db, confidence in tech_stack.databases.items():
            if db in skill_tags:
                score += confidence * 0.3
                matched_tech.append(db)

        # Skip skills with no relevance
        if score == 0.0:
            return None

        # Determine priority
        priority = self._determine_priority(skill_id, tech_stack)

        # Boost score for higher priority
        if priority == SkillPriority.CRITICAL:
            score *= 1.5
        elif priority == SkillPriority.HIGH:
            score *= 1.2

        # Normalize score to 0-1 range
        score = min(score, 1.0)

        # Generate justification
        justification = self._generate_justification(
            matched_tech, tech_stack, toolchain, framework
        )

        return SkillRecommendation(
            skill_name=skill_id.replace("-", " ").title(),
            skill_id=skill_id,
            priority=priority,
            relevance_score=score,
            category=category,
            toolchain=toolchain,
            framework=framework,
            tags=skill.get("tags", []),
            justification=justification,
            matched_technologies=matched_tech,
        )

    def _determine_priority(
        self, skill_id: str, tech_stack: TechnologyStack
    ) -> SkillPriority:
        """Determine priority level for a skill based on technology stack."""
        all_tech = tech_stack.all_technologies()

        # Check critical patterns
        for tech in all_tech:
            tech_lower = tech.lower()
            if tech_lower in self.CRITICAL_PATTERNS:
                if skill_id in self.CRITICAL_PATTERNS[tech_lower]:
                    return SkillPriority.CRITICAL

        # Check high priority patterns
        for tech in all_tech:
            tech_lower = tech.lower()
            if tech_lower in self.HIGH_PRIORITY_PATTERNS:
                if skill_id in self.HIGH_PRIORITY_PATTERNS[tech_lower]:
                    return SkillPriority.HIGH

        # Universal skills are generally medium priority
        if "universal" in skill_id:
            return SkillPriority.MEDIUM

        # Framework-specific skills for detected frameworks are high
        for fw in tech_stack.frameworks:
            if fw.lower() in skill_id:
                return SkillPriority.HIGH

        # Language-specific skills are medium
        for lang in tech_stack.languages:
            if lang.lower() in skill_id:
                return SkillPriority.MEDIUM

        # Default to low
        return SkillPriority.LOW

    def _generate_justification(
        self,
        matched_tech: List[str],
        tech_stack: TechnologyStack,
        toolchain: Optional[str],
        framework: Optional[str],
    ) -> str:
        """Generate human-readable justification for recommendation."""
        if not matched_tech:
            return "General best practices skill"

        # Get confidence for matched technologies
        all_confidences = {
            **tech_stack.languages,
            **tech_stack.frameworks,
            **tech_stack.tools,
            **tech_stack.databases,
        }

        reasons = []
        for tech in matched_tech[:3]:  # Top 3 reasons
            confidence = all_confidences.get(tech, 0.0)
            conf_pct = int(confidence * 100)

            # Determine what was detected
            if tech in tech_stack.frameworks:
                reasons.append(
                    f"{tech.capitalize()} framework detected (confidence: {conf_pct}%)"
                )
            elif tech in tech_stack.languages:
                reasons.append(
                    f"{tech.capitalize()} language detected (confidence: {conf_pct}%)"
                )
            elif tech in tech_stack.tools:
                reasons.append(
                    f"{tech.capitalize()} tool detected (confidence: {conf_pct}%)"
                )
            elif tech in tech_stack.databases:
                reasons.append(
                    f"{tech.capitalize()} database detected (confidence: {conf_pct}%)"
                )
            else:
                reasons.append(
                    f"{tech.capitalize()} detected (confidence: {conf_pct}%)"
                )

        return "; ".join(reasons)

    def get_deployed_skills(self, project_dir: Optional[Path] = None) -> Set[str]:
        """Get set of already deployed skill IDs.

        Args:
            project_dir: Project directory to check (default: cwd)

        Returns:
            Set of deployed skill IDs
        """
        if project_dir is None:
            project_dir = Path.cwd()

        deployed = set()

        # Check project skills directory
        skills_dir = project_dir / ".claude-mpm" / "skills"
        if skills_dir.exists():
            for skill_path in skills_dir.iterdir():
                if skill_path.is_dir() and (skill_path / "SKILL.md").exists():
                    deployed.add(skill_path.name)

        logger.debug(f"Found {len(deployed)} already deployed skills")
        return deployed

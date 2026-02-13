"""Configuration validation service.

Performs comprehensive validation of the Claude MPM configuration,
checking agents, skills, sources, cross-references, and environment overrides.

Each issue includes:
1. What's wrong (message)
2. Where (config path)
3. What to do about it (suggestion)

Results are cached for 60 seconds.
"""

import logging
import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import yaml

logger = logging.getLogger(__name__)

CACHE_TTL_SECONDS = 60


@dataclass
class ValidationIssue:
    """A single validation finding."""

    severity: str  # "error", "warning", "info"
    category: str  # "agent", "skill", "source", "environment", "cross_reference"
    path: str  # config path e.g. "agents.python-engineer"
    message: str
    suggestion: str

    def to_dict(self) -> Dict[str, str]:
        return {
            "severity": self.severity,
            "category": self.category,
            "path": self.path,
            "message": self.message,
            "suggestion": self.suggestion,
        }


@dataclass
class ValidationResult:
    """Aggregated validation result."""

    valid: bool
    issues: List[ValidationIssue] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        errors = sum(1 for i in self.issues if i.severity == "error")
        warnings = sum(1 for i in self.issues if i.severity == "warning")
        info = sum(1 for i in self.issues if i.severity == "info")

        return {
            "valid": self.valid,
            "issues": [i.to_dict() for i in self.issues],
            "summary": {
                "errors": errors,
                "warnings": warnings,
                "info": info,
            },
        }


class ConfigValidationService:
    """Validates Claude MPM configuration for correctness and consistency.

    Checks:
    1. Deployed agents: proper config, referenced skills exist
    2. Agent sources: valid URLs, enabled sources accessible
    3. Skill sources: same URL/accessibility checks
    4. Deployed skills: referenced by at least one agent
    5. Environment variables: CLAUDE_MPM_ overrides
    6. Cross-references: skills referenced but not deployed
    """

    def __init__(self) -> None:
        self._cache: Optional[Dict[str, Any]] = None
        self._cache_time: float = 0.0

    def validate(self) -> ValidationResult:
        """Run all validation checks and return aggregated results."""
        issues: List[ValidationIssue] = []

        issues.extend(self._validate_deployed_agents())
        issues.extend(self._validate_agent_sources())
        issues.extend(self._validate_skill_sources())
        issues.extend(self._validate_deployed_skills())
        issues.extend(self._validate_env_overrides())
        issues.extend(self._validate_cross_references())

        has_errors = any(i.severity == "error" for i in issues)
        return ValidationResult(valid=not has_errors, issues=issues)

    def validate_cached(self) -> Dict[str, Any]:
        """Return cached validation results (60s TTL).

        Returns:
            Dict suitable for JSON response.
        """
        now = time.monotonic()
        if self._cache is not None and (now - self._cache_time) < CACHE_TTL_SECONDS:
            return self._cache

        result = self.validate()
        self._cache = {"success": True, **result.to_dict()}
        self._cache_time = now
        return self._cache

    def invalidate_cache(self) -> None:
        """Invalidate the validation cache (e.g., on config_updated event)."""
        self._cache = None
        self._cache_time = 0.0

    # --- Individual Validators ---

    def _validate_deployed_agents(self) -> List[ValidationIssue]:
        """Check deployed agents for proper configuration."""
        issues: List[ValidationIssue] = []
        agents_dir = Path.cwd() / ".claude" / "agents"

        if not agents_dir.exists():
            issues.append(
                ValidationIssue(
                    severity="warning",
                    category="agent",
                    path="agents",
                    message="No deployed agents directory found at .claude/agents/",
                    suggestion="Run 'claude-mpm init' to set up the project or deploy agents manually.",
                )
            )
            return issues

        agent_files = list(agents_dir.glob("*.md"))
        if not agent_files:
            issues.append(
                ValidationIssue(
                    severity="warning",
                    category="agent",
                    path="agents",
                    message="No agent files found in .claude/agents/",
                    suggestion="Deploy agents using 'claude-mpm agents deploy' or copy .md files to .claude/agents/.",
                )
            )
            return issues

        for agent_file in agent_files:
            agent_name = agent_file.stem
            config_path = f"agents.{agent_name}"

            try:
                content = agent_file.read_text(encoding="utf-8")
            except Exception as e:
                issues.append(
                    ValidationIssue(
                        severity="error",
                        category="agent",
                        path=config_path,
                        message=f"Cannot read agent file: {e}",
                        suggestion=f"Check file permissions on .claude/agents/{agent_name}.md",
                    )
                )
                continue

            # Check for valid frontmatter
            fm_match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
            if not fm_match:
                issues.append(
                    ValidationIssue(
                        severity="warning",
                        category="agent",
                        path=config_path,
                        message=f"Agent '{agent_name}' has no YAML frontmatter",
                        suggestion="Add YAML frontmatter with at least 'name' and 'description' fields.",
                    )
                )
                continue

            try:
                fm = yaml.safe_load(fm_match.group(1))
                if not fm:
                    issues.append(
                        ValidationIssue(
                            severity="warning",
                            category="agent",
                            path=config_path,
                            message=f"Agent '{agent_name}' has empty frontmatter",
                            suggestion="Add 'name' and 'description' fields to the frontmatter.",
                        )
                    )
                    continue
            except yaml.YAMLError as e:
                issues.append(
                    ValidationIssue(
                        severity="error",
                        category="agent",
                        path=config_path,
                        message=f"Agent '{agent_name}' has invalid YAML frontmatter: {e}",
                        suggestion="Fix the YAML syntax in the agent's frontmatter section.",
                    )
                )
                continue

            # Check required fields
            if not fm.get("name"):
                issues.append(
                    ValidationIssue(
                        severity="warning",
                        category="agent",
                        path=config_path,
                        message=f"Agent '{agent_name}' is missing 'name' field in frontmatter",
                        suggestion="Add a 'name' field to the agent's frontmatter.",
                    )
                )

            # Check if file is suspiciously small (might be truncated)
            if len(content.strip()) < 50:
                issues.append(
                    ValidationIssue(
                        severity="warning",
                        category="agent",
                        path=config_path,
                        message=f"Agent '{agent_name}' has very little content ({len(content)} chars)",
                        suggestion="This agent file may be incomplete. Check its content and re-deploy if needed.",
                    )
                )

        return issues

    def _validate_agent_sources(self) -> List[ValidationIssue]:
        """Validate agent source repository configurations."""
        issues: List[ValidationIssue] = []

        try:
            from claude_mpm.config.agent_sources import AgentSourceConfiguration

            config = AgentSourceConfiguration.load()
        except ImportError:
            return issues
        except Exception as e:
            issues.append(
                ValidationIssue(
                    severity="error",
                    category="source",
                    path="sources.agent",
                    message=f"Failed to load agent source configuration: {e}",
                    suggestion="Check .claude-mpm/configuration.yaml for valid agent source entries.",
                )
            )
            return issues

        for i, repo in enumerate(config.repositories):
            source_path = f"sources.agent[{i}]"
            url = getattr(repo, "url", "")
            enabled = getattr(repo, "enabled", True)

            if not url:
                issues.append(
                    ValidationIssue(
                        severity="error",
                        category="source",
                        path=source_path,
                        message="Agent source has an empty URL",
                        suggestion="Provide a valid Git repository URL for this agent source.",
                    )
                )
                continue

            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                issues.append(
                    ValidationIssue(
                        severity="error",
                        category="source",
                        path=source_path,
                        message=f"Agent source URL is invalid: {url}",
                        suggestion="Use a full URL like 'https://github.com/owner/repo'.",
                    )
                )

            if not enabled:
                issues.append(
                    ValidationIssue(
                        severity="info",
                        category="source",
                        path=source_path,
                        message=f"Agent source '{url}' is disabled",
                        suggestion="Enable this source in configuration if you want to use its agents.",
                    )
                )

        return issues

    def _validate_skill_sources(self) -> List[ValidationIssue]:
        """Validate skill source configurations."""
        issues: List[ValidationIssue] = []

        try:
            from claude_mpm.config.skill_sources import SkillSourceConfiguration

            config = SkillSourceConfiguration()
            sources = config.load()
        except ImportError:
            return issues
        except Exception as e:
            issues.append(
                ValidationIssue(
                    severity="error",
                    category="source",
                    path="sources.skill",
                    message=f"Failed to load skill source configuration: {e}",
                    suggestion="Check .claude-mpm/configuration.yaml for valid skill source entries.",
                )
            )
            return issues

        for i, source in enumerate(sources):
            source_path = f"sources.skill[{i}]"
            url = getattr(source, "url", "")
            enabled = getattr(source, "enabled", True)

            if not url:
                issues.append(
                    ValidationIssue(
                        severity="error",
                        category="source",
                        path=source_path,
                        message="Skill source has an empty URL",
                        suggestion="Provide a valid Git repository URL for this skill source.",
                    )
                )
                continue

            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                issues.append(
                    ValidationIssue(
                        severity="error",
                        category="source",
                        path=source_path,
                        message=f"Skill source URL is invalid: {url}",
                        suggestion="Use a full URL like 'https://github.com/owner/repo'.",
                    )
                )

            if not enabled:
                issues.append(
                    ValidationIssue(
                        severity="info",
                        category="source",
                        path=source_path,
                        message=f"Skill source '{url}' is disabled",
                        suggestion="Enable this source in configuration if you want to use its skills.",
                    )
                )

        return issues

    def _validate_deployed_skills(self) -> List[ValidationIssue]:
        """Check deployed skills for orphans (not referenced by any agent)."""
        issues: List[ValidationIssue] = []

        # Get deployed skills
        deployed_skills: List[str] = []
        try:
            from claude_mpm.services.skills_deployer import SkillsDeployerService

            svc = SkillsDeployerService()
            deployed = svc.check_deployed_skills()
            deployed_skills = [s.get("name", "") for s in deployed.get("skills", [])]
        except Exception as e:
            logger.warning(f"Could not check deployed skills: {e}")
            return issues

        if not deployed_skills:
            return issues

        # Get skills referenced by agents
        referenced_skills: set = set()
        agents_dir = Path.cwd() / ".claude" / "agents"
        if agents_dir.exists():
            try:
                from claude_mpm.services.skills.selective_skill_deployer import (
                    get_required_skills_from_agents,
                )

                referenced_skills = get_required_skills_from_agents(agents_dir)
            except ImportError:
                pass

        # Check for orphaned deployed skills
        for skill_name in deployed_skills:
            if skill_name and skill_name not in referenced_skills:
                issues.append(
                    ValidationIssue(
                        severity="info",
                        category="skill",
                        path=f"skills.{skill_name}",
                        message=f"Deployed skill '{skill_name}' is not referenced by any agent",
                        suggestion=(
                            f"This skill may be unused. Consider removing it with "
                            f"'claude-mpm skills remove {skill_name}' or add it to an agent's frontmatter."
                        ),
                    )
                )

        return issues

    def _validate_env_overrides(self) -> List[ValidationIssue]:
        """Flag CLAUDE_MPM_ environment variables that override config values."""
        issues: List[ValidationIssue] = []
        prefix = "CLAUDE_MPM_"

        for key, value in os.environ.items():
            if key.startswith(prefix):
                # Mask sensitive values
                display_value = value
                if any(
                    sensitive in key.lower()
                    for sensitive in ("token", "secret", "password", "key")
                ):
                    display_value = "***"

                issues.append(
                    ValidationIssue(
                        severity="info",
                        category="environment",
                        path=f"env.{key}",
                        message=f"Environment variable '{key}' overrides config (value: {display_value})",
                        suggestion=(
                            "This env var takes precedence over configuration.yaml. "
                            "Remove it from your shell environment if the override is unintended."
                        ),
                    )
                )

        return issues

    def _validate_cross_references(self) -> List[ValidationIssue]:
        """Check for skills referenced by agents but not deployed."""
        issues: List[ValidationIssue] = []

        agents_dir = Path.cwd() / ".claude" / "agents"
        if not agents_dir.exists():
            return issues

        # Get deployed skill names
        deployed_skill_names: set = set()
        try:
            from claude_mpm.services.skills_deployer import SkillsDeployerService

            svc = SkillsDeployerService()
            deployed = svc.check_deployed_skills()
            deployed_skill_names = {
                s.get("name", "") for s in deployed.get("skills", [])
            }
        except Exception:
            return issues

        # Scan each agent for referenced but not deployed skills
        for agent_file in agents_dir.glob("*.md"):
            agent_name = agent_file.stem
            try:
                content = agent_file.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue

            # Parse frontmatter skills
            agent_skills: set = set()
            fm_match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
            if fm_match:
                try:
                    fm = yaml.safe_load(fm_match.group(1))
                    if fm:
                        skills_field = fm.get("skills")
                        if isinstance(skills_field, list):
                            agent_skills = {str(s) for s in skills_field}
                        elif isinstance(skills_field, dict):
                            req = skills_field.get("required") or []
                            opt = skills_field.get("optional") or []
                            if isinstance(req, list):
                                agent_skills.update(str(s) for s in req)
                            if isinstance(opt, list):
                                agent_skills.update(str(s) for s in opt)
                except yaml.YAMLError:
                    pass

            # Check content markers
            pattern = r"\*{0,2}\[SKILL:\s*([a-zA-Z0-9_-]+)\s*\]\*{0,2}"
            matches = re.findall(pattern, content, re.IGNORECASE)
            agent_skills.update(matches)

            # Find missing skills
            for skill_name in agent_skills:
                if skill_name not in deployed_skill_names:
                    issues.append(
                        ValidationIssue(
                            severity="warning",
                            category="cross_reference",
                            path=f"agents.{agent_name}.skills.{skill_name}",
                            message=(
                                f"Agent '{agent_name}' references skill '{skill_name}' "
                                f"which is not deployed"
                            ),
                            suggestion=(
                                f"Deploy the '{skill_name}' skill with "
                                f"'claude-mpm skills deploy --skill {skill_name}' "
                                f"or remove the reference from the agent."
                            ),
                        )
                    )

        return issues

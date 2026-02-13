"""Post-deployment verification for agents, skills, and configuration.

Runs a series of checks after a deploy/undeploy/mode-switch operation
to confirm the expected state was achieved on disk.
"""

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from claude_mpm.core.logging_config import get_logger

logger = get_logger(__name__)

# Maximum reasonable agent file size (10 MB)
MAX_AGENT_FILE_SIZE = 10 * 1024 * 1024


@dataclass
class VerificationCheck:
    """A single verification check result."""

    check: str
    passed: bool
    path: str = ""
    details: str = ""


@dataclass
class VerificationResult:
    """Aggregated result of all verification checks."""

    passed: bool
    checks: List[VerificationCheck] = field(default_factory=list)
    timestamp: str = ""


class DeploymentVerifier:
    """Verifies deployment outcomes by inspecting the filesystem.

    All verification methods return a VerificationResult with individual
    checks that can be inspected by the caller.
    """

    def __init__(
        self,
        agents_dir: Optional[Path] = None,
        skills_dir: Optional[Path] = None,
    ) -> None:
        """Initialize DeploymentVerifier.

        Args:
            agents_dir: Default agents directory. Overridable per-call.
            skills_dir: Default skills directory. Overridable per-call.
        """
        self.default_agents_dir = agents_dir or (Path.cwd() / ".claude" / "agents")
        self.default_skills_dir = skills_dir or (Path.home() / ".claude" / "skills")

    def verify_agent_deployed(
        self, agent_name: str, agents_dir: Optional[Path] = None
    ) -> VerificationResult:
        """Verify an agent was deployed successfully.

        Checks:
            1. File exists at agents_dir/{agent_name}.md
            2. File has valid YAML frontmatter (--- delimited)
            3. Required fields present (name, description)
            4. File size non-zero and < 10 MB

        Args:
            agent_name: Name of the agent (without .md extension).
            agents_dir: Override agents directory.

        Returns:
            VerificationResult with individual check outcomes.
        """
        checks: List[VerificationCheck] = []
        base_dir = agents_dir or self.default_agents_dir
        agent_path = base_dir / f"{agent_name}.md"
        path_str = str(agent_path)

        # Check 1: File exists
        exists = agent_path.exists() and agent_path.is_file()
        checks.append(
            VerificationCheck(
                check="file_exists",
                passed=exists,
                path=path_str,
                details="" if exists else f"File not found: {path_str}",
            )
        )

        if not exists:
            return self._make_result(checks)

        # Check 2: File size
        size = agent_path.stat().st_size
        size_ok = 0 < size < MAX_AGENT_FILE_SIZE
        checks.append(
            VerificationCheck(
                check="file_size",
                passed=size_ok,
                path=path_str,
                details=f"Size: {size} bytes"
                if size_ok
                else (
                    "File is empty"
                    if size == 0
                    else f"File too large: {size} bytes (max {MAX_AGENT_FILE_SIZE})"
                ),
            )
        )

        if not size_ok:
            return self._make_result(checks)

        # Check 3: Valid YAML frontmatter
        content = agent_path.read_text(errors="replace")
        frontmatter = self._extract_frontmatter(content)
        has_frontmatter = frontmatter is not None
        checks.append(
            VerificationCheck(
                check="yaml_frontmatter",
                passed=has_frontmatter,
                path=path_str,
                details=""
                if has_frontmatter
                else "Missing or invalid YAML frontmatter (--- delimiters)",
            )
        )

        if not has_frontmatter:
            return self._make_result(checks)

        # Check 4: Required fields
        has_name = self._has_field(frontmatter, "name")
        has_description = self._has_field(frontmatter, "description")
        fields_ok = has_name and has_description
        missing = []
        if not has_name:
            missing.append("name")
        if not has_description:
            missing.append("description")

        checks.append(
            VerificationCheck(
                check="required_fields",
                passed=fields_ok,
                path=path_str,
                details=""
                if fields_ok
                else f"Missing required fields: {', '.join(missing)}",
            )
        )

        return self._make_result(checks)

    def verify_agent_undeployed(
        self, agent_name: str, agents_dir: Optional[Path] = None
    ) -> VerificationResult:
        """Verify an agent was undeployed (file removed).

        Args:
            agent_name: Name of the agent (without .md extension).
            agents_dir: Override agents directory.

        Returns:
            VerificationResult confirming the file no longer exists.
        """
        base_dir = agents_dir or self.default_agents_dir
        agent_path = base_dir / f"{agent_name}.md"
        path_str = str(agent_path)

        not_exists = not agent_path.exists()
        checks = [
            VerificationCheck(
                check="file_removed",
                passed=not_exists,
                path=path_str,
                details="" if not_exists else f"File still exists: {path_str}",
            )
        ]

        return self._make_result(checks)

    def verify_skill_deployed(
        self, skill_name: str, skills_dir: Optional[Path] = None
    ) -> VerificationResult:
        """Verify a skill was deployed successfully.

        Checks:
            1. Directory exists at skills_dir/{skill_name}/
            2. Directory contains at least one file

        Args:
            skill_name: Name (or deployment name) of the skill.
            skills_dir: Override skills directory.

        Returns:
            VerificationResult with individual check outcomes.
        """
        checks: List[VerificationCheck] = []
        base_dir = skills_dir or self.default_skills_dir
        skill_path = base_dir / skill_name
        path_str = str(skill_path)

        # Check 1: Directory exists
        exists = skill_path.exists() and skill_path.is_dir()
        checks.append(
            VerificationCheck(
                check="directory_exists",
                passed=exists,
                path=path_str,
                details="" if exists else f"Skill directory not found: {path_str}",
            )
        )

        if not exists:
            return self._make_result(checks)

        # Check 2: Contains files
        files = [f for f in skill_path.rglob("*") if f.is_file()]
        has_files = len(files) > 0
        checks.append(
            VerificationCheck(
                check="has_files",
                passed=has_files,
                path=path_str,
                details=f"Contains {len(files)} file(s)"
                if has_files
                else "Skill directory is empty",
            )
        )

        return self._make_result(checks)

    def verify_skill_undeployed(
        self, skill_name: str, skills_dir: Optional[Path] = None
    ) -> VerificationResult:
        """Verify a skill was undeployed (directory removed).

        Args:
            skill_name: Name of the skill.
            skills_dir: Override skills directory.

        Returns:
            VerificationResult confirming the directory no longer exists.
        """
        base_dir = skills_dir or self.default_skills_dir
        skill_path = base_dir / skill_name
        path_str = str(skill_path)

        not_exists = not skill_path.exists()
        checks = [
            VerificationCheck(
                check="directory_removed",
                passed=not_exists,
                path=path_str,
                details=""
                if not_exists
                else f"Skill directory still exists: {path_str}",
            )
        ]

        return self._make_result(checks)

    def verify_mode_switch(
        self, expected_mode: str, config_path: Optional[Path] = None
    ) -> VerificationResult:
        """Verify a mode switch was applied to the configuration file.

        Checks:
            1. Config file exists and is parseable
            2. Config reflects the expected mode

        Args:
            expected_mode: The mode that should now be active.
            config_path: Path to configuration.yaml. Defaults to project root.

        Returns:
            VerificationResult with check outcomes.
        """
        checks: List[VerificationCheck] = []
        cfg_path = config_path or (Path.cwd() / "configuration.yaml")
        path_str = str(cfg_path)

        # Check 1: File exists and is parseable
        if not cfg_path.exists():
            checks.append(
                VerificationCheck(
                    check="config_exists",
                    passed=False,
                    path=path_str,
                    details=f"Config file not found: {path_str}",
                )
            )
            return self._make_result(checks)

        try:
            import yaml

            content = cfg_path.read_text()
            data = yaml.safe_load(content)
            parseable = isinstance(data, dict)
        except Exception as e:
            parseable = False
            checks.append(
                VerificationCheck(
                    check="config_parseable",
                    passed=False,
                    path=path_str,
                    details=f"Failed to parse config: {e}",
                )
            )
            return self._make_result(checks)

        checks.append(
            VerificationCheck(
                check="config_parseable",
                passed=parseable,
                path=path_str,
            )
        )

        if not parseable:
            return self._make_result(checks)

        # Check 2: Mode matches expected
        current_mode = data.get("mode") or data.get("deployment_mode", "")
        mode_ok = current_mode == expected_mode
        checks.append(
            VerificationCheck(
                check="mode_matches",
                passed=mode_ok,
                path=path_str,
                details=""
                if mode_ok
                else f"Expected mode '{expected_mode}', found '{current_mode}'",
            )
        )

        return self._make_result(checks)

    @staticmethod
    def _make_result(checks: List[VerificationCheck]) -> VerificationResult:
        """Build a VerificationResult from a list of checks."""
        return VerificationResult(
            passed=all(c.passed for c in checks),
            checks=checks,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    @staticmethod
    def _extract_frontmatter(content: str) -> Optional[str]:
        """Extract YAML frontmatter from markdown content.

        Expects content starting with --- and ending with ---.

        Returns:
            The frontmatter string (between delimiters), or None if not found.
        """
        match = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
        return match.group(1) if match else None

    @staticmethod
    def _has_field(frontmatter: str, field_name: str) -> bool:
        """Check if a YAML field exists in frontmatter text.

        Simple line-based check (avoids needing a YAML parser for validation).
        """
        pattern = rf"^{re.escape(field_name)}\s*:"
        return bool(re.search(pattern, frontmatter, re.MULTILINE))

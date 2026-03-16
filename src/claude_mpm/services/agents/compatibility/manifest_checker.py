"""Manifest-based compatibility checker for agent repository manifests.

Implements the compatibility decision matrix for agents-manifest.yaml,
determining whether a CLI version can safely use an agent repository.
"""

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional

import yaml
from packaging.specifiers import InvalidSpecifier, SpecifierSet
from packaging.version import InvalidVersion, Version

logger = logging.getLogger(__name__)


class CompatibilityResult(Enum):
    """Outcome of a manifest compatibility check.

    Values:
        COMPATIBLE: CLI version satisfies all manifest constraints; proceed normally.
        INCOMPATIBLE_HARD: repo_format_version exceeds what this CLI understands;
            loading must be blocked to avoid misinterpretation.
        INCOMPATIBLE_WARN: CLI version is below the repo's min_cli_version; loading
            is allowed but a user-visible upgrade nudge is emitted.
        NO_MANIFEST: No manifest was found or it could not be parsed; fail-open and
            proceed without constraint enforcement.
    """

    COMPATIBLE = "compatible"
    INCOMPATIBLE_HARD = "incompatible_hard"
    INCOMPATIBLE_WARN = "incompatible_warn"
    NO_MANIFEST = "no_manifest"


@dataclass
class ManifestCheckResult:
    """Result of checking a manifest against the running CLI version.

    Attributes:
        status: The compatibility outcome.
        repo_format_version: The integer format version declared in the manifest,
            or None when the manifest was absent / unparseable.
        min_cli_version: The minimum CLI version string from the manifest,
            or None when absent.
        cli_version: The CLI version string that was tested.
        message: Human-readable explanation of the decision.
        migration_notes: Optional migration guidance from the manifest.
        deprecation_warnings: Optional list of deprecation warning strings parsed
            from the manifest. Informational only — never blocks compatibility.
    """

    status: CompatibilityResult
    repo_format_version: Optional[int]
    min_cli_version: Optional[str]
    cli_version: str
    message: str
    migration_notes: Optional[str] = None
    deprecation_warnings: Optional[List[str]] = field(default=None)


class ManifestChecker:
    """Checks a fetched manifest content string against the running CLI version.

    Constants:
        MAX_SUPPORTED_REPO_FORMAT: Highest repo_format_version this build can handle.
        MANIFEST_FILENAME: Expected filename inside a repository root.
        MAX_MANIFEST_SIZE: Maximum allowed manifest byte size (1 MiB guard).
        SUSPICIOUS_VERSION_THRESHOLD: Number of major versions ahead of the CLI that
            triggers a warning log (not a block) when seen in min_cli_version.

    Example::

        checker = ManifestChecker()
        result = checker.check(manifest_yaml_text, cli_version="5.9.70")
        if result.status == CompatibilityResult.INCOMPATIBLE_HARD:
            raise RuntimeError(result.message)
    """

    MAX_SUPPORTED_REPO_FORMAT: int = 1
    MANIFEST_FILENAME: str = "agents-manifest.yaml"
    MAX_MANIFEST_SIZE: int = 1_048_576  # 1 MiB
    SUSPICIOUS_VERSION_THRESHOLD: int = 2

    def check(
        self,
        manifest_content: Optional[str],
        cli_version: str,
    ) -> ManifestCheckResult:
        """Evaluate manifest compatibility against the given CLI version.

        Decision matrix (evaluated top-to-bottom, first match wins):

        1. content is None or empty → NO_MANIFEST (fail-open)
        2. content fails YAML parse  → NO_MANIFEST + warning log
        3. parsed value is not a dict → NO_MANIFEST + warning log
        4. repo_format_version > MAX_SUPPORTED_REPO_FORMAT → INCOMPATIBLE_HARD
        4a. compatibility_ranges present → checked before min_cli_version (if result,
            use it and skip to deprecation_warnings collection)
        5. cli_version < min_cli_version → INCOMPATIBLE_WARN
        6. max_cli_version exceeded → advisory log only, still COMPATIBLE
        7. everything else → COMPATIBLE

        Deprecation warnings (informational only, never block) are collected and
        attached to the result regardless of the outcome.

        Version comparison uses PEP 440 (packaging.version.Version).  If either
        version string is unparseable the rule is skipped and processing
        continues (fail-open).

        Args:
            manifest_content: Raw YAML text of the manifest, or None.
            cli_version: PEP 440 version string of the running CLI.

        Returns:
            ManifestCheckResult describing the outcome.
        """
        # Rule 1: absent or empty content
        if not manifest_content or not manifest_content.strip():
            logger.debug("No manifest content provided; treating as NO_MANIFEST.")
            return ManifestCheckResult(
                status=CompatibilityResult.NO_MANIFEST,
                repo_format_version=None,
                min_cli_version=None,
                cli_version=cli_version,
                message=(
                    "No agents-manifest.yaml found in this repository. "
                    "Proceeding without version constraints."
                ),
            )

        # Rule 2 / 3: parse YAML
        data = self._parse_manifest(manifest_content)
        if data is None:
            return ManifestCheckResult(
                status=CompatibilityResult.NO_MANIFEST,
                repo_format_version=None,
                min_cli_version=None,
                cli_version=cli_version,
                message=(
                    "agents-manifest.yaml could not be parsed. "
                    "Proceeding without version constraints."
                ),
            )

        repo_format_version = self._extract_repo_format_version(data)
        min_cli_version = self._extract_min_cli_version(data)
        max_cli_version: Optional[str] = data.get("max_cli_version")
        migration_notes: Optional[str] = data.get("migration_notes") or None

        # Collect deprecation warnings (informational; attached to all results).
        deprecation_warnings = self._check_deprecation_warnings(data, cli_version)

        # Rule 4: hard block on unsupported format version
        if repo_format_version > self.MAX_SUPPORTED_REPO_FORMAT:
            msg = (
                f"Repository manifest format version {repo_format_version} is not "
                f"supported by this CLI (max supported: {self.MAX_SUPPORTED_REPO_FORMAT}). "
                f"Please upgrade: pip install --upgrade claude-mpm"
            )
            if migration_notes:
                msg += f"\n\nMigration notes: {migration_notes}"
            logger.error(msg)
            return ManifestCheckResult(
                status=CompatibilityResult.INCOMPATIBLE_HARD,
                repo_format_version=repo_format_version,
                min_cli_version=min_cli_version,
                cli_version=cli_version,
                message=msg,
                migration_notes=migration_notes,
                deprecation_warnings=deprecation_warnings or None,
            )

        # Rule 4a: compatibility_ranges (takes precedence over min_cli_version check)
        compatibility_ranges = data.get("compatibility_ranges")
        if compatibility_ranges is not None:
            ranges_result = self._check_compatibility_ranges(
                compatibility_ranges,
                cli_version,
                repo_format_version=repo_format_version,
                min_cli_version=min_cli_version,
                migration_notes=migration_notes,
            )
            if ranges_result is not None:
                ranges_result.deprecation_warnings = deprecation_warnings or None
                return ranges_result
            # No range matched → fall through to existing min_cli_version logic.

        # Rule 5: soft warn when CLI is behind min_cli_version
        if min_cli_version != "0.0.0":
            comparison = self._compare_versions(cli_version, min_cli_version)
            if comparison == "less":
                # Check for suspiciously far-ahead min_cli_version
                self._warn_if_suspicious_min_version(cli_version, min_cli_version)
                msg = (
                    f"This agent repository requires claude-mpm >= {min_cli_version}, "
                    f"but you are running {cli_version}. "
                    f"Some agents may not work correctly. "
                    f"Upgrade recommended: pip install --upgrade claude-mpm"
                )
                if migration_notes:
                    msg += f"\n\nMigration notes: {migration_notes}"
                logger.warning(msg)
                return ManifestCheckResult(
                    status=CompatibilityResult.INCOMPATIBLE_WARN,
                    repo_format_version=repo_format_version,
                    min_cli_version=min_cli_version,
                    cli_version=cli_version,
                    message=msg,
                    migration_notes=migration_notes,
                    deprecation_warnings=deprecation_warnings or None,
                )

        # Rule 6: advisory-only max_cli_version check (never blocks)
        if max_cli_version:
            comparison = self._compare_versions(cli_version, max_cli_version)
            if comparison == "greater":
                logger.info(
                    "CLI version %s exceeds advisory max_cli_version %s for this "
                    "agent repository. The repository may not yet support all "
                    "features of your CLI version.",
                    cli_version,
                    max_cli_version,
                )

        # Rule 7: all checks passed
        return ManifestCheckResult(
            status=CompatibilityResult.COMPATIBLE,
            repo_format_version=repo_format_version,
            min_cli_version=min_cli_version,
            cli_version=cli_version,
            message=(
                f"Agent repository manifest is compatible with CLI version {cli_version}."
            ),
            migration_notes=migration_notes,
            deprecation_warnings=deprecation_warnings or None,
        )

    def check_agent(
        self,
        manifest_content: Optional[str],
        cli_version: str,
        agent_name: str,
    ) -> ManifestCheckResult:
        """Check compatibility for a specific agent with per-agent overrides.

        If the manifest contains per-agent overrides and the specified agent
        has a min_cli_version override, use that instead of the repo-level one.
        Agents not listed in overrides inherit the repo-level min_cli_version.

        Args:
            manifest_content: Raw YAML manifest text, or None.
            cli_version: CLI version string.
            agent_name: Name of the agent to check.

        Returns:
            ManifestCheckResult (may differ from repo-level result).
        """
        # First, do the repo-level check
        repo_result = self.check(manifest_content, cli_version)

        # If repo-level is hard stop or no manifest, use that
        if repo_result.status in (
            CompatibilityResult.INCOMPATIBLE_HARD,
            CompatibilityResult.NO_MANIFEST,
        ):
            return repo_result

        # Parse manifest to check for per-agent overrides
        if not manifest_content:
            return repo_result

        data = self._parse_manifest(manifest_content)
        if data is None:
            return repo_result

        agents_section = data.get("agents", {})
        if not isinstance(agents_section, dict):
            return repo_result

        agent_override = agents_section.get(agent_name)
        if not agent_override or not isinstance(agent_override, dict):
            return repo_result

        agent_min = agent_override.get("min_cli_version")
        if not agent_min:
            return repo_result

        # Compare with the agent-specific min version
        comparison = self._compare_versions(cli_version, str(agent_min))
        if comparison == "less":
            agent_notes = agent_override.get("notes", "")
            msg = (
                f"Agent '{agent_name}' requires claude-mpm >= {agent_min}, "
                f"but you are running {cli_version}. {agent_notes} "
                f"Upgrade recommended: pip install --upgrade claude-mpm"
            )
            return ManifestCheckResult(
                status=CompatibilityResult.INCOMPATIBLE_WARN,
                repo_format_version=repo_result.repo_format_version,
                min_cli_version=str(agent_min),
                cli_version=cli_version,
                message=msg,
                migration_notes=agent_notes or None,
            )

        return repo_result

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _check_compatibility_ranges(
        self,
        ranges: object,
        cli_version: str,
        *,
        repo_format_version: int,
        min_cli_version: str,
        migration_notes: Optional[str],
    ) -> Optional["ManifestCheckResult"]:
        """Check cli_version against a compatibility_ranges list.

        Iterates through the ranges list and returns the first match.

        - "full" status → COMPATIBLE
        - "degraded" status → INCOMPATIBLE_WARN (with notes)
        - No range matches → returns None (caller falls through to
          existing min_cli_version logic)
        - Non-list or empty list → returns None

        Invalid specifier strings in individual ranges are logged and
        skipped gracefully.

        Args:
            ranges: The raw value from the manifest (should be a list of dicts).
            cli_version: PEP 440 CLI version string.
            repo_format_version: Parsed repo format version (for result population).
            min_cli_version: Parsed min CLI version (for result population).
            migration_notes: Optional migration notes (for result population).

        Returns:
            ManifestCheckResult if a range matched, else None.
        """
        if not isinstance(ranges, list) or len(ranges) == 0:
            return None

        try:
            cli_ver = Version(cli_version)
        except InvalidVersion:
            logger.debug(
                "Cannot parse CLI version '%s' for range check; skipping ranges.",
                cli_version,
            )
            return None

        for entry in ranges:
            if not isinstance(entry, dict):
                logger.debug("Skipping non-dict compatibility_ranges entry: %r", entry)
                continue

            cli_specifier_str = entry.get("cli")
            if not cli_specifier_str or not isinstance(cli_specifier_str, str):
                logger.debug(
                    "Skipping compatibility_ranges entry with missing/invalid "
                    "'cli' field: %r",
                    entry,
                )
                continue

            # Normalise space-separated specifiers to the comma-separated form
            # required by packaging.specifiers.SpecifierSet.
            # Example: ">=5.8.0 <5.10.0" → ">=5.8.0,<5.10.0"
            normalised = re.sub(r"\s+(?=[><=!~^])", ",", cli_specifier_str.strip())

            try:
                spec = SpecifierSet(normalised)
            except InvalidSpecifier:
                logger.warning(
                    "Invalid specifier '%s' in compatibility_ranges; skipping.",
                    cli_specifier_str,
                )
                continue

            if cli_ver not in spec:
                continue

            # Matched — determine outcome from status field.
            status_str = str(entry.get("status", "full")).lower()
            notes: Optional[str] = entry.get("notes") or None

            if status_str == "full":
                return ManifestCheckResult(
                    status=CompatibilityResult.COMPATIBLE,
                    repo_format_version=repo_format_version,
                    min_cli_version=min_cli_version,
                    cli_version=cli_version,
                    message=(
                        f"Agent repository manifest is compatible with CLI version "
                        f"{cli_version} (matched compatibility range '{cli_specifier_str}')."
                    ),
                    migration_notes=migration_notes,
                )

            if status_str == "degraded":
                msg = (
                    f"CLI version {cli_version} is in a degraded compatibility range "
                    f"('{cli_specifier_str}'). "
                )
                if notes:
                    msg += notes + " "
                msg += "Upgrade recommended: pip install --upgrade claude-mpm"
                logger.warning(msg)
                return ManifestCheckResult(
                    status=CompatibilityResult.INCOMPATIBLE_WARN,
                    repo_format_version=repo_format_version,
                    min_cli_version=min_cli_version,
                    cli_version=cli_version,
                    message=msg,
                    migration_notes=notes or migration_notes,
                )

            # Unknown status — log and skip
            logger.debug(
                "Unrecognised compatibility_ranges status '%s'; skipping entry.",
                status_str,
            )

        # No range matched
        return None

    def _check_deprecation_warnings(
        self,
        data: dict,
        cli_version: str,
    ) -> List[str]:
        """Collect applicable deprecation warnings from the manifest.

        Deprecation warnings are informational only and never block compatibility.

        A warning is "applicable" if the feature has not yet been removed (i.e.
        removed_in > cli_version, using PEP 440 comparison).  If removed_in is
        absent or unparseable the warning is always included.

        Args:
            data: Parsed manifest dict.
            cli_version: Running CLI version string.

        Returns:
            List of warning message strings (may be empty).
        """
        raw_warnings = data.get("deprecation_warnings")
        if not isinstance(raw_warnings, list):
            return []

        result: List[str] = []
        for entry in raw_warnings:
            if not isinstance(entry, dict):
                logger.debug("Skipping non-dict deprecation_warnings entry: %r", entry)
                continue

            feature = entry.get("feature") or "<unknown feature>"
            removed_in = entry.get("removed_in")
            replacement = entry.get("replacement")
            deadline = entry.get("deadline")

            # Check if still applicable: warning applies when NOT yet removed.
            if removed_in:
                try:
                    if Version(cli_version) >= Version(str(removed_in)):
                        # Already removed in this CLI version — no longer a warning.
                        continue
                except InvalidVersion:
                    pass  # Unparseable → include warning.

            parts = [f"Deprecation warning: '{feature}' is deprecated."]
            if removed_in:
                parts.append(f"Scheduled removal in {removed_in}.")
            if replacement:
                parts.append(f"Use '{replacement}' instead.")
            if deadline:
                parts.append(f"Deadline: {deadline}.")

            result.append(" ".join(parts))

        return result

    def _parse_manifest(self, content: str) -> Optional[dict]:
        """Parse YAML manifest content and return a dict, or None on failure.

        Args:
            content: Raw YAML text.

        Returns:
            Parsed dict, or None if parsing failed or result is not a dict.
        """
        try:
            data = yaml.safe_load(content)
        except yaml.YAMLError as exc:
            logger.warning(
                "Failed to parse agents-manifest.yaml: %s. "
                "Treating as NO_MANIFEST (fail-open).",
                exc,
            )
            return None

        if not isinstance(data, dict):
            logger.warning(
                "agents-manifest.yaml parsed to %s instead of a mapping. "
                "Treating as NO_MANIFEST (fail-open).",
                type(data).__name__,
            )
            return None

        return data

    def _extract_repo_format_version(self, data: dict) -> int:
        """Extract repo_format_version from manifest data, defaulting to 1.

        Args:
            data: Parsed manifest dict.

        Returns:
            Integer format version (>= 1); 1 if absent, non-integer, or < 1.
        """
        raw = data.get("repo_format_version")
        if raw is None:
            return 1
        try:
            value = int(raw)
        except (TypeError, ValueError):
            logger.warning(
                "repo_format_version '%s' is not an integer; defaulting to 1.",
                raw,
            )
            return 1
        if value < 1:
            logger.warning(
                "repo_format_version %d is not a positive integer; defaulting to 1.",
                value,
            )
            return 1
        return value

    def _extract_min_cli_version(self, data: dict) -> str:
        """Extract min_cli_version from manifest data, defaulting to '0.0.0'.

        Validates that the value is a valid PEP 440 version string.
        Invalid values (e.g., 'v5.10.0', 'latest') default to '0.0.0'
        to avoid silently disabling the version check.

        Args:
            data: Parsed manifest dict.

        Returns:
            Version string; '0.0.0' if absent, blank, or not valid PEP 440.
        """
        raw = data.get("min_cli_version")
        if not raw or not str(raw).strip():
            return "0.0.0"
        version_str = str(raw).strip()
        try:
            Version(version_str)
            return version_str
        except InvalidVersion:
            logger.warning(
                "min_cli_version '%s' is not a valid PEP 440 version string; "
                "defaulting to '0.0.0'.",
                version_str,
            )
            return "0.0.0"

    def _compare_versions(self, version_a: str, version_b: str) -> str:
        """Compare two PEP 440 version strings.

        Returns 'less', 'equal', or 'greater'.  If either string is
        unparseable, returns 'equal' (fail-open — do not block).

        Args:
            version_a: First version string.
            version_b: Second version string.

        Returns:
            'less' if a < b, 'equal' if a == b, 'greater' if a > b,
            or 'equal' if either version is unparseable.
        """
        try:
            va = Version(version_a)
            vb = Version(version_b)
        except InvalidVersion:
            logger.debug(
                "Could not parse version strings '%s' or '%s'; "
                "treating as equal (fail-open).",
                version_a,
                version_b,
            )
            return "equal"

        if va < vb:
            return "less"
        if va > vb:
            return "greater"
        return "equal"

    def _warn_if_suspicious_min_version(
        self, cli_version: str, min_cli_version: str
    ) -> None:
        """Log a warning when min_cli_version is suspiciously far ahead of the CLI.

        A min_cli_version that is more than SUSPICIOUS_VERSION_THRESHOLD major
        versions ahead of the current CLI version may indicate a manifest error.
        This is advisory only and does not change the compatibility outcome.

        Args:
            cli_version: Running CLI version string.
            min_cli_version: min_cli_version from the manifest.
        """
        try:
            cli_major = Version(cli_version).major
            min_major = Version(min_cli_version).major
        except InvalidVersion:
            return

        if min_major - cli_major > self.SUSPICIOUS_VERSION_THRESHOLD:
            logger.warning(
                "min_cli_version '%s' in agents-manifest.yaml is more than %d "
                "major versions ahead of the running CLI ('%s'). "
                "This may indicate an error in the manifest.",
                min_cli_version,
                self.SUSPICIOUS_VERSION_THRESHOLD,
                cli_version,
            )

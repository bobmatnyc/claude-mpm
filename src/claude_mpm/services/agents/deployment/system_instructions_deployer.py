"""System instructions deployment for agent deployment service.

This module handles deployment of system instructions and framework files.
Extracted from AgentDeploymentService to reduce complexity and improve maintainability.

References
----------
SPEC-AGENTS-07~1 : docs/specs/agents.md#SPEC-AGENTS-07~1
"""

import logging
import re
import shutil
from pathlib import Path
from typing import Any

from claude_mpm.constants import BANNER_DEPLOYED
from claude_mpm.core.framework.loaders.workflow_constants import (
    MEMORY_SYSTEM_REFERENCE,
    WORKFLOW_SYSTEM_REFERENCE,
)

# Markers that uniquely identify content belonging to specific blocks.
# Used to detect stale override files that contain previously-deployed merged content.
# IMPORTANT: these must stay in sync with the actual headings in the source .md files
# under src/claude_mpm/agents/. The regression test
# tests/services/agents/deployment/test_block_markers_exist.py enforces this.
BLOCK_MARKERS: dict[str, list[str]] = {
    "PM_INSTRUCTIONS.md": ["## Identity"],
    "AGENT_DELEGATION.md": ["## When to Delegate to Each Agent"],
    "WORKFLOW.md": ["## Mandatory 5-Phase Sequence"],
    "MEMORY.md": ["## Memory System"],
}


class SystemInstructionsDeployer:
    """Handles deployment of system instructions and framework files."""

    def __init__(self, logger: logging.Logger, working_directory: Path):
        """Initialize the deployer with logger and working directory."""
        self.logger = logger
        self.working_directory = working_directory

    def _resolve_trusty_search_index(self) -> str:
        """Resolve the per-project trusty-search index name.

        WHAT: Returns the index id to substitute into the
              ``{{trusty_search_index}}`` placeholder in PM_INSTRUCTIONS.md.
              Precedence: (1) ``trusty_search.index_id`` from the project's
              ``.claude-mpm/configuration.yaml`` if set; (2) otherwise the
              working-directory basename (``self.working_directory.name``), which
              is the same default trusty-search itself uses for an unnamed index;
              (3) finally the sentinel ``"default"`` when neither yields a
              non-blank name (e.g. ``Path('/')`` has an empty ``.name``).
        WHY:  The index name was previously hardcoded to ``claude-mpm`` in
              PM_INSTRUCTIONS.md and composed verbatim into every project's
              deployed prompt, so agents in ANY project were told to search the
              ``claude-mpm`` index (GitHub issue #872). Resolving per-project
              points each project's PM at its own index. The ``"default"``
              sentinel guards against deploying an empty ``index:`` value when
              the working directory has no basename.

        Never raises: a missing/unreadable/malformed configuration.yaml falls
        back to the directory basename, and an empty basename falls back to the
        ``"default"`` sentinel.

        :spec: SPEC-AGENTS-07~1
        """
        config_path = self.working_directory / ".claude-mpm" / "configuration.yaml"
        try:
            import yaml

            with config_path.open(encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            if isinstance(data, dict):
                section = data.get("trusty_search", {})
                if isinstance(section, dict):
                    override = section.get("index_id")
                    if isinstance(override, str) and override.strip():
                        return override.strip()
        except Exception:
            # Missing file, unreadable, parse error, or yaml unavailable — fall
            # through to the directory-basename default below.
            pass
        # Final guard: an empty/whitespace basename (e.g. Path('/').name == '')
        # would render `index: ` with no value, so fall back to a safe sentinel.
        return self.working_directory.name.strip() or "default"

    def _apply_template_substitutions(self, text: str) -> str:
        """Substitute ``{{...}}`` placeholders in merged system-instruction text.

        WHAT: Replaces the ``{{trusty_search_index}}`` placeholder with the
              per-project index resolved by :meth:`_resolve_trusty_search_index`.
              Idempotent and a no-op when the placeholder is absent.
        WHY:  Centralizing the substitution over the fully merged content (rather
              than per-block) means the placeholder works regardless of which
              block contains it, and keeps the deployed
              ``PM_INSTRUCTIONS_DEPLOYED.md`` free of leaked ``{{...}}`` tokens.

        :spec: SPEC-AGENTS-07~1
        """
        if "{{trusty_search_index}}" not in text:
            return text
        # Resolve once into a local so adding more placeholders later does not
        # re-read configuration.yaml per placeholder.
        index = self._resolve_trusty_search_index()
        return text.replace("{{trusty_search_index}}", index)

    def _detect_stale_override(self, block_name: str, content: str) -> bool:
        """Detect if an override file contains content from other blocks.

        A project or user override is considered "stale" if it contains
        marker strings that belong to OTHER blocks. This typically happens
        when a previously-deployed merged file (PM_INSTRUCTIONS_DEPLOYED.md)
        is copied/renamed to serve as an override, causing content duplication.

        Args:
            block_name: The block this override is for (e.g. "PM_INSTRUCTIONS.md")
            content: The content of the override file

        Returns:
            True if the override appears to be a stale deployed file
        """
        other_markers: list[str] = []
        for other_block, markers in BLOCK_MARKERS.items():
            if other_block != block_name:
                other_markers.extend(markers)

        return any(marker in content for marker in other_markers)

    def _override_is_valid(self, block_name: str, content: str) -> bool:
        """Validate that an override actually contains the block's OWN content.

        Integrity guard (GitHub issue: PM-block override corruption).  A
        project/user override is only accepted if it contains the block's own
        positive marker (from ``BLOCK_MARKERS``) — proving it really is content
        for *this* block and not, e.g., a malformed launcher-cache artefact.

        The bug this prevented (now also addressed by renaming the cache to
        ``PM_INSTRUCTIONS_CACHE.md``): ``.claude-mpm/PM_INSTRUCTIONS.md``
        previously doubled as the launcher cache AND the project-override source.
        A malformed 19-byte cache (``"System instructions"``) was accepted as a
        valid PM override because ``_detect_stale_override`` only checks for
        *other* blocks' markers — and a 19-byte file contains none.  The merged
        DEPLOYED file then LOST the canonical ``## Identity`` / Prohibitions /
        Circuit-Breakers content.

        The positive-marker requirement alone defeats that artefact: the 19-byte
        cache has no ``## Identity`` heading, so it is rejected.  A length floor
        was deliberately NOT added — it would wrongly reject genuinely short but
        valid overrides (e.g. a 55-char custom PM that opens with ``## Identity``,
        per issue #757).  Validity is decided purely by the block's own marker.

        Args:
            block_name: The block this override is for.
            content: The override file content.

        Returns:
            True if the override is structurally valid for *block_name*.
        """
        own_markers = BLOCK_MARKERS.get(block_name, [])
        if not own_markers:
            # No marker entry for this block in BLOCK_MARKERS: the positive-marker
            # guard is a no-op and the override is accepted unconditionally.  Log
            # at DEBUG so that a future block added without a marker entry is
            # immediately discoverable in debug output without changing behaviour.
            self.logger.debug(
                "_override_is_valid: no BLOCK_MARKERS entry for %r — "
                "positive-marker check skipped (override accepted unconditionally). "
                "Add an entry to BLOCK_MARKERS to enable the integrity guard for this block.",
                block_name,
            )
            return True
        if not any(marker in content for marker in own_markers):
            return False
        return True

    def _resolve_workflow_block(self, agents_path: Path) -> str:
        """Resolve WORKFLOW.md with lazy-load logic identical to InstructionLoader.

        When no user or project override is present the full system-level
        WORKFLOW.md is NOT inlined; instead ``WORKFLOW_SYSTEM_REFERENCE`` is
        used.  This mirrors the behaviour of
        ``InstructionLoader.load_workflow_instructions()`` so the deployed
        ``PM_INSTRUCTIONS_DEPLOYED.md`` and the live assembled prompt stay in
        sync.

        If a project (``.claude-mpm/WORKFLOW.md``) or user-level
        (``~/.claude-mpm/WORKFLOW.md``) override exists the override content
        is inlined verbatim, exactly as ``_resolve_block`` does for all other
        blocks.

        Args:
            agents_path: Path to the system agents directory

        Returns:
            Resolved content string — either override content or the reference
            stub for the system default.
        """
        user_path = Path.home() / ".claude-mpm" / "WORKFLOW.md"
        project_path = self.working_directory / ".claude-mpm" / "WORKFLOW.md"

        has_override = False
        parts: list[str] = []

        if user_path.exists():
            try:
                user_content = user_path.read_text(encoding="utf-8")
            except (OSError, ValueError) as exc:
                self.logger.warning(
                    "Could not read ~/.claude-mpm/WORKFLOW.md (%s); "
                    "falling back to system default.",
                    exc,
                )
                user_content = None
            if user_content is not None:
                if self._detect_stale_override("WORKFLOW.md", user_content):
                    self.logger.warning(
                        "Stale override detected: ~/.claude-mpm/WORKFLOW.md contains "
                        "content from other blocks. Ignoring override and using "
                        "system default. Remove ~/.claude-mpm/WORKFLOW.md to suppress "
                        "this warning.",
                    )
                else:
                    parts.append(user_content)
                    has_override = True

        if project_path.exists():
            try:
                project_content = project_path.read_text(encoding="utf-8")
            except (OSError, ValueError) as exc:
                self.logger.warning(
                    "Could not read .claude-mpm/WORKFLOW.md (%s); "
                    "falling back to system default.",
                    exc,
                )
                project_content = None
            if project_content is not None:
                if self._detect_stale_override("WORKFLOW.md", project_content):
                    self.logger.warning(
                        "Stale override detected: .claude-mpm/WORKFLOW.md contains "
                        "content from other blocks. Ignoring override and using "
                        "system default. Remove .claude-mpm/WORKFLOW.md to suppress "
                        "this warning.",
                    )
                else:
                    parts.append(project_content)
                    has_override = True

        if has_override:
            # User/project override present — inline it verbatim (it is
            # project-specific and typically small, so the cost is justified).
            self.logger.debug(
                "Inlining WORKFLOW.md override in PM_INSTRUCTIONS_DEPLOYED.md"
            )
            return "\n\n".join(parts)

        # System default only: substitute the compact reference stub to avoid
        # re-injecting ~1,150 tokens of workflow detail into every PM prompt.
        self.logger.debug(
            "Using WORKFLOW_SYSTEM_REFERENCE in PM_INSTRUCTIONS_DEPLOYED.md "
            "(system default, no user/project override)"
        )
        return WORKFLOW_SYSTEM_REFERENCE

    def _resolve_memory_block(self, agents_path: Path) -> str:
        """Resolve MEMORY.md with lazy-load logic identical to InstructionLoader.

        WHAT: Checks user (~/.claude-mpm/MEMORY.md) and project (.claude-mpm/MEMORY.md)
              override paths in that order, validates each for stale cross-block content,
              and returns the concatenated override texts when any are present. When no
              override exists, returns MEMORY_SYSTEM_REFERENCE (a compact stub) instead
              of inlining the full ~1,776-token system MEMORY.md.
        WHY:  Mirrors _resolve_workflow_block and InstructionLoader.load_memory_instructions()
              so PM_INSTRUCTIONS_DEPLOYED.md stays in sync with the live assembled prompt.
              Using the reference stub for the system default avoids re-injecting the full
              memory detail on every session start while still letting users override it.

        Mirrors ``_resolve_workflow_block``: when no user or project override is
        present the full system-level MEMORY.md is NOT inlined; instead
        ``MEMORY_SYSTEM_REFERENCE`` is used.  This keeps the deployed
        ``PM_INSTRUCTIONS_DEPLOYED.md`` in sync with
        ``InstructionLoader.load_memory_instructions()`` and saves ~1,776 tokens
        per session.  Project/user overrides are inlined verbatim.

        Args:
            agents_path: Path to the system agents directory (unused for the
                system default — the stub replaces it — but kept for signature
                parity with the other block resolvers).

        Returns:
            Resolved content string — either override content or the reference
            stub for the system default.
        """
        user_path = Path.home() / ".claude-mpm" / "MEMORY.md"
        project_path = self.working_directory / ".claude-mpm" / "MEMORY.md"

        has_override = False
        parts: list[str] = []

        # NOTE: unlike _resolve_block for PM_INSTRUCTIONS.md, this intentionally
        # does NOT call _override_is_valid().  MEMORY.md is not a launcher-cache
        # collision target.  The launcher cache was previously at
        # .claude-mpm/PM_INSTRUCTIONS.md (same name as the PM block override
        # input), but has been renamed to PM_INSTRUCTIONS_CACHE.md to eliminate
        # the collision.  A stale old-path cache file lacks "## Identity" and is
        # rejected by _override_is_valid() on the PM_INSTRUCTIONS.md block;
        # MEMORY.md is unaffected.  Stale-override detection (cross-block marker
        # bleed) still applies here.
        if user_path.exists():
            try:
                user_content = user_path.read_text(encoding="utf-8")
            except (OSError, ValueError) as exc:
                self.logger.warning(
                    "Could not read ~/.claude-mpm/MEMORY.md (%s); "
                    "falling back to system default.",
                    exc,
                )
                user_content = None
            if user_content is not None:
                if self._detect_stale_override("MEMORY.md", user_content):
                    self.logger.warning(
                        "Stale override detected: ~/.claude-mpm/MEMORY.md contains "
                        "content from other blocks. Ignoring override and using "
                        "system default. Remove ~/.claude-mpm/MEMORY.md to suppress "
                        "this warning.",
                    )
                else:
                    parts.append(user_content)
                    has_override = True

        if project_path.exists():
            try:
                project_content = project_path.read_text(encoding="utf-8")
            except (OSError, ValueError) as exc:
                self.logger.warning(
                    "Could not read .claude-mpm/MEMORY.md (%s); "
                    "falling back to system default.",
                    exc,
                )
                project_content = None
            if project_content is not None:
                if self._detect_stale_override("MEMORY.md", project_content):
                    self.logger.warning(
                        "Stale override detected: .claude-mpm/MEMORY.md contains "
                        "content from other blocks. Ignoring override and using "
                        "system default. Remove .claude-mpm/MEMORY.md to suppress "
                        "this warning.",
                    )
                else:
                    parts.append(project_content)
                    has_override = True

        if has_override:
            self.logger.debug(
                "Inlining MEMORY.md override in PM_INSTRUCTIONS_DEPLOYED.md"
            )
            return "\n\n".join(parts)

        # System default only: substitute the compact reference stub to avoid
        # re-injecting ~1,776 tokens of memory detail into every PM prompt.
        self.logger.debug(
            "Using MEMORY_SYSTEM_REFERENCE in PM_INSTRUCTIONS_DEPLOYED.md "
            "(system default, no user/project override)"
        )
        return MEMORY_SYSTEM_REFERENCE

    def _resolve_block(self, block_name: str, agents_path: Path) -> str:
        """Resolve a block file with additive project+user override semantics.

        WHAT: Looks for user-level (~/.claude-mpm/<block_name>) and project-level
              (.claude-mpm/<block_name>) override files in that order. Each candidate
              is checked for stale cross-block content (_detect_stale_override) and for
              structural validity (_override_is_valid). Valid overrides are concatenated
              and returned; if no valid overrides are found, the system default from
              agents_path is returned instead.
        WHY:  The additive override model lets teams or individuals customise individual
              PM instruction blocks without forking the entire system default, while the
              stale-detection and positive-marker guards prevent corrupted launcher-cache
              artefacts (e.g. a 19-byte PM_INSTRUCTIONS_CACHE.md) from silently replacing
              canonical content.

        Priority: user_override + project_override (additive, together replace system)
        Fallback: system default from agents_path

        Args:
            block_name: Filename of the block (e.g. "PM_INSTRUCTIONS.md")
            agents_path: Path to the system agents directory

        Returns:
            Resolved content string (may be empty if no sources found)
        """
        system_path = agents_path / block_name
        user_path = Path.home() / ".claude-mpm" / block_name
        project_path = self.working_directory / ".claude-mpm" / block_name

        parts = []
        if user_path.exists():
            user_content = user_path.read_text(encoding="utf-8")
            if self._detect_stale_override(block_name, user_content):
                self.logger.warning(
                    "Stale override detected: ~/.claude-mpm/%s contains "
                    "content from other blocks. Ignoring override and using "
                    "system default. Remove ~/.claude-mpm/%s to suppress "
                    "this warning.",
                    block_name,
                    block_name,
                )
            elif not self._override_is_valid(block_name, user_content):
                self.logger.warning(
                    "Invalid override detected: ~/.claude-mpm/%s is missing its "
                    "own content marker. Ignoring override and "
                    "using system default. Remove ~/.claude-mpm/%s to suppress "
                    "this warning.",
                    block_name,
                    block_name,
                )
            else:
                parts.append(user_content)
        if project_path.exists():
            project_content = project_path.read_text(encoding="utf-8")
            if self._detect_stale_override(block_name, project_content):
                self.logger.warning(
                    "Stale override detected: .claude-mpm/%s contains "
                    "content from other blocks. Ignoring override and using "
                    "system default. Remove .claude-mpm/%s to suppress "
                    "this warning.",
                    block_name,
                    block_name,
                )
            elif not self._override_is_valid(block_name, project_content):
                self.logger.warning(
                    "Invalid override detected: .claude-mpm/%s is missing its "
                    "own content marker. Ignoring override and "
                    "using system default. Remove .claude-mpm/%s to suppress "
                    "this warning.",
                    block_name,
                    block_name,
                )
            else:
                parts.append(project_content)
        if not parts and system_path.exists():
            parts.append(system_path.read_text(encoding="utf-8"))
        return "\n\n".join(parts)

    def _source_pm_version_tag(self, agents_path: Path) -> str:
        """Return the ``PM_INSTRUCTIONS_VERSION`` comment from the source file.

        The deployed ``PM_INSTRUCTIONS_DEPLOYED.md`` is the runtime fast-path
        (PRIORITY 1 in ``InstructionLoader``). The loader decides whether to use
        it by comparing the version tag in the deployed file against the version
        tag in the *source* ``PM_INSTRUCTIONS.md``. If the deployed file lacks
        the tag, ``_extract_version`` returns 0 and the loader discards it as
        "stale" on every startup — even though it was freshly rebuilt.

        A user/project override of ``PM_INSTRUCTIONS.md`` typically will NOT
        carry the tag (users don't know to add it), so we cannot rely on the
        merged block content to supply it. Instead we always propagate the tag
        from the system source file, which correctly expresses "this file was
        compiled from framework version NNNN".

        Args:
            agents_path: Path to the system agents directory.

        Returns:
            The full ``<!-- PM_INSTRUCTIONS_VERSION: NNNN -->`` comment line
            (without trailing newline), or an empty string if the source file
            has no version tag.
        """
        source_path = agents_path / "PM_INSTRUCTIONS.md"
        if not source_path.exists():
            return ""
        match = re.search(
            r"PM_INSTRUCTIONS_VERSION:\s*(\d+)",
            source_path.read_text(encoding="utf-8"),
        )
        if not match:
            return ""
        return f"<!-- PM_INSTRUCTIONS_VERSION: {match.group(1)} -->"

    def deploy_system_instructions(
        self,
        target_dir: Path,
        force_rebuild: bool,
        results: dict[str, Any],
    ) -> None:
        """
        Deploy system instructions and framework files for PM framework.

        Deploys to project .claude-mpm directory as merged PM_INSTRUCTIONS_DEPLOYED.md
        containing PM_INSTRUCTIONS.md + AGENT_DELEGATION.md + WORKFLOW.md + MEMORY.md.

        Each block is resolved with additive override semantics:
          - user override (~/.claude-mpm/<BLOCK>.md) + project override
            (.claude-mpm/<BLOCK>.md) concatenated together replace the system default.
          - If neither override exists, the system default is used.

        Args:
            target_dir: Target directory for deployment (not used - always uses project .claude-mpm)
            force_rebuild: Force rebuild even if exists
            results: Results dictionary to update

        :spec: SPEC-AGENTS-07~1
        """
        # Initialize before try so it's always bound for deploy_templates below
        claude_mpm_dir = self.working_directory / ".claude-mpm"

        try:
            # Ensure .claude-mpm directory exists
            claude_mpm_dir.mkdir(parents=True, exist_ok=True)

            # Find the agents directory with framework files
            # Use centralized paths for consistency
            from claude_mpm.config.paths import paths

            agents_path = paths.agents_dir

            # Blocks that compose PM_INSTRUCTIONS_DEPLOYED.md (in order)
            BLOCKS = [
                "PM_INSTRUCTIONS.md",
                "AGENT_DELEGATION.md",
                "WORKFLOW.md",
                "MEMORY.md",
            ]

            # Resolve each block with additive override semantics.
            # WORKFLOW.md and MEMORY.md use dedicated helpers that apply the
            # same lazy-load logic as InstructionLoader: system-level →
            # reference stub; user/project override → inline verbatim.
            def _resolve(block: str) -> str:
                if block == "WORKFLOW.md":
                    return self._resolve_workflow_block(agents_path)
                if block == "MEMORY.md":
                    return self._resolve_memory_block(agents_path)
                return self._resolve_block(block, agents_path)

            merged_content = [_resolve(b) for b in BLOCKS]
            merged_content = [c for c in merged_content if c]  # drop empty blocks

            if not merged_content:
                self.logger.error("No framework files found to merge")
                results["errors"].append("No framework files found to merge")
                return

            # Collect all paths that should trigger a rebuild when modified
            watched_paths: list[Path] = []
            for block in BLOCKS:
                for base in [
                    agents_path,
                    Path.home() / ".claude-mpm",
                    self.working_directory / ".claude-mpm",
                ]:
                    p = base / block
                    if p.exists():
                        watched_paths.append(p)

            # Always (re)build PM_INSTRUCTIONS_DEPLOYED.md — freshness is ensured
            # by rebuilding on every startup, so no staleness check is needed.
            target_file = claude_mpm_dir / "PM_INSTRUCTIONS_DEPLOYED.md"
            file_existed = target_file.exists()

            # Prepend a stable, deterministic auto-generated banner so users
            # immediately know this file must not be hand-edited.  The banner
            # does not carry a timestamp so it never causes spurious diffs on
            # repeated rebuilds.  Uses the shared constant from constants.py to
            # ensure a single definition across all writers.
            #
            # Always propagate the source PM_INSTRUCTIONS_VERSION tag into the
            # written file, right after the banner. InstructionLoader uses this
            # tag (via _extract_version) to decide whether the deployed file is
            # current relative to source. A user/project override of
            # PM_INSTRUCTIONS.md usually omits the tag, which would make the
            # deployed file read as v0 and be discarded as "stale" on every
            # startup. Injecting the source tag keeps the fast-path usable.
            version_tag = self._source_pm_version_tag(agents_path)
            header = BANNER_DEPLOYED
            if version_tag:
                header = f"{header}{version_tag}\n\n"
            body = self._apply_template_substitutions("\n\n".join(merged_content))
            target_file.write_text(header + body)

            source_desc = ", ".join(str(p) for p in watched_paths if p.exists())
            deployment_info = {
                "name": "PM_INSTRUCTIONS_DEPLOYED.md",
                "template": source_desc,
                "target": str(target_file),
            }

            if file_existed:
                results["updated"].append(deployment_info)
                self.logger.info("Rebuilt PM_INSTRUCTIONS_DEPLOYED.md")
            else:
                results["deployed"].append(deployment_info)
                self.logger.info("Built PM_INSTRUCTIONS_DEPLOYED.md")

        except Exception as e:
            error_msg = f"Failed to deploy system instructions: {e}"
            self.logger.error(error_msg)
            results["errors"].append(error_msg)
            # Not raising AgentDeploymentError as this is non-critical

        # Also deploy templates directory
        self.deploy_templates(claude_mpm_dir, force_rebuild, results)

    def deploy_templates(
        self,
        claude_mpm_dir: Path,
        force_rebuild: bool,
        results: dict[str, Any],
    ) -> None:
        """
        Deploy PM instruction template files to project .claude-mpm/templates directory.

        Only deploys PM instruction templates (not agent definition templates).
        Templates are documentation files referenced in PM_INSTRUCTIONS.md that provide
        detailed protocols, examples, and matrices.

        Args:
            claude_mpm_dir: Project .claude-mpm directory
            force_rebuild: Force rebuild even if exists
            results: Results dictionary to update
        """
        try:
            # Find templates source directory
            from claude_mpm.config.paths import paths

            templates_source = paths.agents_dir / "templates"

            if not templates_source.exists():
                self.logger.warning(
                    f"Templates source directory not found: {templates_source}"
                )
                return

            # Create templates target directory
            templates_target = claude_mpm_dir / "templates"
            templates_target.mkdir(parents=True, exist_ok=True)

            # Only deploy PM instruction templates (not agent definitions)
            pm_templates = [
                "circuit-breakers.md",
                "context-management-examples.md",
                "git-file-tracking.md",
                "pm-examples.md",
                "pm-red-flags.md",
                "pr-workflow-examples.md",
                "research-gate-examples.md",
                "response-format.md",
                "structured-questions-examples.md",
                "ticket-completeness-examples.md",
                "ticketing-examples.md",
                "validation-templates.md",
            ]

            # Get template files that exist
            template_files = [
                templates_source / name
                for name in pm_templates
                if (templates_source / name).exists()
            ]

            deployed_count = 0
            skipped_count = 0
            missing_count = 0

            # Track missing templates
            for name in pm_templates:
                if not (templates_source / name).exists():
                    self.logger.warning(f"PM template not found: {name}")
                    missing_count += 1

            for template_file in template_files:
                target_file = templates_target / template_file.name

                # Check if update needed
                if (
                    not force_rebuild
                    and target_file.exists()
                    and target_file.stat().st_mtime >= template_file.stat().st_mtime
                ):
                    skipped_count += 1
                    continue

                # Copy template file
                shutil.copy2(template_file, target_file)
                deployed_count += 1

                self.logger.debug(f"Deployed PM template: {template_file.name}")

            # Track results
            if deployed_count > 0:
                template_info = {
                    "name": "templates/",
                    "count": deployed_count,
                    "target": str(templates_target),
                }
                results["deployed"].append(template_info)
                self.logger.info(
                    f"Deployed {deployed_count} PM template files to {templates_target}"
                )

            if skipped_count > 0:
                self.logger.debug(
                    f"Skipped {skipped_count} up-to-date PM template files"
                )

            if missing_count > 0:
                self.logger.warning(f"{missing_count} PM templates not found in source")

        except Exception as e:
            error_msg = f"Failed to deploy templates: {e}"
            self.logger.error(error_msg)
            results["errors"].append(error_msg)
            # Not raising exception as template deployment is non-critical

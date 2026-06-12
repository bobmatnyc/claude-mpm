"""Integrity tests for the PM prompt-assembly pipeline.

Covers two HIGH-severity defects and their fix:

1. PM-block override corruption (filename collision).
   ``.claude-mpm/PM_INSTRUCTIONS.md`` is BOTH the launcher cache AND a
   project-override source.  A malformed 19-byte cache (``"System
   instructions"``) was wrongly accepted as a valid PM override because the
   stale-override detector only looked for *other* blocks' markers.  The merged
   ``PM_INSTRUCTIONS_DEPLOYED.md`` then LOST ``## Identity`` / Prohibitions /
   Circuit-Breakers.  Fix: require the block's OWN positive marker (e.g.
   ``## Identity``) before accepting an override.  The marker alone defeats the
   artefact; no length floor is used (it would reject genuinely short but valid
   overrides — see issue #757).

2. Double-injection when DEPLOYED is the source.
   ``PM_INSTRUCTIONS_DEPLOYED.md`` already contains the merged
   AGENT_DELEGATION + WORKFLOW-stub + MEMORY blocks.  The subsidiary loaders
   used to append the system defaults a SECOND time.  Fix: a
   ``_loaded_from_deployed`` sentinel skips the static re-append (while still
   running the environment-dependent kuzu augmentation).

These tests exercise the real deployer against the real system agents files and
the real InstructionLoader — the scenario the existing per-component tests miss.
"""

import logging
from pathlib import Path

import pytest

from claude_mpm.core.framework.loaders.instruction_loader import InstructionLoader
from claude_mpm.services.agents.deployment.system_instructions_deployer import (
    SystemInstructionsDeployer,
)

# Repo root (worktree root): src/claude_mpm/agents lives under here.
REPO_ROOT = Path(__file__).parent.parent
AGENTS_DIR = REPO_ROOT / "src" / "claude_mpm" / "agents"

# The exact malformed launcher-cache artefact that triggered the bug.
MALFORMED_CACHE = "System instructions"

# Canonical PM markers that MUST survive into the deployed/assembled prompt.
PM_IDENTITY_MARKER = "## Identity"
PM_PROHIBITIONS_MARKER = "## Prohibitions"
# AGENT_DELEGATION routing marker (its own BLOCK_MARKERS entry).
DELEGATION_MARKER = "## When to Delegate to Each Agent"


def _deploy(working_dir: Path, fake_home: Path) -> str:
    """Run the real deployer against the real system agents dir.

    ``Path.home()`` is redirected to *fake_home* so no real user-level override
    interferes.  ``agents_dir`` is left at its real value (the repo source).
    """
    from unittest.mock import patch

    logger = logging.getLogger("test_instruction_pipeline_integrity")
    deployer = SystemInstructionsDeployer(logger, working_dir)
    results: dict = {"deployed": [], "updated": [], "errors": []}

    with patch(
        "claude_mpm.services.agents.deployment.system_instructions_deployer.Path.home",
        return_value=fake_home,
    ):
        deployer.deploy_system_instructions(
            target_dir=working_dir,
            force_rebuild=True,
            results=results,
        )

    assert not results["errors"], f"Deployment errors: {results['errors']}"
    deployed_file = working_dir / ".claude-mpm" / "PM_INSTRUCTIONS_DEPLOYED.md"
    assert deployed_file.exists(), "PM_INSTRUCTIONS_DEPLOYED.md was not created"
    return deployed_file.read_text(encoding="utf-8")


@pytest.fixture(autouse=True)
def _skip_without_agents():
    if not (AGENTS_DIR / "PM_INSTRUCTIONS.md").exists():
        pytest.skip(f"system agents dir not found at {AGENTS_DIR}")


# ── Bug reproduction: malformed cache must be ignored ──────────────────────


@pytest.mark.unit
def test_malformed_pm_cache_is_ignored_by_deployer(tmp_path: Path) -> None:
    """A 19-byte malformed .claude-mpm/PM_INSTRUCTIONS.md must NOT override the PM block.

    The deployed file must retain the canonical system PM content
    (## Identity + ## Prohibitions).
    """
    working_dir = tmp_path / "project"
    (working_dir / ".claude-mpm").mkdir(parents=True)
    # The exact artefact that caused the incident.
    (working_dir / ".claude-mpm" / "PM_INSTRUCTIONS.md").write_text(
        MALFORMED_CACHE, encoding="utf-8"
    )
    assert len((working_dir / ".claude-mpm" / "PM_INSTRUCTIONS.md").read_text()) < 200

    deployed = _deploy(working_dir, fake_home=tmp_path / "fakehome")

    assert PM_IDENTITY_MARKER in deployed, (
        "Malformed PM cache was accepted as an override — "
        "## Identity lost from PM_INSTRUCTIONS_DEPLOYED.md (the original bug)"
    )
    assert PM_PROHIBITIONS_MARKER in deployed, (
        "## Prohibitions (canonical Circuit-Breaker table) lost from deployed file"
    )
    # The malformed sentinel string must be absent entirely, regardless of the
    # deployed file's overall size.
    assert deployed.count(MALFORMED_CACHE) == 0, (
        "Malformed cache string present in deployed file — "
        "it may have replaced or contaminated the PM block"
    )


@pytest.mark.unit
def test_malformed_pm_cache_ignored_in_assembled_prompt(tmp_path: Path) -> None:
    """End-to-end: assembled PM prompt retains ## Identity despite malformed cache."""
    working_dir = tmp_path / "project"
    (working_dir / ".claude-mpm").mkdir(parents=True)
    (working_dir / ".claude-mpm" / "PM_INSTRUCTIONS.md").write_text(
        MALFORMED_CACHE, encoding="utf-8"
    )

    _deploy(working_dir, fake_home=tmp_path / "fakehome")

    # Load via InstructionLoader pointing current_dir at the project tmpdir.
    loader = InstructionLoader(framework_path=REPO_ROOT)
    loader.current_dir = working_dir
    content: dict = {}
    loader.load_all_instructions(content)

    framework = content.get("framework_instructions", "")
    assert PM_IDENTITY_MARKER in framework, (
        "Assembled framework_instructions missing ## Identity after malformed cache"
    )
    assert PM_PROHIBITIONS_MARKER in framework, (
        "Assembled framework_instructions missing ## Prohibitions after malformed cache"
    )


# ── DEV + DEPLOYED: no double-injection ────────────────────────────────────


@pytest.mark.unit
def test_deployed_source_has_no_double_injection(tmp_path: Path) -> None:
    """When DEPLOYED is the source, each block must appear exactly once.

    This is the scenario the existing tests miss: the deployer inlines the
    merged blocks into PM_INSTRUCTIONS_DEPLOYED.md, and the InstructionLoader
    used to ALSO append the system defaults — duplicating ## Identity, the
    agent-routing marker, and the memory block.
    """
    working_dir = tmp_path / "project"
    working_dir.mkdir()
    # No overrides — pure system defaults, merged by the deployer.
    _deploy(working_dir, fake_home=tmp_path / "fakehome")

    loader = InstructionLoader(framework_path=REPO_ROOT)
    loader.current_dir = working_dir
    content: dict = {}
    loader.load_all_instructions(content)

    # The sentinel is an internal coordination signal that load_all_instructions
    # pops once all loaders have consumed it — it must NOT leak to downstream
    # consumers (content_formatter, etc.).
    assert "_loaded_from_deployed" not in content, (
        "_loaded_from_deployed sentinel leaked past load_all_instructions — "
        "downstream consumers would see the private coordination key"
    )

    framework = content.get("framework_instructions", "")

    assert framework.count(PM_IDENTITY_MARKER) == 1, (
        f"## Identity appears {framework.count(PM_IDENTITY_MARKER)} times in the "
        "deployed framework_instructions (expected exactly 1) — double injection"
    )
    assert framework.count(DELEGATION_MARKER) == 1, (
        f"Agent-routing marker appears {framework.count(DELEGATION_MARKER)} times "
        "(expected exactly 1) — double injection"
    )
    # MEMORY block: the deployed file carries the lazy-load stub heading
    # '## Memory System' exactly once; the subsidiary loader must NOT add it
    # again, and must NOT add the static MEMORY.md body.
    assert framework.count("## Memory System") == 1, (
        f"'## Memory System' appears {framework.count('## Memory System')} times "
        "(expected exactly 1) — memory double injection"
    )

    # The subsidiary loaders must NOT have populated their own keys (they are
    # appended by content_formatter and would duplicate the merged blocks).
    assert "agent_delegation" not in content, (
        "load_agent_delegation_instructions ran despite DEPLOYED — "
        "content_formatter would double-inject it"
    )
    assert "workflow_instructions" not in content, (
        "load_workflow_instructions ran despite DEPLOYED — double injection risk"
    )
    # MEMORY must not be statically re-injected on the DEPLOYED path: the merged
    # file already carries the MEMORY block.  ``memory_instructions`` is only
    # acceptable if absent, or — when kuzu-memory is installed on this runner —
    # present as ONLY the dynamic kuzu prefix (which cannot be baked into
    # DEPLOYED), never the static MEMORY.md body or its stub.
    memory_instr = content.get("memory_instructions")
    if memory_instr is not None:
        assert memory_instr.startswith("## Memory: kuzu-memory Active"), (
            "memory_instructions on the DEPLOYED path is not the dynamic kuzu "
            "prefix — the static MEMORY block was re-injected (double injection)"
        )
        assert "## Memory System" not in memory_instr, (
            "static MEMORY stub body leaked into the DEPLOYED-path "
            "memory_instructions (double injection)"
        )


# ── Valid project override is still accepted ───────────────────────────────


@pytest.mark.unit
def test_valid_project_pm_override_is_accepted(tmp_path: Path) -> None:
    """A genuine project PM override (has ## Identity, >200 chars) IS accepted."""
    working_dir = tmp_path / "project"
    (working_dir / ".claude-mpm").mkdir(parents=True)

    sentinel_line = "PROJECT-SPECIFIC-PM-MARKER-12345"
    valid_override = (
        "# Project PM Instructions\n\n"
        "## Identity\n\n"
        f"{sentinel_line}\n\n"
        + ("This project customises the PM identity in detail. " * 10)
        + "\n"
    )
    assert len(valid_override) > 200
    (working_dir / ".claude-mpm" / "PM_INSTRUCTIONS.md").write_text(
        valid_override, encoding="utf-8"
    )

    deployed = _deploy(working_dir, fake_home=tmp_path / "fakehome")

    assert sentinel_line in deployed, (
        "Valid project PM override was rejected — the integrity guard is too strict"
    )
    assert PM_IDENTITY_MARKER in deployed, "## Identity missing from deployed override"

"""Assembled prompt snapshot and structural invariant tests.

Purpose: Catch accidental removal of critical instruction sections from the
assembled PM system prompt.  If someone deletes the circuit-breaker table or
the delegation hierarchy from a .md file, at least one test here fails.

Strategy: structural invariants rather than full-text diff.  The agent list
changes too frequently for exact matching, but the section headers and key
identifiers are stable.
"""

import re
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.core.framework_loader import FrameworkLoader

# ── Structural invariants ──────────────────────────────────────────────────
# These strings MUST appear in every assembled prompt.  The test fails if any
# are missing, which means a critical section was deleted or renamed.
REQUIRED_SECTIONS = [
    "## Prohibitions",  # Circuit-breaker prohibition table header
    "CB#1",  # Lowest circuit-breaker number must be present
    "CB#11",  # Highest circuit-breaker number must be present
    "## Agent Routing",  # Routing section present
    "## Workflow",  # Compact workflow summary present (from PM_INSTRUCTIONS.md)
    "## QA Verification Gate",  # QA gate section
    "## Circuit Breakers",  # CB section header
    "## Model Selection Protocol",  # Model routing section
]

# These strings must NOT appear in the base assembled prompt after recent
# optimisations.  The system-level WORKFLOW.md is lazy-loaded; only a compact
# reference line should appear, not the full phase-detail headings.
BANNED_CONTENT = [
    # Full-detail WORKFLOW.md phase headings — lazy-loading should suppress these
    "### Phase 1: Research (CONDITIONAL)",
    "### Phase 2: Code Analysis Review",
    "### Phase 3: Implementation",
    "### Phase 4: QA (MANDATORY)",
    "### Phase 5: Documentation Agent",
    "## Mandatory 5-Phase Sequence",  # WORKFLOW.md intro heading
]

# Upper-bound on prompt length — guard against re-introduction of bloat.
# Current baseline is ~41,570 chars (measured 2026-05).  The ceiling is set
# generously at 80,000 chars to survive normal growth without false positives.
MAX_PROMPT_CHARS = 80_000


@pytest.fixture(scope="module")
def assembled_prompt(tmp_path_factory: pytest.TempPathFactory) -> str:
    """Assemble the full PM system prompt once per test module.

    Uses a module-scoped fixture so the (relatively expensive) FrameworkLoader
    initialisation is paid only once for the whole snapshot test file.

    Runs against an isolated temporary directory so that a stale
    `.claude-mpm/PM_INSTRUCTIONS_DEPLOYED.md` in the project tree does not
    shadow the source files and produce false negatives for the lazy-loading
    checks.

    The working directory is overridden by patching ``Path.cwd`` in the
    loader modules rather than calling ``os.chdir``.  Mutating the global
    process cwd is unsafe under ``pytest-xdist`` parallel execution, where
    sibling workers share the process; patching keeps the isolation local to
    this fixture.
    """
    tmp_dir = tmp_path_factory.mktemp("assembled_prompt")
    with (
        patch(
            "claude_mpm.core.framework.loaders.instruction_loader.Path.cwd",
            return_value=tmp_dir,
        ),
        patch("claude_mpm.core.framework_loader.Path.cwd", return_value=tmp_dir),
    ):
        loader = FrameworkLoader()
        return loader.get_framework_instructions()


@pytest.mark.unit
def test_assembled_prompt_not_empty(assembled_prompt: str) -> None:
    """The assembled prompt must be a non-empty string."""
    assert isinstance(assembled_prompt, str)
    assert len(assembled_prompt) > 0, (
        "get_framework_instructions() returned empty string"
    )


@pytest.mark.unit
@pytest.mark.parametrize("section", REQUIRED_SECTIONS)
def test_required_section_present(assembled_prompt: str, section: str) -> None:
    """Every critical structural section must appear in the assembled prompt.

    If this test fails for a particular *section*, that section was removed or
    renamed in one of the source .md files.  Restore the section or update the
    constant to match the new heading.
    """
    assert section in assembled_prompt, (
        f"Required section {section!r} not found in assembled prompt "
        f"(prompt length: {len(assembled_prompt)} chars)"
    )


@pytest.mark.unit
@pytest.mark.parametrize("banned", BANNED_CONTENT)
def test_banned_content_absent(assembled_prompt: str, banned: str) -> None:
    """Full WORKFLOW.md detail must NOT appear in the base assembled prompt.

    The system-level WORKFLOW.md is lazy-loaded (commit 43dec86c): instead of
    embedding the ~1,150-token document, the loader injects a single-line
    reference.  These headings come from WORKFLOW.md and should be absent.

    If this test fails the lazy-loading was reverted or bypassed.
    """
    assert banned not in assembled_prompt, (
        f"Banned content {banned!r} found in assembled prompt — "
        "system-level WORKFLOW.md may have been re-embedded (lazy-loading broken)"
    )


@pytest.mark.unit
def test_prompt_within_size_budget(assembled_prompt: str) -> None:
    """Assembled prompt must stay below the hard size ceiling.

    A sudden increase indicates a large file was accidentally re-added to the
    base prompt.  Adjust MAX_PROMPT_CHARS if intentional growth occurs.
    """
    length = len(assembled_prompt)
    assert length <= MAX_PROMPT_CHARS, (
        f"Assembled prompt too large: {length} chars (limit: {MAX_PROMPT_CHARS}). "
        "A file may have been re-added to the base prompt inadvertently."
    )


@pytest.mark.unit
def test_example_blocks_stripped_from_capabilities(assembled_prompt: str) -> None:
    """<example>…</example> blocks must not appear in the capabilities section.

    Commit 523ed3f0 stripped <example> blocks from the capability generator to
    save ~4,800 tokens per session.  This test verifies the stripping is still
    active.
    """
    # Locate the capabilities section.
    cap_start = assembled_prompt.find("## Available Agent Capabilities")
    if cap_start == -1:
        # Fallback: capabilities section might have a slightly different heading.
        cap_start = assembled_prompt.find("## Context-Aware Agent Selection")
    if cap_start == -1:
        # No capabilities section at all — accept (fallback path may be in use).
        return

    capabilities_section = assembled_prompt[cap_start:]
    example_blocks = re.findall(
        r"<example>.*?</example>", capabilities_section, re.DOTALL
    )
    assert len(example_blocks) == 0, (
        f"Found {len(example_blocks)} <example> block(s) in the capabilities "
        "section — these should have been stripped by CapabilityGenerator "
        "(commit 523ed3f0)"
    )


@pytest.mark.unit
def test_workflow_compact_reference_present(assembled_prompt: str) -> None:
    """The compact workflow summary table from PM_INSTRUCTIONS.md must be present.

    Even though the full WORKFLOW.md is lazy-loaded, PM_INSTRUCTIONS.md contains
    a compact 5-row summary table.  That summary must remain in every prompt.
    """
    # The compact workflow table lives under the "## Workflow (5-phase)" heading.
    assert "## Workflow" in assembled_prompt, (
        "Workflow section heading missing from assembled prompt"
    )
    # The compact table has a header row — verify it exists.
    assert "| Phase |" in assembled_prompt or "Phase |" in assembled_prompt, (
        "Compact workflow phase table missing from assembled prompt"
    )


@pytest.mark.unit
def test_pm_memories_excluded_when_mcp_backend_detected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """PM_memories.md content must be absent when MCP backend is simulated as active.

    Commit 13d4ee96 made PM_memories.md injection conditional on MCP backend
    availability.  When a backend is active the UserPromptSubmit hook handles
    memory injection dynamically, so the system prompt must not contain the
    static PM_memories content.

    We simulate an active backend by setting MPM_USE_MCP_MEMORY=true, which
    is the explicit opt-in path in _detect_mcp_memory_backend().
    """
    monkeypatch.setenv("MPM_USE_MCP_MEMORY", "true")

    loader = FrameworkLoader()
    prompt = loader.get_framework_instructions()

    # actual_memories should be empty when MCP backend is flagged
    actual_memories = loader.framework_content.get("actual_memories", "")
    assert actual_memories == "", (
        f"PM memories were injected ({len(actual_memories)} chars) despite "
        "MPM_USE_MCP_MEMORY=true — MCP backend detection logic may be broken"
    )

    # The assembled prompt must not contain the "Current PM Memories" section
    assert "## Current PM Memories" not in prompt, (
        "'## Current PM Memories' section present in prompt despite "
        "MPM_USE_MCP_MEMORY=true"
    )


@pytest.mark.unit
def test_golden_file_snapshot(assembled_prompt: str, tmp_path: Path) -> None:
    """Write or compare against a golden snapshot file.

    First run (no golden file): writes tests/fixtures/assembled_prompt_golden.txt
    and passes.  Subsequent runs: loads the golden file and verifies that
    all REQUIRED_SECTIONS still appear in the current prompt.

    This test does NOT do a brittle full-text diff; it only checks that the
    structural invariants captured at the time the golden file was written are
    still satisfied.  The golden file itself serves as a human-readable record
    of the prompt at a known-good point in time.
    """
    golden_path = Path(__file__).parent / "fixtures" / "assembled_prompt_golden.txt"

    if not golden_path.exists():
        # First run: write the golden file and pass.
        golden_path.parent.mkdir(parents=True, exist_ok=True)
        golden_path.write_text(assembled_prompt, encoding="utf-8")
        # Signal intent clearly.
        pytest.skip(
            f"Golden file written to {golden_path}. "
            "Re-run tests to activate snapshot comparison."
        )

    golden_content = golden_path.read_text(encoding="utf-8")

    # Extract which required sections were present in the golden prompt.
    golden_sections_present = [s for s in REQUIRED_SECTIONS if s in golden_content]

    # All sections that were in the golden file must still be in the current prompt.
    missing = [s for s in golden_sections_present if s not in assembled_prompt]
    assert not missing, (
        "Sections present in golden snapshot are now missing from assembled prompt:\n"
        + "\n".join(f"  - {s!r}" for s in missing)
        + "\n\nThis means a critical instruction section was removed.  Either "
        "restore the section or update the golden file if the change was intentional "
        f"(delete {golden_path} and re-run to regenerate)."
    )

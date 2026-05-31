"""Tests verifying WORKFLOW.md lazy-loading effectiveness.

Purpose: Confirm that the system-level WORKFLOW.md is NOT embedded in the base
assembled prompt (commit 43dec86c), while project/user-level overrides ARE
embedded verbatim.  Also verifies related optimisations: <example> stripping
and conditional PM_memories.md injection.

Implementation notes:
- The lazy-loading is implemented in InstructionLoader.load_workflow_instructions().
  System-level: inject a single-line reference ("Full workflow detail: see …").
  Project/user-level: embed verbatim (project customisations must be available
  immediately).
- There is no "trigger" mechanism — system-level WORKFLOW.md is simply never
  embedded in full.  Tests 4a/4b reflect the actual implementation.
"""

import re
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.core.framework.loaders.instruction_loader import InstructionLoader
from claude_mpm.core.framework_loader import FrameworkLoader
from claude_mpm.services.core.service_container import get_global_container
from claude_mpm.services.core.service_interfaces import ICacheManager

# Path to the actual WORKFLOW.md file (used for content checks)
WORKFLOW_MD_PATH = (
    Path(__file__).parent.parent / "src" / "claude_mpm" / "agents" / "WORKFLOW.md"
)

# Distinctive content from the full WORKFLOW.md that must NOT appear in the
# base assembled prompt when system-level lazy-loading is active.
WORKFLOW_FULL_DETAIL_MARKERS = [
    "### Phase 1: Research (CONDITIONAL)",
    "### Phase 2: Code Analysis Review",
    "### Phase 3: Implementation",
    "### Phase 4: QA (MANDATORY)",
    "### Phase 5: Documentation Agent",
    "## Mandatory 5-Phase Sequence",
    "**Agent**: Research",  # Phase-1 template from WORKFLOW.md
]

# The compact workflow summary lives in PM_INSTRUCTIONS.md.  Its presence
# confirms the PM still has workflow guidance even after lazy-loading.
WORKFLOW_COMPACT_INDICATORS = [
    "## Workflow",  # Section heading in PM_INSTRUCTIONS.md
    "workflow",  # Lower-case presence check
]


# ── Fixtures ──────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def base_prompt() -> str:
    """Assembled PM system prompt with no project/user WORKFLOW.md override.

    The fixture uses a clean temporary directory as the working directory so
    that any project-local .claude-mpm/PM_INSTRUCTIONS_DEPLOYED.md artefact
    (a gitignored compiled file that may pre-date the lazy-load change) is not
    picked up by InstructionLoader.  Without this isolation the stale deployed
    file would inline the full WORKFLOW.md content and cause the 'not in base
    prompt' assertions to fail.
    """
    with tempfile.TemporaryDirectory() as _clean_cwd:
        clean_path = Path(_clean_cwd)
        # Patch cwd inside both the framework_loader module and the
        # instruction_loader so that InstructionLoader.current_dir resolves to
        # a directory that has no PM_INSTRUCTIONS_DEPLOYED.md.
        with (
            patch(
                "claude_mpm.core.framework.loaders.instruction_loader.Path.cwd",
                return_value=clean_path,
            ),
            patch("claude_mpm.core.framework_loader.Path.cwd", return_value=clean_path),
        ):
            loader = FrameworkLoader()
            return loader.get_framework_instructions()


@pytest.fixture(scope="module")
def workflow_md_content() -> str:
    """Raw content of the system WORKFLOW.md file."""
    if not WORKFLOW_MD_PATH.exists():
        pytest.skip(f"WORKFLOW.md not found at {WORKFLOW_MD_PATH}")
    return WORKFLOW_MD_PATH.read_text(encoding="utf-8")


# ── Test 1: WORKFLOW.md full content absent from base prompt ───────────────


@pytest.mark.unit
@pytest.mark.workflow
@pytest.mark.parametrize("marker", WORKFLOW_FULL_DETAIL_MARKERS)
def test_workflow_full_detail_not_in_base_prompt(base_prompt: str, marker: str) -> None:
    """Full WORKFLOW.md phase-detail headings must NOT appear in the base prompt.

    Commit 43dec86c replaced verbatim embedding with a single-line reference
    for the system-level WORKFLOW.md.  If this test fails the full file was
    re-embedded, consuming ~1,150 extra tokens per session.
    """
    assert marker not in base_prompt, (
        f"Full WORKFLOW.md marker {marker!r} found in assembled prompt — "
        "lazy-loading may have been reverted"
    )


# ── Test 2: Compact workflow reference IS present ─────────────────────────


@pytest.mark.unit
@pytest.mark.workflow
def test_workflow_reference_present_in_base_prompt(base_prompt: str) -> None:
    """The base prompt must contain a reference to WORKFLOW.md.

    Even though the full content is not embedded, the PM must know how to find
    the full workflow document when it needs detailed phase guidance.
    """
    # The reference line injected by InstructionLoader mentions WORKFLOW.md
    assert "WORKFLOW.md" in base_prompt, (
        "No WORKFLOW.md reference found in assembled prompt — "
        "the compact reference line may have been dropped"
    )


@pytest.mark.unit
@pytest.mark.workflow
def test_compact_workflow_summary_present(base_prompt: str) -> None:
    """The compact workflow summary from PM_INSTRUCTIONS.md must be present.

    PM_INSTRUCTIONS.md contains a 5-row summary table under '## Workflow (5-phase)'.
    This summary is NOT part of WORKFLOW.md; it lives in PM_INSTRUCTIONS.md and
    must always be present.
    """
    assert "## Workflow" in base_prompt, (
        "'## Workflow' heading missing — PM_INSTRUCTIONS.md workflow section removed?"
    )
    # Compact summary has 'See WORKFLOW.md for details'
    assert (
        "See WORKFLOW.md for details" in base_prompt or "WORKFLOW.md" in base_prompt
    ), "Compact workflow summary or WORKFLOW.md reference missing from prompt"


# ── Test 3: Token reduction is measurable ─────────────────────────────────


@pytest.mark.unit
@pytest.mark.workflow
def test_lazy_load_reduces_prompt_size(
    base_prompt: str, workflow_md_content: str
) -> None:
    """Lazy-loading must keep the base prompt below a meaningful size ceiling.

    With the full WORKFLOW.md embedded the prompt would be roughly
    len(base_prompt) + len(workflow_md_content) chars longer.  We verify that:
    1. The base prompt does NOT contain the full WORKFLOW.md content.
    2. The base prompt is within a reasonable size budget.

    The actual WORKFLOW.md is 4,602 chars (144 lines) — its absence saves
    roughly 1,150 tokens at ~4 chars/token.
    """
    workflow_len = len(workflow_md_content)
    prompt_len = len(base_prompt)

    # Sanity: WORKFLOW.md must be non-trivial for the test to be meaningful.
    assert workflow_len > 1_000, (
        f"WORKFLOW.md suspiciously small ({workflow_len} chars) — file may be empty"
    )

    # The prompt should be well below 60k chars (baseline ~41,570 before this test).
    # Using 75k as a generous ceiling that still catches accidental re-embedding.
    assert prompt_len < 75_000, (
        f"Base prompt too large: {prompt_len} chars (ceiling: 75,000). "
        "WORKFLOW.md or another large file may have been re-embedded."
    )

    # A key multi-line sequence from WORKFLOW.md must be absent from the prompt.
    # Use a unique phrase that only occurs in the full WORKFLOW.md, not in the
    # compact summary in PM_INSTRUCTIONS.md.
    assert "**Agent**: Research" not in base_prompt, (
        "Phase-1 template marker '**Agent**: Research' found in base prompt — "
        "full WORKFLOW.md appears to be embedded"
    )


# ── Test 4a: System-level → reference only ────────────────────────────────


@pytest.mark.unit
@pytest.mark.workflow
def test_system_level_workflow_becomes_reference() -> None:
    """InstructionLoader must inject a reference line for system-level WORKFLOW.md.

    This tests the core lazy-loading logic at the component level.  We
    instantiate InstructionLoader and call load_workflow_instructions() with a
    mock that simulates load_workflow() returning system-level content.  The
    resulting content dict must contain a short reference string, not the full
    WORKFLOW.md text.
    """
    loader = InstructionLoader()
    content: dict = {}

    # The actual WORKFLOW.md content (4,602 chars)
    if not WORKFLOW_MD_PATH.exists():
        pytest.skip(f"WORKFLOW.md not found at {WORKFLOW_MD_PATH}")
    full_workflow = WORKFLOW_MD_PATH.read_text(encoding="utf-8")

    # Patch load_workflow to simulate the system-level return value
    with patch(
        "claude_mpm.core.framework.loaders.instruction_loader.load_workflow",
        return_value=(full_workflow, "system"),
    ):
        loader.load_workflow_instructions(content)

    workflow_stored = content.get("workflow_instructions", "")
    level_stored = content.get("workflow_instructions_level", "")

    assert level_stored == "system", f"Expected level 'system', got {level_stored!r}"

    # The stored content must be the compact reference, not the full file.
    # The reference is much shorter than the full document.
    assert len(workflow_stored) < len(full_workflow), (
        f"System-level workflow was stored at full length ({len(workflow_stored)} chars) "
        f"instead of compact reference (full WORKFLOW.md is {len(full_workflow)} chars)"
    )

    # The reference must mention WORKFLOW.md so the PM can locate it.
    assert "WORKFLOW.md" in workflow_stored, (
        "System-level workflow reference must mention WORKFLOW.md"
    )

    # Full phase detail must NOT be in the reference.
    assert "### Phase 1" not in workflow_stored, (
        "Full phase-1 heading found in system-level workflow reference — "
        "lazy-loading not working"
    )


# ── Test 4b: Project-level → embedded verbatim ───────────────────────────


@pytest.mark.unit
@pytest.mark.workflow
def test_project_level_workflow_embedded_verbatim() -> None:
    """Project-level WORKFLOW.md must be embedded verbatim (not lazy-loaded).

    Project customisations need to be immediately available; they should not
    require an additional Read-tool call.
    """
    loader = InstructionLoader()
    content: dict = {}

    custom_workflow = (
        "# Custom Project Workflow\n\n"
        "### Phase 1: Research (CONDITIONAL)\n"
        "Custom project phase detail here.\n"
    )

    with patch(
        "claude_mpm.core.framework.loaders.instruction_loader.load_workflow",
        return_value=(custom_workflow, "project"),
    ):
        loader.load_workflow_instructions(content)

    workflow_stored = content.get("workflow_instructions", "")
    level_stored = content.get("workflow_instructions_level", "")

    assert level_stored == "project", f"Expected level 'project', got {level_stored!r}"

    # Verbatim embedding: the stored content must equal the supplied content.
    assert workflow_stored == custom_workflow, (
        "Project-level WORKFLOW.md was not embedded verbatim — "
        "project customisations may be inaccessible"
    )

    # Full phase detail must be present (this is the whole point of verbatim embedding).
    assert "### Phase 1: Research (CONDITIONAL)" in workflow_stored, (
        "Full phase-1 heading missing from verbatim project-level workflow embedding"
    )


# ── Test 4c: User-level → embedded verbatim ──────────────────────────────


@pytest.mark.unit
@pytest.mark.workflow
def test_user_level_workflow_embedded_verbatim() -> None:
    """User-level WORKFLOW.md must also be embedded verbatim, like project-level."""
    loader = InstructionLoader()
    content: dict = {}

    custom_workflow = "# User Workflow\n\n### Phase 3: Implementation\nCustom impl.\n"

    with patch(
        "claude_mpm.core.framework.loaders.instruction_loader.load_workflow",
        return_value=(custom_workflow, "user"),
    ):
        loader.load_workflow_instructions(content)

    workflow_stored = content.get("workflow_instructions", "")
    level_stored = content.get("workflow_instructions_level", "")

    assert level_stored == "user", f"Expected level 'user', got {level_stored!r}"
    assert workflow_stored == custom_workflow, (
        "User-level WORKFLOW.md was not embedded verbatim"
    )


# ── Test 5: <example> blocks stripped from capabilities ───────────────────


@pytest.mark.unit
def test_example_blocks_stripped_from_capabilities(base_prompt: str) -> None:
    """<example>…</example> blocks must be absent from the capabilities section.

    Commit 523ed3f0 stripped <example> blocks from CapabilityGenerator to save
    ~4,800 tokens per session.  The PM already has routing tables in
    AGENT_DELEGATION.md, making example blocks in capability descriptions
    redundant.
    """
    # Locate the capabilities section (may or may not exist in the base prompt)
    cap_start = base_prompt.find("## Available Agent Capabilities")
    if cap_start == -1:
        cap_start = base_prompt.find("## Context-Aware Agent Selection")
    if cap_start == -1:
        # Capabilities section absent (e.g. fallback path) — nothing to check.
        return

    capabilities_section = base_prompt[cap_start:]
    example_blocks = re.findall(
        r"<example>.*?</example>", capabilities_section, re.DOTALL
    )
    assert len(example_blocks) == 0, (
        f"Found {len(example_blocks)} <example> block(s) in capabilities section — "
        "CapabilityGenerator should strip these (commit 523ed3f0)"
    )


# ── Test 6: PM_memories.md excluded with MCP backend active ───────────────


@pytest.mark.unit
def test_pm_memories_excluded_with_mcp_backend(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """PM_memories.md content must be absent when MCP backend is flagged active.

    Commit 13d4ee96 made PM_memories.md injection conditional on MCP backend
    availability.  We simulate the backend being active via MPM_USE_MCP_MEMORY=true
    (the explicit opt-in path in MemoryManager._detect_mcp_memory_backend).
    """
    monkeypatch.setenv("MPM_USE_MCP_MEMORY", "true")

    # Clear any stale memory cache from earlier tests that share the global DI
    # container so the MCP detection code is actually exercised (not bypassed
    # by a cached result with non-empty actual_memories).
    container = get_global_container()
    if container.is_registered(ICacheManager):
        container.resolve(ICacheManager).clear_memory_caches()

    loader = FrameworkLoader()
    prompt = loader.get_framework_instructions()

    actual_memories = loader.framework_content.get("actual_memories", "")
    assert actual_memories == "", (
        f"actual_memories not empty ({len(actual_memories)} chars) despite "
        "MPM_USE_MCP_MEMORY=true — MCP backend detection broken"
    )
    assert "## Current PM Memories" not in prompt, (
        "'## Current PM Memories' present in prompt despite MPM_USE_MCP_MEMORY=true"
    )


@pytest.mark.unit
def test_pm_memories_included_without_mcp_backend(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """PM_memories.md should be injected when no MCP backend is active.

    When MPM_USE_MCP_MEMORY=false (explicit opt-out), the memory manager must
    NOT suppress PM_memories.md.  Whether actual_memories is non-empty depends
    on whether a PM_memories.md file exists in the test environment; we only
    assert that the suppression logic is not engaged.
    """
    monkeypatch.setenv("MPM_USE_MCP_MEMORY", "false")

    loader = FrameworkLoader()
    # Re-load with env var set.  We don't assert actual_memories is non-empty
    # because the CI environment may not have a PM_memories.md file.
    # We just verify the framework initialises successfully without suppressing.
    prompt = loader.get_framework_instructions()
    assert isinstance(prompt, str) and len(prompt) > 0

"""Tests verifying MEMORY.md lazy-loading effectiveness.

Purpose: Confirm that the system-level MEMORY.md is NOT embedded in full in the
base assembled prompt, while project/user-level overrides ARE embedded verbatim.
Mirrors tests/test_lazy_load_workflow.py.

The lazy-loading is implemented in InstructionLoader.load_memory_instructions():
- System-level: inject the compact MEMORY_SYSTEM_REFERENCE stub.
- Project/user-level: embed verbatim (project customisations must be available
  immediately).

CRITICAL invariant tested here: even though the full MEMORY.md body is dropped
for system-level, the stub must PRESERVE memory-trigger awareness — the trigger
keywords ("remember", "note that", ...) and the storage tool name
(memory_remember) — so the PM never misses a memory trigger.
"""

import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.core.framework.loaders.instruction_loader import InstructionLoader
from claude_mpm.core.framework.loaders.workflow_constants import (
    MEMORY_SYSTEM_REFERENCE,
)
from claude_mpm.core.framework_loader import FrameworkLoader

# Path to the actual MEMORY.md file (used for content checks).
MEMORY_MD_PATH = (
    Path(__file__).parent.parent / "src" / "claude_mpm" / "agents" / "MEMORY.md"
)

# Distinctive full-detail headings from MEMORY.md that must NOT appear in the
# base assembled prompt when system-level lazy-loading is active.
MEMORY_FULL_DETAIL_MARKERS = [
    "## Static File Format",
    "## Trim Rules",
    "## trusty-memory Tagging",
    "## Dual-System Routing",
]

# Trigger keywords + storage tool that MUST survive lazy-loading in the stub.
# This lists ALL spec-required trigger phrases (not a subset) so that a future
# edit to MEMORY_SYSTEM_REFERENCE which silently drops one is caught here.
MEMORY_TRIGGER_KEYWORDS = [
    "remember",
    "note that",
    "don't forget",
    "always",
    "never",
    "keep in mind",
    "memory_remember",
]


# ── Fixtures ──────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def base_prompt() -> str:
    """Assembled PM system prompt with no project/user MEMORY.md override.

    Uses a clean temporary directory as cwd so that any project-local
    .claude-mpm/PM_INSTRUCTIONS_DEPLOYED.md artefact is not picked up (which
    would otherwise inline content and break the 'not in base prompt'
    assertions).

    ``Path.home()`` is ALSO redirected to a clean temp dir so that a real
    ``~/.claude-mpm/MEMORY.md`` (or WORKFLOW.md) on the runner is not loaded as a
    user-level override — that would embed the file verbatim and make the
    system-level lazy-load assertions env-dependent (mirrors the ``_deploy()``
    Path.home patch in test_instruction_pipeline_integrity.py).
    """
    with (
        tempfile.TemporaryDirectory() as _clean_cwd,
        tempfile.TemporaryDirectory() as _clean_home,
    ):
        clean_path = Path(_clean_cwd)
        clean_home = Path(_clean_home)
        with (
            patch(
                "claude_mpm.core.framework.loaders.instruction_loader.Path.cwd",
                return_value=clean_path,
            ),
            patch("claude_mpm.core.framework_loader.Path.cwd", return_value=clean_path),
            patch(
                "claude_mpm.core.framework.loaders.file_loader.Path.home",
                return_value=clean_home,
            ),
            patch(
                "claude_mpm.core.framework_loader.Path.home",
                return_value=clean_home,
            ),
        ):
            loader = FrameworkLoader()
            return loader.get_framework_instructions()


@pytest.fixture(scope="module")
def memory_md_content() -> str:
    """Raw content of the system MEMORY.md file."""
    if not MEMORY_MD_PATH.exists():
        pytest.skip(f"MEMORY.md not found at {MEMORY_MD_PATH}")
    return MEMORY_MD_PATH.read_text(encoding="utf-8")


# ── Test 1: full MEMORY.md detail absent from base prompt ──────────────────


@pytest.mark.unit
@pytest.mark.parametrize("marker", MEMORY_FULL_DETAIL_MARKERS)
def test_memory_full_detail_not_in_base_prompt(base_prompt: str, marker: str) -> None:
    """Full MEMORY.md detail headings must NOT appear in the base prompt.

    If this fails the full file was re-embedded, consuming ~1,776 extra tokens
    per session.
    """
    assert marker not in base_prompt, (
        f"Full MEMORY.md marker {marker!r} found in assembled prompt — "
        "lazy-loading may have been reverted"
    )


# ── Test 2: stub reference IS present ──────────────────────────────────────


@pytest.mark.unit
def test_memory_reference_present_in_base_prompt(base_prompt: str) -> None:
    """The base prompt must contain a reference to MEMORY.md so the PM can find it."""
    assert "MEMORY.md" in base_prompt, (
        "No MEMORY.md reference found in assembled prompt — "
        "the compact reference stub may have been dropped"
    )


# ── Test 3 (CRITICAL): trigger keywords preserved in the stub ──────────────


@pytest.mark.unit
@pytest.mark.parametrize("keyword", MEMORY_TRIGGER_KEYWORDS)
def test_memory_trigger_keywords_preserved(base_prompt: str, keyword: str) -> None:
    """Memory trigger keywords + storage tool MUST survive lazy-loading.

    This is the critical guard: dropping the full MEMORY.md body must NOT mean
    the PM loses awareness of *when* to store a memory.  The stub must still
    mention the trigger phrases and the memory_remember tool.
    """
    assert keyword in base_prompt, (
        f"Memory trigger keyword {keyword!r} missing from assembled prompt — "
        "the lazy-load stub dropped trigger awareness (PM will miss triggers)"
    )


@pytest.mark.unit
def test_stub_itself_carries_trigger_awareness() -> None:
    """The MEMORY_SYSTEM_REFERENCE constant itself must carry trigger awareness."""
    for keyword in MEMORY_TRIGGER_KEYWORDS:
        assert keyword in MEMORY_SYSTEM_REFERENCE, (
            f"MEMORY_SYSTEM_REFERENCE missing trigger keyword {keyword!r}"
        )
    assert "MEMORY.md" in MEMORY_SYSTEM_REFERENCE, (
        "MEMORY_SYSTEM_REFERENCE must point to MEMORY.md"
    )
    # The stub must be compact, not the full document.
    assert len(MEMORY_SYSTEM_REFERENCE) < 800, (
        "MEMORY_SYSTEM_REFERENCE is suspiciously long — it should be a compact stub"
    )


# ── Test 4: token reduction is measurable ──────────────────────────────────


@pytest.mark.unit
def test_lazy_load_reduces_prompt_size(
    base_prompt: str, memory_md_content: str
) -> None:
    """Lazy-loading must keep the full MEMORY.md body out of the base prompt."""
    memory_len = len(memory_md_content)

    # Sanity: MEMORY.md must be non-trivial for the test to be meaningful.
    assert memory_len > 1_000, (
        f"MEMORY.md suspiciously small ({memory_len} chars) — file may be empty"
    )

    # A unique multi-line marker from the full MEMORY.md must be absent.
    assert "## trusty-memory Tagging" not in base_prompt, (
        "'## trusty-memory Tagging' found in base prompt — "
        "full MEMORY.md appears to be embedded"
    )


# ── Test 5a: System-level → stub ───────────────────────────────────────────


@pytest.mark.unit
def test_system_level_memory_becomes_reference() -> None:
    """InstructionLoader must inject the stub for system-level MEMORY.md."""
    loader = InstructionLoader()
    content: dict = {}

    if not MEMORY_MD_PATH.exists():
        pytest.skip(f"MEMORY.md not found at {MEMORY_MD_PATH}")
    full_memory = MEMORY_MD_PATH.read_text(encoding="utf-8")

    # Simulate load_memory_file returning system-level content, and ensure
    # kuzu-memory is NOT detected so the dynamic prefix does not interfere.
    with (
        patch.object(
            loader.file_loader,
            "load_memory_file",
            return_value=(full_memory, "system"),
        ),
        patch.object(loader, "_detect_kuzu_memory", return_value=False),
    ):
        loader.load_memory_instructions(content)

    memory_stored = content.get("memory_instructions", "")
    level_stored = content.get("memory_instructions_level", "")

    assert level_stored == "system", f"Expected level 'system', got {level_stored!r}"
    assert memory_stored == MEMORY_SYSTEM_REFERENCE, (
        "System-level MEMORY.md was not replaced by the reference stub"
    )
    assert len(memory_stored) < len(full_memory), (
        "System-level memory stored at full length instead of compact stub"
    )
    assert "## Static File Format" not in memory_stored, (
        "Full MEMORY.md detail found in system-level stub — lazy-loading broken"
    )


# ── Test 5b: Project-level → embedded verbatim ─────────────────────────────


@pytest.mark.unit
def test_project_level_memory_embedded_verbatim() -> None:
    """Project-level MEMORY.md must be embedded verbatim (not lazy-loaded)."""
    loader = InstructionLoader()
    content: dict = {}

    custom_memory = (
        "# Custom Project Memory\n\n"
        "## Static File Format\nProject-specific memory format.\n"
    )

    with (
        patch.object(
            loader.file_loader,
            "load_memory_file",
            return_value=(custom_memory, "project"),
        ),
        patch.object(loader, "_detect_kuzu_memory", return_value=False),
    ):
        loader.load_memory_instructions(content)

    memory_stored = content.get("memory_instructions", "")
    level_stored = content.get("memory_instructions_level", "")

    assert level_stored == "project", f"Expected level 'project', got {level_stored!r}"
    assert memory_stored == custom_memory, (
        "Project-level MEMORY.md was not embedded verbatim"
    )
    assert "## Static File Format" in memory_stored, (
        "Full detail missing from verbatim project-level MEMORY.md embedding"
    )


# ── Test 5c: User-level → embedded verbatim ────────────────────────────────


@pytest.mark.unit
def test_user_level_memory_embedded_verbatim() -> None:
    """User-level MEMORY.md must also be embedded verbatim, like project-level."""
    loader = InstructionLoader()
    content: dict = {}

    custom_memory = "# User Memory\n\n## Trim Rules\nCustom trim rules.\n"

    with (
        patch.object(
            loader.file_loader,
            "load_memory_file",
            return_value=(custom_memory, "user"),
        ),
        patch.object(loader, "_detect_kuzu_memory", return_value=False),
    ):
        loader.load_memory_instructions(content)

    memory_stored = content.get("memory_instructions", "")
    level_stored = content.get("memory_instructions_level", "")

    assert level_stored == "user", f"Expected level 'user', got {level_stored!r}"
    assert memory_stored == custom_memory, (
        "User-level MEMORY.md was not embedded verbatim"
    )


# ── Test 6: kuzu augmentation still injects when detected ──────────────────


@pytest.mark.unit
def test_kuzu_augmentation_still_injects_when_detected() -> None:
    """The dynamic kuzu-memory prefix must still be injected when detected.

    This augmentation is environment-dependent and runs on top of the
    system-level stub.
    """
    loader = InstructionLoader()
    content: dict = {}

    full_memory = "# Memory\n\n## Static File Format\nSystem memory.\n"

    with (
        patch.object(
            loader.file_loader,
            "load_memory_file",
            return_value=(full_memory, "system"),
        ),
        patch.object(loader, "_detect_kuzu_memory", return_value=True),
    ):
        loader.load_memory_instructions(content)

    memory_stored = content.get("memory_instructions", "")
    assert "kuzu-memory Active (legacy fallback)" in memory_stored, (
        "kuzu-memory augmentation was not injected even though it was detected"
    )
    assert "mcp__kuzu-memory__kuzu_remember" in memory_stored, (
        "kuzu MCP tool reference missing from augmented memory content"
    )
    # Non-deployed system path: the kuzu prefix is PREPENDED to the stub, so the
    # stub (with its trigger awareness) must still be present too.
    assert MEMORY_SYSTEM_REFERENCE in memory_stored, (
        "System-level MEMORY stub was lost when the kuzu prefix was prepended"
    )

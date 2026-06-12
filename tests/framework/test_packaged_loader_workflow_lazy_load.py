"""Tests verifying PackagedLoader uses the WORKFLOW.md lazy-load stub.

Issue #758: PackagedLoader.load_framework_content() was loading WORKFLOW.md
in full unconditionally, costing PyPI-installed users ~1,150 extra tokens per
session that dev/filesystem installs (handled by InstructionLoader) do not pay.

Fix: PackagedLoader now injects WORKFLOW_SYSTEM_REFERENCE (the same single-line
stub used by InstructionLoader for system-level WORKFLOW.md) instead of loading
and embedding the full file content.  Project/user overrides are still handled
by InstructionLoader.load_workflow_instructions() which runs after
PackagedLoader and overwrites the key when an override exists.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from claude_mpm.core.framework.loaders.packaged_loader import PackagedLoader
from claude_mpm.core.framework.loaders.workflow_constants import (
    WORKFLOW_SYSTEM_REFERENCE,
)

# Distinctive phrases from the full WORKFLOW.md that must NOT appear when the
# stub is active.
FULL_WORKFLOW_MARKERS = [
    "## Mandatory 5-Phase Sequence",
    "### Phase 1: Research (CONDITIONAL)",
    "### Phase 2: Code Analysis Review",
    "### Phase 3: Implementation",
    "### Phase 4: QA (MANDATORY)",
    "**Agent**: Research",
]

# Simulate a realistic full WORKFLOW.md body (the actual file is ~4,602 chars).
_FAKE_WORKFLOW_FULL = (
    "# Workflow\n\n"
    "## Mandatory 5-Phase Sequence\n\n"
    "| Phase | Name | Agent |\n"
    "|-------|------|-------|\n"
    "| 1 | Research | **Agent**: Research |\n"
    "| 2 | Code Analysis Review | **Agent**: Code critic |\n\n"
    "### Phase 1: Research (CONDITIONAL)\n"
    "Run this phase when context gathering is needed.\n\n"
    "### Phase 2: Code Analysis Review\n"
    "Mandatory review of existing code before implementation.\n\n"
    "### Phase 3: Implementation\n"
    "Core implementation work.\n\n"
    "### Phase 4: QA (MANDATORY)\n"
    "Quality assurance checks.\n\n"
    "### Phase 5: Documentation Agent\n"
    "Write or update documentation.\n"
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_loader_with_packaged_workflow(workflow_content: str | None) -> PackagedLoader:
    """Return a PackagedLoader whose load_packaged_file is stubbed.

    The stub returns *workflow_content* only when asked for 'WORKFLOW.md', and
    None for all other filenames so we can isolate the WORKFLOW.md logic.
    """
    loader = PackagedLoader()

    def fake_load_packaged_file(filename: str) -> str | None:
        if filename == "WORKFLOW.md":
            return workflow_content
        return None

    loader.load_packaged_file = fake_load_packaged_file  # type: ignore[method-assign]
    return loader


def _make_loader_with_fallback_workflow(workflow_content: str | None) -> PackagedLoader:
    """Return a PackagedLoader whose load_packaged_file_fallback is stubbed."""
    loader = PackagedLoader()

    def fake_fallback(filename: str, resources: object) -> str | None:
        if filename == "WORKFLOW.md":
            return workflow_content
        return None

    loader.load_packaged_file_fallback = fake_fallback  # type: ignore[method-assign]
    return loader


# ---------------------------------------------------------------------------
# Tests: load_framework_content (primary path)
# ---------------------------------------------------------------------------


class TestPackagedLoaderWorkflowLazyLoad:
    """PackagedLoader must inject the WORKFLOW_SYSTEM_REFERENCE stub, not full content."""

    def test_stub_injected_instead_of_full_content(self) -> None:
        """load_framework_content writes WORKFLOW_SYSTEM_REFERENCE, not full WORKFLOW.md.

        This is the core assertion for issue #758: PyPI installs must use the
        same lazy-load stub as filesystem installs.
        """
        loader = _make_loader_with_packaged_workflow(_FAKE_WORKFLOW_FULL)
        content: dict = {}

        # Patch the module-level `files` so the method takes the primary code path.
        with patch(
            "claude_mpm.core.framework.loaders.packaged_loader.files",
            new=MagicMock(),
        ):
            loader.load_framework_content(content)

        workflow_stored = content.get("workflow_instructions", "")

        assert workflow_stored == WORKFLOW_SYSTEM_REFERENCE, (
            f"PackagedLoader stored {len(workflow_stored)!r} chars instead of the "
            f"WORKFLOW_SYSTEM_REFERENCE stub ({len(WORKFLOW_SYSTEM_REFERENCE)} chars). "
            "Full WORKFLOW.md appears to be embedded — issue #758 not fixed."
        )

    @pytest.mark.parametrize("marker", FULL_WORKFLOW_MARKERS)
    def test_full_workflow_markers_absent(self, marker: str) -> None:
        """Full WORKFLOW.md phase-detail headings must NOT appear in the content dict.

        Each marker is checked separately so failures name the exact phrase.
        """
        loader = _make_loader_with_packaged_workflow(_FAKE_WORKFLOW_FULL)
        content: dict = {}

        with patch(
            "claude_mpm.core.framework.loaders.packaged_loader.files",
            new=MagicMock(),
        ):
            loader.load_framework_content(content)

        workflow_stored = content.get("workflow_instructions", "")

        assert marker not in workflow_stored, (
            f"Full WORKFLOW.md marker {marker!r} found in PackagedLoader output — "
            "lazy-loading not applied (issue #758)."
        )

    def test_stub_mentions_workflow_md(self) -> None:
        """The injected stub must reference WORKFLOW.md so the PM can locate the file."""
        loader = _make_loader_with_packaged_workflow(_FAKE_WORKFLOW_FULL)
        content: dict = {}

        with patch(
            "claude_mpm.core.framework.loaders.packaged_loader.files",
            new=MagicMock(),
        ):
            loader.load_framework_content(content)

        workflow_stored = content.get("workflow_instructions", "")

        assert "WORKFLOW.md" in workflow_stored, (
            "WORKFLOW_SYSTEM_REFERENCE stub must mention WORKFLOW.md "
            "so the PM knows where to find the full document."
        )

    def test_workflow_instructions_level_is_system(self) -> None:
        """workflow_instructions_level must be 'system' after lazy-load."""
        loader = _make_loader_with_packaged_workflow(_FAKE_WORKFLOW_FULL)
        content: dict = {}

        with patch(
            "claude_mpm.core.framework.loaders.packaged_loader.files",
            new=MagicMock(),
        ):
            loader.load_framework_content(content)

        assert content.get("workflow_instructions_level") == "system", (
            "workflow_instructions_level must be 'system' after PackagedLoader "
            "lazy-loads the packaged WORKFLOW.md."
        )

    def test_no_workflow_key_when_workflow_md_absent(self) -> None:
        """When WORKFLOW.md is not in the package, no workflow key is set.

        This preserves the existing None-guard behaviour: if the packaged install
        somehow lacks WORKFLOW.md, we should not set workflow_instructions at all.
        """
        loader = _make_loader_with_packaged_workflow(None)
        content: dict = {}

        with patch(
            "claude_mpm.core.framework.loaders.packaged_loader.files",
            new=MagicMock(),
        ):
            loader.load_framework_content(content)

        assert "workflow_instructions" not in content, (
            "workflow_instructions key must not be set when WORKFLOW.md is absent "
            "from the package."
        )

    def test_stub_is_shorter_than_full_content(self) -> None:
        """The injected stub must be substantially shorter than the full WORKFLOW.md.

        Confirms we are not accidentally embedding full content.
        """
        loader = _make_loader_with_packaged_workflow(_FAKE_WORKFLOW_FULL)
        content: dict = {}

        with patch(
            "claude_mpm.core.framework.loaders.packaged_loader.files",
            new=MagicMock(),
        ):
            loader.load_framework_content(content)

        workflow_stored = content.get("workflow_instructions", "")

        assert len(workflow_stored) < len(_FAKE_WORKFLOW_FULL), (
            f"Stored workflow ({len(workflow_stored)} chars) is not shorter than full "
            f"WORKFLOW.md ({len(_FAKE_WORKFLOW_FULL)} chars) — stub not applied."
        )
        # Stub should be well under 300 chars (it is ~150 chars currently).
        assert len(workflow_stored) < 300, (
            f"WORKFLOW_SYSTEM_REFERENCE is suspiciously long ({len(workflow_stored)} chars)."
        )


# ---------------------------------------------------------------------------
# Tests: load_framework_content_fallback (Python 3.8 fallback path)
# ---------------------------------------------------------------------------


class TestPackagedLoaderFallbackWorkflowLazyLoad:
    """Same lazy-load assertions for the importlib.resources fallback path."""

    def test_fallback_injects_stub_not_full_content(self) -> None:
        """load_framework_content_fallback also uses the WORKFLOW_SYSTEM_REFERENCE stub."""
        loader = _make_loader_with_fallback_workflow(_FAKE_WORKFLOW_FULL)
        content: dict = {}
        fake_resources = MagicMock()

        loader.load_framework_content_fallback(content, fake_resources)

        workflow_stored = content.get("workflow_instructions", "")

        assert workflow_stored == WORKFLOW_SYSTEM_REFERENCE, (
            f"Fallback path stored {len(workflow_stored)} chars instead of stub. "
            "Full WORKFLOW.md content embedded (issue #758 not fixed for fallback path)."
        )

    @pytest.mark.parametrize("marker", FULL_WORKFLOW_MARKERS)
    def test_fallback_full_markers_absent(self, marker: str) -> None:
        """Full phase-detail headings must also be absent from fallback path output."""
        loader = _make_loader_with_fallback_workflow(_FAKE_WORKFLOW_FULL)
        content: dict = {}

        loader.load_framework_content_fallback(content, MagicMock())

        workflow_stored = content.get("workflow_instructions", "")

        assert marker not in workflow_stored, (
            f"Full WORKFLOW.md marker {marker!r} found in fallback path output."
        )

    def test_fallback_no_workflow_key_when_absent(self) -> None:
        """Fallback path: no workflow key when WORKFLOW.md is absent."""
        loader = _make_loader_with_fallback_workflow(None)
        content: dict = {}

        loader.load_framework_content_fallback(content, MagicMock())

        assert "workflow_instructions" not in content


# ---------------------------------------------------------------------------
# Tests: shared constant alignment
# ---------------------------------------------------------------------------


class TestWorkflowConstantAlignment:
    """Verify PackagedLoader uses the same constant as InstructionLoader."""

    def test_packaged_loader_uses_shared_constant(self) -> None:
        """PackagedLoader imports WORKFLOW_SYSTEM_REFERENCE from workflow_constants.

        Both PackagedLoader and InstructionLoader must reference the same
        constant so the stub is identical across both code paths.
        """
        import claude_mpm.core.framework.loaders.packaged_loader as pl_module

        # The constant is importable from the packaged_loader module's namespace.
        assert hasattr(pl_module, "WORKFLOW_SYSTEM_REFERENCE"), (
            "WORKFLOW_SYSTEM_REFERENCE not found in packaged_loader module — "
            "import may have been removed."
        )
        assert pl_module.WORKFLOW_SYSTEM_REFERENCE == WORKFLOW_SYSTEM_REFERENCE, (
            "PackagedLoader's WORKFLOW_SYSTEM_REFERENCE differs from the shared "
            "workflow_constants value — they must be identical."
        )

    def test_constant_is_compact(self) -> None:
        """WORKFLOW_SYSTEM_REFERENCE must be under 300 chars (a reference, not a document)."""
        assert len(WORKFLOW_SYSTEM_REFERENCE) < 300, (
            f"WORKFLOW_SYSTEM_REFERENCE is {len(WORKFLOW_SYSTEM_REFERENCE)} chars — "
            "it should be a compact single-line reference."
        )

    def test_constant_mentions_workflow_md(self) -> None:
        """WORKFLOW_SYSTEM_REFERENCE must mention WORKFLOW.md."""
        assert "WORKFLOW.md" in WORKFLOW_SYSTEM_REFERENCE

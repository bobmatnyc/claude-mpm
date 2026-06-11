"""Regression test: every BLOCK_MARKERS entry must appear in its source .md file.

This prevents BLOCK_MARKERS from silently drifting out of sync with the actual
headings in the source agent .md files, which would cause stale-override detection
to always miss (never fire), allowing stale deployed content to persist.

WHAT: Asserts each marker string in BLOCK_MARKERS is present in its corresponding
      source .md file under src/claude_mpm/agents/.
WHY: Three of four markers were historically stale (pointed to headings that no
     longer existed), making stale-override detection silently broken. Closes #749.
"""

from importlib.resources import files
from pathlib import Path

import pytest

from claude_mpm.services.agents.deployment.system_instructions_deployer import (
    BLOCK_MARKERS,
)


def _agents_dir() -> Path:
    """Return the path to src/claude_mpm/agents/ via importlib.resources."""
    # importlib.resources returns a Traversable; cast to Path for .read_text()
    agents_pkg = files("claude_mpm") / "agents"
    # Resolve to a real filesystem path so we can open files
    candidate = Path(str(agents_pkg))
    if candidate.is_dir():
        return candidate
    # Fallback: walk up from this test file
    here = Path(__file__).resolve()
    for parent in here.parents:
        guess = parent / "src" / "claude_mpm" / "agents"
        if guess.is_dir():
            return guess
    raise FileNotFoundError("Cannot locate src/claude_mpm/agents/")


@pytest.mark.parametrize(
    "source_file,markers",
    [(k, v) for k, v in BLOCK_MARKERS.items()],
    ids=list(BLOCK_MARKERS.keys()),
)
def test_each_block_marker_present_in_source_file(
    source_file: str, markers: list[str]
) -> None:
    """Every marker in BLOCK_MARKERS must appear verbatim in the source .md file.

    If this test fails after a heading is renamed in a source .md file, update
    BLOCK_MARKERS in system_instructions_deployer.py to match the new heading.
    """
    agents_dir = _agents_dir()
    source_path = agents_dir / source_file
    assert source_path.exists(), (
        f"Source file {source_file!r} not found at {source_path}. "
        "Remove or rename the entry in BLOCK_MARKERS."
    )
    content = source_path.read_text(encoding="utf-8")
    for marker in markers:
        assert marker in content, (
            f"Marker {marker!r} not found in {source_file}. "
            f"Update BLOCK_MARKERS in system_instructions_deployer.py to match "
            f"the current headings in {source_file}."
        )

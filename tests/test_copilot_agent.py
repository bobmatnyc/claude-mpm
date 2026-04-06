#!/usr/bin/env python3
"""Quick smoke-test for the GitHub Copilot CLI agent integration.

Checks availability, then fires two tasks and prints results with timing.

Usage::

    cd /Users/masa/Projects/claude-mpm
    uv run python scripts/test_copilot_agent.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import TYPE_CHECKING

# ---------------------------------------------------------------------------
# Make sure the project is importable regardless of installation state
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.services.agents.copilot_agent import (
    is_copilot_available,
    run_copilot_task,
)

if TYPE_CHECKING:
    from claude_mpm.services.agents.copilot_agent import CopilotResult


def _print_result(label: str, result: CopilotResult) -> None:
    sep = "-" * 60
    print(f"\n{sep}")
    print(f"Task: {label}")
    print(f"Success:    {result.success}")
    print(f"Exit code:  {result.exit_code}")
    print(f"Duration:   {result.duration_ms} ms")
    print(f"Model:      {result.model}")
    print(f"Raw events: {len(result.raw_events)} received")
    print(f"Response:\n{result.response.strip() or '(empty)'}")
    print(sep)


async def main() -> None:
    # ------------------------------------------------------------------
    # 1. Availability check
    # ------------------------------------------------------------------
    print("=== GitHub Copilot CLI Agent – Smoke Test ===\n")
    available = is_copilot_available()
    print(f"gh copilot available: {available}")

    if not available:
        print(
            "\ngh copilot is not installed or not authenticated.\n"
            "Install with:  gh extension install github/gh-copilot\n"
            "Authenticate:  gh auth login\n"
        )
        sys.exit(0)

    # ------------------------------------------------------------------
    # 2. Filesystem task
    # ------------------------------------------------------------------
    project_root = str(Path(__file__).parent.parent)
    task1 = (
        "List the 5 most recently modified Python files in this project. "
        "Show each file path and its last-modified date. "
        "Focus on files under src/ or tests/."
    )
    print(f"\nRunning task 1 (working_dir={project_root}) ...")
    result1 = await run_copilot_task(
        task1,
        working_dir=project_root,
        timeout=90,
    )
    _print_result("5 most recently modified Python files", result1)

    # ------------------------------------------------------------------
    # 3. Git task
    # ------------------------------------------------------------------
    task2 = (
        "Show the last 3 commits in this repository with their commit hashes, "
        "dates, authors, and the list of files changed in each commit."
    )
    print(f"\nRunning task 2 (working_dir={project_root}) ...")
    result2 = await run_copilot_task(
        task2,
        working_dir=project_root,
        timeout=90,
    )
    _print_result("Last 3 commits with file changes", result2)

    # ------------------------------------------------------------------
    # 4. Summary
    # ------------------------------------------------------------------
    passed = sum(1 for r in (result1, result2) if r.success)
    total = 2
    print(f"\n=== Results: {passed}/{total} tasks succeeded ===")


if __name__ == "__main__":
    asyncio.run(main())

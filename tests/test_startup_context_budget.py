"""Regression guard for PM startup-instruction context size.

WHAT: Measures the byte size and approximate token count of each tracked
contributor to the PM startup context (5 framework instruction files +
CLAUDE.md), compares against a committed baseline snapshot, and hard-fails
when the TOTAL exceeds 1.2x the baseline total.

WHY: The assembled PM prompt has grown organically. Without a size guard,
incremental additions go unnoticed until they cause measurable token-cost and
latency regressions in production.

CONTRIBUTORS TRACKED:
    src/claude_mpm/agents/PM_INSTRUCTIONS.md
    src/claude_mpm/agents/WORKFLOW.md
    src/claude_mpm/agents/MEMORY.md
    src/claude_mpm/agents/AGENT_DELEGATION.md
    src/claude_mpm/agents/BASE_PM.md
    CLAUDE.md (injected by Claude Code into every session)

TOKEN ESTIMATE: bytes / 4  (conservative approximation; real tiktoken count
may vary by ±10-15% but is adequate for regression detection).

BASELINE REGENERATION:
    To update the baseline after an intentional size increase run:

        UPDATE_STARTUP_BASELINE=1 uv run pytest tests/test_startup_context_budget.py -v

    This regenerates tests/data/startup_context_baseline.json from current
    file sizes and the test will then pass.

HARD-FAIL THRESHOLD:
    TOTAL > 1.2x baseline_total triggers a hard failure.
    Individual file growth only emits a warning (does not fail).

LINK: none
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Repo root is two levels up from this file (tests/test_startup_context_budget.py
# → tests/ → repo root).  This is stable regardless of CWD at test time.
_REPO_ROOT = Path(__file__).resolve().parent.parent

_BASELINE_PATH = (
    Path(__file__).resolve().parent / "data" / "startup_context_baseline.json"
)

# Hard-fail multiplier: TOTAL bytes > BUDGET_MULTIPLIER * baseline_total → FAIL
BUDGET_MULTIPLIER = 1.2

# Files tracked (key → repo-root-relative path)
TRACKED_FILES: dict[str, str] = {
    "PM_INSTRUCTIONS": "src/claude_mpm/agents/PM_INSTRUCTIONS.md",
    "WORKFLOW": "src/claude_mpm/agents/WORKFLOW.md",
    "MEMORY": "src/claude_mpm/agents/MEMORY.md",
    "AGENT_DELEGATION": "src/claude_mpm/agents/AGENT_DELEGATION.md",
    "BASE_PM": "src/claude_mpm/agents/BASE_PM.md",
    "CLAUDE_MD": "CLAUDE.md",
}


def _load_baseline() -> dict:
    """Load the committed baseline snapshot."""
    if not _BASELINE_PATH.exists():
        pytest.fail(
            f"Baseline snapshot not found: {_BASELINE_PATH}\n"
            "Run with UPDATE_STARTUP_BASELINE=1 to create it."
        )
    with _BASELINE_PATH.open() as fh:
        return json.load(fh)


def _measure_current() -> dict:
    """Measure current file sizes and compute totals."""
    result: dict[str, dict] = {}
    total_bytes = 0

    for key, rel_path in TRACKED_FILES.items():
        full_path = _REPO_ROOT / rel_path
        if not full_path.exists():
            pytest.fail(
                f"Tracked file missing: {full_path}\n"
                "If the file was intentionally moved, update TRACKED_FILES in "
                "tests/test_startup_context_budget.py and regenerate the baseline."
            )
        size = full_path.stat().st_size
        result[key] = {
            "path": rel_path,
            "bytes": size,
            "approx_tokens": size // 4,
        }
        total_bytes += size

    result["_total"] = {
        "bytes": total_bytes,
        "approx_tokens": total_bytes // 4,
    }
    return result


def _write_baseline(data: dict) -> None:
    """Write (or overwrite) the baseline snapshot."""
    _BASELINE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _BASELINE_PATH.open("w") as fh:
        json.dump(data, fh, indent=2)
        fh.write("\n")


def _format_row(key: str, current_bytes: int, baseline_bytes: int) -> str:
    """Format a per-file comparison row."""
    delta = current_bytes - baseline_bytes
    pct = (delta / baseline_bytes * 100) if baseline_bytes else 0.0
    sign = "+" if delta >= 0 else ""
    flag = "  <-- GREW" if delta > 0 else ""
    return (
        f"  {key:<20}  current={current_bytes:>7}B  baseline={baseline_bytes:>7}B"
        f"  delta={sign}{delta:>+7}B ({sign}{pct:.1f}%){flag}"
    )


# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------


def test_startup_context_budget() -> None:
    """Startup context files stay within 1.2x their committed baseline total.

    WHAT: Compares byte size of each tracked PM instruction file against the
    baseline snapshot.  Warns on individual file growth, hard-fails when the
    running TOTAL exceeds BUDGET_MULTIPLIER (1.2x).

    WHY: Prevents silent context bloat from accumulating across PRs.

    :spec: LINK: none
    """
    # --- Baseline regeneration mode -----------------------------------------
    if os.environ.get("UPDATE_STARTUP_BASELINE", "").strip():
        current = _measure_current()
        _write_baseline(current)
        print(f"\nBaseline regenerated at {_BASELINE_PATH}")
        for key, info in current.items():
            if key == "_total":
                print(
                    f"  TOTAL: {info['bytes']} bytes (~{info['approx_tokens']} tokens)"
                )
            else:
                print(
                    f"  {key}: {info['bytes']} bytes (~{info['approx_tokens']} tokens)"
                )
        return  # always passes in regen mode

    # --- Normal comparison mode ---------------------------------------------
    baseline = _load_baseline()
    current = _measure_current()

    baseline_total = baseline["_total"]["bytes"]
    current_total = current["_total"]["bytes"]
    hard_fail_threshold = int(baseline_total * BUDGET_MULTIPLIER)

    # Build the comparison report
    report_lines: list[str] = [
        "",
        "Startup context size report",
        "=" * 60,
    ]

    any_grew = False
    for key in TRACKED_FILES:
        c_bytes = current[key]["bytes"]
        b_bytes = baseline[key]["bytes"]
        if c_bytes != b_bytes:
            any_grew = True
        report_lines.append(_format_row(key, c_bytes, b_bytes))

    # Total line
    total_delta = current_total - baseline_total
    total_pct = (total_delta / baseline_total * 100) if baseline_total else 0.0
    total_sign = "+" if total_delta >= 0 else ""
    report_lines.extend(
        [
            "-" * 60,
            f"  {'TOTAL':<20}  current={current_total:>7}B  baseline={baseline_total:>7}B"
            f"  delta={total_sign}{total_delta:>+7}B ({total_sign}{total_pct:.1f}%)",
            f"  hard-fail threshold: {hard_fail_threshold}B  ({BUDGET_MULTIPLIER:.1f}x baseline)",
            "=" * 60,
        ]
    )

    if any_grew:
        report_lines.append(
            "\nFiles grew since baseline.  If intentional, regenerate:\n"
            "  UPDATE_STARTUP_BASELINE=1 uv run pytest "
            "tests/test_startup_context_budget.py -v"
        )

    report = "\n".join(report_lines)
    print(report)  # always visible with pytest -v or -s

    # Per-file growth is a warning only (captured in report, not a hard fail)
    # Hard fail: total exceeds budget
    if current_total > hard_fail_threshold:
        pytest.fail(
            f"\nSTARTUP CONTEXT BUDGET EXCEEDED\n"
            f"  current total : {current_total:,} bytes (~{current_total // 4:,} tokens)\n"
            f"  baseline total: {baseline_total:,} bytes (~{baseline_total // 4:,} tokens)\n"
            f"  limit (1.2x)  : {hard_fail_threshold:,} bytes\n"
            f"  excess        : {current_total - hard_fail_threshold:,} bytes\n"
            "\nReview which files grew (see report above) and either:\n"
            "  1. Trim the offending file(s), or\n"
            "  2. Update the baseline deliberately:\n"
            "     UPDATE_STARTUP_BASELINE=1 uv run pytest "
            "tests/test_startup_context_budget.py -v"
        )

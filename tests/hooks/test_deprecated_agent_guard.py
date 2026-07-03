"""Unit tests for the deprecated-agent PreToolUse guard (issue #922).

Covers:

* Dispatching a ``deprecated: true`` agent is blocked and the deny reason
  surfaces the agent's own ``description:`` frontmatter text.
* Dispatching a non-deprecated agent is unaffected (falls through to normal
  model-tier resolution).
* Matching is case-insensitive and works against all three agent-identity
  forms this repo uses: filename stem, ``name:`` frontmatter field, and an
  explicit ``agent_id:`` frontmatter field.
* A missing ``.claude/agents/`` directory (or missing ``cwd``) fails open.
* A deprecated agent with no real description text still gets a fallback
  deny reason rather than silently bypassing the guard.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Make src importable when tests are run directly without an installed package.
_SRC = Path(__file__).resolve().parent.parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from claude_mpm.hooks import model_tier_hook

OPS_FRONTMATTER = """---
model: haiku
name: Ops
description: "[DEPRECATED] Use platform-specific ops agents (Local Ops, Vercel Ops, GCP Ops, AWS Ops, DigitalOcean Ops)"
deprecated: true
agent_id: ops
agent_type: ops
---

# Ops Agent

Body content is irrelevant to metadata parsing.
"""

ENGINEER_FRONTMATTER = """---
model: sonnet
name: Engineer
description: "General-purpose engineering agent."
agent_id: engineer
agent_type: engineer
---

# Engineer Agent
"""


@pytest.fixture(autouse=True)
def _reset_deprecated_agents_cache():
    """Ensure each test starts with a clean per-cwd cache and model config.

    ``_DEPRECATED_AGENTS_CACHE`` is keyed by cwd, so distinct tmp_path
    fixtures across tests do not collide -- but we still clear it to keep
    tests fully independent of execution order/module state.

    ``_AGENT_MODEL_CONFIG`` is forced to an empty dict (rather than left as
    ``None``, which would trigger a real load) so tests never pick up the
    developer machine's actual ``~/.claude-mpm/config/configuration.yaml``
    (which may set per-agent model overrides, e.g. ``engineer: opus``) --
    these tests only care about the deprecation guard and the
    frontmatter-based model fallback, not real user config.
    """
    model_tier_hook._DEPRECATED_AGENTS_CACHE.clear()
    model_tier_hook._AGENT_MODEL_CONFIG = {}
    yield
    model_tier_hook._DEPRECATED_AGENTS_CACHE.clear()
    model_tier_hook._AGENT_MODEL_CONFIG = None


def _write_agent(agents_dir: Path, filename: str, content: str) -> None:
    agents_dir.mkdir(parents=True, exist_ok=True)
    (agents_dir / filename).write_text(content, encoding="utf-8")


def _agent_event(subagent_type: str, cwd: str) -> dict:
    return {
        "hook_event_name": "PreToolUse",
        "tool_name": "Agent",
        "tool_input": {"subagent_type": subagent_type},
        "cwd": cwd,
    }


# ---------------------------------------------------------------------------
# (a) Deprecated agent dispatch is blocked with the expected message
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_deprecated_agent_dispatch_is_denied(tmp_path: Path) -> None:
    """Dispatching a deprecated agent by its filename stem must be denied."""
    agents_dir = tmp_path / ".claude" / "agents"
    _write_agent(agents_dir, "ops.md", OPS_FRONTMATTER)

    response = model_tier_hook.build_model_tier_response(
        _agent_event("ops", str(tmp_path))
    )

    spec = response["hookSpecificOutput"]
    assert spec["hookEventName"] == "PreToolUse"
    assert spec["permissionDecision"] == "deny"
    assert spec["permissionDecisionReason"] == (
        "[DEPRECATED] Use platform-specific ops agents "
        "(Local Ops, Vercel Ops, GCP Ops, AWS Ops, DigitalOcean Ops)"
    )


@pytest.mark.unit
def test_deprecated_agent_denied_even_with_explicit_model(tmp_path: Path) -> None:
    """Pre-setting ``model`` in tool_input must not bypass the deprecation guard."""
    agents_dir = tmp_path / ".claude" / "agents"
    _write_agent(agents_dir, "ops.md", OPS_FRONTMATTER)

    event = _agent_event("ops", str(tmp_path))
    event["tool_input"]["model"] = "opus"

    response = model_tier_hook.build_model_tier_response(event)

    spec = response["hookSpecificOutput"]
    assert spec["permissionDecision"] == "deny"


# ---------------------------------------------------------------------------
# (b) Non-deprecated agent dispatch is unaffected
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_non_deprecated_agent_falls_through_to_model_injection(
    tmp_path: Path,
) -> None:
    """A non-deprecated agent must not be denied; normal tier logic still runs."""
    agents_dir = tmp_path / ".claude" / "agents"
    _write_agent(agents_dir, "ops.md", OPS_FRONTMATTER)
    _write_agent(agents_dir, "engineer.md", ENGINEER_FRONTMATTER)

    model_tier_hook._pretool_modify_supported = True
    try:
        response = model_tier_hook.build_model_tier_response(
            _agent_event("engineer", str(tmp_path))
        )
    finally:
        model_tier_hook._pretool_modify_supported = None

    spec = response["hookSpecificOutput"]
    assert spec.get("permissionDecision") != "deny"
    assert "updatedInput" in spec
    assert spec["updatedInput"]["model"] == "sonnet"


@pytest.mark.unit
def test_missing_agents_directory_fails_open(tmp_path: Path) -> None:
    """No ``.claude/agents/`` directory at all must not crash or deny."""
    model_tier_hook._pretool_modify_supported = True
    try:
        response = model_tier_hook.build_model_tier_response(
            _agent_event("engineer", str(tmp_path))
        )
    finally:
        model_tier_hook._pretool_modify_supported = None

    spec = response["hookSpecificOutput"]
    assert spec.get("permissionDecision") != "deny"


# ---------------------------------------------------------------------------
# (c) Case-insensitive matching against both identity schemes
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.parametrize(
    "subagent_type",
    [
        "ops",
        "Ops",
        "OPS",
        "Ops Agent",
        "ops-agent",
    ],
)
def test_case_insensitive_match_against_filename_stem_and_name_field(
    tmp_path: Path, subagent_type: str
) -> None:
    """Both filename-stem ("ops") and name-field ("Ops") schemes must match.

    ``normalize_agent_id`` strips an ``-agent`` suffix and lowercases/
    dashes the input, so "Ops Agent" / "ops-agent" normalize to the same
    key as the filename stem "ops" and the frontmatter ``name: Ops`` field.
    """
    agents_dir = tmp_path / ".claude" / "agents"
    _write_agent(agents_dir, "ops.md", OPS_FRONTMATTER)

    response = model_tier_hook.build_model_tier_response(
        _agent_event(subagent_type, str(tmp_path))
    )

    spec = response["hookSpecificOutput"]
    assert spec["permissionDecision"] == "deny", (
        f"Expected deny for subagent_type={subagent_type!r}"
    )


@pytest.mark.unit
def test_case_insensitive_match_against_explicit_agent_id_field(
    tmp_path: Path,
) -> None:
    """A deprecated agent whose ``name:`` differs from its ``agent_id:`` must
    still be matched via the explicit ``agent_id:`` frontmatter field.
    """
    frontmatter = """---
name: Local Operations
description: "[DEPRECATED] Use platform-specific ops agents instead."
deprecated: true
agent_id: local-ops-agent
---
"""
    agents_dir = tmp_path / ".claude" / "agents"
    _write_agent(agents_dir, "local-operations.md", frontmatter)

    response = model_tier_hook.build_model_tier_response(
        _agent_event("Local-Ops-Agent", str(tmp_path))
    )

    spec = response["hookSpecificOutput"]
    assert spec["permissionDecision"] == "deny"
    assert "DEPRECATED" in spec["permissionDecisionReason"]


@pytest.mark.unit
def test_deprecated_false_is_not_blocked(tmp_path: Path) -> None:
    """An agent with ``deprecated: false`` (or absent) must never be denied."""
    frontmatter = """---
name: Fresh Agent
description: "A perfectly supported agent."
deprecated: false
agent_id: fresh
---
"""
    agents_dir = tmp_path / ".claude" / "agents"
    _write_agent(agents_dir, "fresh.md", frontmatter)

    model_tier_hook._pretool_modify_supported = True
    try:
        response = model_tier_hook.build_model_tier_response(
            _agent_event("fresh", str(tmp_path))
        )
    finally:
        model_tier_hook._pretool_modify_supported = None

    spec = response["hookSpecificOutput"]
    assert spec.get("permissionDecision") != "deny"


@pytest.mark.unit
def test_deprecated_agent_without_description_still_blocked_with_fallback_reason(
    tmp_path: Path,
) -> None:
    """A deprecated agent lacking real description text must still be denied.

    ``deprecated: true`` is the authoritative signal; a missing/placeholder
    description must never be treated as "not deprecated" (that would let a
    malformed agent file silently bypass the guard). A generic fallback
    reason referencing the agent is used instead of inventing content.
    """
    frontmatter = """---
name: Broken
deprecated: true
agent_id: broken
---
"""
    agents_dir = tmp_path / ".claude" / "agents"
    _write_agent(agents_dir, "broken.md", frontmatter)

    response = model_tier_hook.build_model_tier_response(
        _agent_event("broken", str(tmp_path))
    )

    spec = response["hookSpecificOutput"]
    assert spec["permissionDecision"] == "deny"
    assert "broken" in spec["permissionDecisionReason"]
    assert "deprecated" in spec["permissionDecisionReason"]


@pytest.mark.unit
def test_scan_deprecated_agents_is_cached_per_cwd(tmp_path: Path) -> None:
    """Repeated calls with the same cwd must reuse the cached scan result."""
    agents_dir = tmp_path / ".claude" / "agents"
    _write_agent(agents_dir, "ops.md", OPS_FRONTMATTER)

    first = model_tier_hook._scan_deprecated_agents(str(tmp_path))
    # Mutate the directory after the first scan; a cached second call must
    # not pick up the new file (proves caching, not just idempotent scanning).
    _write_agent(agents_dir, "engineer.md", ENGINEER_FRONTMATTER)
    second = model_tier_hook._scan_deprecated_agents(str(tmp_path))

    assert first == second
    assert "ops" in first

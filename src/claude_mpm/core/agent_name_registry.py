"""Agent Name Registry — single source of truth for agent stem-to-name mappings.

This module provides the canonical mapping between agent filename stems
(e.g., ``"local-ops"``) and their ``name:`` frontmatter field values
(e.g., ``"Local Ops"``) as declared in the deployed ``.md`` agent files
under ``.claude/agents/``.

The mapping is used by PM delegation logic to resolve ``subagent_type``
parameters against the actual ``name:`` field values that agents register.

Usage::

    from claude_mpm.core.agent_name_registry import (
        AGENT_NAME_MAP,
        NAME_TO_STEM,
        get_agent_name,
        get_agent_stem,
        CORE_AGENT_IDS,
        get_agent_name_map,
        invalidate_cache,
    )

    # Stem -> name
    name = get_agent_name("local-ops")       # "Local Ops"

    # Name -> stem (returns the first/canonical stem)
    stem = get_agent_stem("Web QA")          # "web-qa"

    # Graceful fallback: returns input unchanged if not found
    unknown = get_agent_name("nonexistent")  # "nonexistent"

    # Dynamic map with runtime refresh
    name_map = get_agent_name_map()

Note:
    This module is intentionally self-contained and does NOT import from
    any other ``claude_mpm`` module.  It must remain importable without
    side-effects so that it can serve as a low-level dependency.
"""

import re
from pathlib import Path

import yaml

# ---------------------------------------------------------------------------
# Canonical mapping: filename stem -> name: frontmatter value
# ---------------------------------------------------------------------------
# Only hyphen-format stems are included.  Where both a bare stem and a
# ``-agent`` suffixed stem exist as deployed files, both are listed because
# they resolve to the same ``name:`` value.
# ---------------------------------------------------------------------------

AGENT_NAME_MAP: dict[str, str] = {
    # ── Core agents ───────────────────────────────────────────────────────
    "engineer": "Engineer",
    "research": "Research",
    "qa": "QA",
    "documentation": "Documentation Agent",
    "ops": "Ops",
    "security": "Security",
    "version-control": "Version Control",
    "code-analyzer": "Code Analysis",
    "ticketing": "ticketing_agent",  # matches name: frontmatter (ID-style)
    # ── Engineering language agents ────────────────────────────────────────
    "python-engineer": "Python Engineer",
    "golang-engineer": "Golang Engineer",
    "java-engineer": "Java Engineer",
    "javascript-engineer": "Javascript Engineer",
    "typescript-engineer": "Typescript Engineer",
    "rust-engineer": "Rust Engineer",
    "ruby-engineer": "Ruby Engineer",
    "php-engineer": "Php Engineer",
    "dart-engineer": "Dart Engineer",
    "visual-basic-engineer": "Visual Basic Engineer",
    # ── Engineering framework agents ──────────────────────────────────────
    "react-engineer": "React Engineer",
    "nextjs-engineer": "Nextjs Engineer",
    "svelte-engineer": "Svelte Engineer",
    "nestjs-engineer": "nestjs-engineer",  # matches name: frontmatter (ID-style)
    "phoenix-engineer": "Phoenix Engineer",
    "tauri-engineer": "Tauri Engineer",
    # ── Specialist engineers ──────────────────────────────────────────────
    "data-engineer": "Data Engineer",
    "data-scientist": "Data Scientist",
    "refactoring-engineer": "Refactoring Engineer",
    "prompt-engineer": "Prompt Engineer",
    "web-ui": "Web UI",
    # ── Ops platform agents ───────────────────────────────────────────────
    "local-ops": "Local Ops",
    "vercel-ops": "Vercel Ops",
    "gcp-ops": "Google Cloud Ops",
    "clerk-ops": "Clerk Operations",
    "digitalocean-ops": "DigitalOcean Ops",
    "aws-ops": "aws_ops_agent",  # matches name: frontmatter (ID-style)
    # ── QA agents ─────────────────────────────────────────────────────────
    "web-qa": "Web QA",
    "api-qa": "API QA",
    "real-user": "real-user",  # matches name: frontmatter (ID-style)
    # ── Utility agents ────────────────────────────────────────────────────
    "memory-manager-agent": "Memory Manager",
    "project-organizer": "Project Organizer",
    "product-owner": "Product Owner",
    "content-agent": "Content Optimization",
    "imagemagick": "Imagemagick",
    "agentic-coder-optimizer": "Agentic Coder Optimizer",
    "tmux-agent": "Tmux Agent",
    # ── Bare-stem entries for agents deployed with -agent suffix stripped ──
    # (normalize_deployment_filename strips -agent → "content-agent.md" becomes "content.md")
    "content": "Content Optimization",
    "memory-manager": "Memory Manager",
    "tmux": "Tmux Agent",
    # ── MPM meta agents ───────────────────────────────────────────────────
    "mpm-agent-manager": "mpm_agent_manager",  # matches name: frontmatter (ID-style)
    "mpm-skills-manager": "mpm_skills_manager",  # matches name: frontmatter (ID-style)
    # ── Legacy -agent suffix variants (backward compatibility) ────────────
    # These deployed files carry the same name: values as their bare stems.
    "research-agent": "Research",
    "qa-agent": "QA",
    "documentation-agent": "Documentation Agent",
    "ops-agent": "Ops",
    "security-agent": "Security",
    "web-qa-agent": "Web QA",
    "api-qa-agent": "API QA",
    "local-ops-agent": "Local Ops",
    "vercel-ops-agent": "Vercel Ops",
    "gcp-ops-agent": "Google Cloud Ops",
    "digitalocean-ops-agent": "DigitalOcean Ops",
    "javascript-engineer-agent": "Javascript Engineer",
    "web-ui-engineer": "Web UI",
    "ticketing-agent": "ticketing_agent",  # matches name: frontmatter (ID-style)
    "aws-ops-agent": "aws_ops_agent",  # matches name: frontmatter (ID-style)
}

# ---------------------------------------------------------------------------
# Reverse mapping: name -> stem
# ---------------------------------------------------------------------------
# Built from AGENT_NAME_MAP.  When multiple stems map to the same name
# (e.g. "research" and "research-agent" both map to "Research"), the
# *first* (canonical, shorter) stem wins because it appears earlier in
# the dict and is therefore written first by the comprehension.  We then
# skip overwriting with the legacy suffix variant.
# ---------------------------------------------------------------------------

NAME_TO_STEM: dict[str, str] = {}
for _stem, _name in AGENT_NAME_MAP.items():
    if _name not in NAME_TO_STEM:
        NAME_TO_STEM[_name] = _stem


# ---------------------------------------------------------------------------
# Lookup helpers
# ---------------------------------------------------------------------------


def get_agent_name(stem: str) -> str:
    """Return the ``name:`` frontmatter value for the given filename *stem*.

    Why: PM delegation requires the exact ``name:`` value declared in an agent's
    frontmatter; a plain filename stem (e.g. ``"local-ops"``) may not match the
    display name (``"Local Ops"``).  This helper centralises the lookup so
    callers never hardcode the mapping themselves.

    If the stem is not found in :data:`AGENT_NAME_MAP`, the input is
    returned unchanged so that callers degrade gracefully.

    Args:
        stem: The hyphenated filename stem (e.g. ``"local-ops"``).

    Returns:
        The agent's ``name:`` field value, or *stem* itself as a fallback.

    Test: ``get_agent_name("local-ops") == "Local Ops"`` and
    ``get_agent_name("nonexistent") == "nonexistent"`` (graceful fallback).
    """
    return AGENT_NAME_MAP.get(stem, stem)


def get_agent_stem(name: str) -> str:
    """Return the canonical filename stem for the given agent *name*.

    Why: Some callers start with a human-readable name (e.g. from a config
    file or user input) and need the filesystem stem to locate the deployed
    ``.md`` file.  This is the reverse of :func:`get_agent_name` and must
    return the *canonical* (shortest) stem when multiple stems share a name.

    If the name is not found in :data:`NAME_TO_STEM`, the input is
    returned unchanged so that callers degrade gracefully.

    Args:
        name: The ``name:`` frontmatter value (e.g. ``"Local Ops"``).

    Returns:
        The canonical filename stem, or *name* itself as a fallback.

    Test: ``get_agent_stem("Web QA") == "web-qa"`` (not ``"web-qa-agent"``).
    ``get_agent_stem("unknown") == "unknown"`` (graceful passthrough).
    """
    return NAME_TO_STEM.get(name, name)


# ---------------------------------------------------------------------------
# Core agent IDs — canonical set of essential agents (bare filename stems)
# ---------------------------------------------------------------------------
# This set defines agents that are:
#   1. Auto-deployed when no configuration exists (framework_agent_loader)
#   2. Always included in toolchain recommendations (toolchain_detector)
#   3. Protected from undeployment (agent_deployment_handler)
#
# Phase 2 rationale for membership (supersedes prior per-file lists):
#   - engineer, research, qa, documentation: foundational PM workflow agents
#   - security: essential for pre-push credential scanning
#   - local-ops: replaces generic "ops" — specific to local dev (the common case)
#   - version-control: git operations, PR workflows, branch management
#   - code-analyzer: solution review gate (Phase 2 of PM workflow)
#
# Agents intentionally NOT in this set:
#   - ops (generic): superseded by local-ops; platform-specific ops agents
#     (vercel-ops, gcp-ops, etc.) are additive, not core
#   - ticketing: important for PM but not universally needed; deployed via
#     presets or auto-config, not forced as core
#   - web-qa: specialized QA variant; base "qa" covers general testing
#   - memory-manager-agent: utility agent, not essential for delegation
# ---------------------------------------------------------------------------

CORE_AGENT_IDS: frozenset[str] = frozenset(
    {
        "research",
        "engineer",
        "qa",
        "security",
        "local-ops",
        "version-control",
        "documentation",
        "code-analyzer",
    }
)


# ---------------------------------------------------------------------------
# Dynamic refresh — runtime discovery from deployed agent files
# ---------------------------------------------------------------------------

_runtime_name_map: dict[str, str] | None = None


def get_agent_name_map() -> dict[str, str]:
    """Get agent name map with runtime refresh from deployed agents.

    Why: The hardcoded :data:`AGENT_NAME_MAP` cannot know about custom or
    newly-deployed agents.  This function overlays runtime-discovered mappings
    so that delegation works for agents not yet in the static table.  Results
    are module-level cached to avoid repeated filesystem scans; call
    :func:`invalidate_cache` after deploying new agents.

    Priority:
        1. Runtime-discovered agents from ``.claude/agents/`` (most current)
        2. Cached agents from ``~/.claude-mpm/cache/agents/`` (second choice)
        3. Hardcoded :data:`AGENT_NAME_MAP` (fallback for testing/CI)

    Returns:
        A ``dict[str, str]`` mapping filename stems to ``name:`` values.

    Test: In a project with a custom ``my-agent.md`` whose frontmatter declares
    ``name: My Agent``, ``get_agent_name_map()["my-agent"] == "My Agent"``
    after the cache has been invalidated.
    """
    global _runtime_name_map

    if _runtime_name_map is not None:
        return _runtime_name_map

    # Start with hardcoded baseline
    result = dict(AGENT_NAME_MAP)

    # Try to discover from deployed agents
    discovered = _discover_agents_from_paths(
        [
            Path.cwd() / ".claude" / "agents",
            Path.home() / ".claude-mpm" / "cache" / "agents",
        ]
    )

    # Override hardcoded with discovered (discovered is fresher)
    result.update(discovered)

    _runtime_name_map = result
    return result


def invalidate_cache() -> None:
    """Invalidate the runtime cache so the next call re-scans the filesystem.

    Why: :func:`get_agent_name_map` caches its result to avoid repeated disk
    reads.  After an agent is deployed or removed the cached result is stale;
    callers (e.g. deployment handlers) must call this function to force a fresh
    discovery on the next access.

    What: Resets the module-level ``_runtime_name_map`` sentinel to ``None``.

    Test: Call ``get_agent_name_map()``, then ``invalidate_cache()``, then
    ``get_agent_name_map()`` again and verify the second call re-reads
    deployed ``.md`` files (e.g. by adding a file between the two calls).
    """
    global _runtime_name_map
    _runtime_name_map = None


def _discover_agents_from_paths(search_paths: list[Path]) -> dict[str, str]:
    """Read agent ``.md`` files and extract ``name:`` field values.

    Why: Runtime discovery lets the registry learn about agents that were
    deployed after the package was built, without requiring a code change.
    Each ``.md`` file is expected to carry a YAML frontmatter block with a
    ``name:`` key; files without valid frontmatter are silently skipped.

    What: Iterates over each directory in *search_paths*, globs ``*.md``,
    parses the YAML frontmatter, and maps ``stem -> name`` for every file
    that declares a ``name`` field.

    Test: Create a temp directory with ``my-agent.md`` containing valid
    frontmatter (``name: My Agent``).  Call
    ``_discover_agents_from_paths([tmp_dir])`` and assert the result equals
    ``{"my-agent": "My Agent"}``.  A file with invalid YAML should not raise
    and should simply be absent from the result.
    """
    discovered: dict[str, str] = {}
    for dir_path in search_paths:
        if not dir_path.is_dir():
            continue
        for md_file in sorted(dir_path.glob("*.md")):
            content = md_file.read_text(errors="replace")
            match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
            if match:
                try:
                    frontmatter = yaml.safe_load(match.group(1))
                    if isinstance(frontmatter, dict) and "name" in frontmatter:
                        discovered[md_file.stem] = frontmatter["name"]
                except (yaml.YAMLError, Exception):
                    pass
    return discovered

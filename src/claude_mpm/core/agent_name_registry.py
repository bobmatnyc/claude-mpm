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
    "ticketing": "ticketing_agent",
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
    "nestjs-engineer": "nestjs-engineer",
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
    "aws-ops": "aws_ops_agent",
    "digitalocean-ops": "DigitalOcean Ops",
    # ── QA agents ─────────────────────────────────────────────────────────
    "web-qa": "Web QA",
    "api-qa": "API QA",
    "real-user": "real-user",
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
    "mpm-agent-manager": "mpm_agent_manager",
    "mpm-skills-manager": "mpm_skills_manager",
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
    "ticketing-agent": "ticketing_agent",
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

    If the stem is not found in :data:`AGENT_NAME_MAP`, the input is
    returned unchanged so that callers degrade gracefully.

    Args:
        stem: The hyphenated filename stem (e.g. ``"local-ops"``).

    Returns:
        The agent's ``name:`` field value, or *stem* itself as a fallback.
    """
    return AGENT_NAME_MAP.get(stem, stem)


def get_agent_stem(name: str) -> str:
    """Return the canonical filename stem for the given agent *name*.

    If the name is not found in :data:`NAME_TO_STEM`, the input is
    returned unchanged so that callers degrade gracefully.

    Args:
        name: The ``name:`` frontmatter value (e.g. ``"Local Ops"``).

    Returns:
        The canonical filename stem, or *name* itself as a fallback.
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

    Priority:
        1. Runtime-discovered agents from ``.claude/agents/`` (most current)
        2. Cached agents from ``~/.claude-mpm/cache/agents/`` (second choice)
        3. Hardcoded :data:`AGENT_NAME_MAP` (fallback for testing/CI)

    Returns:
        A ``dict[str, str]`` mapping filename stems to ``name:`` values.
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
    """Invalidate the runtime cache (call after deployment)."""
    global _runtime_name_map
    _runtime_name_map = None


def _discover_agents_from_paths(search_paths: list[Path]) -> dict[str, str]:
    """Read agent ``.md`` files and extract ``name:`` field values."""
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

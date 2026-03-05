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
    )

    # Stem -> name
    name = get_agent_name("local-ops")       # "Local Ops"

    # Name -> stem (returns the first/canonical stem)
    stem = get_agent_stem("Web QA")          # "web-qa"

    # Graceful fallback: returns input unchanged if not found
    unknown = get_agent_name("nonexistent")  # "nonexistent"

Note:
    This module is intentionally self-contained and does NOT import from
    any other ``claude_mpm`` module.  It must remain importable without
    side-effects so that it can serve as a low-level dependency.
"""

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

"""Spec-Linked Documentation (SLD) configuration helpers.

WHAT: Provides a single function to read the ``workflow.spec_linked_docs.enabled``
flag from the MPM config, and a companion function that returns the SLD skill
instruction block to inject into engineer / documentation agent prompts when the
flag is true.  All functions return safe defaults (disabled, empty string) when
the config is absent or the key is missing — backward compatible by design.

WHY: SLD is an opt-in convention (see docs/specs/README.md).  Centralizing the
flag-read and instruction-generation here lets the agent-assembly pipeline (and
future hooks) call one clean function rather than duplicating config key paths.
The module intentionally has zero side effects on import.

References
----------
The SLD convention is documented in docs/specs/README.md.
The skill that engineers use is bundled at
src/claude_mpm/skills/bundled/universal/spec-linked-docs/SKILL.md.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from claude_mpm.core.config import Config

# ---------------------------------------------------------------------------
# Default values
# ---------------------------------------------------------------------------

#: Config key path (dot-notation) for the SLD feature toggle.
SLD_CONFIG_KEY = "workflow.spec_linked_docs.enabled"

#: Default — SLD is OFF unless explicitly enabled by the user.
SLD_DEFAULT_ENABLED = False

#: The skill name as registered in the bundled skills directory.
SLD_SKILL_NAME = "spec-linked-docs"

#: Agent types that receive SLD instruction injection when the flag is on.
#: These are **category** values stored in the ``agent_type`` frontmatter field,
#: not agent *names* (which may be slugs like ``python-engineer``).
#: An agent_type of ``"engineer"`` covers all engineer-variant agents because
#: the frontmatter ``agent_type`` field is always the canonical category
#: (e.g. both ``rust-engineer.md`` and ``python-engineer.md`` declare
#: ``agent_type: engineer``).  See :func:`is_sld_target_agent_type` for the
#: matching logic that also handles the unlikely case where agent_type contains
#: a hyphenated suffix (e.g. ``"python-engineer"``).
SLD_TARGET_AGENT_TYPES = frozenset({"engineer", "documentation"})

# ---------------------------------------------------------------------------
# Instruction text
# ---------------------------------------------------------------------------

_SLD_INSTRUCTION_BLOCK = """\
## Spec-Linked Documentation (SLD) — Active for this project

This project has enabled the **Spec-Linked Documentation (SLD)** convention
(`workflow.spec_linked_docs.enabled: true` in configuration.yaml).

### WWL — WHAT / WHY / LINK (granularity rule)

Every Python file under `src/claude_mpm/` needs a **module-level WWL**:
a module docstring containing `WHAT:` (one-line observable behaviour) and
`WHY:` (rationale).  `LINK: SPEC-{SUBSYSTEM}-{NN}~{rev}` ties it to a
governing spec; use `LINK: none` to flag an acknowledged backfill gap.

Functions, methods, and classes need their own WWL doc-comment when they
exceed **either** threshold:

- **LOC > 50** (lines of code), **or**
- **Cyclomatic complexity > 10** (McCabe 1976 / NIST SP 500-235)

Units under both thresholds may include WWL voluntarily.

**Backfill model:** Legacy gaps are captured in `docs/specs/.wwl-baseline.json`.
The CI check (`tests/test_wwl_granularity.py`) fails only on violations NOT
in that baseline — new code is blocked immediately; old code is tolerated until
the team bacfills it and removes entries from the baseline.

### SLD steps

1. **Check `docs/specs/` first** — read any spec that governs your subsystem.

2. **Add a module-level WWL docstring** (WHAT + WHY, plus References / LINK):

   ```python
   \"\"\"
   Module description.

   WHAT: ...
   WHY: ...

   References
   ----------
   SPEC-SUBSYSTEM-01~1 : docs/specs/subsystem.md#SPEC-SUBSYSTEM-01~1
   \"\"\"
   ```

3. **Add WWL to over-threshold functions/classes** (WHAT + WHY at minimum):

   ```python
   def my_function():
       \"\"\"
       Brief description.

       WHAT: ...
       WHY: ...

       :spec: SPEC-SUBSYSTEM-01~1
       \"\"\"
   ```

4. **Update the "Implementing Modules" table** in the spec file when you add
   or remove a module from a governed subsystem.

5. **Run the CI checks** before opening a PR:

   ```bash
   uv run pytest tests/test_spec_traceability.py tests/test_wwl_granularity.py \\
       -p no:xdist -v
   ```

**Important:** The CI checks verify that links *exist*, not that they are
*correct*. Always confirm spec IDs point to the right spec section.

See `docs/specs/README.md` and the `spec-linked-docs` skill for full guidance.
"""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def is_sld_target_agent_type(agent_type: str) -> bool:
    """Return True when *agent_type* should receive the SLD instruction block.

    WHAT: Checks whether *agent_type* is in (or is a hyphenated variant of) one
    of the target categories in :data:`SLD_TARGET_AGENT_TYPES`.  The primary
    matching rule is an exact membership test, which covers all real cases
    because the ``agent_type`` frontmatter field is always set to the canonical
    category string (``"engineer"``, ``"documentation"``, etc.).  A secondary
    suffix rule handles the defensive case where a template sets ``agent_type``
    to a hyphenated slug like ``"python-engineer"`` or ``"api-documentation"``.

    WHY: Centralising the matching logic here keeps :func:`get_sld_instruction_for_agent`
    and the agent-assembly pipeline consistent.  Tests can import and exercise
    this helper directly without constructing a full agent pipeline.

    Parameters
    ----------
    agent_type : str
        The raw ``agent_type`` value from an agent's frontmatter or template.

    Returns
    -------
    bool
        True if SLD instructions should be injected for this agent type.

    Examples
    --------
    >>> is_sld_target_agent_type("engineer")
    True
    >>> is_sld_target_agent_type("python-engineer")
    True
    >>> is_sld_target_agent_type("documentation")
    True
    >>> is_sld_target_agent_type("qa")
    False
    >>> is_sld_target_agent_type("ops")
    False
    """
    if not agent_type:
        return False
    # Exact match is the common case (frontmatter always stores the category)
    if agent_type in SLD_TARGET_AGENT_TYPES:
        return True
    # Suffix match: covers hypothetical hyphenated variants (defensive)
    for category in SLD_TARGET_AGENT_TYPES:
        if agent_type.endswith(f"-{category}"):
            return True
    return False


def is_sld_enabled(config: Config | None = None) -> bool:
    """Return True when the SLD feature toggle is active.

    Reads ``workflow.spec_linked_docs.enabled`` from *config*.  Returns the
    safe default (False) when *config* is None or the key is absent.

    WHAT: Accepts an optional :class:`~claude_mpm.core.config.Config` instance
    and returns a bool indicating whether the SLD convention is enabled for this
    project.  When the key is missing or config is None the function returns
    False — backward compatible with all existing projects.

    WHY: Centralising the flag read here means callers (agent assembler, hooks,
    tests) do not hardcode the config key path.  Defaulting to False makes SLD
    purely opt-in without requiring any config migration for existing projects.

    Parameters
    ----------
    config : Config or None
        An initialised :class:`~claude_mpm.core.config.Config` singleton.  If
        None the function attempts to import and use the global singleton; if
        that too fails, False is returned.

    Returns
    -------
    bool
        True only when ``workflow.spec_linked_docs.enabled`` is explicitly
        set to a truthy value.

    Examples
    --------
    >>> is_sld_enabled()
    False
    >>> is_sld_enabled(config=None)
    False
    """
    if config is None:
        try:
            from claude_mpm.core.config import Config

            config = Config()
        except Exception:
            return SLD_DEFAULT_ENABLED

    try:
        value = config.get(SLD_CONFIG_KEY, SLD_DEFAULT_ENABLED)
        return bool(value)
    except Exception:
        return SLD_DEFAULT_ENABLED


def get_sld_instruction_block() -> str:
    """Return the SLD instruction text to inject into agent prompts.

    WHAT: Returns the static Markdown instruction block that explains the SLD
    convention to an engineer or documentation agent.  The caller is responsible
    for checking :func:`is_sld_enabled` before injecting.  Returns an empty
    string when SLD is disabled so callers can safely concatenate without guards.

    WHY: Keeping the instruction text here (rather than hard-coding it in the
    agent `.md` files or the assembly pipeline) means the text evolves in one
    place and tests can assert the expected content without touching agent files.

    Returns
    -------
    str
        The SLD instruction block, or an empty string if the internal constant
        is blank.

    Examples
    --------
    >>> block = get_sld_instruction_block()
    >>> "spec-linked-docs" in block.lower() or "SLD" in block
    True
    """
    return _SLD_INSTRUCTION_BLOCK


def get_sld_instruction_for_agent(
    agent_type: str,
    config: Config | None = None,
) -> str:
    """Return the SLD instruction block when SLD is enabled for this agent type.

    Convenience wrapper that combines :func:`is_sld_enabled` and
    :func:`get_sld_instruction_block` with an agent-type filter.

    WHAT: Given an *agent_type* string and an optional config, returns the full
    SLD instruction Markdown when all three conditions hold: (1) SLD is enabled
    in configuration, (2) the agent type is in :data:`SLD_TARGET_AGENT_TYPES`.
    Returns an empty string otherwise.

    WHY: Agent-assembly code can call this function once per agent and append
    the result to the agent's prompt, without needing to know the SLD config key
    or the target agent list.

    Parameters
    ----------
    agent_type : str
        The agent type from its frontmatter (e.g. ``"engineer"``,
        ``"documentation"``).
    config : Config or None
        Passed directly to :func:`is_sld_enabled`.

    Returns
    -------
    str
        SLD instruction block if enabled and applicable, otherwise empty string.

    Examples
    --------
    >>> get_sld_instruction_for_agent("engineer")
    ''
    >>> get_sld_instruction_for_agent("research")
    ''
    """
    if not is_sld_target_agent_type(agent_type):
        return ""
    if not is_sld_enabled(config=config):
        return ""
    return get_sld_instruction_block()


def get_sld_default_config() -> dict:
    """Return the default SLD configuration sub-dict for use in Config._apply_defaults().

    WHAT: Returns the nested dict that should live under ``workflow`` in the
    configuration defaults — specifically ``spec_linked_docs: {enabled: false}``.

    WHY: Provides a single authoritative source for the default value so that
    ``Config._apply_defaults()`` and tests both import from the same place.

    Returns
    -------
    dict
        ``{"spec_linked_docs": {"enabled": False}}``

    Examples
    --------
    >>> cfg = get_sld_default_config()
    >>> cfg["spec_linked_docs"]["enabled"]
    False
    """
    return {
        "spec_linked_docs": {
            "enabled": SLD_DEFAULT_ENABLED,
            # Informational comment preserved in YAML templates:
            # opt-in: when true, engineers build SLD specs + traceability
            # alongside code (see docs/specs/README.md).
            "wwl": {
                # Require WHAT + WHY at module level for every .py file.
                "file_level_required": True,
                # LOC threshold — units exceeding this need a WWL doc-comment.
                # Grounded in common linter defaults (black, pylint, ruff).
                "function_line_threshold": 50,
                # Cyclomatic complexity threshold (McCabe 1976 / NIST SP 500-235).
                # CC > 10 is the widely-adopted "high-risk" boundary.
                "complexity_threshold": 10,
                # Enforcement mode: off | baseline | strict
                #   off      — report only, never fail CI
                #   baseline — fail only on violations NOT in .wwl-baseline.json
                #   strict   — fail on any violation
                "enforcement": "baseline",
            },
        }
    }

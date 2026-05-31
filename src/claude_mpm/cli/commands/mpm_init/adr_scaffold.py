"""ADR scaffold for mpm-init — creates docs/adr/ convention files.

WHY: Issue #562 — make ADRs a first-class, opt-in convention in claude-mpm.
     When a new project is initialised with ``/mpm-init``, we drop a
     ``docs/adr/`` directory containing a README and the Nygard template so
     the location is standardised and ready to use without ceremony.

DESIGN DECISIONS:
- Idempotent: never clobbers an existing README.md or 0000-template.md.
- Opt-in: the scaffold only runs during mpm-init; nothing forces ADR usage.
- Location: ``docs/adr/`` (workspace-wide decisions).  Component-specific
  decisions go in ``docs/<component>/decisions/`` — that is project-managed
  and intentionally not scaffolded here.

Prior art: bobmatnyc/trusty-tools
"""

from pathlib import Path

# ---------------------------------------------------------------------------
# Content constants
# ---------------------------------------------------------------------------

_README_CONTENT = """\
# Architecture Decision Records

This directory contains Architecture Decision Records (ADRs) for this project.

ADRs capture *why* a significant architectural decision was made — not just
what was decided.  They live alongside the code so future contributors can
understand the constraints and trade-offs that shaped the system.

## When to write an ADR

Write an ADR **only** when all three conditions hold:

1. **Architecturally significant** — the decision shapes how major parts of
   the system are structured, constrains future options, or affects multiple
   teams or components.
2. **Costly to reverse** — changing the decision later would require
   substantial rework, data migration, or coordination.
3. **Not obvious from the code** — the rationale is not apparent from
   reading the implementation alone.

Typical candidates: choice of database, async framework, authentication
approach, service boundary definition, major dependency selection, or a
cross-cutting pattern (error handling, logging format).

**Do NOT write an ADR** for routine bug fixes, small features, style
decisions, or anything already obvious from the codebase.  Over-forcing
ADRs is the documented adoption-killer.

## Hybrid location convention

| Scope | Location |
|---|---|
| Workspace-wide decisions | `docs/adr/NNNN-kebab-title.md` |
| Component-specific decisions | `docs/<component>/decisions/NNNN-kebab-title.md` |

## File naming

ADRs are numbered sequentially with zero-padded four-digit integers:

```
0000-template.md           ← master template (never a real decision)
0001-use-postgres.md
0002-adopt-async-framework.md
```

Pick the next available number: `ls docs/adr/ | sort | tail -5`

## Status lifecycle

| Status | Meaning |
|---|---|
| `Proposed` | Draft under discussion; not yet adopted |
| `Accepted` | Adopted — this is the current approach |
| `Deprecated` | No longer recommended; superseded or abandoned |
| `Superseded by [NNNN]` | Replaced by a later ADR |

Never delete old ADRs — the historical record is the point.  When a
decision changes, update the old ADR's status to `Superseded by NNNN`
and create a new ADR for the replacement.

## References

- Michael Nygard, "Documenting Architecture Decisions" (2011)
- [bobmatnyc/trusty-tools](https://github.com/bobmatnyc/trusty-tools)
- `/mpm-adr` skill — full template and workflow details
- `docs/features/adr.md` — trigger criteria and hybrid location guide
"""

_TEMPLATE_CONTENT = """\
# 0000. [Title — short, imperative: "Use X for Y"]

Date: YYYY-MM-DD

## Status

Proposed

## Context

<!--
What is the issue that is motivating this decision?
Describe the forces at play: technical constraints, team constraints,
organisational constraints, product requirements.  Be factual.
-->

## Decision

<!--
State the change that we are proposing or have agreed to implement.
Use active voice: "We will use X because Y."
-->

## Consequences

<!--
What becomes easier or more difficult as a result of this change?
List both positive and negative consequences.  Include known risks.
Be honest about trade-offs — this section is the most valuable part.
-->
"""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def scaffold_adr_directory(project_path: Path) -> dict[str, bool]:
    """Create ``docs/adr/`` with README and Nygard template if not present.

    This function is **idempotent**: it will never overwrite an existing
    ``README.md`` or ``0000-template.md``.  Re-running ``mpm-init`` on an
    already-initialised project is therefore safe.

    Args:
        project_path: Root directory of the target project.

    Returns:
        A dict mapping each relative path (str) to whether it was created
        (``True``) or already existed / skipped (``False``).

        Example::

            {
                "docs/adr/README.md": True,
                "docs/adr/0000-template.md": True,
            }
    """
    adr_dir = project_path / "docs" / "adr"
    adr_dir.mkdir(parents=True, exist_ok=True)

    created: dict[str, bool] = {}

    readme = adr_dir / "README.md"
    created["docs/adr/README.md"] = _write_if_absent(readme, _README_CONTENT)

    template = adr_dir / "0000-template.md"
    created["docs/adr/0000-template.md"] = _write_if_absent(template, _TEMPLATE_CONTENT)

    return created


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _write_if_absent(path: Path, content: str) -> bool:
    """Write *content* to *path* only if the file does not already exist.

    Args:
        path: Target file path.
        content: Text content to write.

    Returns:
        ``True`` if the file was written, ``False`` if it already existed.
    """
    if path.exists():
        return False
    path.write_text(content, encoding="utf-8")
    return True

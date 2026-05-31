---
name: mpm-adr
description: Architecture Decision Records (ADRs) — opt-in convention for documenting significant, hard-to-reverse architectural decisions using the Nygard template.
user-invocable: true
version: "1.0.0"
category: mpm-command
tags: [mpm-command, documentation, architecture, adr, pm-optional]
---

# /mpm-adr

Architecture Decision Records (ADRs) are short, structured documents that capture *why* a significant architectural decision was made — not just what was decided. They live alongside the code so future contributors understand the constraints and trade-offs that shaped the system.

This skill is **opt-in**. Only use it for decisions that are architecturally significant AND costly to reverse. Over-forcing ADRs on routine work is the documented adoption-killer.

---

## When to Write an ADR

Write an ADR **only** when all three conditions are true:

1. **Architecturally significant** — the decision shapes how major parts of the system are structured, constrain future options, or affect multiple teams/components.
2. **Costly to reverse** — undoing or changing the decision later would require substantial rework, data migration, or coordination.
3. **Not obvious from the code** — the rationale is not apparent from reading the implementation alone.

**Write an ADR for:**
- Choosing a database engine or persistence strategy
- Adopting an async framework or concurrency model
- Selecting an authentication/authorization approach
- Defining service boundaries or API contracts
- Committing to a major dependency or platform
- Establishing a cross-cutting pattern (error handling, logging format)
- Deprecating a foundational component

**Do NOT write an ADR for:**
- Routine bug fixes
- Small features or minor enhancements
- Style/formatting decisions (use a linter config)
- Decisions already obvious from the codebase
- Every library version bump

If you are unsure, ask: "Would a new team member in six months need to understand *why* this choice was made?" If no — skip it.

---

## File Location Convention

| Scope | Location |
|---|---|
| Workspace-wide decisions | `docs/adr/NNNN-kebab-title.md` |
| Component-specific decisions | `docs/<component>/decisions/NNNN-kebab-title.md` |

Use `docs/adr/` for decisions that span the whole project or affect architectural boundaries. Use `docs/<component>/decisions/` for decisions scoped to a single service or library within a monorepo.

---

## Numbering Convention

ADRs are numbered sequentially with zero-padded four-digit integers:

```
docs/adr/
  0000-template.md           ← master template (never a real decision)
  0001-use-postgres.md
  0002-adopt-async-framework.md
  0003-api-versioning-strategy.md
```

Pick the next available number by listing existing files:

```bash
ls docs/adr/ | sort | tail -5
```

---

## Status Lifecycle

Every ADR carries a `Status` field with one of these values:

| Status | Meaning |
|---|---|
| `Proposed` | Draft under discussion; not yet adopted |
| `Accepted` | Adopted — this is the current approach |
| `Deprecated` | No longer recommended; superseded or abandoned |
| `Superseded by [NNNN]` | Replaced by a later ADR (link to the new one) |

When a decision changes, update the old ADR's status to `Superseded by NNNN` and create a new ADR for the replacement. Never delete old ADRs — the historical record is the point.

---

## Nygard Template

```markdown
# NNNN. Title (short, imperative: "Use X for Y")

Date: YYYY-MM-DD

## Status

Proposed | Accepted | Deprecated | Superseded by [NNNN](NNNN-replacement.md)

## Context

What is the issue that we are seeing that is motivating this decision?
Describe the forces at play: technical constraints, team constraints,
organizational constraints, product requirements. Be factual.

## Decision

The change that we are proposing or have agreed to implement.
State the decision clearly in active voice: "We will use X."

## Consequences

What becomes easier or more difficult as a result of this change?
List both positive and negative consequences. Include known risks.
Be honest about trade-offs — this section is the most valuable part.
```

---

## Workflow

### Creating a new ADR

1. Run `/mpm-init` on a new project — `docs/adr/` is scaffolded with `README.md` and `0000-template.md`.
2. Copy `0000-template.md` to `NNNN-your-title.md` with the next number.
3. Fill in Context, Decision, and Consequences. Set Status to `Proposed`.
4. Submit for review. Once agreed, change Status to `Accepted`.
5. Commit with: `docs: ADR-NNNN adopt X for Y`

### Superseding an ADR

1. Create a new ADR (`MMMM-new-approach.md`) with Status `Accepted`.
2. Edit the old ADR's Status to `Superseded by [MMMM](MMMM-new-approach.md)`.
3. Commit both files together.

---

## Follow-up (Stretch Goal)

A future documentation-agent hook could auto-draft ADRs from significant commits or conversation context. This is tracked as a follow-up to issue #562 and is not part of the current implementation.

---

## References

- Michael Nygard, "Documenting Architecture Decisions" (2011)
- [bobmatnyc/trusty-tools](https://github.com/bobmatnyc/trusty-tools) — prior art for this convention
- `docs/features/adr.md` — trigger criteria and hybrid location guide

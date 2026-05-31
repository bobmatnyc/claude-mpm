# Architecture Decision Records (ADRs)

ADRs are short, structured documents that capture *why* a significant
architectural decision was made.  They are an **opt-in** convention in
claude-mpm — nothing forces their use, and that is intentional.

---

## Opt-in trigger criteria

Use an ADR **only** when all three of the following are true:

| Criterion | Question to ask |
|---|---|
| Architecturally significant | Does this decision constrain major structural choices, affect multiple components, or set a precedent for how the system is built? |
| Costly to reverse | Would undoing this later require substantial rework, data migration, or cross-team coordination? |
| Non-obvious from code | Would a future contributor reading the implementation still wonder *why* this approach was chosen? |

This threshold is deliberately the same one used to decide whether the
Code-Analysis phase runs: high-impact, hard-to-undo, not self-explanatory.

**If any criterion is missing, do not write an ADR.**

Examples that pass the threshold:
- Choosing PostgreSQL over SQLite as the primary persistence layer
- Adopting asyncio for all I/O-bound services
- Establishing a JWT-based auth strategy
- Defining a monorepo service-boundary policy

Examples that fail (do not write an ADR):
- Fixing a pagination bug
- Adding a new CLI flag
- Bumping a library from 2.x to 3.x
- Formatting or style choices covered by a linter

---

## Hybrid location convention

claude-mpm uses a two-tier location scheme so that ADRs live close to
the code they govern:

```
docs/adr/                          ← workspace-wide decisions
  README.md
  0000-template.md
  0001-use-postgres.md
  0002-adopt-asyncio.md

docs/<component>/decisions/        ← component-specific decisions
  README.md  (managed by that component's team)
  0001-schema-migration-strategy.md
```

**`docs/adr/`** — Use for decisions that affect the project as a whole,
cross service boundaries, or establish conventions that all contributors
must follow.

**`docs/<component>/decisions/`** — Use for decisions scoped entirely to
one service, library, or bounded context within a monorepo.  This
location is *not* scaffolded automatically; the component's maintainers
create it when they need it.

---

## Auto-scaffolding via mpm-init

When you run `/mpm-init` on a new project, claude-mpm creates:

```
docs/adr/
  README.md          ← explains the convention and when to write an ADR
  0000-template.md   ← Nygard template (copy and fill in for each ADR)
```

This scaffold is **idempotent** — re-running `/mpm-init` on an existing
project will never overwrite an edited `README.md` or template.

---

## Skill reference

The `/mpm-adr` skill provides the full workflow:

- Nygard template (Status / Context / Decision / Consequences)
- Numbering convention (`NNNN-kebab-title.md`)
- Status lifecycle (`Proposed` → `Accepted` → `Deprecated` → `Superseded by`)
- Step-by-step workflow for creating and superseding ADRs

---

## Future work

A documentation-agent hook that auto-drafts ADRs from significant
commits or conversation context is tracked as a follow-up to issue #562.
It is explicitly out of scope for the current implementation.

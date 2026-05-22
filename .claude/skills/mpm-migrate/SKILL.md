---
name: mpm-migrate
description: Catalog and router for migration skill wizards (service installation guides)
type: skill
version: "2.0.0"
category: mpm-command
user-invocable: true
tags: [mpm-command, migration, setup, router]
---

# /mpm-migrate — Migration Skill Catalog & Router

This skill is the **catalog and router** for all migration skill wizards.
Its job is to:

1. List known migration subskills (via `SkillManager.get_migration_skills()`).
2. Surface their current status (pending / deferred / declined / completed).
3. Load the appropriate subskill when the user picks one to run.
4. **Always** load the `migration-wizard` protocol alongside any subskill
   it dispatches to.

> Analogy: this skill is to migration subskills what `registry.py` is to
> individual `migrate_*.py` modules. It does not contain wizard logic
> itself — that lives in the parent `migration-wizard` protocol and the
> per-service subskills.

## Invocation Forms

| User says | Behaviour |
|---|---|
| `/mpm-migrate` | List all migration skills and their statuses. |
| `/mpm-migrate <state_key>` | Run that wizard (load protocol + subskill). |
| `/mpm-migrate trusty-services` | Run the trusty-services wizard. |
| "install trusty-services" | Same as `/mpm-migrate trusty-services`. |
| "decline trusty-services" | Mark declined; do not run wizard. |
| "defer trusty-services" | Defer for 24 hours. |

## Behaviour: Run a Wizard

When the user invokes `/mpm-migrate <state_key>`:

1. **Always** load the parent protocol first:
   `.claude/skills/migration-wizard/SKILL.md`. This defines the five
   phases you must follow.
2. Resolve the named subskill via `SkillManager.get_migration_skills()`.
   Match by `state_key` first, then by `name`.
3. If no skill matches, list available `state_key`s and stop.
4. Read the subskill's frontmatter (the declarative data) AND its body
   (motivation, gotchas, post-install notes).
5. Execute the five-phase protocol with that data.

> **Never skip loading the migration-wizard protocol.** Subskills are
> declarative — they describe what to install, not how. The how lives in
> the protocol.

## Behaviour: List Pending Migrations

When invoked with no argument:

```python
from claude_mpm.skills.skill_manager import get_manager
mgr = get_manager()

all_migrations = mgr.get_migration_skills()
pending = mgr.get_pending_migration_skills()
```

Render a table summarising each known migration:

| state_key | status | description |
|---|---|---|
| trusty-services | pending | Install trusty-memory and trusty-search |

For pending entries, suggest:

- `/mpm-migrate <state_key>` to install.
- "decline <state_key>" to permanently dismiss.
- "defer <state_key>" to remind in 24 hours.

You may also run the shared helper:

```bash
bash .claude/skills/migration-wizard/scripts/list-pending-migrations.sh
```

to get a plain newline-separated list of pending state_keys (cheap,
script-friendly).

## Behaviour: Decline / Defer

For "decline <state_key>" or "defer <state_key>":

```bash
bash .claude/skills/migration-wizard/scripts/record-choice.sh \
    <state_key> decline "user declined via /mpm-migrate"

bash .claude/skills/migration-wizard/scripts/record-choice.sh \
    <state_key> defer "user deferred via /mpm-migrate"
```

Confirm the action to the user. The PM context will refresh on next
session boot (driven by the `check_migration_skills` startup migration).

## Behaviour: Re-running a Completed Wizard

If the user invokes `/mpm-migrate <state_key>` for a service that is
already `completed`, tell them so and ask whether they want to re-run
anyway (to repair an install). Do NOT silently re-run — the protocol's
Phase 1 detection would short-circuit, but bypassing it requires explicit
consent.

## Implementation Notes

- This skill is **PM-invocable**. The PM handles the user-facing dialog
  itself and only delegates the actual install commands to the local-ops
  agent (per the parent protocol's Phase 3).
- Subskill bodies are **context, not procedure**. They explain WHY and
  document gotchas. The procedure is always defined in the parent
  protocol.
- When in doubt, load `migration-wizard/SKILL.md` first, then the
  matched subskill. The combination is authoritative.

## Known Migration Subskills

This list reflects what ships in the project today. Subskills are
auto-discovered by `SkillManager` from `.claude/skills/`, so this is
informational, not load-bearing.

- `trusty-services` — install trusty-memory + trusty-search.

Add more by creating a new `.claude/skills/<name>/SKILL.md` with
`type: migration` and the frontmatter fields documented in the parent
protocol.

---
name: migration-wizard
description: General protocol for executing migration skill wizards - service installation and configuration guides
type: migration-protocol
version: "1.0.0"
category: migration
tags: [migration, protocol, wizard, framework]
---

# Migration Wizard Protocol

This skill defines the **general protocol** for executing migration skill
wizards. It is the parent contract: every concrete migration subskill (e.g.
`trusty-services`) provides declarative DATA in its frontmatter, and this
protocol tells you HOW to execute that data.

> Analogy: this skill is to migration subskills what `runner.py` is to
> individual `migrate_*.py` modules in `src/claude_mpm/migrations/`. The
> subskill describes WHAT to install; this protocol describes HOW.

**You (the PM agent) MUST load this protocol whenever you execute a migration
subskill.** Read the subskill's frontmatter and body for service-specific
context (WHY, gotchas, post-install notes), then follow the five phases below
verbatim.

---

## Subskill Frontmatter Contract

A migration subskill declares the following fields in its YAML frontmatter:

| Field | Required | Purpose |
|---|---|---|
| `state_key` | yes | Stable identifier for user-choice tracking |
| `services` | yes | Human-friendly list of services being installed |
| `recommended` | no | Whether to surface as recommended (default `true`) |
| `check_commands` | yes | Phase 1 detection commands (each must exit 0 to skip install) |
| `health_checks` | no | List of `{url, service}` daemons to probe after install |
| `system_requirements` | no | `{min_ram_gb, min_disk_gb, tools_required: [{name, check, install_hint}]}` |
| `install_commands` | yes (or `install_script`) | Phase 3 commands to run |
| `install_script` | no | Path to a shell script (relative to subskill dir) |
| `verify_commands` | yes | Phase 4 commands; each must exit 0 |
| `verify_scripts` | no | Path(s) to verification scripts |
| `post_install_notes` | no | Free-form text shown after Phase 5 |

The body of the subskill is FREE-FORM context: motivation, what to expect,
known gotchas, configuration tips. It is **not** procedural — the procedure
lives here.

---

## Phase 0 — User Choice (MANDATORY FIRST STEP)

**Always present the user with three options BEFORE any other action.** Use
the subskill's `services` list to phrase the prompt:

> The `<state_key>` migration installs `<services>`. It is recommended but
> optional. How would you like to proceed?
>
> 1. **Install now** — I'll walk you through it.
> 2. **Remind me later** — Defer for 24 hours.
> 3. **Never** — Permanently decline; I won't suggest this again.

**Record the choice IMMEDIATELY** before doing anything else:

```bash
# Option 1: proceed -> nothing recorded yet (complete is set in Phase 5)
# Option 2: defer
bash .claude/skills/migration-wizard/scripts/record-choice.sh <state_key> defer "user said: not now"
# Option 3: decline
bash .claude/skills/migration-wizard/scripts/record-choice.sh <state_key> decline "user declined permanently"
```

If the user chose **Defer** or **Never**, confirm to the user and **STOP**.
Do not proceed to Phase 1.

If the user chose **Install now**, continue.

> NEVER skip Phase 0 even if Phase 1 detection would auto-complete the skill.
> Phase 0 is the user-consent gate. Phase 1 is the idempotency gate.

---

## Phase 1 — Detection

Run every command in the subskill's `check_commands` list. If **all** exit 0,
the service is already installed. Auto-complete and stop:

```bash
bash .claude/skills/migration-wizard/scripts/record-choice.sh <state_key> complete "already installed"
```

If the subskill defines `health_checks`, also probe each one using
`check-service-health.sh`. The skill is "fully installed" only when both
`check_commands` AND `health_checks` pass.

If detection passes fully, tell the user and stop the wizard.

If detection is **partial** (binary present but daemon down, etc.), note
what's missing and continue to Phase 2 — the install commands should be
idempotent and will repair the partial install.

---

## Phase 2 — System Capability Check

Verify host prerequisites BEFORE attempting install.

### General Capability Checks (Defined Here)

Run these regardless of subskill:

```bash
bash .claude/skills/migration-wizard/scripts/check-system-capabilities.sh \
    --min-ram-gb <subskill.system_requirements.min_ram_gb || 4> \
    --min-disk-gb <subskill.system_requirements.min_disk_gb || 2>
```

Exits 0 if capable, 1 with a human-readable explanation if not.

### Service-Specific Checks (Defined in Subskill)

Iterate `system_requirements.tools_required`. For each tool:

```bash
# Run tool.check; if non-zero, the tool is missing.
eval "<tool.check>"
```

If a required tool is missing, show the user the tool's `install_hint` and
**stop the wizard** — do not record a decline. The user may install the tool
and re-run later.

If system resources are below the minimum, warn the user clearly. Offer:

1. Proceed anyway (record nothing; user accepts risk).
2. Decline permanently.
3. Defer for 24h.

Do not silently proceed when prerequisites fail.

---

## Phase 3 — Installation

Delegate the actual install to the **local-ops** agent. Prefer
`install_script` if present (preserves complex setup logic); fall back to
running `install_commands` sequentially.

```bash
# Preferred: dedicated install script
bash .claude/skills/<subskill>/scripts/<install_script>

# Fallback: run install_commands in order
<install_command_1>
<install_command_2>
```

**Do not continue to Phase 4 until the install command returns success.** If
any install step fails:

1. Surface the error to the user verbatim.
2. Offer to retry, defer, or decline.
3. Do not record completion.

The subskill body may document known install failures (e.g., "Xcode CLT
required on macOS"). Read it before reporting unknown errors.

---

## Phase 4 — Verification

Re-run the subskill's `verify_commands`. Every command must exit 0. Then run
any `verify_scripts` listed.

If verification fails:

1. Tell the user exactly which command failed.
2. **Do not record completion.**
3. Offer to retry installation or surface the error for manual investigation.

A partial install left in this state is correctly modeled as "still pending":
the next session will re-detect and re-prompt.

---

## Phase 5 — Completion

When all verification steps pass:

```bash
bash .claude/skills/migration-wizard/scripts/record-choice.sh <state_key> complete "installation verified"
```

Then show the user a short summary:

- What was installed (the `services` list).
- How to use it (whatever the subskill body documents).
- What changed in `.mcp.json` or other config files.
- Any `post_install_notes` from the subskill.

Suggest restarting Claude Code to pick up any new MCP tools, and recommend
`claude-mpm doctor` for verification.

---

## Error Handling Summary

- **User changes mind mid-wizard** → treat as defer (24h) unless they say
  "never". Always record something; never leave state in limbo.
- **Unexpected error you can't resolve** → file via `/mpm-bug`, defer the
  skill for 24h, tell the user.
- **Phase 4 fails** → do not record completion; the next session will
  re-detect.
- **User explicitly says "skip detection"** → respect them; jump to Phase 3,
  but warn that a re-install over a working install can break things.

---

## Quick Reference: Shared Scripts

All located in `.claude/skills/migration-wizard/scripts/`:

- `record-choice.sh <state_key> <action> [reason]` — wraps user_choices_cli
- `check-service-health.sh <url> [timeout]` — HTTP health check
- `check-system-capabilities.sh [--min-ram-gb N] [--min-disk-gb N]` — RAM + disk
- `list-pending-migrations.sh` — read `~/.claude-mpm/pending-migrations.json`

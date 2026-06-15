---
name: session-manager-driver
description: Drive the trusty-mpm session manager (binary `tm`) to spawn, observe, command, and decommission durable tmux-backed Claude Code sessions in isolated workspaces. Wraps the `tm session` CLI / REST API and provides the spawn → observe → answer → stop/resume/decommission loop. Critically, the DRIVER interprets the raw tmux pane using its own inference — it does NOT depend on the daemon's optional LLM (no OpenRouter key required).
version: 1.0.0
category: infrastructure
when_to_use: when spawning, observing, commanding, answering decisions for, stopping, resuming, or decommissioning trusty-mpm session-manager sessions; when driving a fleet of durable Claude Code harness sessions; when a task requires delegating work to an isolated, observable, long-running coding session
author: Claude MPM Team
license: Elastic-2.0
effort: high
tags:
  - session-manager
  - trusty-mpm
  - tmux
  - harness
  - orchestration
  - autonomy-tiers
requires_tools:
  - bash
progressive_disclosure:
  level: 1
  references: []
  note: Single-file procedural skill. The driver loop and autonomy policy are the deliverable; no deeper reference files needed.
---

# Session Manager Driver

Procedural how-to for driving the **trusty-mpm session manager** — a Rust daemon
(binary `tm`) that spawns, observes, and controls durable, tmux-backed Claude Code
sessions, each in its own isolated git workspace. This skill wraps the
`tm session` CLI verbs and the underlying REST API, and defines the
**spawn → observe → answer → stop/resume/decommission** control loop plus the
**T1–T4 autonomy policy** that governs how much the driver may do without a human.

## Core design principle: YOU do the reasoning

The session manager exposes **raw observability**, not conclusions. When driven by
claude-mpm, **inference is provided by claude-mpm's own Claude — there is no
OpenRouter key and none is needed.**

- The daemon ALWAYS returns `raw_pane` (the last ~60 lines of the tmux pane).
- It returns a best-effort structured `state`, `summary`, `pending_decision`,
  and `proposed_default` — but when no OpenRouter key is configured these may be
  `state: "unknown"` / `summary` thin / `confidence: 0.0`. **This is expected and
  fine.**
- **The driver reads `raw_pane` and decides.** Never block on the daemon's
  optional LLM classification. Treat `state` as a hint; treat `raw_pane` as ground
  truth.

## Prerequisites

- The `tm` binary on PATH (trusty-mpm session manager).
- The session-manager daemon running. Default base URL: `http://localhost:7424`.
- A health check before driving anything (see Health & Status below).

## Command reference (`tm session` verbs)

Prefer the CLI over raw HTTP. Each verb maps to a REST endpoint on the daemon.

| Operation | CLI command | HTTP endpoint |
|---|---|---|
| spawn | `tm session new <repo> --git-ref <ref> --task "<desc>" [--name-hint <h>]` | `POST /api/v1/sessions/managed` |
| list | `tm session ls [--json]` | `GET /api/v1/sessions/managed` |
| activity (poll) | `tm session activity <id>` | `GET /api/v1/sessions/managed/{id}/activity` |
| send text | `tm session send <id> "<text>"` | `POST /api/v1/sessions/managed/{id}/send` |
| answer decision | `tm session answer <id> "<answer>"` | `POST /api/v1/sessions/managed/{id}/answer` |
| attach (human) | `tm session attach <id>` | `GET /api/v1/sessions/managed/{id}/attach-cmd` |
| stop (keep workspace) | `tm session stop <id>` | `POST /api/v1/sessions/managed/{id}/runtime-stop` |
| resume | `tm session resume <id>` | `POST /api/v1/sessions/managed/{id}/resume` |
| decommission (delete workspace) | `tm session decommission <id>` | `POST /api/v1/sessions/managed/{id}/decommission` |

### Health & status

Before spawning or driving, confirm the daemon is reachable and healthy:

```bash
# Daemon liveness/health (warm-boot, degraded flags, etc.)
curl -sf http://localhost:7424/health || echo "DAEMON DOWN"

# Fleet snapshot (machine-readable)
tm session ls --json
```

If `/health` reports a degraded or unreachable daemon, **do not spawn** — escalate
to the human (T4-equivalent: infrastructure problem).

## The activity response (the object you interpret)

`tm session activity <id>` returns:

```json
{
  "raw_pane": "<last ~60 lines of the tmux pane; ALWAYS present>",
  "runtime_active": true,
  "state": "working|idle|blocked_on_permission|errored|done|unknown",
  "summary": "<best-available text>",
  "confidence": 0.0,
  "pending_decision": "<question the session is waiting on, or null>",
  "proposed_default": "<a suggested answer, or null>"
}
```

How to read it:

- **`raw_pane`** — your primary signal. Read it like a human reading the terminal.
  Look for prompts (`? Do you want to…`, `(y/N)`, `Press enter to continue`),
  errors (panics, tracebacks, `error[`), completion markers, and the trailing
  cursor line.
- **`pending_decision` non-null** — the session is blocked waiting for an answer.
  Decide per the autonomy policy below, then `tm session answer <id> "<answer>"`.
- **`runtime_active: false`** — the tmux runtime is stopped (the session may be
  `stopped` lifecycle state but resumable). Use `tm session resume <id>` to restart
  the runtime before sending.
- **`state: "unknown"` / `confidence: 0.0`** — the daemon's optional LLM did not
  classify (no OpenRouter key). **Ignore the absence and classify from `raw_pane`
  yourself.**

## Lifecycle states

```
provisioning ──▶ active ⇄ stopped ──▶ decommissioned (terminal)
```

- **provisioning** — workspace being prepared; not yet driveable. Poll until active.
- **active** — runtime live; observe/send/answer freely (within tier).
- **stopped** — runtime halted but **workspace preserved**; resumable with
  `tm session resume`. `tm session stop` puts a session here.
- **decommissioned** — **workspace deleted**; terminal and irreversible. Only
  `tm session decommission` reaches this state.

> `stop` keeps the workspace (cheap, resumable). `decommission` DELETES it
> (destructive, irreversible). Never conflate the two.

## The driver loop

```
1. spawn       → tm session new <repo> --git-ref <ref> --task "<desc>" --name-hint <h>
                 capture the returned session id.
2. wait active → poll `tm session activity <id>` until runtime_active && not provisioning.
3. observe     → read raw_pane. Classify: working / idle / blocked / errored / done.
4. branch:
   - working    → wait, then poll again (backoff; see cadence below).
   - blocked    → pending_decision != null → decide (autonomy policy) → answer or escalate.
   - idle/needs nudge → tm session send <id> "<next instruction>"  (T3).
   - errored    → capture raw_pane, escalate to human (do not auto-retry destructive steps).
   - done       → record result, then tm session stop <id> (preserve workspace).
5. teardown    → stop (keep) for later resume, OR decommission (delete) ONLY with
                 explicit human confirmation (T4).
```

### Polling cadence

Poll `activity` on a backoff to avoid hammering the daemon:

- Just after spawn / after sending input: poll every **3–5 s** for the first
  ~30 s (state changes fast right after input).
- Steady "working" state: back off to every **15–30 s**.
- Always re-poll immediately after `send` or `answer` to confirm the session
  consumed it.

Use a bounded poll loop, never an unbounded busy-wait:

```bash
SID="$1"
for i in $(seq 1 40); do
  ACT="$(tm session activity "$SID")"
  PENDING="$(printf '%s' "$ACT" | jq -r '.pending_decision // empty')"
  ACTIVE="$(printf '%s' "$ACT" | jq -r '.runtime_active')"
  # Print raw_pane for the driver (Claude) to read and reason over.
  printf '%s' "$ACT" | jq -r '.raw_pane'
  [ -n "$PENDING" ] && { echo "PENDING_DECISION: $PENDING"; break; }
  [ "$ACTIVE" = "false" ] && { echo "RUNTIME_INACTIVE"; break; }
  sleep 15
done
```

> The script surfaces `raw_pane` + the pending question; **the reasoning step
> (what the answer should be) is performed by you, the driver, not by the script
> and not by the daemon.**

## Detecting and answering a pending decision

A session is "blocked on a decision" when **either**:

1. `pending_decision` is non-null in the activity response, **or**
2. `raw_pane` shows an interactive prompt the structured state missed
   (e.g. a `(y/N)` confirmation, a numbered menu, a `Proceed? [Y/n]`).

To answer:

```bash
tm session answer <id> "<your answer>"
# Then immediately re-poll activity to confirm the session advanced.
```

Decide WHAT to answer using the autonomy policy. If the policy says auto-answer
is allowed, prefer `proposed_default` when it is present and consistent with your
reading of `raw_pane`; otherwise compose the answer yourself from `raw_pane`.

If `tm session answer` does not unblock the prompt (some TUIs need a literal
keystroke), fall back to `tm session send <id> "<keystroke>"` (e.g. `"y"`,
`"1"`, or an empty line to accept a default).

## Autonomy tiers (T1–T4)

The driver operates at an explicitly chosen tier. **Default to the most
conservative tier appropriate for the task; never silently escalate your own
tier.** Tiers are cumulative (T3 includes T1–T2 capabilities).

| Tier | Name | The driver MAY… | Examples |
|---|---|---|---|
| **T1** | Read-only observe | spawn? no. Only `ls`, `activity`, `attach-cmd`, `/health`. Never mutate session state. | Monitor a fleet, report status, surface pending decisions for a human to answer. |
| **T2** | Auto-answer safe defaults | everything in T1, **plus** answer **low-risk** pending decisions using `proposed_default` when it is present and matches your reading of `raw_pane`. | Accept "create directory? (Y/n)", "install dev dependency? (Y/n)", "format code? (Y/n)". |
| **T3** | Routine drive | everything in T2, **plus** `spawn` sessions, `send` routine non-destructive instructions, `stop` (workspace preserved), `resume`. Compose answers (not just accept defaults) for non-destructive decisions. | Spawn a session for a scoped task, nudge it through a build, answer "which test runner?", stop it when done. |
| **T4** | Destructive / irreversible | everything in T3, **but ONLY with explicit, logged human confirmation** for: `decommission` (deletes workspace), answering decisions that delete data / force-push / publish / spend money / touch production, or running anything outside the session's assigned task scope. | Decommission a session, approve a `git push --force`, approve a `cargo publish`, approve `rm -rf`. |

### Auto-answer vs. escalate decision rule

Classify the **risk** of a pending decision from `raw_pane` + `pending_decision`:

- **Low-risk (auto-answer at T2+):** idempotent, reversible, scoped to the
  workspace — create file/dir, install a dependency, run tests, format, choose a
  conventional default. Prefer `proposed_default` when present.
- **Medium-risk (auto-answer only at T3, otherwise escalate):** non-destructive
  but consequential — choosing an architecture, committing, opening a PR, picking a
  dependency version. Compose a reasoned answer; if uncertain, escalate.
- **High-risk (ALWAYS escalate; never auto-answer regardless of tier):** deletes
  data, `--force`, publishes/releases, spends money, modifies production, leaves
  the assigned task scope, or `decommission`. Surface the exact `raw_pane` excerpt
  and the proposed action; wait for explicit human "yes."

> When in doubt, escalate. A blocked session is recoverable; a wrong destructive
> answer may not be.

## Stop / resume / decommission semantics

- **`tm session stop <id>`** — halts the runtime, **keeps the workspace**. Cheap,
  reversible. Use when a task is done but you might resume, or to free runtime
  resources. (T3.)
- **`tm session resume <id>`** — restarts the runtime of a `stopped` session in its
  preserved workspace. Re-poll `activity` after resuming; the pane resumes where it
  left off. (T3.)
- **`tm session decommission <id>`** — **deletes the workspace**; terminal. Use
  only after the work is captured (committed/PR'd) and **only with explicit human
  confirmation**. (T4.)

## Escalation protocol

Escalate to the human (return control, surface context) when:

- a decision is high-risk (per the rule above),
- the session is `errored` and recovery is non-obvious,
- `/health` reports the daemon degraded/unreachable,
- a session has been "working" past a reasonable bound with no progress in
  `raw_pane` (possible hang — offer `attach`, `stop`, or escalate),
- the current tier does not permit the needed action.

When escalating, include: the session id, the relevant `raw_pane` excerpt, the
`pending_decision` (if any), and the action you recommend.

## Full-cycle smoke test

End-to-end exercise of every verb (mirrors issue #842 acceptance criteria):

```bash
# 0. health
curl -sf http://localhost:7424/health

# 1. spawn
SID="$(tm session new https://github.com/org/repo --git-ref main \
        --task "run the test suite and report failures" \
        --name-hint smoke --json | jq -r '.id')"

# 2. observe until active, reading raw_pane
tm session activity "$SID"

# 3. drive: answer a decision (T2) or send an instruction (T3)
tm session answer "$SID" "y"          # if pending_decision present
tm session send   "$SID" "cargo test" # routine instruction

# 4. stop (keep workspace) — reversible
tm session stop "$SID"

# 5. resume — back to active in the same workspace
tm session resume "$SID"

# 6. decommission (delete workspace) — T4, requires human confirmation
tm session decommission "$SID"
```

## Anti-patterns (do NOT do these)

- ❌ Waiting on / trusting `state` over `raw_pane`. The pane is ground truth;
  `state: "unknown"` is expected without an OpenRouter key.
- ❌ Treating `stop` and `decommission` as interchangeable. `decommission`
  deletes the workspace.
- ❌ Auto-answering a high-risk decision because `proposed_default` was present.
  `proposed_default` is a hint, not authorization.
- ❌ Unbounded busy-wait polling. Always bound the loop and back off.
- ❌ Decommissioning before the work is captured (committed / PR'd).
- ❌ Silently escalating your own autonomy tier.

## Related skills

- `mpm-bug-reporting` — file a GitHub issue when the session manager itself misbehaves.
- `mpm-verification-protocols` — verification gates before declaring a driven task complete.
- `verification-before-completion` — confirm a session's task actually succeeded (read `raw_pane`, don't assume).

---
name: session-analyzer
skill_id: session-analyzer
skill_version: 0.3.0
description: "Debug and teach agentic coding: a deterministic-first session timeline + cost report, with optional narrative polish and a standalone JSX visualiser."
when_to_use: when analyzing a completed Claude session to understand cost breakdown, agent behavior, tool usage timeline, or to generate a visual session report
updated_at: 2026-06-12T00:00:00Z
tags: [session, reporting, cost, teaching, debugging]
effort: medium
---

# Session Analyzer

Produce a deterministic-first session report for **debugging** and **teaching**
agentic coding with Claude MPM. The report reconstructs an entire session's
timeline — every PM turn, subagent call, skill use, MCP call, the model behind
each call, tokens in/out (plus cache), and a TOTAL estimated cost at public
rack rates — directly from Claude Code's JSONL transcripts.

The core data is generated with **zero LLM inference**. Inference is an
**optional, opt-in** polish step that only rewrites human-readable prose; the
machine-readable data is never touched by a model.

## When to use this skill

- **Post-session debugging** — understand what the PM actually did: which
  subagents ran, what they reported back, where time and tokens went, which
  MCP calls were made and how they responded.
- **Teaching effective MPM usage** — turn a real session into a readable,
  annotated timeline that shows good (and bad) delegation, skill use, and cost
  patterns.
- **Cost analysis** — see per-model and per-call token/cost breakdowns and a
  grand-total estimate at rack rates, split into PM vs. subagent cost.

## The hybrid workflow

The workflow has three stages. Stages 1 and 3 are fully deterministic. Stage 2
is the only place inference is allowed, and it is entirely optional.

### 1. Extract (deterministic, no inference)

Run the offline reporter to parse the JSONL transcripts and emit the canonical
Markdown report. **This stage alone produces a complete, valid, usable report** —
token, cost, model, agent, skill, and MCP data, all with zero LLM inference.

```bash
# Most-recent session for the current project directory
claude-mpm session-report

# A specific session
claude-mpm session-report --session <UUID>

# Custom output path (use - for stdout)
claude-mpm session-report --session <UUID> --output /tmp/report.md

# A different project directory
claude-mpm session-report --project /path/to/project
```

Equivalent module form: `uv run python -m claude_mpm.cli session-report ...`

**Flags:**

- `--session <id>` — session UUID; defaults to the most recent session for the
  project.
- `--project <path>` — project directory whose transcripts to read; defaults to
  the current directory.
- `-o, --output <file.md>` — output path; `-` writes to stdout.

**Default output path:** `docs/reporting/session-tracker/{session_id}.md`

The generated file has two parts: a **YAML frontmatter** block (session metadata
and cost totals) and a `## Timeline` section with one `####`-headed entry per
event. Each entry carries a machine-readable `<!-- meta: ... -->` comment that
holds the canonical per-call data (model, tokens, cost, type, attribution).

### 2. Optional narrative polish (opt-in inference)

This is the **only** non-deterministic stage, and it is **optional** — skipping
it yields a fully valid report.

If you want a more teachable, readable report, you may edit the Markdown in
place to rewrite each entry's prose:

- the `#### HH:MM · {actor} · {title}` heading text (the `{title}`),
- the entry's `{detail}` body prose,
- the `**Outcome:**` line.

**Hard constraints — do not break these:**

- **Never alter the `<!-- meta: ... -->` comment** on any entry. It is the
  canonical machine data the JSX renderer and downstream tooling read.
- **Never alter the frontmatter totals** (`model_breakdown`, `grand_total_cost_usd`,
  `pm_cost_usd`, `subagent_cost_usd`, `autonomy`, `stat_cards`,
  `has_pricing_fallback`, etc.).
- Only rephrase human-facing prose. Do not invent facts not present in the
  transcript.

### 3. Render (deterministic)

Convert the canonical Markdown into a standalone React/JSX timeline:

```bash
python scripts/session_timeline_to_jsx.py docs/reporting/session-tracker/<session_id>.md \
  -o docs/reporting/session-tracker/<session_id>.jsx
```

The script is bundled at `scripts/session_timeline_to_jsx.py` relative to this
skill directory. An identical copy also lives at `scripts/session_timeline_to_jsx.py`
in the repo root (used by the CLI render path and the test suite — do not delete
the root copy).

The renderer reads the `frontmatter` + `events` structure parsed from the
report and produces an interactive timeline dashboard. Because it consumes the
`<!-- meta: ... -->` data, it works on both raw (stage 1) and polished
(stage 2) reports identically — the polish only changes the prose it displays.

## What each captured data point means

- **Timeline entry** — one event: a user prompt, a PM turn, an `Agent` call, a
  `Skill` call, an MCP call, or an outcome. Headed `#### HH:MM · {actor} · {title}`.
- **actor** — `bob` (the human), `mpm` (the PM agent), or a subagent attribution
  name (e.g. `Python Engineer`).
- **Subagents called + their responses** — `Agent` calls render as
  `Agent → **agent-name** (model) — _short response to the PM_`, capturing what
  each subagent reported back.
- **Skills used** — `Skill → **skill-name** — _result_`.
- **MCP calls + responses** — memory / search / review MCP invocations and their
  responses, tagged `mcp`.
- **model** — the model that served each call (e.g. `claude-opus-4-8`,
  `claude-haiku-3`), recorded per entry in the meta comment.
- **Tokens** — per call: `in` (non-cached input), `out` (output),
  `cache_read`, `cache_write`. Aggregated per model in `model_breakdown`.
- **Cost** — per-call `cost_usd` and a frontmatter grand total, split into
  `pm_cost_usd` and `subagent_cost_usd`.
- **autonomy** — `{bob_pct, mpm_pct, basis}`, a turn-count split of how much of
  the session was human- vs. PM-driven.
- **stat_cards** — six summary cards for dashboard rendering.

## Caveats

### Rack-rate cost estimates

All costs are **estimates** computed at Anthropic's public list prices
(rack rates), not your actual billed amount. Rates used (USD per 1,000,000
tokens):

| Model family | Input | Output | Cache write | Cache read |
|---|---|---|---|---|
| `claude-opus`   | $15.00 | $75.00 | $18.75 | $1.50 |
| `claude-sonnet` | $3.00  | $15.00 | $3.75  | $0.30 |
| `claude-haiku`  | $0.80  | $4.00  | $1.00  | $0.08 |

Unknown model strings **fall back to sonnet rates**, and the report sets
`has_pricing_fallback: true` in the frontmatter so a fallback-affected total is
visible and flagged. Treat such totals as approximate.

### Subagent ↔ PM correlation

The parser links a PM `Agent` call to a subagent's JSONL transcript by matching
timestamps within a **±2-second tolerance window** (typical skew ~300 ms).

Under **parallel delegation** — multiple `Agent` calls fired nearly
simultaneously — two PM calls can fall within the window of the same subagent
file. The parser assigns the nearest match and sets `ambiguous: true` on the
event. When you see an ambiguous entry, resolve it manually by inspecting the
raw subagent transcripts in
`~/.claude/projects/{encoded_cwd}/{session_id}/subagents/`.

## Reference

- `references/schema.md` — full canonical Markdown schema, frontmatter key
  reference, pricing table, and correlation details (bundled copy).
- `scripts/session_timeline_to_jsx.py` — the deterministic Markdown → JSX
  renderer (bundled copy; repo-root copy also used by CLI and tests).

## Remember

- **Stage 1 is a complete report on its own** — run it and you already have
  every cost/model/agent/skill/MCP fact, with zero inference.
- **Inference is opt-in and prose-only** — never touch `<!-- meta: ... -->` or
  the frontmatter totals.
- **Costs are rack-rate estimates** — watch for `has_pricing_fallback: true`.
- **Parallel delegation is ambiguous** — verify `ambiguous: true` entries
  against the raw subagent transcripts.

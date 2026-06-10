# Session Tracker — Report Format & CLI Reference

Offline, deterministic session reporting for Claude MPM.
No LLM calls; reads the JSONL transcripts that Claude Code writes natively.

---

## CLI Usage

```bash
# Report on the most-recent session for the current project directory
claude-mpm session-report

# Report on a specific session, write to stdout
claude-mpm session-report --session <UUID> --output -

# Write to a custom path
claude-mpm session-report --session <UUID> --output /tmp/my-report.md

# Specify a different project directory
claude-mpm session-report --project /path/to/project
```

Default output path: `docs/reporting/session-tracker/{session_id}.md`

---

## Canonical Markdown Schema

Every report is a single `.md` file with two sections:

1. **YAML frontmatter** (between `---` fences)
2. **Timeline** (`## Timeline`) — one `####`-headed entry per event

### Frontmatter Keys

| Key | Type | Description |
|-----|------|-------------|
| `session_id` | `str` | Claude Code session UUID |
| `project` | `str` | Basename of the project directory |
| `project_path` | `str` | Absolute project directory path |
| `generated_at` | `str` | ISO-8601 UTC timestamp of report generation |
| `date` | `str` | `YYYY-MM-DD` wall-clock date the session started |
| `title` | `str` | First user message (truncated to 120 chars) |
| `model_breakdown` | `list` | Per-model token/cost summary (see below) |
| `grand_total_cost_usd` | `float` | PM + all subagent costs combined |
| `pm_cost_usd` | `float` | PM-only cost |
| `subagent_cost_usd` | `float` | Subagent-only cost |
| `autonomy` | `dict` | `{bob_pct, mpm_pct, basis}` — turn-count autonomy split |
| `stat_cards` | `list` | 6-entry summary cards for dashboard rendering |
| `has_pricing_fallback` | `bool` | `true` if any unknown model used fallback (sonnet) rates |

Each `model_breakdown` entry:

```yaml
model_breakdown:
- model: claude-opus-4-8
  input: 61862       # input tokens (non-cached)
  output: 144541     # output tokens
  cache_write: 1046469
  cache_read: 5272111
  cost_usd: 39.297965
  turns: 58
```

### Timeline Entry Format

```markdown
#### HH:MM · {actor} · {title}
<!-- meta: who={actor}; tags={tags}; model={model}; in={N}; out={N}; cache_read={N}; cache_write={N}; cost_usd={F}; type={event_type}; ambiguous={bool}; subagent_file={stem} -->

{detail prose — full text of the turn}

**Calls:**

- `Agent` → **python-engineer** (claude-haiku-3) — _Fixed the regex pattern._
- `Skill` → **verification-before-completion** — _All tests pass._

**Outcome:** Fixed the regex pattern on line 42 of src/parser.py.

**Links:** https://github.com/example/repo/issues/42

---
```

**Field descriptions:**

- `actor` — `bob` (human), `mpm` (PM agent), or the subagent attribution name (e.g. `Python Engineer`)
- `tags` — comma-separated: `prompt`, `agent`, `skill`, `mcp`, `outcome`, `turn`, `links`, `ambiguous`
- `type` — one of: `user_prompt`, `pm_turn`, `agent_call`, `skill_call`, `mcp_call`, `outcome`
- `ambiguous` — `true` when the subagent↔PM timestamp correlation is uncertain (see caveat below)
- `subagent_file` — stem of the subagent's JSONL file, or `none`

The `<!-- meta: ... -->` comment is machine-readable and survives most Markdown renderers invisible.

---

## Rack-Rate Pricing Table

All costs use Anthropic's public list prices at the time of implementation.
**Source: https://www.anthropic.com/pricing (retrieved 2025-06-10)**

| Model Family | Input | Output | Cache Write | Cache Read |
|---|---|---|---|---|
| `claude-opus` | $15.00 | $75.00 | $18.75 | $1.50 |
| `claude-sonnet` | $3.00 | $15.00 | $3.75 | $0.30 |
| `claude-haiku` | $0.80 | $4.00 | $1.00 | $0.08 |

Prices are in **USD per 1 000 000 tokens**.

Unknown model strings fall back to sonnet rates; `has_pricing_fallback: true`
is set in the frontmatter when this occurs.

---

## Subagent ↔ PM Timestamp Correlation

Claude Code writes the main PM transcript and each subagent's transcript
independently. The parser correlates an `Agent` tool-use call in the PM
transcript to a subagent JSONL file by matching the PM call timestamp against
the subagent's first user-message timestamp, within a **±2-second tolerance
window**.

**Caveat:** Under parallel delegation (multiple `Agent` calls fired near-
simultaneously), two PM calls may both fall within the tolerance window of the
same subagent file. In this case the nearest match is assigned and
`ambiguous: true` is set on the event. Inspect the raw subagent JSONL files
in `~/.claude/projects/{encoded_cwd}/{session_id}/subagents/` to resolve
ambiguous attributions manually.

Typical observed skew is ~300 ms; the 2-second window is deliberately generous
to handle momentary system load.

---

## JSX Visualiser

`claude-mpm-timeline.jsx` in this directory is a React component that reads a
session report Markdown file (via the `frontmatter` + `events` structure
produced by `read_markdown()`) and renders an interactive timeline dashboard.

The component expects:
- `frontmatter` dict as returned by `read_markdown(path)["frontmatter"]`
- `events` list as returned by `read_markdown(path)["events"]`

See `src/claude_mpm/services/session_analysis/markdown_writer.py` for the
`read_markdown()` function that parses the report file.

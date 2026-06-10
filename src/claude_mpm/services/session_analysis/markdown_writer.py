"""
Render a SessionReport to canonical Markdown and parse it back.

WHAT: Emits a deterministic, human-readable Markdown document with YAML
      frontmatter and a Timeline section.  Each entry carries an invisible
      HTML comment with machine-readable metadata so a converter can parse
      the file without re-doing timeline extraction.
WHY:  Separating rendering from parsing keeps the canonical format versioned
      and auditable; the ``read_markdown`` function enables round-trip testing
      and lets the JSX-converter work purely from the Markdown artefact.

References
----------
LINK: none  (new subsystem — spec backfill pending)

Canonical format contract
-------------------------
Frontmatter keys (YAML between ``---`` fences):

    session_id          str
    project             str  (basename of project_path)
    project_path        str
    generated_at        ISO-8601 UTC string
    date                YYYY-MM-DD (local wall-clock)
    title               str
    model_breakdown     list of {model, input, output, cache_write, cache_read, cost_usd, turns}
    grand_total_cost_usd  float
    pm_cost_usd         float
    subagent_cost_usd   float
    autonomy            {bob_pct, mpm_pct, basis}   -- turn-count basis
    stat_cards          list of {label, value, sub}  (6 entries)
    has_pricing_fallback  bool

Timeline entry format::

    #### HH:MM · {actor} · {title}
    <!-- meta: who={actor}; tags={tags}; model={model}; in={N}; out={N}; cache_read={N}; cache_write={N}; cost_usd={F}; type={event_type}; ambiguous={bool}; subagent_file={stem} -->
    {detail prose}

    **Calls:**
    - `{tool_name}` ({in}/{out} tok, ${cost:.4f}) — {response_summary}

    **Outcome:** {response_summary}

    **Links:** {url1} {url2}
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml  # PyYAML — already a project dep via other modules

from .transcript_parser import SessionReport, TimelineEvent  # noqa: TC001

# ---------------------------------------------------------------------------
# Rendering helpers
# ---------------------------------------------------------------------------


def _fmt_dt(dt: datetime | None) -> str:
    """ISO-8601 UTC string."""
    if dt is None:
        return ""
    return dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _fmt_time(dt: datetime | None) -> str:
    """HH:MM local wall-clock."""
    if dt is None:
        return "??:??"
    return dt.astimezone().strftime("%H:%M")


def _fmt_date(dt: datetime | None) -> str:
    if dt is None:
        return ""
    return dt.astimezone().strftime("%Y-%m-%d")


def _safe_yaml_str(value: Any) -> str:
    """Render *value* as a YAML-safe inline scalar (single-quoted)."""
    return str(value).replace("'", "''")


def _escape_md_title(text: str) -> str:
    """Minimal escaping for Markdown heading text."""
    return text.replace("`", "'").replace("\n", " ").strip()


def _make_tags(event: TimelineEvent) -> str:
    tags: list[str] = []
    if event.event_type == "agent_call":
        tags.append("agent")
    elif event.event_type == "skill_call":
        tags.append("skill")
    elif event.event_type == "mcp_call":
        tags.append("mcp")
    elif event.event_type == "user_prompt":
        tags.append("prompt")
    elif event.event_type == "outcome":
        tags.append("outcome")
    if event.github_links:
        tags.append("links")
    if event.correlation_ambiguous:
        tags.append("ambiguous")
    return ",".join(tags) if tags else "turn"


def _autonomy(report: SessionReport) -> dict[str, Any]:
    bob = sum(1 for e in report.events if e.actor == "bob")
    mpm_like = sum(1 for e in report.events if e.actor != "bob")
    total = bob + mpm_like or 1
    return {
        "bob_pct": round(bob / total * 100, 1),
        "mpm_pct": round(mpm_like / total * 100, 1),
        "basis": "turn_count",
    }


def _stat_cards(report: SessionReport) -> list[dict[str, Any]]:
    duration = ""
    if report.started_at and report.ended_at:
        secs = (report.ended_at - report.started_at).total_seconds()
        h, rem = divmod(int(secs), 3600)
        m, s = divmod(rem, 60)
        if h:
            duration = f"{h}h {m}m"
        else:
            duration = f"{m}m {s}s"
    return [
        {
            "label": "Total Cost",
            "value": f"${report.grand_total_cost_usd:.4f}",
            "sub": "rack rate",
        },
        {
            "label": "PM Cost",
            "value": f"${report.pm_cost_usd:.4f}",
            "sub": "PM turns only",
        },
        {
            "label": "Agent Cost",
            "value": f"${report.subagent_cost_usd:.4f}",
            "sub": "subagent turns",
        },
        {
            "label": "Agent Calls",
            "value": str(report.agent_call_count),
            "sub": "delegations",
        },
        {
            "label": "Tool Calls",
            "value": str(report.skill_call_count + report.mcp_call_count),
            "sub": "skill + mcp",
        },
        {"label": "Duration", "value": duration or "—", "sub": "wall-clock"},
    ]


def _model_breakdown(report: SessionReport) -> list[dict[str, Any]]:
    rows = []
    for mt in report.model_totals.values():
        rows.append(
            {
                "model": mt.model,
                "input": mt.input_tokens,
                "output": mt.output_tokens,
                "cache_write": mt.cache_creation_input_tokens,
                "cache_read": mt.cache_read_input_tokens,
                "cost_usd": round(mt.total_cost_usd, 6),
                "turns": mt.turn_count,
            }
        )
    rows.sort(key=lambda r: r["cost_usd"], reverse=True)
    return rows


# ---------------------------------------------------------------------------
# Public render function
# ---------------------------------------------------------------------------


def render_markdown(report: SessionReport) -> str:
    """Render *report* to the canonical Markdown string.

    WHAT: Produces YAML frontmatter + Timeline section from a SessionReport.
    WHY:  Centralises all rendering logic; callers and tests work only with
          the report dataclass and never with raw JSONL.
    """
    now = datetime.now(tz=UTC)
    project_path = Path(report.project_path)

    # -- Frontmatter ----------------------------------------------------------
    frontmatter: dict[str, Any] = {
        "session_id": report.session_id,
        "project": project_path.name,
        "project_path": report.project_path,
        "generated_at": _fmt_dt(now),
        "date": _fmt_date(report.started_at or now),
        "title": report.title,
        "model_breakdown": _model_breakdown(report),
        "grand_total_cost_usd": round(report.grand_total_cost_usd, 6),
        "pm_cost_usd": round(report.pm_cost_usd, 6),
        "subagent_cost_usd": round(report.subagent_cost_usd, 6),
        "autonomy": _autonomy(report),
        "stat_cards": _stat_cards(report),
        "has_pricing_fallback": report.has_pricing_fallback,
    }

    lines: list[str] = []
    lines.append("---")
    lines.append(
        yaml.dump(frontmatter, default_flow_style=False, allow_unicode=True).rstrip()
    )
    lines.append("---")
    lines.append("")

    # -- Document title -------------------------------------------------------
    lines.append(f"# Session: {_escape_md_title(report.title)}")
    lines.append("")

    # -- Summary stat cards ---------------------------------------------------
    lines.append("## Summary")
    lines.append("")
    for card in _stat_cards(report):
        lines.append(f"- **{card['label']}**: {card['value']} _{card['sub']}_")
    lines.append("")

    if report.has_pricing_fallback:
        lines.append(
            "> **Warning:** one or more model calls used fallback (sonnet) pricing."
        )
        lines.append("")

    # -- Timeline -------------------------------------------------------------
    lines.append("## Timeline")
    lines.append("")

    for event in report.events:
        time_str = _fmt_time(event.timestamp)
        actor = event.actor
        title = _escape_md_title(event.title) or event.event_type

        # Level-4 heading
        lines.append(f"#### {time_str} · {actor} · {title}")
        lines.append("")

        # Machine-readable metadata comment
        in_tok = event.usage.get("input_tokens", 0)
        out_tok = event.usage.get("output_tokens", 0)
        cr_tok = event.usage.get("cache_read_input_tokens", 0)
        cw_tok = event.usage.get("cache_creation_input_tokens", 0)
        meta = (
            f"<!-- meta: who={actor}; tags={_make_tags(event)}; "
            f"model={event.model or 'none'}; "
            f"in={in_tok}; out={out_tok}; "
            f"cache_read={cr_tok}; cache_write={cw_tok}; "
            f"cost_usd={event.cost_usd:.6f}; "
            f"type={event.event_type}; "
            f"ambiguous={str(event.correlation_ambiguous).lower()}; "
            f"subagent_file={event.subagent_file or 'none'} -->"
        )
        lines.append(meta)
        lines.append("")

        # Detail prose
        if event.detail.strip():
            lines.append(event.detail.strip())
            lines.append("")

        # Calls bullet list
        if event.calls:
            lines.append("**Calls:**")
            lines.append("")
            for call in event.calls:
                resp_preview = (
                    call.response_text[:100].replace("\n", " ").strip()
                    if call.response_text
                    else ""
                )
                bullet = f"- `{call.tool_name}`"
                if call.tool_name == "Agent" and call.subagent_type:
                    bullet += f" → **{call.subagent_type}**"
                    if call.subagent_model:
                        bullet += f" ({call.subagent_model})"
                elif call.tool_name == "Skill" and call.skill_name:
                    bullet += f" → **{call.skill_name}**"
                if resp_preview:
                    bullet += f" — _{resp_preview}_"
                lines.append(bullet)
            lines.append("")

        # Outcome (for outcome events: show response)
        if event.event_type == "outcome" and event.detail:
            preview = event.detail[:200].replace("\n", " ").strip()
            lines.append(f"**Outcome:** {preview}")
            lines.append("")

        # Links
        if event.github_links:
            links_str = " ".join(event.github_links)
            lines.append(f"**Links:** {links_str}")
            lines.append("")

        lines.append("---")
        lines.append("")

    return "\n".join(lines)


def write_report(report: SessionReport, output_path: Path) -> None:
    """Render *report* and write it to *output_path*, creating parent dirs."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_markdown(report), encoding="utf-8")


# ---------------------------------------------------------------------------
# Round-trip reader
# ---------------------------------------------------------------------------

_META_RE = re.compile(
    r"<!--\s*meta:\s*(?P<kv>[^>]+)-->",
    re.DOTALL,
)
_HEADING_RE = re.compile(
    r"^####\s+(?P<time>\d{2}:\d{2})\s+·\s+(?P<actor>[^·]+)\s+·\s+(?P<title>.+)$"
)


def _parse_meta_comment(comment_body: str) -> dict[str, str]:
    """Parse ``key=value; key2=value2`` pairs from an HTML meta comment body."""
    result: dict[str, str] = {}
    for part in comment_body.split(";"):
        part = part.strip()
        if "=" in part:
            k, _, v = part.partition("=")
            result[k.strip()] = v.strip()
    return result


def read_markdown(path: Path) -> dict[str, Any]:
    """Parse a canonical session-report Markdown file.

    Returns a dict with:
    - ``frontmatter`` (dict from YAML)
    - ``events`` (list of dicts, one per timeline entry)

    Each event dict has:
    ``time``, ``actor``, ``title``, ``detail``, ``meta`` (from HTML comment),
    ``calls_text``, ``outcome_text``, ``links_text``.

    WHY: Enables round-trip testing (render → read → verify) and gives the
         JSX converter a structured parse target without re-implementing the
         full JSONL parser.
    """
    text = path.read_text(encoding="utf-8")

    # -- Split frontmatter ----------------------------------------------------
    fm: dict[str, Any] = {}
    body = text
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            fm_text = text[3:end].strip()
            try:
                fm = yaml.safe_load(fm_text) or {}
            except yaml.YAMLError:
                fm = {}
            body = text[end + 4 :]

    # -- Parse timeline entries -----------------------------------------------
    events: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    detail_lines: list[str] = []
    calls_lines: list[str] = []
    outcome_line = ""
    links_line = ""
    in_calls = False

    def _flush() -> None:
        nonlocal current, detail_lines, calls_lines, outcome_line, links_line, in_calls
        if current is None:
            return
        current["detail"] = "\n".join(detail_lines).strip()
        current["calls_text"] = "\n".join(calls_lines).strip()
        current["outcome_text"] = outcome_line
        current["links_text"] = links_line
        events.append(current)
        current = None
        detail_lines = []
        calls_lines = []
        outcome_line = ""
        links_line = ""
        in_calls = False

    for line in body.splitlines():
        # New heading?
        m = _HEADING_RE.match(line)
        if m:
            _flush()
            current = {
                "time": m.group("time").strip(),
                "actor": m.group("actor").strip(),
                "title": m.group("title").strip(),
                "meta": {},
            }
            in_calls = False
            continue

        if current is None:
            continue

        # Meta comment?
        mm = _META_RE.search(line)
        if mm:
            current["meta"] = _parse_meta_comment(mm.group("kv"))
            continue

        # Horizontal rule separator
        if line.strip() == "---":
            continue

        # Calls section?
        if line.startswith("**Calls:**"):
            in_calls = True
            continue

        if line.startswith("**Outcome:**"):
            in_calls = False
            outcome_line = line[len("**Outcome:**") :].strip()
            continue

        if line.startswith("**Links:**"):
            in_calls = False
            links_line = line[len("**Links:**") :].strip()
            continue

        if in_calls:
            if line.startswith("- "):
                calls_lines.append(line)
        else:
            detail_lines.append(line)

    _flush()

    return {"frontmatter": fm, "events": events}

"""
Convert a canonical session-tracker Markdown report into a self-contained JSX
timeline visualiser component.

WHAT: Parses a claude-mpm session-report Markdown file (YAML frontmatter +
      Timeline entries) and emits a standalone React JSX file with all session
      data embedded as constants — no external fetch required.
WHY:  Enables offline, shareable visual timelines from the deterministic
      session-tracker reports without requiring a build step or data server.

Usage::

    python scripts/session_timeline_to_jsx.py <input.md> [-o output.jsx]

If ``-o`` is omitted the output path is the input path with ``.jsx`` extension.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# YAML frontmatter parser (minimal, stdlib-only fall-back when PyYAML absent)
# ---------------------------------------------------------------------------

try:
    import yaml as _yaml

    def _load_yaml(text: str) -> Any:
        return _yaml.safe_load(text)

except ImportError:  # pragma: no cover

    def _load_yaml(text: str) -> Any:  # type: ignore[misc]
        """Tiny YAML subset: handles scalars, lists, and nested dicts."""
        raise RuntimeError(
            "PyYAML is required but not installed; run: pip install pyyaml"
        )


# ---------------------------------------------------------------------------
# Markdown parser
# ---------------------------------------------------------------------------

_ENTRY_HEADING = re.compile(
    r"^####\s+(\d{1,2}:\d{2})\s+·\s+([^·]+?)\s+·\s+(.+?)\s*$",
    re.MULTILINE,
)

_META_COMMENT = re.compile(
    r"<!--\s*meta:\s*(.*?)\s*-->",
    re.DOTALL,
)

_META_KV = re.compile(r"(\w+)=([^;]*?)(?:;|$)")

_CALLS_SECTION = re.compile(r"\*\*Calls:\*\*\s*\n((?:\s*-[^\n]+\n?)*)", re.MULTILINE)
_CALL_ITEM = re.compile(
    r"^\s*-\s*`([^`]+)`(?:\s*→\s*\*\*([^*]+)\*\*)?(?:\s*\(([^)]+)\))?\s*(?:—\s*_(.+?)_)?\s*$"
)

_OUTCOME_SECTION = re.compile(r"\*\*Outcome:\*\*\s*(.+?)(?=\n\n|\n\*\*|\Z)", re.DOTALL)
_LINKS_SECTION = re.compile(r"\*\*Links:\*\*\s*(.+?)(?=\n\n|\n---|\Z)", re.DOTALL)
_URL_RE = re.compile(r"https?://\S+")


def _parse_meta(comment_text: str) -> dict[str, str]:
    """Parse ``key=value; key=value`` pairs from a meta comment body."""
    result: dict[str, str] = {}
    for m in _META_KV.finditer(comment_text):
        result[m.group(1).strip()] = m.group(2).strip()
    return result


def _parse_calls(text: str) -> list[dict[str, str]]:
    """Extract **Calls:** bullet list into structured dicts."""
    calls: list[dict[str, str]] = []
    m = _CALLS_SECTION.search(text)
    if not m:
        return calls
    for line in m.group(1).splitlines():
        cm = _CALL_ITEM.match(line)
        if cm:
            calls.append(
                {
                    "tool": cm.group(1) or "",
                    "target": cm.group(2) or "",
                    "model": cm.group(3) or "",
                    "result": cm.group(4) or "",
                }
            )
        elif line.strip().startswith("- "):
            # Fallback: just grab what's between the backticks
            raw = line.strip()[2:]
            tool_m = re.match(r"`([^`]+)`(.*)", raw)
            if tool_m:
                calls.append(
                    {
                        "tool": tool_m.group(1),
                        "target": "",
                        "model": "",
                        "result": tool_m.group(2).strip(" —_"),
                    }
                )
    return calls


def _parse_outcome(text: str) -> str:
    m = _OUTCOME_SECTION.search(text)
    if not m:
        return ""
    return m.group(1).strip()


def _parse_links(text: str) -> list[dict[str, str]]:
    """Return list of ``{label, url, type}`` dicts from **Links:** section."""
    links: list[dict[str, str]] = []
    m = _LINKS_SECTION.search(text)
    if not m:
        return links
    raw = m.group(1).strip()
    for url in _URL_RE.findall(raw):
        url = url.rstrip(".,)")
        ltype = "pr" if "/pull/" in url else "issue"
        # Label: last path segment
        label_raw = url.rstrip("/").split("/")[-1]
        label = f"PR #{label_raw}" if ltype == "pr" else f"#{label_raw}"
        links.append({"label": label, "url": url, "type": ltype})
    return links


def _infer_tags(meta: dict[str, str], calls: list[dict[str, str]]) -> list[str]:
    """Derive display tags from meta type and call list."""
    tags_raw = meta.get("tags", "")
    tag_set: set[str] = set()
    for t in tags_raw.split(","):
        t = t.strip()
        if t and t not in ("turn", "prompt", "outcome", "links", "ambiguous"):
            tag_set.add(t)
    # Augment from calls
    for c in calls:
        tool = c.get("tool", "")
        if "trusty-review" in tool or "review_pr" in tool:
            tag_set.add("review")
        elif tool == "Agent":
            tag_set.add("agent")
        elif tool == "Skill":
            tag_set.add("skill")
    return sorted(tag_set)


def _frontmatter_split(content: str) -> tuple[str, str]:
    """Split ``---`` fenced YAML frontmatter from the body."""
    if not content.startswith("---"):
        return "", content
    end = content.find("\n---", 3)
    if end == -1:
        return "", content
    return content[3:end].strip(), content[end + 4 :].lstrip("\n")


def parse_markdown(path: Path) -> dict[str, Any]:
    """
    Parse a session-tracker Markdown report into structured data.

    WHAT: Reads the YAML frontmatter and `## Timeline` entries, returning a
          dict with ``frontmatter`` and ``events`` keys.
    WHY:  Provides a clean, testable boundary between file I/O and JSX
          generation logic.
    """
    content = path.read_text(encoding="utf-8")
    fm_text, body = _frontmatter_split(content)
    frontmatter: dict[str, Any] = _load_yaml(fm_text) if fm_text else {}

    # Split on #### headings
    splits = list(_ENTRY_HEADING.finditer(body))
    entries: list[dict[str, Any]] = []

    for i, m in enumerate(splits):
        time_str = m.group(1).strip()
        actor = m.group(2).strip()
        title = m.group(3).strip()

        # Body between this heading and the next (or EOF)
        start = m.end()
        end = splits[i + 1].start() if i + 1 < len(splits) else len(body)
        segment = body[start:end]

        # Meta comment
        meta_m = _META_COMMENT.search(segment)
        meta = _parse_meta(meta_m.group(1)) if meta_m else {}

        # Strip the meta comment from the segment for further parsing
        clean = _META_COMMENT.sub("", segment).strip()
        # Remove leading/trailing horizontal rules
        clean = re.sub(r"^\s*---+\s*", "", clean).strip()
        clean = re.sub(r"\s*---+\s*$", "", clean).strip()

        calls = _parse_calls(clean)
        outcome = _parse_outcome(clean)
        links = _parse_links(clean)
        tags = _infer_tags(meta, calls)

        # Detail prose = clean text minus Calls/Outcome/Links sub-sections
        detail = clean
        detail = _CALLS_SECTION.sub("", detail)
        detail = _OUTCOME_SECTION.sub("", detail)
        detail = _LINKS_SECTION.sub("", detail)
        detail = re.sub(r"\n{3,}", "\n\n", detail).strip()

        entries.append(
            {
                "time": time_str,
                "who": actor,
                "title": title,
                "tags": tags,
                "detail": detail,
                "calls": calls,
                "outcome": outcome,
                "links": links,
                "meta": meta,
            }
        )

    return {"frontmatter": frontmatter, "events": entries}


# ---------------------------------------------------------------------------
# JSX generator
# ---------------------------------------------------------------------------

_JSX_TEMPLATE = """\
import {{ useState, useRef, useEffect }} from "react";

// ── Session data (auto-generated by session_timeline_to_jsx.py) ─────────────

const SESSION = {session_json};

const COST_BREAKDOWN = {cost_breakdown_json};

const GRAND_TOTAL_COST = {grand_total_cost};

const EVENTS = {events_json};

// ── Colour tokens ────────────────────────────────────────────────────────────

const C = {{
  bg: "#f8f9fa",
  surface: "#ffffff",
  surfaceAlt: "#f1f3f5",
  border: "#dee2e6",
  borderStrong: "#adb5bd",
  text: "#212529",
  textMid: "#495057",
  textMuted: "#868e96",
  bobAccent: "#c2255c",
  bobBg: "#fff0f6",
  bobBorder: "#f783ac",
  mpmAccent: "#1971c2",
  mpmBg: "#e7f5ff",
  mpmBorder: "#74c0fc",
  ticketColor: "#2f9e44",
  ticketBg: "#ebfbee",
  ticketBorder: "#8ce99a",
  worktreeColor: "#1971c2",
  worktreeBg: "#e7f5ff",
  worktreeBorder: "#74c0fc",
  reviewColor: "#e67700",
  reviewBg: "#fff9db",
  reviewBorder: "#ffd43b",
  agentColor: "#6741d9",
  agentBg: "#f3f0ff",
  agentBorder: "#b197fc",
  skillColor: "#0c8599",
  skillBg: "#e3fafc",
  skillBorder: "#66d9e8",
  outcomeBg: "#f1f3f5",
  costBg: "#fff9db",
  costBorder: "#ffd43b",
  costColor: "#e67700",
  tokenBg: "#f3f0ff",
  tokenBorder: "#b197fc",
  tokenColor: "#6741d9",
  sans: "Inter, system-ui, -apple-system, sans-serif",
  mono: "'JetBrains Mono', 'Fira Code', ui-monospace, monospace",
}};

const TAG_CFG = {{
  ticket:   {{ label: "ticket-driven", color: C.ticketColor,   bg: C.ticketBg,   border: C.ticketBorder }},
  worktree: {{ label: "worktree",      color: C.worktreeColor, bg: C.worktreeBg, border: C.worktreeBorder }},
  review:   {{ label: "trusty-review", color: C.reviewColor,   bg: C.reviewBg,   border: C.reviewBorder }},
  agent:    {{ label: "agent-call",    color: C.agentColor,    bg: C.agentBg,    border: C.agentBorder }},
  skill:    {{ label: "skill",         color: C.skillColor,    bg: C.skillBg,    border: C.skillBorder }},
}};

const FILTERS = [
  {{ id: "all",      label: "All events",     color: C.text }},
  {{ id: "bob",      label: "Bob only",       color: C.bobAccent }},
  {{ id: "mpm",      label: "mpm only",       color: C.mpmAccent }},
  {{ id: "review",   label: "trusty-review",  color: C.reviewColor }},
  {{ id: "agent",    label: "agent-call",     color: C.agentColor }},
  {{ id: "skill",    label: "skill",          color: C.skillColor }},
];

// ── Helpers ──────────────────────────────────────────────────────────────────

function fmtTokens(n) {{
  if (!n || n === 0) return null;
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + "M";
  if (n >= 1_000) return (n / 1_000).toFixed(0) + "k";
  return String(n);
}}

function fmtCost(usd) {{
  if (!usd || usd === 0) return null;
  return "$" + usd.toFixed(4);
}}

function isVisible(entry, filter) {{
  if (filter === "all") return true;
  if (filter === "bob") return entry.who === "bob";
  if (filter === "mpm") return entry.who === "mpm";
  return (entry.tags || []).includes(filter);
}}

// ── Sub-components ───────────────────────────────────────────────────────────

function Tag({{ type }}) {{
  const t = TAG_CFG[type];
  if (!t) return null;
  return (
    <span style={{{{
      fontSize: 12, fontFamily: C.mono, fontWeight: 500,
      padding: "2px 9px", borderRadius: 4,
      background: t.bg, color: t.color,
      border: `1px solid ${{t.border}}`,
      whiteSpace: "nowrap",
    }}}}>{{t.label}}</span>
  );
}}

function ModelBadge({{ model }}) {{
  if (!model || model === "none") return null;
  const isOpus = model.includes("opus");
  const isHaiku = model.includes("haiku");
  const color = isOpus ? C.costColor : isHaiku ? C.ticketColor : C.mpmAccent;
  const bg = isOpus ? C.costBg : isHaiku ? C.ticketBg : C.mpmBg;
  const border = isOpus ? C.costBorder : isHaiku ? C.ticketBorder : C.mpmBorder;
  const short = model.replace("claude-", "").replace(/-20\\d{{6}}$/, "");
  return (
    <span style={{{{
      fontSize: 11, fontFamily: C.mono, fontWeight: 500,
      padding: "2px 8px", borderRadius: 4,
      background: bg, color, border: `1px solid ${{border}}`,
      whiteSpace: "nowrap",
    }}}}>{{short}}</span>
  );
}}

function TokenPill({{ meta }}) {{
  const inTok = parseInt(meta.in || 0, 10);
  const outTok = parseInt(meta.out || 0, 10);
  const cacheRead = parseInt(meta.cache_read || 0, 10);
  const cacheWrite = parseInt(meta.cache_write || 0, 10);
  const cost = parseFloat(meta.cost_usd || 0);
  if (!inTok && !outTok) return null;
  return (
    <span style={{{{
      fontSize: 11, fontFamily: C.mono, fontWeight: 400,
      padding: "2px 8px", borderRadius: 4,
      background: C.tokenBg, color: C.tokenColor,
      border: `1px solid ${{C.tokenBorder}}`,
      whiteSpace: "nowrap",
    }}}}>
      ↑{{fmtTokens(inTok)}} ↓{{fmtTokens(outTok)}}
      {{cacheRead > 0 ? ` cr:${{fmtTokens(cacheRead)}}` : ""}}
      {{cacheWrite > 0 ? ` cw:${{fmtTokens(cacheWrite)}}` : ""}}
      {{cost > 0 ? ` · ${{fmtCost(cost)}}` : ""}}
    </span>
  );
}}

function CallsList({{ calls }}) {{
  if (!calls || calls.length === 0) return null;
  return (
    <div style={{{{ marginTop: 10 }}}}>
      <div style={{{{ fontSize: 12, color: C.textMuted, marginBottom: 4, fontWeight: 600, textTransform: "uppercase", letterSpacing: ".05em" }}}}>Calls</div>
      {{calls.map((c, i) => (
        <div key={{i}} style={{{{
          fontSize: 13, fontFamily: C.mono,
          padding: "3px 0",
          color: C.textMid,
        }}}}>
          <span style={{{{ color: C.mpmAccent }}}}>{{"`"}}</span>
          <span style={{{{ color: C.text, fontWeight: 500 }}}}>{{c.tool}}</span>
          <span style={{{{ color: C.mpmAccent }}}}>{{"`"}}</span>
          {{c.target ? <span> → <strong>{{c.target}}</strong></span> : null}}
          {{c.model ? <span style={{{{ color: C.textMuted }}}}> ({{c.model}})</span> : null}}
          {{c.result ? <span style={{{{ color: C.textMuted }}}}> — <em>{{c.result.slice(0, 80)}}{{c.result.length > 80 ? "…" : ""}}</em></span> : null}}
        </div>
      ))}}
    </div>
  );
}}

function Links({{ links }}) {{
  if (!links || links.length === 0) return null;
  return (
    <div style={{{{ display: "flex", gap: 6, flexWrap: "wrap", marginTop: 12 }}}}>
      {{links.map((l, i) => {{
        const isPr = l.type === "pr";
        return (
          <a key={{i}} href={{l.url}} target="_blank" rel="noreferrer"
            onClick={{e => e.stopPropagation()}}
            style={{{{
              fontSize: 12, fontFamily: C.mono, fontWeight: 500,
              padding: "3px 10px", borderRadius: 4,
              background: isPr ? C.worktreeBg : C.ticketBg,
              color: isPr ? C.worktreeColor : C.ticketColor,
              border: `1px solid ${{isPr ? C.worktreeBorder : C.ticketBorder}}`,
              textDecoration: "none",
              display: "inline-flex", alignItems: "center", gap: 4,
            }}}}>
            <span style={{{{ fontSize: 11, opacity: 0.7 }}}}>{{isPr ? "⤴" : "◎"}}</span>
            {{l.label}}
          </a>
        );
      }}}}
    </div>
  );
}}

function Entry({{ entry, filter, open, onToggle }}) {{
  const ref = useRef(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {{
    const el = ref.current;
    if (!el) return;
    const obs = new IntersectionObserver(([e]) => {{
      if (e.isIntersecting) {{ setVisible(true); obs.disconnect(); }}
    }}, {{ threshold: 0.05 }});
    obs.observe(el);
    return () => obs.disconnect();
  }}, []);

  if (!isVisible(entry, filter)) return null;
  const isBob = entry.who === "bob";

  return (
    <div ref={{ref}} style={{{{
      position: "relative", marginBottom: 6,
      opacity: visible ? 1 : 0, transform: visible ? "none" : "translateY(8px)",
      transition: "opacity .25s, transform .25s",
    }}}}>
      <div style={{{{
        position: "absolute", left: -26, top: 17,
        width: 12, height: 12, borderRadius: "50%",
        background: isBob ? C.bobBg : C.mpmBg,
        border: `2px solid ${{isBob ? C.bobBorder : C.mpmBorder}}`,
        zIndex: 1,
      }}}} />
      <div onClick={{onToggle}} style={{{{
        background: C.surface,
        border: `1.5px solid ${{open ? (isBob ? C.bobBorder : C.borderStrong) : C.border}}`,
        borderLeft: `4px solid ${{isBob ? C.bobAccent : C.mpmAccent}}`,
        borderRadius: "0 8px 8px 0",
        padding: "12px 16px",
        cursor: "pointer",
        userSelect: "none",
      }}}}>
        <div style={{{{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}}}>
          <span style={{{{ fontSize: 13, fontFamily: C.mono, color: C.textMuted, minWidth: 40, flexShrink: 0 }}}}>
            {{entry.time}}
          </span>
          <span style={{{{
            fontSize: 13, fontWeight: 600, fontFamily: C.sans,
            padding: "2px 10px", borderRadius: 4,
            background: isBob ? C.bobBg : C.mpmBg,
            color: isBob ? C.bobAccent : C.mpmAccent,
            border: `1px solid ${{isBob ? C.bobBorder : C.mpmBorder}}`,
            flexShrink: 0,
          }}}}>
            {{isBob ? "Bob" : (entry.who === "mpm" ? "mpm" : entry.who)}}
          </span>
          {{(entry.tags || []).map(t => <Tag key={{t}} type={{t}} />)}}
          <ModelBadge model={{entry.meta?.model}} />
          <TokenPill meta={{entry.meta || {{}}}} />
          <span style={{{{ flex: 1, minWidth: 120, fontSize: 15, fontWeight: 500, color: C.text, fontFamily: C.sans, lineHeight: 1.4 }}}}>
            {{entry.title}}
          </span>
          <span style={{{{
            fontSize: 16, color: C.textMuted, flexShrink: 0,
            transform: open ? "rotate(180deg)" : "none",
            transition: "transform .2s", display: "block",
          }}}}>▾</span>
        </div>

        {{open && (
          <div style={{{{ marginTop: 12, paddingTop: 12, borderTop: `1px solid ${{C.border}}` }}}}>
            {{entry.detail && (
              <p style={{{{ fontSize: 15, fontFamily: C.sans, color: C.textMid, lineHeight: 1.7, whiteSpace: "pre-line", margin: 0 }}}}>
                {{entry.detail}}
              </p>
            )}}
            <CallsList calls={{entry.calls}} />
            {{entry.outcome && (
              <div style={{{{
                marginTop: 12, padding: "9px 14px",
                background: C.outcomeBg, borderRadius: 6,
                border: `1px solid ${{C.border}}`,
                fontSize: 14, fontFamily: C.mono,
                color: C.ticketColor, fontWeight: 500,
              }}}}>
                {{entry.outcome}}
              </div>
            )}}
            <Links links={{entry.links}} />
          </div>
        )}}
      </div>
    </div>
  );
}}

function CostPanel() {{
  if (!COST_BREAKDOWN || COST_BREAKDOWN.length === 0) return null;
  return (
    <div style={{{{
      background: C.surface, border: `1px solid ${{C.costBorder}}`,
      borderRadius: 10, padding: "18px 20px", marginBottom: 28,
    }}}}>
      <div style={{{{ fontSize: 12, color: C.textMuted, textTransform: "uppercase", letterSpacing: ".06em", marginBottom: 14 }}}}>
        Cost Breakdown — rack rates
      </div>
      <div style={{{{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))", gap: 10, marginBottom: 14 }}}}>
        {{COST_BREAKDOWN.map((row, i) => (
          <div key={{i}} style={{{{
            background: C.costBg, border: `1px solid ${{C.costBorder}}`,
            borderRadius: 8, padding: "12px 14px",
          }}}}>
            <div style={{{{ fontSize: 12, fontFamily: C.mono, color: C.costColor, fontWeight: 600, marginBottom: 4 }}}}>
              {{row.model.replace("claude-", "").replace(/-20\\d{{6}}$/, "")}}
            </div>
            <div style={{{{ fontSize: 20, fontWeight: 700, fontFamily: C.mono, color: C.text }}}}>
              ${{row.cost_usd?.toFixed(4)}}
            </div>
            <div style={{{{ fontSize: 11, color: C.textMuted, marginTop: 4 }}}}>
              {{fmtTokens(row.input)}} in · {{fmtTokens(row.output)}} out
              {{row.cache_read > 0 ? ` · ${{fmtTokens(row.cache_read)}} cr` : ""}}
              {{" · "}}{{row.turns}} turn{{row.turns !== 1 ? "s" : ""}}
            </div>
          </div>
        ))}}
      </div>
      <div style={{{{
        display: "flex", alignItems: "baseline", gap: 10,
        paddingTop: 12, borderTop: `1px solid ${{C.costBorder}}`,
      }}}}>
        <span style={{{{ fontSize: 13, color: C.textMuted }}}}>Grand total</span>
        <span style={{{{ fontSize: 24, fontWeight: 700, fontFamily: C.mono, color: C.costColor }}}}>
          ${{GRAND_TOTAL_COST?.toFixed(4)}}
        </span>
      </div>
    </div>
  );
}}

function StatCards() {{
  const cards = SESSION.stat_cards || [];
  if (cards.length === 0) return null;
  return (
    <div style={{{{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 10, marginBottom: 28 }}}}>
      {{cards.map(s => (
        <div key={{s.label}} style={{{{
          background: C.surface, border: `1px solid ${{C.border}}`,
          borderRadius: 10, padding: "16px 18px",
        }}}}>
          <div style={{{{ fontSize: 12, color: C.textMuted, textTransform: "uppercase", letterSpacing: ".06em", marginBottom: 6 }}}}>{{s.label}}</div>
          <div style={{{{ fontSize: 28, fontWeight: 700, color: C.text, fontFamily: C.mono, lineHeight: 1, marginBottom: 4 }}}}>{{s.value}}</div>
          <div style={{{{ fontSize: 12, color: C.textMuted }}}}>{{s.sub}}</div>
        </div>
      ))}}
    </div>
  );
}}

function AutonomyBar() {{
  const {{ bob_pct = 0, mpm_pct = 100 }} = SESSION.autonomy || {{}};
  return (
    <div style={{{{ background: C.surface, border: `1px solid ${{C.border}}`, borderRadius: 10, padding: "18px 20px", marginBottom: 28 }}}}>
      <div style={{{{ fontSize: 12, color: C.textMuted, textTransform: "uppercase", letterSpacing: ".06em", marginBottom: 12 }}}}>
        Session time — Bob vs mpm
      </div>
      <div style={{{{ height: 14, background: C.surfaceAlt, borderRadius: 7, overflow: "hidden", border: `1px solid ${{C.border}}`, marginBottom: 12, display: "flex" }}}}>
        <div style={{{{ width: `${{bob_pct}}%`, background: C.bobAccent, borderRadius: "7px 0 0 7px", minWidth: bob_pct > 0 ? 4 : 0 }}}} />
        <div style={{{{ flex: 1, background: "#4dabf7", opacity: .35 }}}} />
      </div>
      <div style={{{{ display: "flex", gap: 28, fontSize: 14, fontFamily: C.mono }}}}>
        <span style={{{{ color: C.bobAccent, fontWeight: 600 }}}}>● Bob ~{{bob_pct}}%</span>
        <span style={{{{ color: C.mpmAccent, fontWeight: 600 }}}}>● mpm ~{{mpm_pct}}%</span>
      </div>
    </div>
  );
}}

// ── Main component ────────────────────────────────────────────────────────────

export default function App() {{
  const [filter, setFilter] = useState("all");
  const [openIds, setOpenIds] = useState(new Set());

  const allEntries = EVENTS.flatMap((s, si) =>
    s.entries.map((e, ei) => ({{ ...e, id: `${{si}}-${{ei}}` }}))
  );
  const visibleEntries = allEntries.filter(e => isVisible(e, filter));
  const visibleIds = visibleEntries.map(e => e.id);
  const allExpanded = visibleIds.length > 0 && visibleIds.every(id => openIds.has(id));

  function toggleEntry(id) {{
    setOpenIds(prev => {{
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    }});
  }}

  function expandAll() {{ setOpenIds(prev => new Set([...prev, ...visibleIds])); }}
  function collapseAll() {{
    setOpenIds(prev => {{
      const next = new Set(prev);
      visibleIds.forEach(id => next.delete(id));
      return next;
    }});
  }}

  useEffect(() => {{ setOpenIds(new Set()); }}, [filter]);

  const sessionDate = SESSION.date || "";
  const sessionTitle = (SESSION.title || "Session timeline").slice(0, 120);
  const project = SESSION.project || "";

  return (
    <div style={{{{ background: C.bg, minHeight: "100vh", fontFamily: C.sans }}}}>
      <div style={{{{ maxWidth: 860, margin: "0 auto", padding: "48px 28px 80px" }}}}>

        {{/* Header */}}
        <div style={{{{ marginBottom: 36 }}}}>
          <div style={{{{ fontSize: 12, fontFamily: C.mono, color: C.textMuted, letterSpacing: ".07em", textTransform: "uppercase", marginBottom: 12 }}}}>
            claude-mpm · {{project}} · {{sessionDate}}
          </div>
          <h1 style={{{{ fontSize: 28, fontWeight: 700, color: C.text, letterSpacing: "-.02em", lineHeight: 1.2, margin: "0 0 10px" }}}}>
            {{sessionTitle}}
          </h1>
          <div style={{{{ fontSize: 13, fontFamily: C.mono, color: C.textMuted }}}}>
            Session {{SESSION.session_id || ""}}
          </div>
        </div>

        {{/* Stat cards */}}
        <StatCards />

        {{/* Cost breakdown */}}
        <CostPanel />

        {{/* Autonomy bar */}}
        <AutonomyBar />

        {{/* Filter bar */}}
        <div style={{{{ marginBottom: 32 }}}}>
          <div style={{{{ fontSize: 13, color: C.textMuted, marginBottom: 12, fontWeight: 500 }}}}>Filter by event type</div>
          <div style={{{{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 14 }}}}>
            {{FILTERS.map(f => {{
              const active = filter === f.id;
              return (
                <button key={{f.id}} onClick={{() => setFilter(f.id)}} style={{{{
                  fontSize: 14, fontFamily: C.sans, fontWeight: active ? 600 : 400,
                  padding: "8px 18px", borderRadius: 20, cursor: "pointer",
                  background: active ? f.color : C.surface,
                  color: active ? "#fff" : C.textMid,
                  border: `1.5px solid ${{active ? f.color : C.border}}`,
                  transition: "all .15s",
                }}}}>{{f.label}}</button>
              );
            }}}}
          </div>
          <div style={{{{ display: "flex", alignItems: "center", gap: 10 }}}}>
            <span style={{{{ fontSize: 13, color: C.textMuted }}}}>
              {{visibleIds.length}} event{{visibleIds.length !== 1 ? "s" : ""}}
            </span>
            <span style={{{{ color: C.border }}}}>·</span>
            <button onClick={{allExpanded ? collapseAll : expandAll}} style={{{{
              fontSize: 13, fontFamily: C.sans, fontWeight: 500,
              padding: "5px 14px", borderRadius: 6, cursor: "pointer",
              background: C.surface, color: C.textMid,
              border: `1px solid ${{C.border}}`,
            }}}}>
              {{allExpanded ? "Collapse all" : "Expand all"}}
            </button>
          </div>
        </div>

        {{/* Timeline */}}
        <div style={{{{ position: "relative", paddingLeft: 32 }}}}>
          <div style={{{{
            position: "absolute", left: 11, top: 8, bottom: 8, width: 2,
            background: C.border, borderRadius: 1,
          }}}} />
          {{EVENTS.map((sec, si) => {{
            const anyVisible = sec.entries.some(e => isVisible(e, filter));
            if (!anyVisible) return null;
            return (
              <div key={{si}} style={{{{ marginBottom: 8 }}}}>
                <div style={{{{
                  fontSize: 13, fontFamily: C.mono, color: C.textMuted,
                  fontWeight: 600, letterSpacing: ".04em",
                  paddingBottom: 10, marginBottom: 8,
                  borderBottom: `1px solid ${{C.border}}`,
                }}}}>
                  {{sec.section}}
                </div>
                {{sec.entries.map((entry, ei) => {{
                  const id = `${{si}}-${{ei}}`;
                  return (
                    <Entry key={{id}} entry={{entry}} filter={{filter}}
                           open={{openIds.has(id)}} onToggle={{() => toggleEntry(id)}} />
                  );
                }})}}
              </div>
            );
          }})}}
        </div>

        {{/* Footer */}}
        <div style={{{{ marginTop: 56, paddingTop: 24, borderTop: `2px solid ${{C.border}}` }}}}>
          <p style={{{{ fontSize: 14, color: C.textMuted, fontFamily: C.mono, margin: 0 }}}}>
            Generated by claude-mpm session_timeline_to_jsx.py · {{SESSION.generated_at || ""}}
          </p>
        </div>

      </div>
    </div>
  );
}}
"""


def _group_events_by_time(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Group timeline entries into sections by HH:MM time bucket.

    WHAT: Merges consecutive entries with the same HH:MM timestamp into one
          section labelled ``HH:MM — ...`` mirroring the reference template.
    WHY:  The reference JSX groups entries under time-section headers; this
          preserves the visual rhythm of the original format.
    """
    if not events:
        return []

    sections: list[dict[str, Any]] = []
    current_time: str | None = None
    current_section: dict[str, Any] | None = None

    for entry in events:
        t = entry.get("time", "00:00")
        if t != current_time:
            if current_section is not None:
                sections.append(current_section)
            current_time = t
            current_section = {
                "section": f"{t} — {entry.get('who', 'unknown')}",
                "entries": [],
            }
        assert current_section is not None
        current_section["entries"].append(entry)

    if current_section is not None:
        sections.append(current_section)

    return sections


def _safe_json(obj: Any) -> str:
    """Serialize obj to compact JSON, safe for embedding in JSX."""
    return json.dumps(obj, ensure_ascii=False, indent=2)


def generate_jsx(parsed: dict[str, Any]) -> str:
    """
    Generate a self-contained JSX string from parsed session data.

    WHAT: Takes the ``frontmatter`` + ``events`` dict from ``parse_markdown``
          and renders the full JSX file content as a string.
    WHY:  Separates the generation concern from I/O so the function is
          independently testable.
    """
    fm: dict[str, Any] = parsed.get("frontmatter", {})
    events: list[dict[str, Any]] = parsed.get("events", [])

    # Session summary block for the header
    session_data = {
        "session_id": fm.get("session_id", ""),
        "project": fm.get("project", ""),
        "project_path": fm.get("project_path", ""),
        "date": fm.get("date", ""),
        "generated_at": fm.get("generated_at", ""),
        "title": fm.get("title", ""),
        "autonomy": fm.get("autonomy", {}),
        "stat_cards": fm.get("stat_cards", []),
        "has_pricing_fallback": fm.get("has_pricing_fallback", False),
    }

    cost_breakdown = fm.get("model_breakdown", [])
    grand_total = fm.get("grand_total_cost_usd", 0.0)

    sections = _group_events_by_time(events)

    return _JSX_TEMPLATE.format(
        session_json=_safe_json(session_data),
        cost_breakdown_json=_safe_json(cost_breakdown),
        grand_total_cost=json.dumps(grand_total),
        events_json=_safe_json(sections),
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    """Entry point for the CLI converter."""
    parser = argparse.ArgumentParser(
        description="Convert a session-tracker Markdown report to a self-contained JSX file.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Example:\n  python scripts/session_timeline_to_jsx.py report.md -o timeline.jsx",
    )
    parser.add_argument("input", type=Path, help="Input .md file path")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Output .jsx file path (default: <input>.jsx)",
    )
    args = parser.parse_args(argv)

    input_path: Path = args.input
    if not input_path.exists():
        print(f"Error: input file not found: {input_path}", file=sys.stderr)
        return 1

    output_path: Path = args.output or input_path.with_suffix(".jsx")

    try:
        parsed = parse_markdown(input_path)
    except Exception as exc:
        print(f"Error parsing {input_path}: {exc}", file=sys.stderr)
        return 1

    jsx = generate_jsx(parsed)
    output_path.write_text(jsx, encoding="utf-8")
    print(f"Written: {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

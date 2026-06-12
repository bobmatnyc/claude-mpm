import { useState, useRef, useEffect, useCallback } from "react";

const C = {
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
  ticketColor: "#2f9e44",
  ticketBg: "#ebfbee",
  ticketBorder: "#8ce99a",
  worktreeColor: "#1971c2",
  worktreeBg: "#e7f5ff",
  worktreeBorder: "#74c0fc",
  reviewColor: "#e67700",
  reviewBg: "#fff9db",
  reviewBorder: "#ffd43b",
  outcomeBg: "#f1f3f5",
  sans: "Inter, system-ui, -apple-system, sans-serif",
  mono: "'JetBrains Mono', 'Fira Code', ui-monospace, monospace",
};

const TAG_CFG = {
  ticket:   { label: "ticket-driven", color: C.ticketColor,   bg: C.ticketBg,   border: C.ticketBorder },
  worktree: { label: "worktree",      color: C.worktreeColor, bg: C.worktreeBg, border: C.worktreeBorder },
  review:   { label: "trusty-review", color: C.reviewColor,   bg: C.reviewBg,   border: C.reviewBorder },
};

const STATS = [
  { label: "Bob's active time",       value: "~8 min", sub: "across ~3 hr session" },
  { label: "Bob's interventions",     value: "11",     sub: "never a task spec"     },
  { label: "Tickets written by Bob",  value: "0",      sub: "mpm wrote all of them" },
  { label: "Issues closed",           value: "7",      sub: "#716 720 721 723 725 726 +1" },
  { label: "PRs merged",              value: "6",      sub: "#719 721 722 724 727 728" },
  { label: "Releases shipped",        value: "2",      sub: "v6.5.27 → v6.5.28" },
];

const REPO = "https://github.com/bobmatnyc/claude-mpm";
const issue = n => ({ label: `#${n}`, url: `${REPO}/issues/${n}`, type: "issue" });
const pr    = n => ({ label: `PR #${n}`, url: `${REPO}/pull/${n}`,   type: "pr"    });

const EVENTS = [
  {
    section: "09:00 — session opens",
    entries: [
      {
        time: "09:00", who: "bob", tags: ["ticket"],
        title: "Any gh issues or PRs?",
        detail: "The session opens not with a task but with a query to the tracker. mpm treats the issue list as the canonical backlog — work that isn't tracked isn't work. Bob's total input: 6 words.",
        outcome: "Result: 1 open issue — #716 startup-banner stdio display",
        links: [issue(716)],
      },
      {
        time: "09:00", who: "mpm", tags: ["ticket"],
        title: "Reads #716, confirms exact lines, delegates to engineer",
        detail: "The issue is the spec. mpm reads #716, confirms the exact lines to change in trusty_status.py, and delegates — no design discussion needed because the issue already contains it. Bob didn't write this ticket.",
        outcome: null,
        links: [issue(716)],
      },
      {
        time: "09:01", who: "bob", tags: [],
        title: '"yes"',
        detail: "Bob's entire contribution to issue #716: one word. mpm already understood the work from the ticket.",
        outcome: null,
        links: [],
      },
      {
        time: "09:01", who: "mpm", tags: ["worktree"],
        title: "Engineer commits to main — mpm intercepts, moves to branch",
        detail: `The engineer agent committed directly to main. mpm catches it: "Need to move that to a branch and open a PR per the workflow." The protocol enforces itself — source directory stays at HEAD. PR #719 opened.`,
        outcome: null,
        links: [pr(719)],
      },
      {
        time: "09:02", who: "mpm", tags: ["review"],
        title: "PR #719 → APPROVE A− · 1 nitpick fixed and merged",
        detail: "Nitpick: add inline comment explaining the bracket syntax. mpm applies the fix and merges.",
        outcome: "Merged: 7b85ca3 — Closes #716 ✓",
        links: [pr(719), issue(716)],
      },
    ],
  },
  {
    section: "09:05 — architecture discussion",
    entries: [
      {
        time: "09:05", who: "bob", tags: ["worktree"],
        title: "Proposes worktree-first as framework default",
        detail: `"Source directory pinned to HEAD, work on issue-linked branches, commit with close, PR after review." mpm analyses the proposal, outlines benefits (parallel isolation, no branch gymnastics, explicit cleanup), recommends yes with a config opt-out toggle.`,
        outcome: null,
        links: [],
      },
      {
        time: "09:05", who: "bob", tags: [],
        title: '"yes" + "document this … as part of release notes … including rationale"',
        detail: `Three short follow-up messages adding scope. No implementation instructions — mpm infers what "document this" means in context.`,
        outcome: null,
        links: [],
      },
      {
        time: "09:06", who: "mpm", tags: ["ticket"],
        title: "Creates Issue #720 before writing a line of code",
        detail: "Ticketing + Research agents run in parallel. Issue #720 scoped and opened. Research confirms current workflow skill structure. Bob did not write this ticket.",
        outcome: null,
        links: [issue(720)],
      },
      {
        time: "09:30", who: "mpm", tags: ["worktree"],
        title: "First worktree created — to implement the worktree workflow",
        detail: ".claude/worktrees/issue-720-worktree-workflow/\n\nThe new workflow implements itself. 6 commits, 7,277 tests passing. Changes: mpm-pr-workflow skill, workflow.worktree.enabled: true config, WORKFLOW.md, release notes. PR #721 opened.",
        outcome: null,
        links: [issue(720), pr(721)],
      },
    ],
  },
  {
    section: "09:50 — trusty-review gate: multiple passes",
    entries: [
      {
        time: "09:50", who: "mpm", tags: ["review"],
        title: "PR #721 pass 1 → 2 medium findings, fixes applied",
        detail: "Findings: missing dirty-worktree recovery path, redundant comment. mpm applies fixes and re-submits.",
        outcome: null,
        links: [pr(721)],
      },
      {
        time: "09:55", who: "mpm", tags: ["review"],
        title: "PR #721 pass 3 → reviewer contradicts itself, mpm makes the call",
        detail: `Reviewer first said drop worktrees/, now says add it back. mpm: "The reviewer is oscillating — contradiction with itself. I'm making the call." The gate is a tool, not an oracle.`,
        outcome: null,
        links: [pr(721)],
      },
      {
        time: "09:57", who: "bob", tags: ["worktree"],
        title: "Design call: use .claude/worktrees/ — the Claude Code standard",
        detail: `"I'm not vacillating — we should use .claude as the worktree home, whatever standard Claude Code uses." One sentence. mpm propagates across all PR files.`,
        outcome: "Merged: 2991fce — Closes #720 ✓ · worktree cleaned up",
        links: [pr(721), issue(720)],
      },
    ],
  },
  {
    section: "10:15 — mid-session discovery",
    entries: [
      {
        time: "10:15", who: "bob", tags: ["ticket"],
        title: "Surfaces duplicate hooks bug — multiple projects affected",
        detail: `"Let's also double-check on the duplicate hooks issue." No root cause, no reproduction steps — just the symptom. mpm researches, finds the cause (two divergent installer files), and tracks it before fixing.`,
        outcome: null,
        links: [],
      },
      {
        time: "10:20", who: "mpm", tags: ["ticket", "worktree"],
        title: "Researches root cause, runs parallel fix + rename tracks",
        detail: "Finding: installer.py and hook_installer_service.py each implemented deduplication independently and diverged. Three-layer fix: idempotent write, cross-matcher dedup, startup migration for ~/.claude/settings.json. Engineer went off-script mid-task — mpm caught it and parallelized.",
        outcome: "Merged: ea532a2 — hook idempotency ✓ · Issue #723 filed for tech debt",
        links: [pr(722), issue(723)],
      },
      {
        time: "10:30", who: "mpm", tags: ["review"],
        title: "PRs #721 + #722 reviewed in parallel → both A−, APPROVE",
        detail: `mpm: "Both PRs have verdict: APPROVE internally. I'm going to stop chasing the reviewer in circles." Grade A− with APPROVE means merge — not another fix loop.`,
        outcome: null,
        links: [pr(721), pr(722)],
      },
      {
        time: "10:45", who: "mpm", tags: ["worktree", "review"],
        title: "Issue #723 → worktree → implement → review → merge",
        detail: ".claude/worktrees/issue-723-merge-hooks-helper/\n\nExtract shared merge_hooks_for_event helper. 35/35 tests pass. trusty-review: A−, APPROVE — one finding is pre-existing, doesn't block. mpm tracks it as follow-up #725. Merged, worktree cleaned up.",
        outcome: "Merged: 7269c79 — Closes #723 ✓",
        links: [issue(723), pr(724), issue(725)],
      },
    ],
  },
  {
    section: "11:00 — release notes system",
    entries: [
      {
        time: "11:00", who: "bob", tags: ["ticket"],
        title: "Requests structured release notes compilation system",
        detail: `"Per-minor-version files, patch sections appended, archived on new minor. Then use this to publish a bump." No implementation spec — mpm designs the system, opens issue #726, sets up worktree, implements, reviews, merges.`,
        outcome: null,
        links: [issue(726)],
      },
      {
        time: "11:05", who: "mpm", tags: ["ticket", "worktree"],
        title: "Issue #726 opened · worktree created · implementation starts",
        detail: ".claude/worktrees/issue-726-release-notes/\n\nscripts/compile_release_notes.py: patch releases prepend to docs/releases/vX.Y.md (newest-first), minor releases create a new file, always writes dist/release-notes-latest.md for gh release create. PR #727 opened.",
        outcome: null,
        links: [issue(726), pr(727)],
      },
      {
        time: "11:30", who: "mpm", tags: ["review"],
        title: "PR #727 → B+, APPROVE · 2 real findings caught and fixed",
        detail: "Findings: (1) missing guard if notes file absent at publish time — real defensive gap; (2) patch releases should prepend, not append. Both fixed before merge. Validated end-to-end with a live patch release.",
        outcome: "v6.5.27 published — PyPI ✓  npm ✓  Homebrew ✓  agent repo ✓",
        links: [pr(727), issue(726)],
      },
    ],
  },
  {
    section: "11:50 — final issue + release",
    entries: [
      {
        time: "11:50", who: "bob", tags: ["ticket"],
        title: '"Address 725 then publish a bump"',
        detail: "Six words. mpm creates the worktree, researches the exact call sites, implements a one-line fix, merges in a single clean pass, and publishes.",
        outcome: "v6.5.28 published — Closes #725 ✓",
        links: [issue(725), pr(728)],
      },
    ],
  },
];

const FILTERS = [
  { id: "all",      label: "All events",     color: C.text },
  { id: "bob",      label: "Bob only",       color: C.bobAccent },
  { id: "ticket",   label: "ticket-driven",  color: C.ticketColor },
  { id: "worktree", label: "worktree",       color: C.worktreeColor },
  { id: "review",   label: "trusty-review",  color: C.reviewColor },
  { id: "mpm",      label: "mpm only",       color: C.mpmAccent },
];

function isVisible(entry, filter) {
  if (filter === "all") return true;
  if (filter === "bob") return entry.who === "bob";
  if (filter === "mpm") return entry.who === "mpm";
  return entry.tags.includes(filter);
}

function Tag({ type }) {
  const t = TAG_CFG[type];
  return (
    <span style={{
      fontSize: 12, fontFamily: C.mono, fontWeight: 500,
      padding: "2px 9px", borderRadius: 4,
      background: t.bg, color: t.color,
      border: `1px solid ${t.border}`,
      whiteSpace: "nowrap",
    }}>{t.label}</span>
  );
}

function Links({ links }) {
  if (!links || links.length === 0) return null;
  return (
    <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginTop: 12 }}>
      {links.map((l, i) => {
        const isPr = l.type === "pr";
        return (
          <a
            key={i}
            href={l.url}
            target="_blank"
            rel="noreferrer"
            onClick={e => e.stopPropagation()}
            style={{
              fontSize: 12, fontFamily: C.mono, fontWeight: 500,
              padding: "3px 10px", borderRadius: 4,
              background: isPr ? C.worktreeBg : C.ticketBg,
              color: isPr ? C.worktreeColor : C.ticketColor,
              border: `1px solid ${isPr ? C.worktreeBorder : C.ticketBorder}`,
              textDecoration: "none",
              display: "inline-flex", alignItems: "center", gap: 4,
            }}
          >
            <span style={{ fontSize: 11, opacity: 0.7 }}>{isPr ? "⤴" : "◎"}</span>
            {l.label}
          </a>
        );
      })}
    </div>
  );
}

function Entry({ entry, filter, open, onToggle }) {
  const ref = useRef(null);
  const [in_, setIn] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const obs = new IntersectionObserver(([e]) => {
      if (e.isIntersecting) { setIn(true); obs.disconnect(); }
    }, { threshold: 0.05 });
    obs.observe(el);
    return () => obs.disconnect();
  }, []);

  if (!isVisible(entry, filter)) return null;
  const isBob = entry.who === "bob";

  return (
    <div ref={ref} style={{
      position: "relative", marginBottom: 6,
      opacity: in_ ? 1 : 0, transform: in_ ? "none" : "translateY(8px)",
      transition: "opacity .25s, transform .25s",
    }}>
      <div style={{
        position: "absolute", left: -26, top: 17,
        width: 12, height: 12, borderRadius: "50%",
        background: isBob ? C.bobBg : C.mpmBg,
        border: `2px solid ${isBob ? C.bobBorder : C.worktreeBorder}`,
        zIndex: 1,
      }} />

      <div
        onClick={onToggle}
        style={{
          background: C.surface,
          border: `1.5px solid ${open ? (isBob ? C.bobBorder : C.borderStrong) : C.border}`,
          borderLeft: `4px solid ${isBob ? C.bobAccent : C.mpmAccent}`,
          borderRadius: "0 8px 8px 0",
          padding: "12px 16px",
          cursor: "pointer",
          userSelect: "none",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
          <span style={{ fontSize: 13, fontFamily: C.mono, color: C.textMuted, minWidth: 40, flexShrink: 0 }}>
            {entry.time}
          </span>
          <span style={{
            fontSize: 13, fontWeight: 600, fontFamily: C.sans,
            padding: "2px 10px", borderRadius: 4,
            background: isBob ? C.bobBg : C.mpmBg,
            color: isBob ? C.bobAccent : C.mpmAccent,
            border: `1px solid ${isBob ? C.bobBorder : C.worktreeBorder}`,
            flexShrink: 0,
          }}>
            {isBob ? "Bob" : "mpm"}
          </span>
          {entry.tags.map(t => <Tag key={t} type={t} />)}
          <span style={{ flex: 1, minWidth: 120, fontSize: 15, fontWeight: 500, color: C.text, fontFamily: C.sans, lineHeight: 1.4 }}>
            {entry.title}
          </span>
          <span style={{
            fontSize: 16, color: C.textMuted, flexShrink: 0,
            transform: open ? "rotate(180deg)" : "none",
            transition: "transform .2s", display: "block",
          }}>▾</span>
        </div>

        {open && (
          <div style={{ marginTop: 12, paddingTop: 12, borderTop: `1px solid ${C.border}` }}>
            <p style={{ fontSize: 15, fontFamily: C.sans, color: C.textMid, lineHeight: 1.7, whiteSpace: "pre-line", margin: 0 }}>
              {entry.detail}
            </p>
            {entry.outcome && (
              <div style={{
                marginTop: 12, padding: "9px 14px",
                background: C.outcomeBg, borderRadius: 6,
                border: `1px solid ${C.border}`,
                fontSize: 14, fontFamily: C.mono,
                color: C.ticketColor, fontWeight: 500,
              }}>
                {entry.outcome}
              </div>
            )}
            <Links links={entry.links} />
          </div>
        )}
      </div>
    </div>
  );
}

export default function App() {
  const [filter, setFilter] = useState("all");
  const [openIds, setOpenIds] = useState(new Set());

  const allEntries = EVENTS.flatMap((s, si) =>
    s.entries.map((e, ei) => ({ ...e, id: `${si}-${ei}` }))
  );
  const visibleEntries = allEntries.filter(e => isVisible(e, filter));
  const visibleIds = visibleEntries.map(e => e.id);
  const allExpanded = visibleIds.length > 0 && visibleIds.every(id => openIds.has(id));

  function toggleEntry(id) {
    setOpenIds(prev => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  }

  function expandAll() {
    setOpenIds(prev => new Set([...prev, ...visibleIds]));
  }

  function collapseAll() {
    setOpenIds(prev => {
      const next = new Set(prev);
      visibleIds.forEach(id => next.delete(id));
      return next;
    });
  }

  // Reset open cards when filter changes
  useEffect(() => { setOpenIds(new Set()); }, [filter]);

  return (
    <div style={{ background: C.bg, minHeight: "100vh", fontFamily: C.sans }}>
      <div style={{ maxWidth: 800, margin: "0 auto", padding: "48px 28px 80px" }}>

        {/* Header */}
        <div style={{ marginBottom: 36 }}>
          <div style={{ fontSize: 12, fontFamily: C.mono, color: C.textMuted, letterSpacing: ".07em", textTransform: "uppercase", marginBottom: 12 }}>
            claude-mpm · session transcript · June 10 2026
          </div>
          <h1 style={{ fontSize: 32, fontWeight: 700, color: C.text, letterSpacing: "-.02em", lineHeight: 1.15, margin: "0 0 14px" }}>
            Autonomous development<br />in practice
          </h1>
          <p style={{ fontSize: 16, color: C.textMid, lineHeight: 1.65, maxWidth: 580, margin: 0 }}>
            v6.5.26 → v6.5.28. Three practices: ticket-driven development,
            worktree isolation, and trusty-review as a gate.
            The human provides direction. mpm handles the rest — including writing every ticket.
          </p>
        </div>

        {/* Stats */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 10, marginBottom: 28 }}>
          {STATS.map(s => (
            <div key={s.label} style={{
              background: C.surface, border: `1px solid ${C.border}`,
              borderRadius: 10, padding: "16px 18px",
            }}>
              <div style={{ fontSize: 12, color: C.textMuted, textTransform: "uppercase", letterSpacing: ".06em", marginBottom: 6 }}>{s.label}</div>
              <div style={{ fontSize: 28, fontWeight: 700, color: C.text, fontFamily: C.mono, lineHeight: 1, marginBottom: 4 }}>{s.value}</div>
              <div style={{ fontSize: 12, color: C.textMuted }}>{s.sub}</div>
            </div>
          ))}
        </div>

        {/* Autonomy bar */}
        <div style={{ background: C.surface, border: `1px solid ${C.border}`, borderRadius: 10, padding: "18px 20px", marginBottom: 28 }}>
          <div style={{ fontSize: 12, color: C.textMuted, textTransform: "uppercase", letterSpacing: ".06em", marginBottom: 12 }}>
            Session time — Bob vs mpm
          </div>
          <div style={{ height: 14, background: C.surfaceAlt, borderRadius: 7, overflow: "hidden", border: `1px solid ${C.border}`, marginBottom: 12, display: "flex" }}>
            <div style={{ width: "4.4%", background: C.bobAccent, borderRadius: "7px 0 0 7px" }} />
            <div style={{ flex: 1, background: "#4dabf7", opacity: .35 }} />
          </div>
          <div style={{ display: "flex", gap: 28, fontSize: 14, fontFamily: C.mono }}>
            <span style={{ color: C.bobAccent, fontWeight: 600 }}>● Bob ~8 min (4%)</span>
            <span style={{ color: C.mpmAccent, fontWeight: 600 }}>● mpm ~173 min (96%)</span>
          </div>
        </div>

        {/* Filter bar + expand/collapse */}
        <div style={{ marginBottom: 32 }}>
          <div style={{ fontSize: 13, color: C.textMuted, marginBottom: 12, fontWeight: 500 }}>Filter by event type</div>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 14 }}>
            {FILTERS.map(f => {
              const active = filter === f.id;
              return (
                <button
                  key={f.id}
                  onClick={() => setFilter(f.id)}
                  style={{
                    fontSize: 14, fontFamily: C.sans, fontWeight: active ? 600 : 400,
                    padding: "8px 18px", borderRadius: 20, cursor: "pointer",
                    background: active ? f.color : C.surface,
                    color: active ? "#fff" : C.textMid,
                    border: `1.5px solid ${active ? f.color : C.border}`,
                    transition: "all .15s",
                  }}
                >
                  {f.label}
                </button>
              );
            })}
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <span style={{ fontSize: 13, color: C.textMuted }}>
              {visibleIds.length} event{visibleIds.length !== 1 ? "s" : ""}
            </span>
            <span style={{ color: C.border }}>·</span>
            <button
              onClick={allExpanded ? collapseAll : expandAll}
              style={{
                fontSize: 13, fontFamily: C.sans, fontWeight: 500,
                padding: "5px 14px", borderRadius: 6, cursor: "pointer",
                background: C.surface, color: C.textMid,
                border: `1px solid ${C.border}`,
                transition: "all .15s",
              }}
            >
              {allExpanded ? "Collapse all" : "Expand all"}
            </button>
          </div>
        </div>

        {/* Timeline */}
        <div style={{ position: "relative", paddingLeft: 32 }}>
          <div style={{
            position: "absolute", left: 11, top: 8, bottom: 8, width: 2,
            background: C.border, borderRadius: 1,
          }} />

          {EVENTS.map((sec, si) => {
            const anyVisible = sec.entries.some(e => isVisible(e, filter));
            if (!anyVisible) return null;
            return (
              <div key={si} style={{ marginBottom: 8 }}>
                <div style={{
                  fontSize: 13, fontFamily: C.mono, color: C.textMuted,
                  fontWeight: 600, letterSpacing: ".04em",
                  paddingBottom: 10, marginBottom: 8,
                  borderBottom: `1px solid ${C.border}`,
                }}>
                  {sec.section}
                </div>
                {sec.entries.map((entry, ei) => {
                  const id = `${si}-${ei}`;
                  return (
                    <Entry
                      key={id}
                      entry={entry}
                      filter={filter}
                      open={openIds.has(id)}
                      onToggle={() => toggleEntry(id)}
                    />
                  );
                })}
              </div>
            );
          })}
        </div>

        {/* Footer */}
        <div style={{ marginTop: 56, paddingTop: 24, borderTop: `2px solid ${C.border}` }}>
          <p style={{ fontSize: 15, color: C.textMid, lineHeight: 1.7, margin: 0 }}>
            The model: the human holds context and authority; mpm holds the operational detail.
            GitHub issues, memory, and search make it possible — mpm can research prior decisions,
            understand the codebase, and produce a well-scoped ticket without being told how.
          </p>
        </div>

      </div>
    </div>
  );
}

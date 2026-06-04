# Product Research Practices

The general research discipline for the **product** side: how to turn a fuzzy problem into
evidence-grounded requirements. This is where general research best practices live for PRDs —
defining the question, user/market/competitive research, evidence gathering, citing sources,
validating assumptions, and making evidence-based decisions. Authoritative pointer:
[`docs/prd/README.md` §8](../../../../../../../docs/prd/README.md).

> **Boundary.** Product research justifies the *requirement* ("who needs this and why").
> **Technical** research (algorithms, benchmarks, how to build it) belongs to the engineering
> side (`docs/specs/research/`; the `spec-authoring` skill's `research-conventions.md`). Keep
> them in separate directories so each standard stays clean.

---

## 1. Where product research lives

```
docs/prd/research/NN-topic-slug.md
```

- `NN` — two-digit sequence, monotonic within the directory.
- `topic-slug` — short hyphenated description: `03-search-user-interviews.md`,
  `07-competitive-pricing-scan.md`.
- Excluded from spec traceability (it is not under `docs/specs/`); it never appears in the SLD
  checker.

---

## 2. The research loop

### Step 1 — Define the question

State the *decision* the research must inform, in product terms. A research doc without a
question becomes an unfocused dump.

> ✅ "Do users abandon search because results are slow, irrelevant, or both?"
> ❌ "Search research."

### Step 2 — Choose the right kind of research

| Kind | Answers | Typical methods |
|------|---------|-----------------|
| **User research** | What do users actually need / do / struggle with? | Interviews, surveys, session analytics, support tickets, usability tests. |
| **Market research** | Is there demand? How large / urgent? | Market sizing, trend data, analyst reports, segment analysis. |
| **Competitive research** | How do others solve this? Where is the gap? | Competitor teardowns, feature matrices, pricing scans, reviews. |
| **Internal data** | What does our own usage say? | Product analytics, funnels, retention cohorts, NPS/CSAT. |

Most PRDs need a blend of user + competitive + internal data.

### Step 3 — Gather evidence

- Talk to (or observe) real users; do not substitute opinion for data.
- Pull quantitative signals (funnels, drop-off, adoption) from product analytics.
- Survey the competitive landscape for prior art and table-stakes expectations.
- Record raw evidence (quotes, numbers, screenshots) so conclusions are auditable.

### Step 4 — Cite sources with links

Every claim that drives a requirement gets a citable source: an interview note, an analytics
query, a competitor URL, a report. **Unsourced assertions are assumptions, not evidence** —
mark them as such (Step 5).

### Step 5 — Validate assumptions explicitly

Separate what you **verified** from what you are **assuming**.

- Tag each as `[verified]` or `[assumed]`.
- For `[assumed]` items, state *how* you will validate (experiment, A/B test, prototype, more
  interviews).
- When an assumption becomes a committed product bet, promote it to an **ADR**
  (`mpm-adr`, `docs/adr/NNNN-*.md`) and cite it from the PRD.

### Step 6 — Make an evidence-based decision

The research's *Decision* is what becomes a requirement (or a non-goal). Keep exploratory
analysis in the research doc; the PRD records only the chosen requirements, each citing the
research that justifies it.

---

## 3. The citation rule

**Every non-obvious requirement cites its evidence.** If a reviewer would ask "why do we believe
users need this?", the requirement links to a `research/NN-*.md` doc, an ADR, or an external
source. Obvious requirements need no citation; non-obvious ones always do.

---

## 4. Product research doc skeleton

```markdown
# {NN} — {Topic}

**Question:** {the product decision this research informs}
**Status:** Open | Resolved → {PRD-AREA-NN}
**Date:** {YYYY-MM-DD}

## Context
{What prompted this. Which product area / problem.}

## Method
{Who/what we studied: N interviews, analytics window, competitors examined.}

## Findings
{What the evidence shows. Cite every claim.}

## Assumptions
- [verified] {…} — source: {link}
- [assumed]  {…} — validation plan: {experiment / A-B / prototype}; promote to ADR if committed

## Decision
{The requirement(s) this justifies, or the non-goal it rules out.}

## Sources
- {interview notes / analytics query / competitor URL / report}
```

---

## 5. Evidence-based decisions and ADRs

Significant, hard-to-reverse **product** decisions (a pricing model, a platform bet, a
deprecation) should be recorded as ADRs via the `mpm-adr` skill, the same Nygard template the
engineering side uses. The PRD requirement cites the ADR; the ADR captures the alternatives and
why this one was chosen. This keeps the *why* durable even as the team changes.

---

## 6. Research → PRD handoff

When research resolves:

1. Set the research doc's `Status:` to `Resolved → PRD-{AREA}-{NN}`.
2. Write (or update) the requirement, encoding only the **Decision**.
3. From the requirement's prose or the PRD References, link back to the research doc.
4. Record any committed bet as an ADR and link it.

This leaves a chain: requirement → evidence → sources, mirroring the engineering side's
spec → rationale → research chain.

---

## See also

- [`prd-template.md`](prd-template.md) — where requirements and citations land.
- The `spec-authoring` skill's `research-conventions.md` — the **technical** research counterpart.
- [`docs/prd/README.md` §8](../../../../../../../docs/prd/README.md) — the authoritative pointer.

# Filling the PRD Template

How to fill [`docs/prd/TEMPLATE.md`](../../../../../../../docs/prd/TEMPLATE.md) section by section.
The canonical, copy-pasteable document is `TEMPLATE.md` itself; this reference explains *what
goes in each section* and the common mistakes. The authoritative standard is
[`docs/prd/README.md`](../../../../../../../docs/prd/README.md).

> **PRD ≠ SPEC.** A PRD states the problem and requirements; it never states inputs/outputs,
> pre/postconditions, or error contracts. Those are the implementing **spec's** job
> (`docs/specs/`). When you feel the urge to write "the function returns…", stop — that belongs
> in a `SPEC-{SUBSYSTEM}-{NN}~{rev}`. Cite the spec instead via the Linked Specs table.

---

## Header block

| Field | What to put | Rule |
|-------|-------------|------|
| `Title` | `{Area} — {one-line}` | Reader knows the area at a glance. |
| `Status` | `Draft \| Review \| Approved \| In-development \| Shipped \| Superseded` | The product lifecycle (see `prd-lifecycle.md`). |
| `Owner` | **Product** (Product Owner / PM name or role) | Always Product. If an engineer is the owner, you are probably writing a spec. |
| `Version` | `v{N}` | Bump on substantial revisions. |
| `Last-updated` | `YYYY-MM-DD` | Update on every material edit. |
| `Related specs/ADRs` | Relative links into `../specs/` and `docs/adr/` | Orienting pointers; the full mapping is the Linked Specs table. |

---

## Problem & Context — the *why*

State the problem, the evidence it matters, and the cost of inaction. Keep it about the
**problem**, not the solution. Link the research that establishes it.

- ✅ "Users abandon search after the first irrelevant result; session logs show 38% drop-off
  after one query (research/03-search-funnel.md)."
- ❌ "We will add a vector index with RRF fusion." (That is a solution / engineering detail.)

---

## Target Users / Personas

Name the user segments and what they are trying to do. A requirement without a persona is a
requirement without a customer. Use the table in the template.

---

## Goals & Non-Goals

- **Goals** — product outcomes, not features. "Users find the right result on the first query."
- **Non-Goals** — explicitly out of scope. Non-goals are the single most effective tool against
  requirement sprawl; write them deliberately.

---

## User Stories / Jobs-to-be-Done

Frame each need from the user's perspective:

- `As a {persona}, I want {capability} so that {outcome}.`
- `When {situation}, I want to {motivation}, so I can {expected result}.`

These motivate the requirements; they are not themselves the trackable requirements.

---

## Requirements — the trackable core

Each requirement is a stable `PRD-{AREA}-{NN}` item, declared in a heading anchor plus an
`**ID:**` field:

```markdown
#### Sub-second relevance ranking {#PRD-SEARCH-03}
**ID:** PRD-SEARCH-03
**Status:** Approved
**Priority:** Must

Search results must be ordered by relevance and the first screen must be useful without
scrolling. (Why: research/03-search-funnel.md shows users judge quality on the first result.)
```

Rules:

- **Split functional vs. non-functional.** Functional = what it does; non-functional = quality
  attributes (performance, reliability, security, accessibility, compliance).
- **State non-functional targets measurably** in *product* terms ("results in under 1s at p95"),
  leaving the engineering *how* to the spec.
- **Use MoSCoW priority** (Must / Should / Could / Won't) so scope tradeoffs are explicit.
- **One requirement = one independently-trackable need.** If two needs ship and succeed
  independently, they are two IDs.
- **No engineering contract.** No inputs/outputs/error handling — cite the implementing spec.

---

## Acceptance Criteria

Observable, product-level checks for "done," grouped by requirement ID. Distinct from success
metrics: acceptance is checked *at/ before* ship; metrics are measured *after*.

```markdown
**PRD-SEARCH-03**
- [ ] First result is relevant for the top 20 known queries (manual eval).
- [ ] No horizontal scroll needed to see the first result on a 1280px viewport.
```

---

## Success Metrics / KPIs

How you will know it worked after launch. Always include baseline, target, and measurement
source.

| Metric | Baseline | Target | How measured |
|--------|----------|--------|--------------|
| First-query success rate | 62% | ≥ 85% | search analytics |
| p95 result latency | 1.4s | ≤ 1.0s | monitoring dashboard |

---

## Scope & Out-of-Scope, Risks & Assumptions, Open Questions

- **Scope / Out-of-Scope** — reinforce the Goals/Non-Goals at the requirement level.
- **Risks & Assumptions** — tabulate; mark assumptions for validation; promote load-bearing
  assumptions to ADRs (see `prd-research-practices.md`).
- **Open Questions** — keep unresolved decisions *out* of the requirements so requirements stay
  stable.

---

## Linked Specs

The PRD→SPEC traceability table. One row per requirement, mapping to implementing
`SPEC-{SUBSYSTEM}-{NN}~{rev}` IDs. Full rules in
[`prd-to-spec-linkage.md`](prd-to-spec-linkage.md).

---

## References

Cite the research docs and external sources that justify the PRD. Every non-obvious requirement
points to its evidence.

---

## See also

- [`docs/prd/TEMPLATE.md`](../../../../../../../docs/prd/TEMPLATE.md) — the document to copy.
- [`prd-to-spec-linkage.md`](prd-to-spec-linkage.md) · [`prd-lifecycle.md`](prd-lifecycle.md) ·
  [`prd-research-practices.md`](prd-research-practices.md) · [`ia-and-categories.md`](ia-and-categories.md)
- [`docs/prd/README.md`](../../../../../../../docs/prd/README.md) — the authoritative standard.

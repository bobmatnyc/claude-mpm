# {Product Area} — PRD

> Copy this file to `docs/prd/{area}.md` and fill it in. Delete this blockquote and any
> `{placeholder}` guidance. This template implements the **Product PRD Standard**
> ([`README.md`](README.md)). A PRD is **product-owned**; it states the problem and
> requirements, never the engineering contract (that is a SPEC — see
> [`../specs/AUTHORING.md`](../specs/AUTHORING.md)).

**Title:** {Product Area} — {one-line description}
**Status:** Draft | Review | Approved | In-development | Shipped | Superseded
**Owner:** Product ({Product Owner / PM name or role})
**Version:** v{N}
**Last-updated:** {YYYY-MM-DD}
**Related specs/ADRs:** [SPEC-{SUBSYSTEM}-{NN}~{rev}](../specs/{subsystem}.md#SPEC-{SUBSYSTEM}-{NN}~{rev}), `docs/adr/NNNN-*.md`

---

## Problem & Context

{The *why*. What problem are we solving, and why now? What is the current pain, the evidence
that it matters, and the cost of not solving it? Link the product research that establishes the
problem (`research/NN-*.md`). Keep this about the problem, not the solution.}

---

## Target Users / Personas

{Who has this problem? Name the personas or user segments and what they are trying to do.}

| Persona | Who they are | What they need |
|---------|--------------|----------------|
| {Persona A} | {context} | {need} |
| {Persona B} | {context} | {need} |

---

## Goals & Non-Goals

**Goals**
- {What this PRD is trying to achieve, in product terms.}

**Non-Goals**
- {Explicitly out of scope. Non-goals prevent requirement sprawl and set expectations.}

---

## User Stories / Jobs-to-be-Done

{Frame the need from the user's perspective. Use the form that fits — user stories or JTBD.}

- As a **{persona}**, I want **{capability}** so that **{outcome}**.
- When **{situation}**, I want to **{motivation}**, so I can **{expected result}**.

---

## Requirements

> Each requirement is a stable, individually-trackable `PRD-{AREA}-{NN}` item. Declare the ID in
> the heading anchor and the `**ID:**` field (see [`README.md` §3](README.md#3-prd-id-grammar--prd-area-nn)).
> Split functional and non-functional requirements.

### Functional Requirements

#### {Requirement title} {#PRD-{AREA}-01}
**ID:** PRD-{AREA}-01
**Status:** Draft | Approved | In-development | Shipped | Superseded
**Priority:** Must | Should | Could | Won't (MoSCoW)

{What the product must do, in product terms — the capability the user gets. Do **not** specify
inputs/outputs/error contracts here; that is the implementing SPEC's job. Cite the research that
justifies a non-obvious requirement.}

#### {Requirement title} {#PRD-{AREA}-02}
**ID:** PRD-{AREA}-02
**Status:** Draft
**Priority:** Should

{…}

### Non-Functional Requirements

#### {Quality attribute} {#PRD-{AREA}-03}
**ID:** PRD-{AREA}-03
**Status:** Draft
**Priority:** Must

{Performance, reliability, security, accessibility, compliance, etc. State the target in
measurable product terms — e.g. "search results return in under 1 second at p95." The engineering
*how* lives in the linked spec.}

---

## Acceptance Criteria

> What must be observably true for each requirement to be considered done, from the user's /
> product's perspective. Group by requirement ID.

**PRD-{AREA}-01**
- [ ] {An externally observable, product-level check.}
- [ ] {Another.}

**PRD-{AREA}-03**
- [ ] {Measurable acceptance check for the non-functional requirement.}

---

## Success Metrics / KPIs

> How we will know the shipped feature succeeded. Distinct from acceptance criteria: these are
> measured *after* launch.

| Metric | Baseline | Target | How measured |
|--------|----------|--------|--------------|
| {e.g. search adoption} | {current} | {goal} | {instrumentation / source} |
| {e.g. p95 result latency} | {current} | {goal} | {monitoring} |

---

## Scope & Out-of-Scope

**In scope**
- {What this PRD covers.}

**Out of scope**
- {What it explicitly does not cover — defer to a future PRD or mark as a non-goal.}

---

## Risks & Assumptions

| Risk / Assumption | Type | Impact | Mitigation / Validation |
|-------------------|------|--------|--------------------------|
| {…} | Risk | {H/M/L} | {how we reduce or accept it} |
| {…} | Assumption | {H/M/L} | {how we will validate it; promote to ADR if it becomes a commitment} |

---

## Open Questions

- {Unresolved product decisions. Keep distinct from requirements so requirements stay stable.}

---

## Linked Specs

> The PRD→SPEC traceability table (see [`README.md` §7](README.md#7-prd--spec-linkage)). One row
> per requirement. A requirement may map to several specs. Reference specs at the `~{rev}` you
> validated against. The implementing spec must cite this PRD ID back.

| Requirement | Implementing spec(s) | Status |
|-------------|----------------------|--------|
| [PRD-{AREA}-01](#PRD-{AREA}-01) | [SPEC-{SUBSYSTEM}-{NN}~{rev}](../specs/{subsystem}.md#SPEC-{SUBSYSTEM}-{NN}~{rev}) | Active |
| [PRD-{AREA}-02](#PRD-{AREA}-02) | _(not yet specced)_ | Approved |
| [PRD-{AREA}-03](#PRD-{AREA}-03) | [SPEC-{SUBSYSTEM}-{MM}~{rev}](../specs/{subsystem}.md#SPEC-{SUBSYSTEM}-{MM}~{rev}) | In-development |

---

## References

- `research/NN-topic-slug.md` — product/user/market/competitive research justifying requirements.
- `docs/adr/NNNN-*.md` — Architecture Decision Records for significant product decisions.
- {External sources: user interviews, market data, competitive analysis, with links.}
- [`README.md`](README.md) — the Product PRD Standard governing this document.
- [`../specs/AUTHORING.md`](../specs/AUTHORING.md) — the Engineering Spec Authoring Standard
  (where the implementing contracts are authored).

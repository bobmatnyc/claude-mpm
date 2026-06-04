# Product PRD Standard

**Status:** Active
**Version:** v1
**Owner:** Product (Product Owner / Product Manager)
**Scope:** Portable standard for authoring **Product Requirements Documents (PRDs)** in
`docs/prd/`. claude-mpm is the reference instantiation; other projects may adopt this standard
independently.

---

## Table of Contents

1. [Purpose: What a PRD Is](#1-purpose-what-a-prd-is)
2. [PRDs vs. Specs: Two Distinct Standards](#2-prds-vs-specs-two-distinct-standards)
3. [PRD ID Grammar — `PRD-{AREA}-{NN}`](#3-prd-id-grammar--prd-area-nn)
4. [Information Architecture & Areas](#4-information-architecture--areas)
5. [PRD Lifecycle](#5-prd-lifecycle)
6. [README & Internal-Link Conventions](#6-readme--internal-link-conventions)
7. [PRD → SPEC Linkage](#7-prd--spec-linkage)
8. [Research Conventions](#8-research-conventions)

---

## 1. Purpose: What a PRD Is

A **PRD (Product Requirements Document)** answers one set of questions:

> **What problem are we solving, for which users, what must the solution do, and what does
> success look like?**

It is owned by **Product** (a Product Owner or Product Manager). It is deliberately *not* an
engineering design: it states the **requirements and intent**, not the behavioral contract or
the implementation. The engineering contract that realizes a PRD lives in a separate, distinct
standard — the **Engineering Spec Authoring Standard** ([`docs/specs/AUTHORING.md`](../specs/AUTHORING.md)).

This file is the **governance doc** for PRDs: ID grammar, information architecture, lifecycle,
link conventions, and the PRD→SPEC traceability convention. The copy-pasteable PRD document
itself is [`TEMPLATE.md`](TEMPLATE.md).

---

## 2. PRDs vs. Specs: Two Distinct Standards

PRD and SPEC are **two distinct standards**, owned by different people, with their own homes,
templates, IDs, and skills. **Neither absorbs the other.**

| | **PRD** (this standard) | **SPEC** ([`docs/specs/`](../specs/AUTHORING.md)) |
|---|--------------------------|----------------------------------------------------|
| **Owner** | Product (Product Owner / PM) | Engineering / Architecture |
| **Answers** | What problem, for which users, what requirements, what success looks like. | The behavioral contract & how it is implemented. |
| **Home** | `docs/prd/` | `docs/specs/` |
| **ID namespace** | `PRD-{AREA}-{NN}` | `SPEC-{SUBSYSTEM}-{NN}~{rev}` |
| **Organized by** | Product **AREA** / feature | Engineering **SUBSYSTEM** |
| **Primary content** | Problem, personas, goals, user stories, requirements, acceptance criteria, success metrics. | Inputs/Outputs/Pre/Postconditions/Errors, Rationale, Implementing Modules. |
| **Skill** | `prd-authoring` | `spec-authoring` |
| **Lifecycle** | Draft → Review → Approved → In-development → Shipped → Superseded | Draft → Review → Active → Superseded |

**The link is bidirectional:**

- **PRD → SPEC (downward):** each PRD requirement links *down* to the spec(s) that implement it,
  recorded in the PRD's **Linked Specs** traceability table (§7).
- **SPEC → PRD (upward):** each spec section that realizes a requirement cites *up* to the
  `PRD-{AREA}-{NN}` it implements (from its Rationale or References).

Distinct ID namespaces, distinct directories, distinct owners, bidirectional cross-references.
A PRD never specifies inputs/outputs/error contracts (that is the spec's job); a spec never
specifies the problem, personas, or success metrics (that is the PRD's job).

---

## 3. PRD ID Grammar — `PRD-{AREA}-{NN}`

Every individually-trackable **requirement** in a PRD carries a stable ID:

```
PRD-{AREA}-{NN}
```

| Component | Format | Example | Notes |
|-----------|--------|---------|-------|
| `PRD` | Literal prefix | `PRD` | Always uppercase |
| `{AREA}` | Uppercase alpha, hyphens allowed | `SEARCH`, `ONBOARDING`, `MODEL-ROUTING` | The product area; matches the PRD file name |
| `{NN}` | Two-digit zero-padded integer | `01`, `12` | Sequential within the area |

**Full example:** `PRD-SEARCH-03`.

### No revision suffix

Unlike spec IDs (`~{rev}`), PRD IDs have **no revision suffix**. Requirements evolve through the
**lifecycle** (§5) and through supersession, not through a tilde counter. When a requirement
materially changes after it has shipped, supersede it with a new ID and mark the old one
`Superseded` (§5). This keeps PRD IDs stable references that a spec can cite without churn.

### Declaration rule

A requirement ID is **declared** when it appears as a named heading anchor in the PRD's
*Requirements* section:

```markdown
### Sub-second relevance ranking {#PRD-SEARCH-03}
**ID:** PRD-SEARCH-03
```

IDs appearing in prose, tables, or other documents (including this README) are references, not
declarations. Each PRD area file owns its own `{NN}` sequence.

---

## 4. Information Architecture & Areas

The IA mirrors the spec side's flatness — two levels:

```
Area (file)  →  Requirements (governed PRD-{AREA}-{NN} items)
```

- **Area** = one product area or feature = one file `docs/prd/{area}.md`. The uppercased name is
  the `{AREA}` token in every requirement ID in that file.
- **Requirement** = one governed `PRD-{AREA}-{NN}` item in the file's *Requirements* section.

### Choosing an area

Organize PRDs by **product area / feature** — the unit a Product Owner reasons about and a user
would name ("search", "onboarding", "billing"). This is intentionally **different** from the
engineering SUBSYSTEM axis used by specs: one product area is often realized by several
subsystems, and one subsystem may serve several areas. Do not force PRD areas to match spec
subsystems; record the cross-mapping via the Linked Specs table (§7).

### Add an area vs. add a requirement

- **Add a requirement** (the common case) when the new need fits an existing area's scope.
- **Add a new area file** when the need is a cohesive, separately-owned product surface with
  several requirements' worth of content.

### Naming

- `{AREA}` token: UPPERCASE alpha, hyphens allowed (`SEARCH`, `MODEL-ROUTING`).
- File name: lowercase form of the token — `model-routing.md` ↔ `PRD-MODEL-ROUTING-01`.
- The token appears in every requirement ID; renaming it is a breaking change to every spec that
  cites it. Choose durable names.

---

## 5. PRD Lifecycle

A PRD (and each requirement within it) moves through a product lifecycle, tracked in the
header-block **Status** field (and per-requirement `**Status:**` where they diverge):

| Stage | Meaning | Status value |
|-------|---------|--------------|
| **Draft** | Problem and requirements being written; not yet agreed. | `Draft` |
| **Review** | Stakeholder review of problem framing, requirements, and success metrics. | `Review` |
| **Approved** | Product has signed off. Requirements are stable enough for engineering to spec against. | `Approved` |
| **In-development** | Implementing specs are being authored/built (`SPEC-…` linked). | `In-development` |
| **Shipped** | The requirement is live; success metrics are being measured. | `Shipped` |
| **Superseded** | Replaced by a newer requirement; retained for history; links forward. | `Superseded` |

### Handoff to engineering

Engineering should begin authoring specs once a requirement reaches **Approved**. The
`PRD-{AREA}-{NN}` is the inception trigger for a spec (see
[`docs/specs/AUTHORING.md` §8](../specs/AUTHORING.md)).

### Supersession

When a requirement materially changes after Approval/Ship, do not rewrite it in place — IDs are
stable references that specs cite. Instead:

- Mark the old requirement `**Status:** Superseded` and add `**Superseded-by:** PRD-{AREA}-{NN}`.
- Create a new requirement with a new ID and `**Supersedes:** PRD-{AREA}-{NN}`.
- Update the Linked Specs table so engineering knows the contract target moved.

---

## 6. README & Internal-Link Conventions

### 6.1 Every directory has an orienting index

`docs/prd/` is indexed by this `README.md`. Any new subdirectory (e.g. `research/`) must carry
its own index that orients a reader: what lives here, the naming convention, and where to go
next.

### 6.2 Cross-reference conventions

- **Within and across PRD files**, link to requirements by their stable `#PRD-…` anchor with a
  relative path: `[PRD-SEARCH-03](search.md#PRD-SEARCH-03)`. Never link by mutable heading text.
- **PRD ↔ SPEC** is the core cross-standard link (§7): the PRD's *Linked Specs* table maps each
  requirement to the implementing `SPEC-{SUBSYSTEM}-{NN}~{rev}` IDs (path into `../specs/`); the
  spec cites the `PRD-{AREA}-{NN}` back.
- **PRD ↔ research** — a requirement's *References* links to the `research/NN-topic-slug.md`
  document(s) that justify it (§8).
- **PRD ↔ ADR** — when a product decision is significant and hard to reverse, link the ADR
  (`docs/adr/NNNN-*.md`).

### 6.3 No dangling anchors

Before committing, confirm every `#PRD-…` and `#SPEC-…` anchor you link to is actually declared
in the target file, and every relative path resolves. A link to a nonexistent anchor is a silent
traceability gap.

---

## 7. PRD → SPEC Linkage

This is the convention that connects the two standards. Every PRD carries a **Linked Specs**
traceability table mapping each requirement to the engineering spec(s) that implement it.

```markdown
## Linked Specs

| Requirement | Implementing spec(s) | Status |
|-------------|----------------------|--------|
| [PRD-SEARCH-01](#PRD-SEARCH-01) | [SPEC-INTEGRATIONS-04~1](../specs/integrations.md#SPEC-INTEGRATIONS-04~1) | Active |
| [PRD-SEARCH-03](#PRD-SEARCH-03) | [SPEC-SESSIONS-07~2](../specs/sessions.md#SPEC-SESSIONS-07~2), [SPEC-INTEGRATIONS-05~1](../specs/integrations.md#SPEC-INTEGRATIONS-05~1) | In-development |
| [PRD-SEARCH-04](#PRD-SEARCH-04) | _(not yet specced)_ | Approved |
```

### Rules

1. **One row per requirement.** Every `PRD-{AREA}-{NN}` declared in the file appears in the
   table, even if not yet specced (use `_(not yet specced)_`).
2. **A requirement may map to many specs.** A product requirement is frequently realized by
   several subsystems — list all implementing `SPEC-…~{rev}` IDs.
3. **Cite the revision.** Reference specs at the `~{rev}` you validated against. If the spec
   bumps its `~{rev}`, Product should re-confirm the requirement still holds and update the row.
4. **Bidirectional.** The implementing spec section must cite this `PRD-{AREA}-{NN}` back (from
   its Rationale or References). The link only counts if both directions exist.
5. **Distinct namespaces.** Never reuse a `SPEC-…` ID as a PRD ID or vice versa. The directories
   (`docs/prd/` vs `docs/specs/`), owners (Product vs Engineering), and templates stay separate.

### Why this matters

The Linked Specs table is the product-side half of a Requirements Traceability Matrix: it lets a
Product Owner answer "is requirement X implemented, and by what?" and lets engineering answer
"why does this contract exist?" — without either standard absorbing the other.

---

## 8. Research Conventions

Pre-PRD **product / user / market / competitive** research lives in `docs/prd/research/`,
separate from the requirements themselves (mirroring `docs/specs/research/` on the engineering
side, but for product questions).

- **Naming:** `docs/prd/research/NN-topic-slug.md` — `NN` two-digit sequence, `topic-slug` a
  short hyphenated description (e.g. `03-search-user-interviews.md`).
- **Scope:** define the question; user/market/competitive research; evidence gathering; citing
  sources; validating assumptions; evidence-based decisions linked to ADRs. The full product
  research discipline lives in the `prd-authoring` skill's `prd-research-practices.md`.
- **Boundary:** product research justifies the *requirement*; **technical** research (algorithms,
  benchmarks, how to build it) belongs to `docs/specs/research/` on the engineering side.

A requirement's *References* block links to the research doc(s) that justify it. Every non-obvious
requirement cites its evidence.

---

## References

- [`TEMPLATE.md`](TEMPLATE.md) — the copy-pasteable PRD document template.
- [`../specs/AUTHORING.md`](../specs/AUTHORING.md) — the **Engineering Spec Authoring Standard**
  (the engineering-owned companion; specs realize PRD requirements).
- [`../specs/README.md`](../specs/README.md) — Spec-Linked Documentation (SLD): how code traces
  to specs (the downstream half of the engineering side).
- `prd-authoring` skill (`src/claude_mpm/skills/bundled/main/prd-authoring/`) — the agent-facing
  companion to this standard.
- `spec-authoring` skill (`src/claude_mpm/skills/bundled/main/spec-authoring/`) — the engineering
  spec-authoring companion.
- `mpm-adr` skill / `docs/adr/` — Architecture Decision Records for significant decisions.

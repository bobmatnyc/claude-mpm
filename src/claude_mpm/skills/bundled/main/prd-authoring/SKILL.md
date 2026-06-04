---
name: prd-authoring
description: "Standard for authoring product PRDs in docs/prd/: state the problem, users, requirements, and success; assign PRD-{AREA}-{NN} IDs; link down to specs."
version: 1.0.0
category: documentation
agent_types: [product-owner, pm]
tags: [prd, product, requirements, authoring, standards]
effort: medium
user-invocable: true
progressive_disclosure:
  entry_point:
    summary: "Author product PRDs in docs/prd/ using the PRD-{AREA}-{NN} grammar, a product-owned template (problem, users, requirements, acceptance, metrics), and a product lifecycle. PRDs are realized by engineering specs."
    when_to_use: "When defining a product problem and its requirements, creating a docs/prd/{area}.md file, adding PRD-{AREA}-{NN} requirements, running product/user/market research, or mapping requirements to implementing specs."
    quick_start: "1. Read docs/prd/README.md for ID grammar 2. Pick/create the area file from TEMPLATE.md 3. State problem, users, requirements 4. Add acceptance criteria + success metrics 5. Fill the Linked Specs table"
  references:
    - prd-template.md
    - prd-research-practices.md
    - prd-lifecycle.md
    - prd-to-spec-linkage.md
    - ia-and-categories.md
---

# PRD Authoring

## Overview

This skill is the agent-facing entry point to the **Product PRD Standard**: how to *write*
Product Requirements Documents in `docs/prd/`. A PRD answers **what problem, for which users,
what requirements, and what success looks like** — and is owned by **Product** (Product Owner /
PM).

It has a distinct engineering companion — keep the roles separate:

- **`prd-authoring`** (this skill) = **authoring product PRDs.** State the problem, target users,
  goals, user stories, requirements, acceptance criteria, and success metrics; assign stable
  `PRD-{AREA}-{NN}` IDs; run product/user/market research; map requirements down to implementing
  specs.
- **`spec-authoring`** = **engineering specs** (a separate, engineering-owned standard —
  `docs/specs/`, `SPEC-{SUBSYSTEM}-{NN}~{rev}`). Specs *implement* PRD requirements.
- **`spec-linked-docs`** = traceability between specs and source code.

> **PRD ≠ SPEC.** A PRD is a *product* requirements doc (`PRD-{AREA}-{NN}`, in `docs/prd/`,
> owned by Product). A SPEC is an *engineering* behavior contract (`SPEC-{SUBSYSTEM}-{NN}~{rev}`,
> in `docs/specs/`, owned by Engineering). A PRD requirement is **realized by** one or more
> specs; list them in the Linked Specs table. Do **not** put inputs/outputs/error contracts in a
> PRD — that is the spec's job.

**Full standard:** [`docs/prd/README.md`](../../../../../../docs/prd/README.md).
This skill orients and links; `README.md` is the authoritative, portable standard, and
[`docs/prd/TEMPLATE.md`](../../../../../../docs/prd/TEMPLATE.md) is the copy-pasteable document.

> **Use this skill, do not duplicate it.** SKILL.md is a concise router. The detailed rules live
> in `docs/prd/README.md` and the five reference files below. Read the reference you need.

---

## When to Use

- Defining a product problem and turning it into stable requirements.
- Creating a new `docs/prd/{area}.md` file for a product area.
- Adding a governed `PRD-{AREA}-{NN}` requirement to an existing PRD.
- Running product / user / market / competitive research and recording it.
- Mapping requirements to the engineering spec(s) that implement them (Linked Specs table).
- Moving a PRD through its lifecycle (Draft → Review → Approved → In-development → Shipped).

If your task is instead authoring the *engineering contract*, use **`spec-authoring`**.

---

## Core Model (at a glance)

A PRD is **product-owned**: one product area = one file (`docs/prd/{area}.md`). Each governed
requirement has a stable `{#PRD-{AREA}-{NN}}` ID. A PRD document carries:

- **Header** — Title, Status, **Owner = Product**, Version, Last-updated, Related specs/ADRs.
- **Problem & Context** — the *why*.
- **Target Users / Personas**, **Goals & Non-Goals**, **User Stories / JTBD**.
- **Requirements** — Functional & Non-functional, each a stable `PRD-{AREA}-{NN}` item.
- **Acceptance Criteria**, **Success Metrics / KPIs**.
- **Scope & Out-of-Scope**, **Risks & Assumptions**, **Open Questions**.
- **Linked Specs** — the PRD→SPEC traceability table.
- **References** — research + sources.

PRD IDs have **no** `~{rev}` suffix — requirements evolve via lifecycle and supersession, not a
tilde counter.

The copy-pasteable template is [`docs/prd/TEMPLATE.md`](../../../../../../docs/prd/TEMPLATE.md)
(and [`references/prd-template.md`](references/prd-template.md) explains how to fill it).

---

## Quick Start

1. **Read the grammar.** [`docs/prd/README.md` §3](../../../../../../docs/prd/README.md) defines
   `PRD-{AREA}-{NN}` and the declaration rule. Do not invent IDs.
2. **Pick or create the area file.** One product area = one file. See
   [`references/ia-and-categories.md`](references/ia-and-categories.md).
3. **Apply the template.** Copy [`docs/prd/TEMPLATE.md`](../../../../../../docs/prd/TEMPLATE.md);
   fill problem, users, requirements, acceptance criteria, success metrics. Guidance in
   [`references/prd-template.md`](references/prd-template.md).
4. **Ground it in research.** Non-obvious requirements cite product/user/market research. See
   [`references/prd-research-practices.md`](references/prd-research-practices.md).
5. **Map requirements to specs.** Fill the Linked Specs table; engineering authors the specs and
   cites the PRD ID back. See [`references/prd-to-spec-linkage.md`](references/prd-to-spec-linkage.md).
6. **Manage the lifecycle.** Draft → Review → Approved → In-development → Shipped → Superseded.
   See [`references/prd-lifecycle.md`](references/prd-lifecycle.md).

---

## Reference Files

| Reference | Read it when you need to… |
|-----------|---------------------------|
| [`prd-template.md`](references/prd-template.md) | Fill the PRD document section by section. |
| [`prd-research-practices.md`](references/prd-research-practices.md) | Run product/user/market/competitive research and cite evidence. |
| [`prd-lifecycle.md`](references/prd-lifecycle.md) | Walk the lifecycle (Draft → Shipped → Superseded) and the review checklist. |
| [`prd-to-spec-linkage.md`](references/prd-to-spec-linkage.md) | Build and maintain the PRD→SPEC traceability table. |
| [`ia-and-categories.md`](references/ia-and-categories.md) | Choose/name a product area; decide add-area vs. add-requirement. |

---

## Relationship to Specs

A PRD states *what* and *why*; a spec states the *engineering contract* that realizes it. The two
are distinct standards (distinct dirs, IDs, owners, templates) with a **bidirectional link**: the
PRD's Linked Specs table points *down* to implementing `SPEC-{SUBSYSTEM}-{NN}~{rev}` IDs; each
spec section cites the `PRD-{AREA}-{NN}` it implements *up*. Read `spec-authoring` when you need
to understand or coordinate the engineering side.

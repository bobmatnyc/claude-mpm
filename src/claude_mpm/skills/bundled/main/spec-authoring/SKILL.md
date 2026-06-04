---
name: spec-authoring
description: "Standard for authoring engineering behavior-contract specs in docs/specs/: scope subsystems, assign stable IDs, structure docs, manage lifecycle."
version: 1.0.0
category: documentation
agent_types: [engineer, documentation]
tags: [specification, spec, authoring, engineering, standards]
effort: medium
user-invocable: true
progressive_disclosure:
  entry_point:
    summary: "Author engineering specs in docs/specs/ using the SPEC-{SUBSYSTEM}-{NN}~{rev} grammar, a behavior-contract template, and a defined lifecycle. Specs are engineering-owned and implement PRD requirements."
    when_to_use: "When creating a new docs/specs/{subsystem}.md file, adding spec sections, deciding granularity, establishing a new subsystem, or running pre-spec technical research."
    quick_start: "1. Read docs/specs/README.md for ID grammar 2. Pick/create the subsystem file 3. Apply the spec template 4. Cite the PRD requirement realized 5. Link implementing modules 6. Run the CI traceability check"
  references:
    - spec-template.md
    - category-taxonomy.md
    - granularity-guide.md
    - research-conventions.md
    - authoring-workflow.md
---

# Spec Authoring

## Overview

This skill is the agent-facing entry point to the **Engineering Spec Authoring Standard**:
how to *write* engineering specifications in `docs/specs/`. A spec is a **behavior contract**
(testable WHAT + WHY, linked to implementing modules), owned by **Engineering / Architecture**.

It has two distinct companions — keep the roles separate:

- **`spec-authoring`** (this skill) = **authoring engineering specs.** Scope a subsystem into a
  file, assign stable IDs, structure a behavior-contract document, decide granularity, run
  pre-spec technical research, and move a spec through its lifecycle.
- **`spec-linked-docs`** (SLD) = **traceability.** Keep source code in sync with the spec via
  docstring `References` and a CI checker.
- **`prd-authoring`** = **product PRDs** (a separate, product-owned standard — `docs/prd/`).

> **SPEC ≠ PRD.** A SPEC is an *engineering* contract (`SPEC-{SUBSYSTEM}-{NN}~{rev}`, in
> `docs/specs/`, owned by Engineering). A PRD is a *product* requirements doc
> (`PRD-{AREA}-{NN}`, in `docs/prd/`, owned by Product). A spec **implements** a PRD
> requirement and cites it; product framing (problem, users, acceptance criteria, metrics)
> stays in the PRD. Do **not** put PRD content in a spec.

**Full standard:** [`docs/specs/AUTHORING.md`](../../../../../../docs/specs/AUTHORING.md).
This skill orients and links; `AUTHORING.md` is the authoritative, portable standard.
The **ID grammar** itself lives in [`docs/specs/README.md`](../../../../../../docs/specs/README.md)
— defer to it; never re-derive it.

> **Use this skill, do not duplicate it.** SKILL.md is a concise router. The detailed rules
> live in `AUTHORING.md` and the five reference files below. Read the reference you need.

---

## When to Use

- Creating a new `docs/specs/{subsystem}.md` file for a subsystem.
- Adding a governed `SPEC-{SUBSYSTEM}-{NN}~{rev}` section to an existing spec.
- Deciding whether a behavior is one ID, several, or none.
- Deciding whether to add a new subsystem (file) or a section to an existing one.
- Running pre-spec *technical* research and recording it in `docs/specs/research/`.
- Moving a spec through its lifecycle (Draft → Review → Active → Superseded).

If your task is instead *linking code to an existing spec*, use **`spec-linked-docs`**.
If you are authoring product requirements, use **`prd-authoring`**.

---

## Core Model (at a glance)

A claude-mpm spec is a **behavior contract**: one bounded subsystem = one file
(`docs/specs/{subsystem}.md`). Each governed section has a stable
`{#SPEC-{SUBSYSTEM}-{NN}~{rev}}` ID and contains:

- **Behavior Contract (WHAT)** — Inputs / Outputs / Preconditions / Postconditions / Error conditions.
- **Rationale (WHY)** — design decisions and constraints (mandatory; never HOW). Cite the
  `PRD-{AREA}-{NN}` requirement realized, if any.
- **Implementing Modules** — the HOW-link table (SLD verifies these).

Around the governed sections sit a **header block** (Status, Version, Subsystem, Owner=eng,
Last-updated, Related), **Purpose & Scope**, a **Table of Contents** (ID → section →
modules), **Open Questions / Future Work**, and **References**.

There is **no** Acceptance Criteria or Success Metrics section — those are PRD concerns.

The copy-pasteable template is in [`references/spec-template.md`](references/spec-template.md).

---

## Quick Start

1. **Read the grammar.** [`docs/specs/README.md` §4](../../../../../../docs/specs/README.md)
   defines `SPEC-{SUBSYSTEM}-{NN}~{rev}` and the declaration rule. Do not invent IDs.
2. **Pick or create the subsystem file.** One bounded subsystem = one file. See
   [`references/category-taxonomy.md`](references/category-taxonomy.md) for the existing
   seven subsystems and the add-subsystem-vs-section rules.
3. **Apply the spec template.** Copy [`references/spec-template.md`](references/spec-template.md);
   fill the header block, Purpose & Scope, ToC, and each governed section.
4. **Get granularity right.** One ID per independently-verifiable behavior. Use the litmus
   test and split/merge heuristics in
   [`references/granularity-guide.md`](references/granularity-guide.md).
5. **Cite the PRD requirement realized** (if any) and your research. Non-obvious decisions
   link to `docs/specs/research/NN-topic-slug.md`. See
   [`references/research-conventions.md`](references/research-conventions.md).
6. **Link implementing modules** in each section's table; engineers then add SLD
   `References` blocks (handoff to `spec-linked-docs`).
7. **Run the CI check.** `uv run pytest tests/test_spec_traceability.py` verifies the
   traceability graph. Draft sections are exempt from UNCOVERED (see README §9b).

---

## Reference Files

| Reference | Read it when you need to… |
|-----------|---------------------------|
| [`spec-template.md`](references/spec-template.md) | Copy the canonical behavior-contract spec document template. |
| [`category-taxonomy.md`](references/category-taxonomy.md) | See existing subsystems; decide add-subsystem vs. add-section; name a subsystem. |
| [`granularity-guide.md`](references/granularity-guide.md) | Decide whether a behavior is one ID, several, or none; split/merge. |
| [`research-conventions.md`](references/research-conventions.md) | Run pre-spec *technical* research and record it in `docs/specs/research/`. |
| [`authoring-workflow.md`](references/authoring-workflow.md) | Walk the full lifecycle (Inception → Superseded) and the review checklist. |

---

## Relationship to SLD and PRDs

`spec-authoring` is upstream of the contract; `spec-linked-docs` is downstream of it. You
author a section here; SLD then keeps source code in sync with it via docstring `References`
and the four-status CI checker. A `~rev` bump you make on a contract change is what SLD's
OUTDATED status detects.

A spec **implements** product requirements. The `prd-authoring` skill (`docs/prd/`) is the
product-owned companion: PRDs state the problem and requirements; specs state the engineering
contract that realizes them and cite the `PRD-{AREA}-{NN}`. Read both skills when a feature
spans product intent and engineering contract.

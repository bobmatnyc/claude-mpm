# PRD Lifecycle & Review

The end-to-end lifecycle of a product PRD and the review checklist. Agent-facing copy of
[`docs/prd/README.md` §5](../../../../../../../docs/prd/README.md).

---

## 1. Lifecycle stages

A PRD (and each requirement within it) moves through a **product** lifecycle, distinct from the
engineering spec lifecycle. Tracked in the header-block **Status** field and per-requirement
`**Status:**` where they diverge:

| Stage | Meaning | Status value |
|-------|---------|--------------|
| **Draft** | Problem and requirements being written; not yet agreed. | `Draft` |
| **Review** | Stakeholder review of problem framing, requirements, success metrics. | `Review` |
| **Approved** | Product has signed off. Requirements are stable enough to spec against. | `Approved` |
| **In-development** | Implementing specs authored/built; `SPEC-…` linked. | `In-development` |
| **Shipped** | Live; success metrics being measured. | `Shipped` |
| **Superseded** | Replaced by a newer requirement; retained for history; links forward. | `Superseded` |

> Contrast with the **spec** lifecycle (Draft → Review → Active → Superseded). The PRD has extra
> product-facing states (`Approved`, `In-development`, `Shipped`) because it tracks a product
> commitment through delivery, not just a contract's validity.

---

## 2. The lifecycle flow

```
[Draft]        Problem + requirements written. Research linked. Status: Draft.
     │
     ▼
[Review]       Stakeholders review problem framing, requirements, metrics.
     │
     ▼
[Approved]     Product signs off. ── handoff ──▶ Engineering begins spec-authoring
     │                                            (PRD-{AREA}-{NN} is the spec's inception trigger)
     ▼
[In-development]  Implementing specs authored/built; Linked Specs table filled with SPEC IDs.
     │
     ▼
[Shipped]      Feature live. Success metrics measured against baseline/target.
     │
     ▼ (if requirements materially change post-ship)
[Superseded]   New requirement ID created; old one marked Superseded with forward link.
```

### Stage detail

1. **Draft.** Copy `TEMPLATE.md`. Write the problem, users, requirements, acceptance criteria,
   metrics. Ground non-obvious requirements in research (`prd-research-practices.md`).
2. **Review.** Stakeholders (eng lead, design, GTM as relevant) review. Confirm the problem is
   real, requirements are testable, metrics are measurable, non-goals are explicit.
3. **Approved.** Product signs off. This is the **handoff to engineering**: a requirement at
   `Approved` is the inception trigger for a spec
   ([`docs/specs/AUTHORING.md` §8](../../../../../../../docs/specs/AUTHORING.md)).
4. **In-development.** As engineering authors specs, fill the **Linked Specs** table with the
   `SPEC-{SUBSYSTEM}-{NN}~{rev}` IDs realizing each requirement. Confirm each spec cites the PRD
   ID back (bidirectional link — `prd-to-spec-linkage.md`).
5. **Shipped.** Feature is live. Begin measuring success metrics against their baselines/targets.
6. **Superseded.** See below.

---

## 3. Supersession (no `~rev` on PRD IDs)

PRD IDs have **no** `~{rev}` suffix. When a requirement materially changes after Approval/Ship,
do **not** rewrite it in place — specs cite it as a stable reference. Instead:

- Mark the old requirement `**Status:** Superseded` and add `**Superseded-by:** PRD-{AREA}-{NN}`.
- Create a new requirement with a new ID and `**Supersedes:** PRD-{AREA}-{NN}`.
- Update the **Linked Specs** table so engineering knows the contract target moved (the old
  spec may need a `~rev` bump or supersession of its own).

This preserves a navigable history: a spec citing an old `PRD-{AREA}-{NN}` can follow the chain
forward to the current requirement.

---

## 4. Review checklist

Before moving a PRD to **Approved**, confirm:

### Structure
- [ ] Header block present: Title, Status, **Owner = Product**, Version, Last-updated,
      Related specs/ADRs.
- [ ] Each requirement has a `{#PRD-{AREA}-{NN}}` anchor and matching `**ID:**` field.
- [ ] Requirements split into Functional and Non-functional.

### Content
- [ ] Problem & Context states the *why* with evidence (not a solution).
- [ ] Target users / personas named.
- [ ] Goals **and** Non-Goals are explicit.
- [ ] Each requirement is one independently-trackable need, with a MoSCoW priority.
- [ ] **No engineering contract leaked in** — no inputs/outputs/error handling, no module names
      as requirements. (Cite the implementing spec instead.)
- [ ] Acceptance criteria are observable and grouped by requirement ID.
- [ ] Success metrics have baseline, target, and measurement source.

### Research & links
- [ ] Non-obvious requirements cite product/user/market research or an ADR.
- [ ] Every `#PRD-…` / `#SPEC-…` anchor linked exists; every relative path resolves (no dangling
      links).

### Traceability
- [ ] The **Linked Specs** table has a row for every requirement (use `_(not yet specced)_`
      where appropriate).
- [ ] For each filled row, the implementing spec cites this `PRD-{AREA}-{NN}` back.

---

## 5. Handoffs

| To | When | Skill |
|----|------|-------|
| Engineering | At `Approved`, to author implementing specs | `spec-authoring` |
| Engineering | As specs go Active, to confirm the Linked Specs table | `spec-authoring` |
| Product | Post-ship, to measure success metrics | (this skill) |

---

## See also

- [`prd-to-spec-linkage.md`](prd-to-spec-linkage.md) — the bidirectional link the lifecycle relies on.
- [`prd-template.md`](prd-template.md) — the document being moved through the lifecycle.
- [`docs/prd/README.md` §5](../../../../../../../docs/prd/README.md) — the authoritative lifecycle.

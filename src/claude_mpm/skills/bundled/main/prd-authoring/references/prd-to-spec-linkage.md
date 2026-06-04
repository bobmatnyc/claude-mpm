# PRD → SPEC Linkage

How to build and maintain the bidirectional link between a **product** PRD and the **engineering**
spec(s) that implement it. This is the convention that connects the two distinct standards
without either absorbing the other. Authoritative pointer:
[`docs/prd/README.md` §7](../../../../../../../docs/prd/README.md).

---

## 1. Two standards, one bidirectional link

| | PRD | SPEC |
|---|-----|------|
| Owner | Product | Engineering |
| Home | `docs/prd/` | `docs/specs/` |
| ID | `PRD-{AREA}-{NN}` | `SPEC-{SUBSYSTEM}-{NN}~{rev}` |
| Organized by | product **AREA** | engineering **SUBSYSTEM** |

They are linked in **both directions**:

- **PRD → SPEC (downward):** the PRD's *Linked Specs* table maps each requirement to the spec(s)
  that implement it.
- **SPEC → PRD (upward):** each spec section that realizes a requirement cites the
  `PRD-{AREA}-{NN}` in its Rationale or References.

A link **only counts when both directions exist.** A Linked Specs row with no reciprocal cite in
the spec (or vice versa) is an incomplete link — fix it before marking the requirement
`In-development`.

---

## 2. The Linked Specs table

Every PRD carries this table near the end of the document:

```markdown
## Linked Specs

| Requirement | Implementing spec(s) | Status |
|-------------|----------------------|--------|
| [PRD-SEARCH-01](#PRD-SEARCH-01) | [SPEC-INTEGRATIONS-04~1](../specs/integrations.md#SPEC-INTEGRATIONS-04~1) | Active |
| [PRD-SEARCH-03](#PRD-SEARCH-03) | [SPEC-SESSIONS-07~2](../specs/sessions.md#SPEC-SESSIONS-07~2), [SPEC-INTEGRATIONS-05~1](../specs/integrations.md#SPEC-INTEGRATIONS-05~1) | In-development |
| [PRD-SEARCH-04](#PRD-SEARCH-04) | _(not yet specced)_ | Approved |
```

### Rules

1. **One row per requirement.** Every `PRD-{AREA}-{NN}` declared in the file appears, even if not
   yet specced (use `_(not yet specced)_`). This makes coverage gaps visible.
2. **Many-to-many is normal.** One requirement is often realized by several subsystems; list all
   implementing `SPEC-…~{rev}` IDs. One subsystem may also serve several requirements.
3. **Cite the revision you validated against.** Reference specs at the `~{rev}` Product confirmed
   the requirement against. If a spec bumps `~{rev}`, Product re-confirms the requirement still
   holds and updates the row.
4. **Bidirectional.** The implementing spec section must cite this `PRD-{AREA}-{NN}` back. Both
   directions or it does not count.
5. **Distinct namespaces.** Never reuse a `SPEC-…` ID as a PRD ID or vice versa.

---

## 3. The reciprocal cite on the spec side

For each filled row, the engineering spec section names the PRD requirement it realizes — in its
**Rationale** (preferred) or **References**:

```markdown
### Rationale (WHY)
This contract realizes [PRD-SEARCH-03](../prd/search.md#PRD-SEARCH-03): sub-second relevance
ranking is a product requirement, not an implementation choice.
```

Engineering owns writing this (via the `spec-authoring` skill); Product confirms it exists when
filling the Linked Specs row.

---

## 4. Why AREA ≠ SUBSYSTEM (and that's fine)

PRDs are organized by product **AREA** (what a user/PM names); specs by engineering **SUBSYSTEM**
(what changes together / one team owns). They deliberately do not map 1:1:

```
PRD-SEARCH-03  ──realized by──▶  SPEC-SESSIONS-07~2   (query session handling)
               └─also by────────▶  SPEC-INTEGRATIONS-05~1 (vector index adapter)

SPEC-HOOKS-12~1  ──realizes──▶  PRD-GOVERNANCE-02  (model-tier policy)
                 └─also──────▶  PRD-COST-04        (spend guardrails)
```

The Linked Specs table is exactly the artifact that records this many-to-many mapping. Do **not**
rename a product AREA to match a subsystem or vice versa — record the relationship in the table
instead. See [`ia-and-categories.md`](ia-and-categories.md) for choosing areas.

---

## 5. Maintaining the link over time

| Event | What to do |
|-------|------------|
| Requirement reaches `Approved` | Engineering authors a spec; add the SPEC ID to the row once it exists. |
| Spec bumps `~{rev}` (contract changed) | Update the row's `~{rev}`; re-confirm the requirement still holds. |
| Spec is superseded | Point the row at the new SPEC ID; supersede the requirement if intent changed. |
| Requirement superseded | New PRD ID; carry forward / re-target the spec links (see `prd-lifecycle.md` §3). |
| Requirement shipped | Status column → `Shipped`/`Active`; begin measuring success metrics. |

---

## 6. Traceability as a product asset

The Linked Specs table is the product-side half of a Requirements Traceability Matrix. It lets a
Product Owner answer **"is requirement X implemented, and by what?"** and lets engineering answer
**"why does this contract exist?"** — the bidirectional trace OpenFastTrace/DO-178C disciplines
formalize, applied across the product/engineering boundary instead of within code.

---

## See also

- [`prd-template.md`](prd-template.md) — where the Linked Specs table sits in the document.
- [`ia-and-categories.md`](ia-and-categories.md) — why AREA and SUBSYSTEM are different axes.
- The `spec-authoring` skill — the engineering side that writes the reciprocal cite.
- [`docs/prd/README.md` §7](../../../../../../../docs/prd/README.md) — the authoritative convention.
- [`docs/specs/AUTHORING.md` §2](../../../../../../../docs/specs/AUTHORING.md) — the spec side's view of the same link.

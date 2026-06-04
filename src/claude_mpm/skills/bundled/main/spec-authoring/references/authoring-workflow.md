# Authoring Workflow & Lifecycle

The end-to-end workflow for taking an engineering spec from inception to active (and eventually
to superseded), plus the review checklist. Agent-facing copy of
[`docs/specs/AUTHORING.md` §8](../../../../../../../docs/specs/AUTHORING.md).

---

## 1. Lifecycle stages

A spec moves through a defined lifecycle, tracked in the header-block **Status** field (and
per-section `**Status:**` where sections diverge):

| Stage | Meaning | Status value |
|-------|---------|--------------|
| **Inception** | Need identified — often by an approved `PRD-{AREA}-{NN}` requirement. No document yet. | (no file) |
| **Research** | Technical investigation underway in `research/`; question defined, evidence gathering. | (research doc only) |
| **Draft** | Spec sections written but not yet implemented/reviewed. CI tolerates uncovered IDs via the draft exemption ([`README.md` §9b](../../../../../../../docs/specs/README.md)). | `Draft` / `draft (pending backfill)` |
| **Review** | Sections complete; human review of semantic correctness and code linkage in progress. | `Draft` (during review) |
| **Active** | Reviewed, implementing modules linked, CI green. The contract is binding. | `Active` |
| **Superseded** | Replaced by a newer section; retained for history; links forward. | `Superseded` |
| **Deprecated** | Behavior being removed; no replacement. | `Deprecated` |

---

## 2. The authoring loop (Inception → Active)

```
PRD requirement approved (or technical need identified)
        │
        ▼
[Inception]  Identify the subsystem. Existing file or new? → category-taxonomy.md
        │
        ▼
[Research]   Non-obvious decisions? Write docs/specs/research/NN-*.md → research-conventions.md
        │
        ▼
[Draft]      Apply spec-template.md. Mark **Status:** draft (pending backfill).
             - One ID per verifiable behavior → granularity-guide.md
             - Cite the PRD-{AREA}-{NN} realized
             - Fill Behavior Contract, Rationale, Implementing Modules
             - Add ToC rows; verify anchors resolve
        │
        ▼
[Review]     Human review: does each contract match intended behavior? Are links real?
        │
        ▼
[Backfill]   Engineers add SLD References blocks to implementing modules (spec-linked-docs)
        │
        ▼
[Active]     Remove the draft marker. CI UNCOVERED enforcement now applies.
             Update PRD's Linked Specs table with the now-Active SPEC IDs.
```

### Step detail

1. **Inception.** Confirm the driving need. If it comes from product, note the
   `PRD-{AREA}-{NN}`. Decide subsystem placement using
   [`category-taxonomy.md`](category-taxonomy.md).
2. **Research (if needed).** For any non-obvious decision, write a research doc first
   ([`research-conventions.md`](research-conventions.md)). Skip for obvious contracts.
3. **Draft.** Copy [`spec-template.md`](spec-template.md). Mark sections
   `**Status:** draft (pending backfill)` so CI stays green while code is unwritten. Size each
   section with [`granularity-guide.md`](granularity-guide.md). Cite the PRD requirement.
4. **Review.** A human (or reviewing agent) confirms the contract is correct and the
   Implementing Modules table names the right code. This catches the false-confidence risk SLD
   warns about — CI proves links *exist*, not that they are *correct*.
5. **Backfill.** Engineers add `References: SPEC-…` blocks to the named module docstrings. This
   is the `spec-linked-docs` handoff.
6. **Active.** Remove the `draft` marker (`**Status:** Active`). Normal UNCOVERED enforcement
   applies immediately — if backfill missed a reference, CI catches it. Update the PRD's
   *Linked Specs* table so the product side now points to a live contract.

---

## 3. Supersession (changing a contract that already shipped)

When a contract materially changes, you do **not** edit the old ID's meaning in place — IDs are
stable history.

- If the change is a **contract revision** of the same behavior: bump `~{rev}` on the same ID
  (`SPEC-HOOKS-05~1` → `SPEC-HOOKS-05~2`). Docstrings on the old rev are flagged OUTDATED.
- If the change **replaces** the behavior with a different one: create a **new ID** and mark the
  old one superseded:
  - Old section: `**Status:** Superseded` + `**Superseded-by:** SPEC-{SUBSYSTEM}-{NN}~{rev}`.
  - New section: `**Supersedes:** SPEC-{SUBSYSTEM}-{MM}~{rev}`.

This preserves a navigable chain: a reader landing on an old docstring reference follows it
forward to the current contract.

---

## 4. Review checklist

Before marking a spec section **Active**, confirm:

### Structure
- [ ] Header block present: Status, Version, Subsystem, **Owner = engineering team/role**,
      Last-updated, Related.
- [ ] Section has a stable `{#SPEC-{SUBSYSTEM}-{NN}~{rev}}` anchor and matching `**ID:**` field.
- [ ] ToC has a row for the section (ID → anchor → modules).

### Content
- [ ] Behavior Contract covers Inputs, Outputs, Preconditions, Postconditions, Error conditions.
- [ ] Rationale (WHY) is present and non-empty — a section without WHY is incomplete.
- [ ] **No HOW** in the contract or rationale (no "first we…, then we…").
- [ ] **No PRD content** leaked in — no problem statement, personas, user stories, acceptance
      criteria, or success metrics. (Those are in the PRD; cite it instead.)
- [ ] Implementing Modules table names real modules.

### Granularity
- [ ] One independently-verifiable behavior per ID ([`granularity-guide.md`](granularity-guide.md)).
- [ ] `~rev` bumped iff the contract changed materially.

### Links & traceability
- [ ] The `PRD-{AREA}-{NN}` realized (if any) is cited, and the PRD's Linked Specs table will be
      updated to point back.
- [ ] Every `#SPEC-…` / `#PRD-…` anchor linked actually exists; every relative path resolves
      (no dangling links).
- [ ] Non-obvious decisions cite research / ADR / PRD / external source.

### CI
- [ ] `uv run pytest tests/test_spec_traceability.py` passes.
- [ ] Draft sections carry `**Status:** draft (pending backfill)` until code is linked.

---

## 5. Handoffs

| To | When | Skill |
|----|------|-------|
| Engineers | After Draft/Review, to add docstring `References` | `spec-linked-docs` |
| Product Owner | To update the PRD's Linked Specs table once specs are Active | `prd-authoring` |
| Reviewer | At Review stage, to verify semantic correctness | (human / QA agent) |

---

## See also

- [`spec-template.md`](spec-template.md) · [`category-taxonomy.md`](category-taxonomy.md) ·
  [`granularity-guide.md`](granularity-guide.md) · [`research-conventions.md`](research-conventions.md)
- [`docs/specs/AUTHORING.md`](../../../../../../../docs/specs/AUTHORING.md) — the authoritative standard.
- [`docs/specs/README.md`](../../../../../../../docs/specs/README.md) — SLD traceability (the downstream half).

# Spec Template (Behavior Contract)

Copy-pasteable template for an engineering spec file at `docs/specs/{subsystem}.md`. This is
the agent-facing copy of the canonical model in
[`docs/specs/AUTHORING.md` §3](../../../../../../../docs/specs/AUTHORING.md). The behavior-contract
section skeleton itself is owned by SLD ([`docs/specs/README.md` §5](../../../../../../../docs/specs/README.md)) —
reuse it verbatim.

> **SPEC ≠ PRD.** This template carries **no** product sections — no problem statement, no
> personas, no acceptance criteria, no success metrics. Those belong to the PRD
> (`docs/prd/`, owned by Product). A spec is the engineering contract that *realizes* a PRD
> requirement; cite the `PRD-{AREA}-{NN}` from the section's Rationale or References.

---

## Full file template

```markdown
# {Subsystem} Subsystem — Spec

**Status:** Active | Draft | Superseded | Deprecated
**Version:** v{N}
**Subsystem:** {UPPERCASE-SUBSYSTEM}
**Owner:** Engineering / Architecture ({team or role})
**Last-updated:** {YYYY-MM-DD}
**Related:** [{SUBSYSTEM}](other.md), [PRD-{AREA}-{NN}](../prd/{area}.md#PRD-{AREA}-{NN})

## Purpose & Scope

{2–5 sentences. What this subsystem is responsible for, and — equally important — what is
explicitly out of scope. Out-of-scope statements prevent ID sprawl. If this subsystem realizes
a product requirement, name the PRD area here.}

## Table of Contents

| ID | Section | Implementing module(s) |
|----|---------|--------------------------|
| SPEC-{SUBSYSTEM}-01~1 | [{Section title}](#section-anchor-spec-subsystem-011) | `pkg.module` |

## {Section Title} {#SPEC-{SUBSYSTEM}-01~1}

**ID:** SPEC-{SUBSYSTEM}-01~1
**Status:** Active | Draft | Superseded
**Supersedes:** SPEC-{SUBSYSTEM}-NN~{rev}   (only if applicable)

### Behavior Contract (WHAT)

*Observable behavior from the caller's perspective. No implementation steps (no HOW).*

- **Inputs:** {what the caller supplies; types, ranges, sources}
- **Outputs:** {what the caller receives; types, guarantees}
- **Preconditions:** {what must hold before the behavior is invoked}
- **Postconditions:** {what is guaranteed to hold afterward}
- **Error conditions:** {failure modes and their observable effects — raises, returns, retries}

### Rationale (WHY)

{Design decisions and constraints — why this contract over alternatives. Never HOW.
If this contract realizes a product requirement, cite it:
"Realizes [PRD-{AREA}-{NN}](../prd/{area}.md#PRD-{AREA}-{NN})."}

### Implementing Modules

| Module | Role |
|--------|------|
| `pkg.module` | {what this module contributes to the contract} |

## Open Questions / Future Work

{Unresolved decisions, deferred behavior, known gaps. Keep distinct from the contract.}

## References

- [PRD-{AREA}-{NN}](../prd/{area}.md#PRD-{AREA}-{NN}) — the product requirement this spec realizes.
- `research/NN-topic-slug.md` — technical research behind a non-obvious decision.
- `docs/adr/NNNN-*.md` — ADR for a significant, hard-to-reverse decision.
- [{RELATED-SUBSYSTEM}](other.md) — related spec.
```

---

## Field-by-field guidance

### Header block

| Field | Rule |
|-------|------|
| `Status` | File-level status. Per-section `**Status:**` overrides where sections diverge. |
| `Version` | `v{N}`, bumped for substantial file-level revisions; orthogonal to per-ID `~{rev}`. |
| `Subsystem` | The UPPERCASE token. Must equal the `{SUBSYSTEM}` slot in every ID in this file. |
| `Owner` | **Always an engineering team or role.** A spec is engineering-owned. If you find yourself wanting to name a PM here, you are writing a PRD — go to `docs/prd/`. |
| `Last-updated` | `YYYY-MM-DD`. Update on every material edit. |
| `Related` | Relative links to sibling spec files and to the `PRD-{AREA}-{NN}` requirement(s) realized. |

### The three governed subsections (verbatim from SLD)

- **Behavior Contract (WHAT)** — the only place outputs/guarantees are stated. Active voice
  from the caller's perspective: "Accepts…", "Returns…", "Raises…". This is what tests assert
  against and what SLD docstring links attach to.
- **Rationale (WHY)** — mandatory. Explains *why this contract* over alternatives, plus the
  product requirement realized. A section without a WHY is incomplete.
- **Implementing Modules** — names the code that fulfills the contract. SLD verifies these
  references bidirectionally against docstring `References` blocks.

### What is deliberately absent

| Section you might expect | Where it actually lives |
|--------------------------|--------------------------|
| Problem statement / context | PRD — `docs/prd/{area}.md` |
| Target users / personas | PRD |
| User stories / jobs-to-be-done | PRD |
| Acceptance criteria | PRD |
| Success metrics / KPIs | PRD |

If a reviewer asks "where are the acceptance criteria?", the answer is: in the linked PRD. The
spec's Behavior Contract is the *engineering* contract; product acceptance is a product concern.

---

## Minimal section (smallest valid governed section)

```markdown
## Cache TTL refresh {#SPEC-CACHE-03~1}

**ID:** SPEC-CACHE-03~1
**Status:** Active

### Behavior Contract (WHAT)
- **Inputs:** A cache key and a TTL in seconds.
- **Outputs:** The cached value if within TTL; otherwise a freshly computed value.
- **Preconditions:** None.
- **Postconditions:** A value computed within the last TTL seconds is returned.
- **Error conditions:** Computation failure propagates; the stale value is not returned.

### Rationale (WHY)
Bounds recompute cost to once per TTL window. Realizes
[PRD-PERF-02](../prd/performance.md#PRD-PERF-02): sub-100ms reads under load.

### Implementing Modules
| Module | Role |
|--------|------|
| `claude_mpm.cache.ttl` | Stores values with timestamps and gates recompute. |
```

---

## See also

- [`category-taxonomy.md`](category-taxonomy.md) — which file (subsystem) the section belongs in.
- [`granularity-guide.md`](granularity-guide.md) — whether the behavior is one ID or several.
- [`docs/specs/AUTHORING.md`](../../../../../../../docs/specs/AUTHORING.md) — the authoritative standard.
- [`docs/specs/README.md`](../../../../../../../docs/specs/README.md) — ID grammar and section skeleton (SLD).

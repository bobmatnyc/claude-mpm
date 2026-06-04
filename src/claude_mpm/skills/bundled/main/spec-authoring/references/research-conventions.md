# Research Conventions (Engineering / Technical)

How to run and record **engineering / technical** research before writing a spec. Agent-facing
copy of [`docs/specs/AUTHORING.md` §7](../../../../../../../docs/specs/AUTHORING.md).

> **Scope boundary.** This is *technical* research — algorithms, prior art, benchmarks,
> failure modes, "how should we build it." **Product / user / market / competitive** research
> belongs to the PRD side (`docs/prd/research/`; see the `prd-authoring` skill). Keep the two
> separate: technical research justifies the *contract*; product research justifies the
> *requirement*.

---

## 1. The `docs/specs/research/` directory

Pre-spec technical investigation lives in [`docs/specs/research/`](../../../../../../../docs/specs/research/),
**separate from the spec contract**.

- The SLD checker **excludes** this directory ([`README.md` §4 Subsystem Allowlist](../../../../../../../docs/specs/README.md)),
  so research notes never count as spec declarations and never appear in coverage.
- Keep exploratory thinking here so the spec files stay clean, terse contracts.

### Naming

```
docs/specs/research/NN-topic-slug.md
```

- `NN` — two-digit sequence (`01`, `02`, …), monotonic within the directory.
- `topic-slug` — short hyphenated description: `05-cache-eviction-strategies.md`,
  `12-mcp-transport-tradeoffs.md`.

### Purpose

Capture the **technical evidence and reasoning** that led to a spec contract — algorithms
considered, prior art surveyed, benchmarks run, trade-offs weighed — so the spec itself can stay
terse and every non-obvious decision is traceable to its justification.

---

## 2. How to research before speccing

A repeatable five-step loop for technical pre-spec work:

### Step 1 — Define the technical question

State precisely what design decision the research must inform. A research doc without a question
becomes an unfocused dump.

> ✅ "Which cache-eviction policy meets the ≤100ms read target under 10k-key working sets?"
> ❌ "Caching."

### Step 2 — Gather technical evidence

At minimum, look at:

- **Code / prior art** — how does the current system (or a comparable one) already do this?
  Read the existing implementation; cite file paths and commits.
- **Algorithms / standards / papers** — existing techniques, RFCs, benchmarks. (SLD itself is
  grounded in OpenFastTrace and DO-178C RTM — see [`README.md` §2](../../../../../../../docs/specs/README.md).)
- **Constraints** — latency, memory, concurrency, failure modes the contract must respect.
  These often become the Preconditions and Error conditions of the eventual contract.

### Step 3 — Cite sources with links

Every claim that drives a decision gets a citable source: a URL, a `file:line`, or a commit
hash. **Unsourced assertions are assumptions, not evidence** (and must be marked as such — Step 4).

### Step 4 — Record assumptions explicitly

Separate what you **verified** from what you are **assuming**. Mark assumptions clearly. When an
assumption becomes an architectural commitment, promote it to an ADR (`mpm-adr`,
`docs/adr/NNNN-*.md`) and cite the ADR from the spec.

### Step 5 — Keep research distinct from the contract

The research doc may explore alternatives, dead ends, and trade-offs. The spec records only the
**chosen** contract. Do **not** let exploratory prose leak into the Behavior Contract — that is
the most common way a clean spec rots.

---

## 3. The citation rule

**Every non-obvious spec decision cites its justification.**

If a section's Rationale makes a claim a reasonable reviewer would ask "why?" about, that claim
links to:

- a `research/NN-*.md` doc, or
- an ADR (`docs/adr/NNNN-*.md`), or
- the `PRD-{AREA}-{NN}` requirement it realizes (for *why this is needed*), or
- an external source (RFC, paper, benchmark).

Obvious decisions need no citation; non-obvious ones always do.

---

## 4. Research doc skeleton

```markdown
# {NN} — {Topic}

**Question:** {the precise decision this research informs}
**Status:** Open | Resolved → {SPEC-SUBSYSTEM-NN~1}
**Date:** {YYYY-MM-DD}

## Context
{What prompted this. Link the PRD-{AREA}-{NN} or the spec section that needs the answer.}

## Options considered
| Option | Pros | Cons | Evidence |
|--------|------|------|----------|
| A | … | … | [link] |
| B | … | … | [link] |

## Findings
{What the evidence shows. Cite every claim.}

## Assumptions
- [verified] {…} — source: {link}
- [assumed]  {…} — promote to ADR if it becomes a commitment

## Decision
{The chosen contract, in one or two sentences. This is what the spec section will encode.}

## Sources
- {URL / file:line / commit / RFC / paper}
```

---

## 5. Research → spec handoff

When research resolves:

1. Set the research doc's `Status:` to `Resolved → SPEC-{SUBSYSTEM}-{NN}~1`.
2. Write (or update) the spec section, encoding only the **Decision** as the contract.
3. From the section's Rationale or References, link back to the research doc.
4. If a load-bearing assumption became a commitment, record an ADR and link it too.

This leaves a navigable chain: spec contract → rationale → research → sources.

---

## See also

- [`authoring-workflow.md`](authoring-workflow.md) — where research sits in the full lifecycle.
- [`spec-template.md`](spec-template.md) — where citations land (Rationale, References).
- The `prd-authoring` skill's `prd-research-practices.md` — the **product** research counterpart.
- [`docs/specs/AUTHORING.md` §7](../../../../../../../docs/specs/AUTHORING.md) — the authoritative rules.

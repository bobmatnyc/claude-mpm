# Spec Authoring Standard

**Status:** Active
**Version:** v1
**Scope:** Portable standard for authoring product specifications in `docs/specs/`. claude-mpm is the reference instantiation; other projects may adopt this standard independently.

---

## Table of Contents

1. [Purpose: Authoring vs. Traceability](#1-purpose-authoring-vs-traceability)
2. [The Spec Document Model (Hybrid Contract + PRD)](#2-the-spec-document-model-hybrid-contract--prd)
3. [Information Architecture & Categories](#3-information-architecture--categories)
4. [Granularity: One ID per Verifiable Behavior](#4-granularity-one-id-per-verifiable-behavior)
5. [README & Internal-Link Conventions](#5-readme--internal-link-conventions)
6. [Research Before Speccing](#6-research-before-speccing)
7. [Spec Lifecycle](#7-spec-lifecycle)
8. [Relationship to Spec-Linked Documentation (SLD)](#8-relationship-to-spec-linked-documentation-sld)

---

## 1. Purpose: Authoring vs. Traceability

This standard answers one question: **how do you author a product specification in `docs/specs/`?**

It is the companion to [`README.md`](README.md), the Spec-Linked Documentation (SLD) convention guide. The two are deliberately distinct and you need both:

| Document | Question it answers | Audience |
|----------|---------------------|----------|
| **`AUTHORING.md`** (this file) | *How do I write a spec?* — scope a subsystem, assign IDs, structure the document, decide granularity, run research, manage the lifecycle. | Spec authors (documentation agents, PMs, engineers drafting a subsystem). |
| [**`README.md`**](README.md) | *How does code trace to a spec?* — the ID grammar, docstring `References` blocks, the four-status CI checker, the WWL code-granularity model. | Engineers linking code to specs; reviewers verifying coverage. |

A useful mnemonic: **AUTHORING.md is upstream of the contract; README.md is downstream of it.** You author a spec section here; SLD then keeps source code in sync with it.

This standard does **not** redefine anything README.md owns. The **ID grammar**, the **declaration rule** (`{#SPEC-...}` anchors / `**ID:**` fields), the **Behavior Contract / Rationale / Implementing Modules** section skeleton, the **four-status model**, and the **WWL thresholds** all live in README.md. This file references them and tells you how to *produce* documents that satisfy them.

> **Canonical grammar:** Spec IDs follow `SPEC-{CATEGORY}-{NN}~{rev}` (e.g. `SPEC-HOOKS-01~1`). The full grammar, including the declaration rule and when to bump `~{rev}`, is defined in [`README.md` §4 — Spec ID Grammar](README.md#4-spec-id-grammar). Do not re-derive it; cite it.

---

## 2. The Spec Document Model (Hybrid Contract + PRD)

A claude-mpm spec is a **hybrid**: it carries the precision of a *behavior contract* (testable WHAT/WHY, the SLD core) and the framing of a lightweight *Product Requirements Document* (purpose, scope, acceptance criteria, open questions). One bounded subsystem or domain maps to one file: `docs/specs/{category}.md`.

### 2.1 Document skeleton

Every spec file has the following structure, top to bottom:

```markdown
# {Subsystem} Subsystem — Spec

**Status:** Active | Draft | Superseded | Deprecated
**Version:** v{N}
**Category:** {UPPERCASE-CATEGORY}
**Owner:** {team or role}
**Last-updated:** {YYYY-MM-DD}
**Related specs:** [{CATEGORY}](other.md), ...

## Purpose & Scope
{2–5 sentences: what this subsystem is responsible for, and — equally important —
what is explicitly out of scope. Out-of-scope statements prevent ID sprawl.}

## Table of Contents
{One row per governed section: ID → section anchor → implementing module(s).}

## {Section Title} {#SPEC-{CATEGORY}-{NN}~{rev}}
**ID:** SPEC-{CATEGORY}-{NN}~{rev}
**Status:** Active | Draft | Superseded
**Supersedes:** SPEC-{CATEGORY}-{MM}~{rev}   (if applicable)

### Behavior Contract (WHAT)
- **Inputs:** ...
- **Outputs:** ...
- **Preconditions:** ...
- **Postconditions:** ...
- **Error conditions:** ...

### Rationale (WHY)
{Design decisions and constraints — why this contract over alternatives. Never HOW.}

### Implementing Modules
| Module | Role |
|--------|------|
| `pkg.module` | ... |

### Acceptance Criteria / Success Metrics
- [ ] {An externally observable check a reviewer or test can evaluate.}
- {Optional success metric: target latency, error rate, adoption, etc.}

## Open Questions / Future Work
{Unresolved decisions, deferred behavior, known gaps. Keep distinct from the contract.}

## References
{Links to research docs, ADRs, external prior art, related specs.}
```

The three middle subsections — **Behavior Contract (WHAT)**, **Rationale (WHY)**, **Implementing Modules** — are owned by the SLD convention ([`README.md` §5](README.md#5-spec-section-structure)) and are reused verbatim. This standard adds two PRD-flavored wrappers around them: the **header block** and **Acceptance Criteria / Success Metrics**.

### 2.2 Why each part exists

- **Header block** — makes status and ownership scannable; `Last-updated` and `Related specs` give a reader orientation without reading the body.
- **Purpose & Scope** — the boundary statement that decides what becomes an ID *here* vs. in another file.
- **Table of Contents (ID → section → modules)** — the per-file traceability index; mirrors the project-level index in [`README.md`](README.md).
- **Behavior Contract (WHAT)** — the testable, observable contract. This is what acceptance checks and SLD docstring links attach to.
- **Rationale (WHY)** — mandatory. A section without a WHY is incomplete ([`README.md` §5 Content Rules](README.md#5-spec-section-structure)).
- **Implementing Modules** — the HOW-link: where the behavior lives in code. SLD verifies these references bidirectionally.
- **Acceptance Criteria / Success Metrics** — the PRD addition: each criterion is a check a reviewer (or test) can evaluate to decide "done." Drives the granularity test in §4.
- **Open Questions / Future Work** — keeps exploratory thinking *out* of the contract so the contract stays stable.
- **References** — every non-obvious decision points back to the research or ADR that justifies it (§6).

### 2.3 Filled mini-example

```markdown
## Disk-cached version check {#SPEC-HOOKS-14~1}

**ID:** SPEC-HOOKS-14~1
**Status:** Active

### Behavior Contract (WHAT)
- **Inputs:** The current package version string; a cache file path under `~/.claude-mpm/`.
- **Outputs:** A boolean `update_available` and the latest known version string.
- **Preconditions:** The cache file may be absent or stale.
- **Postconditions:** On a cache miss older than the TTL, the cache is refreshed; the
  returned value always reflects either a fresh check or a within-TTL cached value.
- **Error conditions:** Network failure returns the last cached value and never raises;
  a corrupt cache file is treated as a miss.

### Rationale (WHY)
Hook handlers must not block on network I/O. A disk cache with a TTL bounds the cost of
the version check to one network round-trip per TTL window, keeping the common path
purely local. Failing closed to the cached value preserves hook latency targets.

### Implementing Modules
| Module | Role |
|--------|------|
| `claude_mpm.hooks.version_check` | Reads/writes the cache and performs the gated network check. |

### Acceptance Criteria / Success Metrics
- [ ] A second invocation within the TTL performs zero network calls (assert via mock).
- [ ] A simulated network failure returns the cached value and does not raise.
- Target: added hook latency from this check ≤ 1 ms on a cache hit.
```

---

## 3. Information Architecture & Categories

### 3.1 Two levels only

The IA is intentionally flat: **Category → numbered sections.**

- **Category** = one bounded subsystem or domain = one file, `docs/specs/{category}.md`. The category name (uppercased) is the `{CATEGORY}` token in every ID declared in that file.
- **Sections** = the governed `SPEC-{CATEGORY}-{NN}~{rev}` units within the file, numbered sequentially.

There is no third level. Resist nesting sub-subsystems inside a file; if a section needs its own children, that is a signal to split it into a new section (or, if the whole cluster is large and independently owned, a new category — see §3.3).

### 3.2 claude-mpm's existing categories

The reference instantiation governs seven categories, one file each:

| File | Category token | Domain |
|------|----------------|--------|
| [`agents.md`](agents.md) | `AGENTS` | Agent templates, assembly, deployment. |
| [`cli.md`](cli.md) | `CLI` | Click commands and interactive wizards. |
| [`hooks.md`](hooks.md) | `HOOKS` | PreToolUse/PostToolUse and lifecycle hook handlers, enforcement. |
| [`integrations.md`](integrations.md) | `INTEGRATIONS` | MCP servers and external service integration. |
| [`manifest.md`](manifest.md) | `MANIFEST` | Manifest, presets, model routing. |
| [`sessions.md`](sessions.md) | `SESSIONS` | Session lifecycle, runtime, persistence. |
| [`skills.md`](skills.md) | `SKILLS` | Skill definitions, discovery, deployment. |

### 3.3 When to add a category vs. a section

Add a **section** to an existing category (the common case) when the new behavior belongs to a subsystem that already has a file.

Add a **new category** (a new file) only when **all** of these hold:

1. **Bounded domain.** The behavior forms a cohesive subsystem with a clear boundary, not a feature of an existing one.
2. **Independent ownership / lifecycle.** It can be specced, reviewed, and versioned without churning an existing file.
3. **Several sections' worth.** It will hold more than one or two IDs; a single behavior belongs as a section, not a category.

If you are unsure, prefer a section. Categories are cheap to read but expensive to split later (IDs are stable and cannot be renamed without a supersession).

### 3.4 Naming

- Category tokens are **UPPERCASE alpha, hyphens allowed** (e.g. `HOOKS`, `INTEGRATIONS`, a hypothetical `MODEL-ROUTING`). This matches the `{CATEGORY}` slot in [`README.md` §4](README.md#4-spec-id-grammar).
- The file name is the **lowercase** form of the token: `model-routing.md` ↔ `SPEC-MODEL-ROUTING-01~1`.
- Keep tokens short and durable. The token appears in every ID and in every docstring reference; renaming it is a breaking change.

---

## 4. Granularity: One ID per Verifiable Behavior

### 4.1 The test

**One spec ID = one independently-verifiable behavior or requirement.** The litmus test:

> *Could you write a single acceptance check or test that passes or fails against this section?*

If yes, it is one ID. If a section needs several unrelated checks that could pass or fail independently, it is probably several IDs.

### 4.2 Too broad / too narrow

- **Too broad** ("the hooks subsystem dispatches events") — split. You cannot write *one* acceptance check for it; PreToolUse enforcement, PostToolUse observability, and Stop handling each have distinct contracts. Each becomes its own ID.
- **Too narrow** ("the dispatcher lowercases the event name") — merge. That is an implementation detail of a larger behavior (event routing), not an independently-verifiable requirement. It belongs in the WHAT of the routing section, not its own ID.

### 4.3 Split / merge heuristics

Split when a section has:
- Multiple, unrelated error-condition clusters.
- Distinct callers relying on distinct, separable outputs.
- An Acceptance Criteria list whose items have no logical reason to pass or fail together.

Merge when sections share:
- The same inputs/outputs and the same implementing module, differing only in incidental detail.
- A contract where changing one inevitably changes the other (they are one behavior described twice).

### 4.4 `~rev` bumps and WWL alignment

- Bump `~{rev}` only on a **material change to the behavior contract** (inputs, outputs, pre/postconditions, error conditions). Clarifying prose does not bump. The authority is [`README.md` §4 — When to Increment `~{rev}`](README.md#4-spec-id-grammar).
- A contract that justifies its own spec ID typically governs code that crosses the **SLD WWL thresholds** (function > 50 LOC or cyclomatic complexity > 10) and therefore requires a docstring link. See [`README.md` §6a — WWL Granularity Model](README.md#6a-code-level-granularity-the-wwl-model). Spec granularity and code-link granularity should be consistent: if a behavior is too small to warrant a WWL link, it is usually too small to warrant its own spec ID.

---

## 5. README & Internal-Link Conventions

### 5.1 Every directory has an orienting index

`docs/specs/` is indexed by [`README.md`](README.md). The research subdirectory is indexed by [`research/`](#6-research-before-speccing) conventions (§6). Any new directory under `docs/specs/` must carry a `README.md` (or equivalent index) that orients a reader: what lives here, what the naming convention is, and where to go next.

### 5.2 Cross-reference conventions

- **Within and across spec files**, link to sections by their stable `#SPEC-…` anchor using a relative path: `[SPEC-HOOKS-01~1](hooks.md#SPEC-HOOKS-01~1)`. Never link by mutable heading text alone.
- **Spec ↔ code** is maintained by SLD, not by manual links: the spec's *Implementing Modules* table names the module; the module's docstring carries the `References` block. The CI checker keeps them in sync. See [§8](#8-relationship-to-spec-linked-documentation-sld) and [`README.md` §6](README.md#6-docstring-references-format).
- **Spec ↔ research** — a spec section's *References* block links to the `research/NN-topic-slug.md` document(s) that justify its non-obvious decisions (§6).
- **Spec ↔ ADR** — when a section embodies a significant, hard-to-reverse architectural decision, link to its Architecture Decision Record. claude-mpm uses the `mpm-adr` skill (Nygard-template ADRs under `docs/adr/`). Cite the ADR from the section's *Rationale* or *References*: "Decision recorded in `docs/adr/0007-...md`."

### 5.3 No dangling anchors

Before committing, confirm every `#SPEC-…` anchor you link to is actually declared by a heading in the target file, and every relative path resolves. A link to a nonexistent anchor is a silent traceability gap.

---

## 6. Research Before Speccing

### 6.1 The `research/` directory

Pre-spec investigation lives in [`docs/specs/research/`](research/), **separate from the spec contract**. The SLD checker explicitly excludes this directory ([`README.md` §4 — Subsystem Allowlist](README.md#4-spec-id-grammar)), so research notes never count as spec declarations and never appear in coverage. Keep exploratory thinking here so the spec files stay clean contracts.

- **Naming:** `NN-topic-slug.md`, where `NN` is a two-digit sequence (`01`, `02`, …) and `topic-slug` is a short hyphenated description — e.g. `05-sdd-best-practices.md`.
- **Purpose:** capture the evidence and reasoning that *led to* a spec, so the spec itself can stay terse and every non-obvious decision is traceable to its justification.

### 6.2 How to research before speccing (general best practices)

This is project-agnostic; the `research/` directory is where the output lands.

1. **Define the question.** State precisely what decision the research must inform. A research doc without a question becomes an unfocused dump.
2. **Gather evidence across sources.** Look at, at minimum:
   - **Code / prior art** — how does the current system (or a comparable one) already do this?
   - **User / market need** — who needs this behavior and why?
   - **Competitive / external prior art** — existing tools, standards, papers. (SLD itself is grounded in OpenFastTrace, DO-178C RTM, etc. — see [`README.md` §2](README.md#2-lineage-oft-rtm-and-decades-of-prior-art) for the model.)
3. **Cite sources with links.** Every claim that drives a decision gets a citable source (URL, file path, or commit). Unsourced assertions are assumptions, not evidence.
4. **Record assumptions explicitly.** Mark what you are *assuming* vs. what you *verified*. Link assumptions that became architectural commitments to an ADR (`mpm-adr`).
5. **Keep research distinct from the contract.** The research doc may explore alternatives, dead ends, and trade-offs. The spec records only the *chosen* contract. Do not let exploratory prose leak into the Behavior Contract.

### 6.3 The citation rule

**Every non-obvious spec decision cites its research.** If a section's Rationale makes a claim that a reasonable reviewer would ask "why?" about, that claim links to a `research/NN-*.md` doc, an ADR, or an external source. Obvious decisions need no citation; non-obvious ones always do.

---

## 7. Spec Lifecycle

A spec moves through a defined lifecycle, tracked in the header-block **Status** field (and per-section `**Status:**` where sections diverge):

| Stage | Meaning | Status value |
|-------|---------|--------------|
| **Inception** | The need is identified; no document yet. | (no file) |
| **Research** | Investigation underway in `research/`; question defined, evidence gathering. | (research doc only) |
| **Draft** | Spec sections written but not yet implemented/reviewed. CI tolerates uncovered IDs via the draft exemption — see [`README.md` §9b](README.md#9b-draft-specs--incremental-backfill). | `Draft` / `draft (pending backfill)` |
| **Review** | Sections complete; human review of semantic correctness and code linkage in progress. | `Draft` (during review) |
| **Active** | Reviewed, implementing modules linked, CI green. The contract is binding. | `Active` |
| **Superseded** | Replaced by a newer section; retained for history. Links forward to its replacement. | `Superseded` |
| **Deprecated** | The behavior is being removed; no replacement. | `Deprecated` |

### Supersession links

When a section is superseded, do **not** delete it — IDs are stable history. Instead:

- Mark the old section `**Status:** Superseded`.
- Add `**Superseded-by:** SPEC-{CATEGORY}-{NN}~{rev}` to the old section.
- Add `**Supersedes:** SPEC-{CATEGORY}-{MM}~{rev}` to the new section (per [`README.md` §5](README.md#5-spec-section-structure)).

This preserves a navigable chain so a reader landing on an old docstring reference can follow it forward to the current contract.

---

## 8. Relationship to Spec-Linked Documentation (SLD)

This standard and SLD are two halves of one discipline:

- **Spec Authoring Standard (this file)** = *authoring*. How to write the spec: scope, structure, IDs, granularity, research, lifecycle.
- **[SLD](README.md)** = *traceability*. How code stays linked to the spec: docstring `References`, the four-status checker, WWL code granularity.

**The handoff:** You author a section here (with a stable ID, a Behavior Contract, an Implementing Modules table). SLD then takes over — engineers add `References: SPEC-…` blocks to the named modules, and the CI checker (`tests/test_spec_traceability.py`) enforces bidirectional completeness. A `~rev` bump you make here (on a contract change) is what SLD's OUTDATED status detects downstream.

Read both: this file to **write** a spec; [`README.md`](README.md) to **trace code to it**. The companion skills mirror this split — `spec-authoring` (this standard) and `spec-linked-docs` (traceability) — and cross-reference each other.

---

## References

- [`README.md`](README.md) — Spec-Linked Documentation (SLD) convention guide (ID grammar, section structure, four-status model, WWL).
- [`research/`](research/) — pre-spec investigation documents (`NN-topic-slug.md`).
- `mpm-adr` skill / `docs/adr/` — Architecture Decision Records (Nygard template) for significant, hard-to-reverse decisions.
- `spec-authoring` skill (`src/claude_mpm/skills/bundled/main/spec-authoring/`) — the agent-facing companion to this standard.
- `spec-linked-docs` skill (`src/claude_mpm/skills/bundled/universal/spec-linked-docs/`) — the traceability companion.

# Engineering Spec Authoring Standard

**Status:** Active
**Version:** v1
**Owner:** Engineering / Architecture
**Scope:** Portable standard for authoring **engineering specifications** in `docs/specs/`. claude-mpm is the reference instantiation; other projects may adopt this standard independently.

---

## Table of Contents

1. [Purpose: Authoring vs. Traceability](#1-purpose-authoring-vs-traceability)
2. [Specs vs. PRDs: Two Distinct Standards](#2-specs-vs-prds-two-distinct-standards)
3. [The Spec Document Model (Behavior Contract)](#3-the-spec-document-model-behavior-contract)
4. [Information Architecture & Subsystems](#4-information-architecture--subsystems)
5. [Granularity: One ID per Verifiable Behavior](#5-granularity-one-id-per-verifiable-behavior)
6. [README & Internal-Link Conventions](#6-readme--internal-link-conventions)
7. [Research Before Speccing](#7-research-before-speccing)
8. [Spec Lifecycle](#8-spec-lifecycle)
9. [Relationship to Spec-Linked Documentation (SLD)](#9-relationship-to-spec-linked-documentation-sld)

---

## 1. Purpose: Authoring vs. Traceability

This standard answers one question: **how does an engineer or architect author an engineering specification in `docs/specs/`?**

A spec here is a **behavioral contract**: a precise, testable statement of *what* a subsystem does (inputs, outputs, pre/postconditions, error conditions) and *why* it is designed that way (rationale), linked to the modules that implement it. It is owned by **Engineering / Architecture**.

This standard is the companion to [`README.md`](README.md), the Spec-Linked Documentation (SLD) convention guide. The two are deliberately distinct and you need both:

| Document | Question it answers | Audience |
|----------|---------------------|----------|
| **`AUTHORING.md`** (this file) | *How do I write an engineering spec?* — scope a subsystem, assign IDs, structure the document, decide granularity, run technical research, manage the lifecycle. | Engineers / architects drafting a subsystem; documentation agents. |
| [**`README.md`**](README.md) | *How does code trace to a spec?* — the ID grammar, docstring `References` blocks, the four-status CI checker, the WWL code-granularity model. | Engineers linking code to specs; reviewers verifying coverage. |

A useful mnemonic: **AUTHORING.md is upstream of the contract; README.md is downstream of it.** You author a spec section here; SLD then keeps source code in sync with it.

This standard does **not** redefine anything README.md owns. The **ID grammar**, the **declaration rule** (`{#SPEC-...}` anchors / `**ID:**` fields), the **Behavior Contract / Rationale / Implementing Modules** section skeleton, the **four-status model**, and the **WWL thresholds** all live in README.md. This file references them and tells you how to *produce* documents that satisfy them.

> **Canonical grammar:** Spec IDs follow `SPEC-{SUBSYSTEM}-{NN}~{rev}` (e.g. `SPEC-HOOKS-01~1`). The full grammar, including the declaration rule and when to bump `~{rev}`, is defined in [`README.md` §4 — Spec ID Grammar](README.md#4-spec-id-grammar). Do not re-derive it; cite it.

---

## 2. Specs vs. PRDs: Two Distinct Standards

A SPEC is **not** a PRD, and this standard is deliberately scoped to the spec side only.

| | **SPEC** (this standard) | **PRD** ([`docs/prd/`](../prd/README.md)) |
|---|--------------------------|--------------------------------------------|
| **Owner** | Engineering / Architecture | Product (Product Owner / PM) |
| **Answers** | The behavioral contract & how it is implemented. | What problem, for which users, what requirements, and what success looks like. |
| **Home** | `docs/specs/` | `docs/prd/` |
| **ID namespace** | `SPEC-{SUBSYSTEM}-{NN}~{rev}` | `PRD-{AREA}-{NN}` |
| **Primary content** | Inputs/Outputs/Pre/Postconditions/Errors, Rationale, Implementing Modules. | Problem, personas, goals, user stories, requirements, acceptance criteria, success metrics. |

**Do not** put product framing in a spec. Problem statements, target users, personas, user stories, acceptance criteria, and success metrics belong to **PRDs**, not specs. A spec records the *engineering contract* that realizes one or more PRD requirements.

**The link (spec → PRD, upward):** a spec section that implements a product requirement cites the `PRD-{AREA}-{NN}` it implements — from its **Rationale** or **References**:

```markdown
### Rationale (WHY)
This contract realizes [PRD-SEARCH-03](../prd/semantic-search.md#PRD-SEARCH-03):
sub-second relevance ranking is a product requirement, not an implementation choice.
```

The PRD links back **downward** to the spec(s) implementing it via its *Linked Specs* traceability table (see [`docs/prd/README.md`](../prd/README.md)). The two namespaces, directories, owners, and templates stay distinct; neither template absorbs the other.

---

## 3. The Spec Document Model (Behavior Contract)

A claude-mpm spec is a **behavior contract**: a testable statement of observable WHAT and the WHY behind it, linked to implementing modules. One bounded subsystem or domain maps to one file: `docs/specs/{subsystem}.md`.

This standard adds **no** product sections (no problem statement, no personas, no acceptance criteria, no success metrics). Those are PRD concerns (§2). The spec carries exactly the SLD section skeleton plus orienting wrappers (header, Purpose & Scope, ToC, Open Questions, References).

### 3.1 Document skeleton

Every spec file has the following structure, top to bottom:

```markdown
# {Subsystem} Subsystem — Spec

**Status:** Active | Draft | Superseded | Deprecated
**Version:** v{N}
**Subsystem:** {UPPERCASE-SUBSYSTEM}
**Owner:** Engineering / Architecture (team or role)
**Last-updated:** {YYYY-MM-DD}
**Related:** [{SUBSYSTEM}](other.md), [PRD-{AREA}-{NN}](../prd/{area}.md#PRD-{AREA}-{NN}), ...

## Purpose & Scope
{2–5 sentences: what this subsystem is responsible for, and — equally important —
what is explicitly out of scope. Out-of-scope statements prevent ID sprawl.}

## Table of Contents
{One row per governed section: ID → section anchor → implementing module(s).}

## {Section Title} {#SPEC-{SUBSYSTEM}-{NN}~{rev}}
**ID:** SPEC-{SUBSYSTEM}-{NN}~{rev}
**Status:** Active | Draft | Superseded
**Supersedes:** SPEC-{SUBSYSTEM}-{MM}~{rev}   (if applicable)

### Behavior Contract (WHAT)
- **Inputs:** ...
- **Outputs:** ...
- **Preconditions:** ...
- **Postconditions:** ...
- **Error conditions:** ...

### Rationale (WHY)
{Design decisions and constraints — why this contract over alternatives. Never HOW.
Cite the PRD-{AREA}-{NN} requirement this contract realizes, if any.}

### Implementing Modules
| Module | Role |
|--------|------|
| `pkg.module` | ... |

## Open Questions / Future Work
{Unresolved decisions, deferred behavior, known gaps. Keep distinct from the contract.}

## References
{Links to research docs, ADRs, the PRD requirement(s) realized, external prior art, related specs.}
```

The three middle subsections — **Behavior Contract (WHAT)**, **Rationale (WHY)**, **Implementing Modules** — are owned by the SLD convention ([`README.md` §5](README.md#5-spec-section-structure)) and are reused **verbatim**. This standard adds only orienting wrappers around them (the header block, Purpose & Scope, ToC, Open Questions, References). It deliberately does **not** add Acceptance Criteria or Success Metrics — those are PRD sections (§2).

### 3.2 Why each part exists

- **Header block** — makes status and ownership scannable; `Last-updated` and `Related` give a reader orientation without reading the body. `Owner` is always an engineering team/role.
- **Purpose & Scope** — the boundary statement that decides what becomes an ID *here* vs. in another file.
- **Table of Contents (ID → section → modules)** — the per-file traceability index; mirrors the project-level index in [`README.md`](README.md).
- **Behavior Contract (WHAT)** — the testable, observable contract. This is what SLD docstring links attach to.
- **Rationale (WHY)** — mandatory. A section without a WHY is incomplete ([`README.md` §5 Content Rules](README.md#5-spec-section-structure)). Where the contract realizes a product requirement, cite the `PRD-{AREA}-{NN}`.
- **Implementing Modules** — the HOW-link: where the behavior lives in code. SLD verifies these references bidirectionally.
- **Open Questions / Future Work** — keeps exploratory thinking *out* of the contract so the contract stays stable.
- **References** — every non-obvious decision points back to the research, ADR, or PRD requirement that justifies it (§7).

### 3.3 Filled mini-example

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
```

(Note: there is **no** Acceptance Criteria subsection. The observable behavior in the contract is what tests assert against; product-level acceptance criteria, if any, live in the linked PRD.)

---

## 4. Information Architecture & Subsystems

### 4.1 Two levels only

The IA is intentionally flat: **Subsystem → numbered sections.**

- **Subsystem** = one bounded subsystem or domain = one file, `docs/specs/{subsystem}.md`. The subsystem name (uppercased) is the `{SUBSYSTEM}` token in every ID declared in that file.
- **Sections** = the governed `SPEC-{SUBSYSTEM}-{NN}~{rev}` units within the file, numbered sequentially.

There is no third level. Resist nesting sub-subsystems inside a file; if a section needs its own children, that is a signal to split it into a new section (or, if the whole cluster is large and independently owned, a new subsystem — see §4.3).

### 4.2 claude-mpm's existing subsystems

The reference instantiation governs seven subsystems, one file each:

| File | Subsystem token | Domain |
|------|----------------|--------|
| [`agents.md`](agents.md) | `AGENTS` | Agent templates, assembly, deployment. |
| [`cli.md`](cli.md) | `CLI` | Click commands and interactive wizards. |
| [`hooks.md`](hooks.md) | `HOOKS` | PreToolUse/PostToolUse and lifecycle hook handlers, enforcement. |
| [`integrations.md`](integrations.md) | `INTEGRATIONS` | MCP servers and external service integration. |
| [`manifest.md`](manifest.md) | `MANIFEST` | Manifest, presets, model routing. |
| [`sessions.md`](sessions.md) | `SESSIONS` | Session lifecycle, runtime, persistence. |
| [`skills.md`](skills.md) | `SKILLS` | Skill definitions, discovery, deployment. |

### 4.3 When to add a subsystem vs. a section

Add a **section** to an existing subsystem (the common case) when the new behavior belongs to a subsystem that already has a file.

Add a **new subsystem** (a new file) only when **all** of these hold:

1. **Bounded domain.** The behavior forms a cohesive subsystem with a clear boundary, not a feature of an existing one.
2. **Independent ownership / lifecycle.** It can be specced, reviewed, and versioned without churning an existing file.
3. **Several sections' worth.** It will hold more than one or two IDs; a single behavior belongs as a section, not a subsystem.

If you are unsure, prefer a section. Subsystems are cheap to read but expensive to split later (IDs are stable and cannot be renamed without a supersession).

### 4.4 Naming

- Subsystem tokens are **UPPERCASE alpha, hyphens allowed** (e.g. `HOOKS`, `INTEGRATIONS`, a hypothetical `MODEL-ROUTING`). This matches the `{SUBSYSTEM}` slot in [`README.md` §4](README.md#4-spec-id-grammar).
- The file name is the **lowercase** form of the token: `model-routing.md` ↔ `SPEC-MODEL-ROUTING-01~1`.
- Keep tokens short and durable. The token appears in every ID and in every docstring reference; renaming it is a breaking change.

---

## 5. Granularity: One ID per Verifiable Behavior

### 5.1 The test

**One spec ID = one independently-verifiable behavior.** The litmus test:

> *Could you write a single test that passes or fails against this section's Behavior Contract?*

If yes, it is one ID. If a section needs several unrelated checks that could pass or fail independently, it is probably several IDs.

### 5.2 Too broad / too narrow

- **Too broad** ("the hooks subsystem dispatches events") — split. You cannot write *one* contract test for it; PreToolUse enforcement, PostToolUse observability, and Stop handling each have distinct contracts. Each becomes its own ID.
- **Too narrow** ("the dispatcher lowercases the event name") — merge. That is an implementation detail of a larger behavior (event routing), not an independently-verifiable contract. It belongs in the WHAT of the routing section, not its own ID.

### 5.3 Split / merge heuristics

Split when a section has:
- Multiple, unrelated error-condition clusters.
- Distinct callers relying on distinct, separable outputs.
- Contract clauses that have no logical reason to change together.

Merge when sections share:
- The same inputs/outputs and the same implementing module, differing only in incidental detail.
- A contract where changing one inevitably changes the other (they are one behavior described twice).

### 5.4 `~rev` bumps and WWL alignment

- Bump `~{rev}` only on a **material change to the behavior contract** (inputs, outputs, pre/postconditions, error conditions). Clarifying prose does not bump. The authority is [`README.md` §4 — When to Increment `~{rev}`](README.md#4-spec-id-grammar).
- A contract that justifies its own spec ID typically governs code that crosses the **SLD WWL thresholds** (function > 50 LOC or cyclomatic complexity > 10) and therefore requires a docstring link. See [`README.md` §6a — WWL Granularity Model](README.md#6a-code-level-granularity-the-wwl-model). Spec granularity and code-link granularity should be consistent: if a behavior is too small to warrant a WWL link, it is usually too small to warrant its own spec ID.

---

## 6. README & Internal-Link Conventions

### 6.1 Every directory has an orienting index

`docs/specs/` is indexed by [`README.md`](README.md). The research subdirectory is indexed by [`research/`](#7-research-before-speccing) conventions (§7). Any new directory under `docs/specs/` must carry a `README.md` (or equivalent index) that orients a reader: what lives here, what the naming convention is, and where to go next.

### 6.2 Cross-reference conventions

- **Within and across spec files**, link to sections by their stable `#SPEC-…` anchor using a relative path: `[SPEC-HOOKS-01~1](hooks.md#SPEC-HOOKS-01~1)`. Never link by mutable heading text alone.
- **Spec ↔ code** is maintained by SLD, not by manual links: the spec's *Implementing Modules* table names the module; the module's docstring carries the `References` block. The CI checker keeps them in sync. See [§9](#9-relationship-to-spec-linked-documentation-sld) and [`README.md` §6](README.md#6-docstring-references-format).
- **Spec ↔ PRD** — a spec section's *Rationale* or *References* cites the `PRD-{AREA}-{NN}` requirement it realizes, using a relative path into `docs/prd/`: `[PRD-SEARCH-03](../prd/semantic-search.md#PRD-SEARCH-03)`. The PRD lists this spec in its *Linked Specs* table (see [`docs/prd/README.md`](../prd/README.md)). The link is bidirectional and the namespaces stay distinct.
- **Spec ↔ research** — a spec section's *References* block links to the `research/NN-topic-slug.md` document(s) that justify its non-obvious decisions (§7).
- **Spec ↔ ADR** — when a section embodies a significant, hard-to-reverse architectural decision, link to its Architecture Decision Record. claude-mpm uses the `mpm-adr` skill (Nygard-template ADRs under `docs/adr/`). Cite the ADR from the section's *Rationale* or *References*: "Decision recorded in `docs/adr/0007-...md`."

### 6.3 No dangling anchors

Before committing, confirm every `#SPEC-…` and `#PRD-…` anchor you link to is actually declared by a heading in the target file, and every relative path resolves. A link to a nonexistent anchor is a silent traceability gap.

---

## 7. Research Before Speccing

### 7.1 The `research/` directory

Pre-spec **engineering / technical** investigation lives in [`docs/specs/research/`](research/), **separate from the spec contract**. The SLD checker explicitly excludes this directory ([`README.md` §4 — Subsystem Allowlist](README.md#4-spec-id-grammar)), so research notes never count as spec declarations and never appear in coverage. Keep exploratory thinking here so the spec files stay clean contracts.

- **Naming:** `NN-topic-slug.md`, where `NN` is a two-digit sequence (`01`, `02`, …) and `topic-slug` is a short hyphenated description — e.g. `05-cache-eviction-strategies.md`.
- **Purpose:** capture the technical evidence and reasoning that *led to* a spec contract (algorithms, prior art, benchmarks, trade-offs), so the spec itself can stay terse and every non-obvious decision is traceable to its justification.
- **Scope:** this is *technical* research — how to build it. *Product / user / market* research belongs to the PRD side (`docs/prd/research/`, see [`docs/prd/README.md`](../prd/README.md)).

### 7.2 How to research before speccing (engineering focus)

1. **Define the technical question.** State precisely what design decision the research must inform. A research doc without a question becomes an unfocused dump.
2. **Gather technical evidence.** Look at, at minimum:
   - **Code / prior art** — how does the current system (or a comparable one) already do this?
   - **Algorithms / standards / papers** — existing techniques, RFCs, benchmarks. (SLD itself is grounded in OpenFastTrace, DO-178C RTM, etc. — see [`README.md` §2](README.md#2-lineage-oft-rtm-and-decades-of-prior-art).)
   - **Constraints** — latency, memory, concurrency, failure modes the contract must respect.
3. **Cite sources with links.** Every claim that drives a decision gets a citable source (URL, file path, or commit). Unsourced assertions are assumptions, not evidence.
4. **Record assumptions explicitly.** Mark what you are *assuming* vs. what you *verified*. Link assumptions that became architectural commitments to an ADR (`mpm-adr`).
5. **Keep research distinct from the contract.** The research doc may explore alternatives, dead ends, and trade-offs. The spec records only the *chosen* contract. Do not let exploratory prose leak into the Behavior Contract.

### 7.3 The citation rule

**Every non-obvious spec decision cites its justification.** If a section's Rationale makes a claim that a reasonable reviewer would ask "why?" about, that claim links to a `research/NN-*.md` doc, an ADR, the PRD requirement it realizes, or an external source. Obvious decisions need no citation; non-obvious ones always do.

---

## 8. Spec Lifecycle

A spec moves through a defined lifecycle, tracked in the header-block **Status** field (and per-section `**Status:**` where sections diverge):

| Stage | Meaning | Status value |
|-------|---------|--------------|
| **Inception** | The need is identified (often by an approved PRD requirement); no document yet. | (no file) |
| **Research** | Technical investigation underway in `research/`; question defined, evidence gathering. | (research doc only) |
| **Draft** | Spec sections written but not yet implemented/reviewed. CI tolerates uncovered IDs via the draft exemption — see [`README.md` §9b](README.md#9b-draft-specs--incremental-backfill). | `Draft` / `draft (pending backfill)` |
| **Review** | Sections complete; human review of semantic correctness and code linkage in progress. | `Draft` (during review) |
| **Active** | Reviewed, implementing modules linked, CI green. The contract is binding. | `Active` |
| **Superseded** | Replaced by a newer section; retained for history. Links forward to its replacement. | `Superseded` |
| **Deprecated** | The behavior is being removed; no replacement. | `Deprecated` |

### Supersession links

When a section is superseded, do **not** delete it — IDs are stable history. Instead:

- Mark the old section `**Status:** Superseded`.
- Add `**Superseded-by:** SPEC-{SUBSYSTEM}-{NN}~{rev}` to the old section.
- Add `**Supersedes:** SPEC-{SUBSYSTEM}-{MM}~{rev}` to the new section (per [`README.md` §5](README.md#5-spec-section-structure)).

This preserves a navigable chain so a reader landing on an old docstring reference can follow it forward to the current contract.

---

## 9. Relationship to Spec-Linked Documentation (SLD)

This standard and SLD are two halves of one discipline:

- **Engineering Spec Authoring Standard (this file)** = *authoring*. How to write the spec: scope, structure, IDs, granularity, research, lifecycle.
- **[SLD](README.md)** = *traceability*. How code stays linked to the spec: docstring `References`, the four-status checker, WWL code granularity.

**The handoff:** You author a section here (with a stable ID, a Behavior Contract, an Implementing Modules table). SLD then takes over — engineers add `References: SPEC-…` blocks to the named modules, and the CI checker (`tests/test_spec_traceability.py`) enforces bidirectional completeness. A `~rev` bump you make here (on a contract change) is what SLD's OUTDATED status detects downstream.

Read both: this file to **write** a spec; [`README.md`](README.md) to **trace code to it**. The companion skills mirror this split — `spec-authoring` (this standard) and `spec-linked-docs` (traceability) — and cross-reference each other.

> **Specs implement PRD requirements.** A spec is the engineering contract that realizes a product requirement. When a section implements a `PRD-{AREA}-{NN}`, cite it (§2, §6.2). Product framing (problem, users, acceptance, metrics) stays in the PRD ([`docs/prd/`](../prd/README.md)); the spec stays a contract.

---

## References

- [`README.md`](README.md) — Spec-Linked Documentation (SLD) convention guide (ID grammar, section structure, four-status model, WWL).
- [`../prd/README.md`](../prd/README.md) — the **Product PRD Standard** (the product-owned companion; specs realize PRD requirements).
- [`research/`](research/) — pre-spec technical investigation documents (`NN-topic-slug.md`).
- `mpm-adr` skill / `docs/adr/` — Architecture Decision Records (Nygard template) for significant, hard-to-reverse decisions.
- `spec-authoring` skill (`src/claude_mpm/skills/bundled/main/spec-authoring/`) — the agent-facing companion to this standard.
- `prd-authoring` skill (`src/claude_mpm/skills/bundled/main/prd-authoring/`) — the product-side companion (authoring PRDs).
- `spec-linked-docs` skill (`src/claude_mpm/skills/bundled/universal/spec-linked-docs/`) — the traceability companion.

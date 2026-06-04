# Spec-Linked Documentation (SLD) — Convention Guide

**Status:** Active  
**Version:** v1  
**Scope:** claude-mpm repository (opt-in convention; other projects are not bound by this)

---

## Table of Contents

1. [What SLD Is — and What It Is Not](#1-what-sld-is-and-what-it-is-not)
2. [Lineage: OFT, RTM, and Decades of Prior Art](#2-lineage-oft-rtm-and-decades-of-prior-art)
3. [Why Revive This Discipline Now — and the False-Confidence Risk](#3-why-revive-this-discipline-now-and-the-false-confidence-risk)
4. [Spec ID Grammar](#4-spec-id-grammar)
5. [Spec Section Structure](#5-spec-section-structure)
6. [Docstring References Format](#6-docstring-references-format)
6a. [Code-Level Granularity: The WWL Model](#6a-code-level-granularity-the-wwl-model)
7. [The Four-Status Model](#7-the-four-status-model)
8. [The Checker: What It Proves and What It Does Not](#8-the-checker-what-it-proves-and-what-it-does-not)
9. [Opt-In Statement](#9-opt-in-statement)
9a. [Backfilling Existing Codebases](#9a-backfilling-existing-codebases)
10. [PR Review Checklist](#10-pr-review-checklist)
11. [Enabling SLD in claude-mpm](#11-enabling-sld-in-claude-mpm)
12. [Citations](#12-citations)

---

## 1. What SLD Is — and What It Is Not

**Spec-Linked Documentation (SLD)** is a documentation convention that maintains bidirectional
traceability between subsystem-level specification documents and Python source-code docstrings.
It is a documentation *discipline*, not a development methodology.

SLD is a Python-idiomatic adaptation of the [OpenFastTrace](https://github.com/itsallcode/openfasttrace)
(OFT) bidirectional traceability model and the decades-old Requirements Traceability Matrix (RTM)
discipline. See [section 2](#2-lineage-oft-rtm-and-decades-of-prior-art) for full attribution.

**SLD is NOT:**

- A development process (not "Spec-Driven Development" in the AI-SDD sense used by Kiro,
  GitHub Spec Kit, or Tessl — those are distinct concepts).
- An architecture documentation framework (not arc42, not C4, not Diataxis — those are
  complementary and operate at different levels).
- A requirement-management tool (not a replacement for Doorstop or StrictDoc — those
  are heavier tools with richer feature sets).
- A guarantee that code correctly implements its spec (see section 8).

**SLD IS:**

- A lightweight, zero-dependency, CI-enforced mechanism for verifying that stable spec IDs
  declared in `docs/specs/*.md` are referenced in the docstrings of implementing Python modules,
  and that no docstring reference points to a non-existent spec.
- A prose discipline mandating that spec sections capture observable *behavior contracts*
  (WHAT) and *rationale* (WHY), never implementation steps (HOW).
- An opt-in convention adopted by this repository and implemented as a pytest checker.

### What is Genuinely Distinctive About This Instantiation

Three things distinguish the claude-mpm SLD implementation from OFT and its peers — all modest,
none claiming novelty of the underlying idea:

1. **Docstring as the annotation site.** OFT, StrictDoc, and Doorstop all place traceability
   tags in code *comments*. SLD places the reference in the Python *docstring* — a first-class
   language object visible to `help()`, Sphinx autodoc, and IDE hover tooltips. This is
   Python-idiomatic; no existing tool has standardized this approach.

2. **Zero runtime dependencies.** The checker (`tests/test_spec_traceability.py`) uses only
   `re`, `pathlib`, and `ast` from the Python standard library. OFT requires a Java 17 runtime.
   StrictDoc requires its own installation. The pytest-based approach adds zero new tooling.

3. **Explicit WHAT/WHY/HOW prose rule.** OFT, Doorstop, and StrictDoc enforce mechanical
   link-completeness but say nothing about prose content. SLD mandates a structure: spec sections
   capture observable contracts (WHAT) and rationale (WHY); implementation steps (HOW) belong
   only in inline code comments. This documentation discipline has no direct equivalent in the
   traceability tooling ecosystem.

---

## 2. Lineage: OFT, RTM, and Decades of Prior Art

**SLD is not original.** The core idea — assigning stable IDs to specification sections,
annotating source code with those IDs, and running a CI tool that verifies bidirectional
completeness — is the exact feature set of **OpenFastTrace (OFT)**, which has been publicly
available and used in production since at least 2017-2018.

### Requirements Traceability Matrix (RTM)

The RTM discipline dates to the 1970s and is mandated today in regulated industries under
DO-178C (aviation), ISO 26262 (automotive), IEC 62304 (medical devices), and ASPICE.
Every requirement must link to design, source code, and tests; every code element must trace
back to a requirement. What SLD adds — embedding links in source files rather than a separate
spreadsheet — is the Git-native evolution of this discipline, first systematized in the 2010s
by tools like Doorstop (2014), StrictDoc (2019), and OFT.

### OpenFastTrace (OFT)

**Repository:** https://github.com/itsallcode/openfasttrace  
**License:** GPL-3.0

OFT is an open-source requirement tracing suite (Java runtime, language-agnostic) that
enforces bidirectional traceability between Markdown specification documents and source code.
Its status model (COVERED, UNCOVERED, ORPHANED, OUTDATED) is the direct inspiration for SLD's
four-status model (section 7). SLD adopts OFT's convention and status vocabulary; it does not
adopt the Java binary, the comment-tag syntax `[impl->req~name~1]`, or the Gradle/Maven build
integration.

The key difference: OFT tags go in code *comments*; SLD tags go in *docstrings*. This is the
deliberate Python-idiomatic adaptation.

### Other Prior Art

| Tool | What it does | Why SLD differs |
|------|-------------|-----------------|
| **Doorstop** | YAML requirement files with `ref` fields | No bidirectional completeness enforcement; code is passive |
| **StrictDoc** | `.sdoc` format with `@relation` markers in comments | Heavier tooling; comment-based, not docstring-based |
| **Sphinx-Needs** | RST `need` objects with traceability matrices | No native source-code scanner |
| **ReqToCode** | Compile-time verifiable traceability objects | Over-engineered; not widely adopted |
| **IBM DOORS / Polarion** | Enterprise commercial RTM tooling | License-gated; not applicable to OSS |

SLD is a lightweight implementation of the same bidirectional traceability discipline that all
of these tools embody, adapted for a Python-first, zero-dependency context.

---

## 3. Why Revive This Discipline Now — and the False-Confidence Risk

### The Historical Failure Mode

Bidirectional spec-to-code traceability is a well-understood practice. It is not widely
adopted outside regulated industries for one reason: **manual maintenance cost**. A 2023
peer-reviewed study (Springer, n=55 practitioners) found that 80% of practitioners identify
cost as the primary barrier to traceability. Agile velocity and RTM maintenance are structurally
incompatible: traces go stale within weeks as code and requirements diverge, and stale links
are worse than missing links — they create false confidence that a requirement is covered.

### The AI-Agent Rationale

AI coding agents (Claude Code, Cursor, Copilot Workspace) change this cost equation in a
specific way. When an agent modifies a function, it can update the spec ID reference in the
docstring *as part of the same action* — atomically, in the same diff, reviewed in the same
PR. The maintenance cost that caused traceability to fail ("nobody has time to update the
link") is absorbed into the agent's normal code-authoring workflow.

This is the rationale for reviving a historically-abandoned discipline in a non-regulated
project. Research literature through 2025-2026 has explored AI-assisted *traceability link
recovery* (reconstructing broken links after the fact) but not yet *agent-integrated authoring*
(atomic spec+docstring+code update as a single agent action). SLD is an attempt to make the
latter the default workflow.

### The False-Confidence Risk — Read This Section

**The CI check is a necessary condition, not a sufficient condition.**

The `tests/test_spec_traceability.py` checker proves:

- A string matching a declared spec ID appears in a docstring in `src/claude_mpm/`.
- A spec section with that ID exists in `docs/specs/*.md`.

**The checker does NOT prove:**

- The function actually implements the behavior described by the spec section.
- The docstring text accurately describes what the function does.
- The link is semantically meaningful and not accidentally copied from another function.

LLMs fabricate citations. TraceLLM, the most sophisticated LLM-based traceability system
currently published (Springer Nature, 2026), achieves precision of approximately 0.52 in
zero-shot settings — roughly half of AI-generated trace links are incorrect. An agent under
time pressure or with degraded context-window attention may write `References: SPEC-HOOKS-01`
under the wrong function. The CI check will pass. The trace will look correct. The coverage
is a lie.

**Mitigations built into SLD:**

1. **Descriptive IDs.** Spec IDs encode subsystem and sequence (e.g., `SPEC-HOOKS-01~1`)
   rather than opaque integers, making a semantically wrong cross-reference obviously
   suspicious on inspection.

2. **PR review checklist.** Every PR that changes code covered by a spec must include a
   human verification step: "Verify that spec references in changed docstrings point to the
   correct spec sections." See [section 10](#10-pr-review-checklist).

3. **Explicit documentation of limits.** This section. The CI check is a floor, not a ceiling.
   It catches missing links and broken links; it does not catch wrong links.

**Consequence:** Treat a passing traceability check as a signal that the codebase is maintaining
the form of the convention, not as proof that the codebase correctly implements its specs.
Semantic correctness is a human responsibility, aided by the structure the convention provides.

---

## 4. Spec ID Grammar

Every governed spec section has a stable ID with the following grammar:

```
SPEC-{SUBSYSTEM}-{NN}~{rev}
```

Components:

| Component | Format | Example | Notes |
|-----------|--------|---------|-------|
| `SPEC` | Literal prefix | `SPEC` | Always uppercase |
| `{SUBSYSTEM}` | Uppercase alpha, hyphens allowed | `HOOKS`, `AGENTS`, `SESSION` | Matches the spec file name |
| `{NN}` | Two-digit zero-padded integer | `01`, `12` | Sequential within subsystem |
| `~{rev}` | Tilde followed by integer | `~1`, `~3` | Increments when behavior contract changes materially |

**Full example:** `SPEC-HOOKS-01~1`

### When to Increment `~{rev}`

The revision integer increments when the **behavior contract** (inputs, outputs, preconditions,
postconditions, or error conditions) changes materially. Incrementing the revision enables
OUTDATED detection: a docstring that references `SPEC-HOOKS-01~1` when the current spec
revision is `SPEC-HOOKS-01~2` is flagged as OUTDATED and fails CI.

Do NOT increment the revision for:

- Clarifying prose that does not change the contract.
- Fixing typos or improving wording without altering behavior.
- Adding links to implementing modules.

### Subsystem Allowlist

Only files matching the pattern `docs/specs/{subsystem}.md` (directly in `docs/specs/`,
not in subdirectories) are scanned for declared spec IDs. The research directory
(`docs/specs/research/`) is explicitly excluded. This file (`docs/specs/README.md`) is also
excluded because it contains example IDs in prose that are not declarations. The authoring
guide (`docs/specs/AUTHORING.md`) is excluded for the same reason — it contains example IDs
in its templates and filled mini-example, which are illustrative, not declarations.

**Declaration rule:** A spec ID is considered *declared* only when it appears in a section
heading in the form `## ... {#SPEC-...}` (a Markdown heading with a named anchor), or as the
value of a bold `**ID:**` field immediately below such a heading. IDs that appear in prose,
tables, or code blocks elsewhere in the document (including this README) are not declarations.

---

## 5. Spec Section Structure

Each subsystem spec file lives at `docs/specs/{subsystem}.md`. Each governed section follows
this template exactly:

```markdown
## {Section Title} {#SPEC-{SUBSYSTEM}-{NN}~{rev}}

**ID:** SPEC-{SUBSYSTEM}-{NN}~{rev}
**Status:** Active | Draft | Superseded
**Supersedes:** SPEC-{SUBSYSTEM}-{NN}~{prev_rev} (if applicable)

### Behavior Contract (WHAT)

*Observable behavior from the caller's perspective. No implementation steps.*

- **Inputs:** ...
- **Outputs:** ...
- **Preconditions:** ...
- **Postconditions:** ...
- **Error conditions:** ...

### Rationale (WHY)

*Design decisions and constraints that shaped this contract. Not steps.*

- Why this approach over alternatives...
- Key constraints driving the design...
- Performance targets or resource bounds, if any...

### Implementing Modules

| Module | Role |
|--------|------|
| `claude_mpm.{module}` | ... |
```

### Content Rules

**Spec sections capture WHAT and WHY — never HOW.**

- **WHAT** (Behavior Contract): Observable behavior as seen from outside the subsystem.
  Inputs, outputs, preconditions, postconditions, error conditions. Written from the caller's
  perspective. Active voice: "Accepts...", "Returns...", "Raises...".

- **WHY** (Rationale): Design decisions and constraints. Explains *why this contract* over
  alternatives. Does NOT describe algorithm steps. "Centralizes routing so that individual
  handlers remain testable" is WHY. "First reads the JSON, then routes by type" is HOW.

- **HOW** belongs exclusively in inline code comments (`#`) within the function body.
  It never appears in spec files or docstrings.

The Rationale subsection is mandatory. A spec section without a WHY is incomplete regardless
of how thorough the Behavior Contract is.

---

## 6. Docstring References Format

Every Python module whose behavior is governed by one or more spec sections carries a
`References` block in its **module-level docstring**:

```python
"""
{Module name} — {one-line summary}.

WHAT: {Two to four sentences describing observable behavior — what callers
can rely on, what inputs are accepted, what outputs are produced.}

WHY: {One to three sentences explaining why this module exists and why it
is designed this way — constraints, performance targets, architectural
decisions.}

References
----------
SPEC-HOOKS-01~1 : docs/specs/hooks.md#SPEC-HOOKS-01~1
SPEC-HOOKS-02~1 : docs/specs/hooks.md#SPEC-HOOKS-02~1
"""
```

### References Line Format

Each reference line must match the pattern:

```
SPEC-{SUBSYSTEM}-{NN}~{rev}[ : {optional human-readable path or URL}]
```

The checker uses the regex `SPEC-[A-Z]+-\d+~\d+` to extract IDs. The optional path after
the colon is for human readers only; the checker ignores it.

### Function and Class Docstrings

Individual functions or classes that implement a *specific* spec section distinct from the
module-level spec may add a `:spec:` field:

```python
def dispatch_hook(event: dict) -> dict:
    """
    Route a hook event to its handler and return the response.

    WHAT: Accepts a parsed hook event dict, identifies the handler by event
    type, and returns the handler's structured response dict.

    WHY: Centralizes routing logic so individual handlers remain testable
    in isolation without depending on the full dispatch infrastructure.

    :spec: SPEC-HOOKS-02~1
    """
```

The `:spec:` field is scanned by the checker using the same regex pattern.

### WHAT/WHY Prose Rules

- **WHAT** uses active voice from the caller's perspective.
- **WHY** explains constraints and design decisions, not implementation steps.
- **HOW** (how the function achieves its result) belongs in inline comments, not docstrings.
- No docstring should say "First we do X, then Y" — that is HOW.
- No docstring should replicate implementation detail visible from reading the code.

---

## 6a. Code-Level Granularity: The WWL Model

The **WWL (WHAT/WHY/LINK) Granularity Model** defines exactly which code units require explicit spec linkage in their docstrings. Not every line of code needs a link — that would create excessive maintenance burden — but every significant function should be traceable.

### WHAT, WHY, LINK: The Three Parts

Every governed code unit carries three elements in its docstring:

- **WHAT:** One line describing observable behavior from the caller's perspective. No implementation steps.
- **WHY:** Rationale for why this unit is designed this way. No implementation steps.
- **LINK:** The governing `SPEC-{SUBSYSTEM}-{NN}~{rev}` ID, or `LINK: none` to flag a backfill gap.

### Granularity Thresholds

A function, class, or method **requires its own WHAT/WHY/LINK** when **either**:

- **Lines of code > 50** (configurable; based on cognitive load research and linter consensus)
- **Cyclomatic complexity > 10** (configurable; NIST SP 500-235 threshold for structured testing)

Units below both thresholds may omit WHAT/WHY/LINK and use simple one-line docstrings instead.

### Configurable Thresholds

Thresholds are **project-configurable** via `.claude-mpm/configuration.yaml`:

```yaml
workflow:
  spec_linked_docs:
    enabled: true
    wwl:
      file_level_required: true          # module-level WHAT/WHY always required
      function_line_threshold: 50        # functions > 50 LOC require WWL
      complexity_threshold: 10           # functions > CC 10 require WWL
      enforcement: baseline              # off | baseline | strict
```

- **`off`:** No enforcement; WWL is optional.
- **`baseline`:** Enforce only on new/modified code; tolerate existing code until touched.
- **`strict`:** Enforce on all code regardless of age (appropriate after backfill complete).

### Thresholds Are Evidence-Based

- **50 LOC threshold:** Aligns with Google Python Style Guide ("avoid functions > 40 lines"), Pylint defaults (max-function-body-length = 50), and cognitive load research on working memory limits.
- **CC = 10 threshold:** NIST SP 500-235 ("Structured Testing") mandates CC ≤ 10 for code requiring comprehensive path testing. Also McCabe's original recommendation (1976) and SonarQube baseline.

### Backfill Gaps

During backfill of existing codebases, code may exist without spec coverage. Use `LINK: none` to flag:

```python
def legacy_function():
    """Legacy function — backfill phase.
    
    WHAT: Accepts input, produces output.
    WHY: Spec coverage planned in future phase.
    LINK: none  # TODO: Add SPEC-ID when spec complete
    """
```

The `LINK: none` annotation marks the gap as **intentional**, not forgotten.

For full details, see **[WWL Granularity Model](../src/claude_mpm/skills/bundled/universal/spec-linked-docs/reference/wwl-granularity.md)**.

---

## 7. The Four-Status Model

SLD adopts the four-status model from OpenFastTrace. The CI checker assigns each ID one of
these statuses:

| Status | Meaning | CI result |
|--------|---------|-----------|
| **COVERED** | A spec ID declared in `docs/specs/*.md` has at least one matching docstring reference in `src/claude_mpm/`, and the revisions match. | Pass |
| **UNCOVERED** | A spec ID is declared in `docs/specs/*.md` but has no matching docstring reference anywhere in `src/claude_mpm/`. | Fail |
| **ORPHANED** | A spec ID appears in a docstring in `src/claude_mpm/` but has no matching declaration in `docs/specs/*.md`. | Fail |
| **OUTDATED** | A spec ID in a docstring has a revision number that does not match the current revision in the spec file (e.g., docstring says `~1`, spec now says `~2`). | Fail |

**UNCOVERED** means a spec section has been written but no implementing module has claimed it.
**ORPHANED** means code claims a spec that does not exist.
**OUTDATED** means the code was written against an old revision of the spec and has not been
updated to acknowledge the contract change.

COVERED is the only passing status; all other statuses cause `pytest` to fail.

**Configurability of UNCOVERED:** In the current implementation, UNCOVERED specs cause a
test failure. Because no subsystem specs exist yet (this is a bootstrapping phase), the checker
passes trivially when both sets are empty. As specs are added, any spec section without an
implementing module reference will fail CI — which is the intended behavior.

---

## 8. The Checker: What It Proves and What It Does Not

The checker in `tests/test_spec_traceability.py` is a necessary condition for traceability
health, not a sufficient one. This distinction is not a caveat to be minimized — it is
structurally important.

### What Passes the Checker

- Every `SPEC-*~*` ID found in docstrings under `src/claude_mpm/` resolves to a declared
  spec ID in `docs/specs/*.md` (no ORPHANED IDs).
- Every declared spec ID has at least one docstring reference (no UNCOVERED IDs).
- Every docstring reference uses the same revision as the current spec declaration (no
  OUTDATED IDs).

### What the Checker Cannot Detect

- Whether the linked function actually implements the behavior described in the spec.
- Whether the docstring's WHAT description accurately reflects the function's observable
  behavior.
- Whether the link was accidentally copied from another function without being updated.
- Whether the spec section itself accurately describes the system's intended behavior.

The checker verifies *syntactic completeness* of the traceability graph, not *semantic
correctness* of the links. Human review remains the only mechanism for the latter.

---

## 9. Opt-In Statement

SLD is an opt-in convention. The claude-mpm repository adopts it. Other repositories and
projects are not bound by this convention and need not adopt it.

Within claude-mpm, SLD governs subsystems for which a spec section has been written in
`docs/specs/{subsystem}.md`. Modules that implement behavior not yet covered by any spec
section are not required to carry `References` blocks; they will not appear in the
checker's UNCOVERED set because the spec has not been declared.

SLD is intended as a Python reference implementation of a language-agnostic convention.
The underlying discipline (stable spec IDs, docstring references, four-status CI check) is
directly portable to TypeScript, Go, Rust, or any language with module-level documentation
strings. The specific `References` block format and `:spec:` field are Python conventions;
other languages would use their idiomatic equivalents.

---

## 9a. Backfilling Existing Codebases

When SLD is first enabled on a project with existing code, **backfill** is the process of retroactively bringing subsystems into SLD compliance. It is a **five-phase progression** that keeps CI passing and maintains traceability throughout:

1. **Phase 0 (Baseline):** Record current state; prioritize subsystems.
2. **Phase 1 (Spec):** Documentation agent authors subsystem spec in `docs/specs/{subsystem}.md`.
3. **Phase 2 (Annotate):** Engineer agent adds WHAT/WHY/LINK to code docstrings.
4. **Phase 3 (Verify):** Human reviewer confirms semantic correctness; baseline recorded; spec marked Active.
5. **Phase 4 (Enforce):** CI enforces WWL on new code; full SLD discipline active for this subsystem.

### Prioritization

Backfill **highest-impact subsystems first**:

- **Tier 1:** High churn, high complexity, central to system → backfill immediately.
- **Tier 2:** Medium churn, public API → backfill next.
- **Tier 3:** Low churn, internal utilities → backfill last or defer.

### CRITICAL: False-Confidence Risk in Backfill

**The CI check validates that links are present, not that they are correct.** LLM-generated trace links have ~52% precision (TraceLLM, 2026, Springer Nature). An engineer or AI agent may write `LINK: SPEC-HOOKS-01` under the wrong function; the CI check passes; downstream reviewers see what appears to be coverage but is a false link.

**Mandatory mitigation during Phase 2 (Annotation):**

1. **Engineer reads the code and spec.** Engineer personally verifies that the function's observable behavior matches the spec's Behavior Contract section.
2. **Engineer does not copy-paste links.** Do not assume a spec link from another function applies here.
3. **Engineer flags ambiguity.** If a function could match multiple specs, flag the choice in the PR description.

**Mandatory mitigation during Phase 3 (Verification):**

1. **Human reviewer checks semantic correctness.** Confirm WHAT/WHY prose matches actual code behavior (read the code).
2. **Human reviewer confirms correct linkage.** Confirm LINK points to the correct spec section (read the spec).
3. **Human reviewer approves the PR.** Only after these checks; do not assume CI passing means links are correct.

### Example: Backfilling the Hooks Subsystem

**Phase 1:** Documentation agent creates `docs/specs/hooks.md` with `SPEC-HOOKS-01~1`, `SPEC-HOOKS-02~1`, etc.

**Phase 2:** Engineer agent reads `hooks.py` and `docs/specs/hooks.md`, adds:

```python
"""Hook event dispatcher — routes events to handlers.

WHAT: Accepts event dict, routes to handler, returns response dict.
WHY: Centralizes routing so handlers are independently testable.

References
----------
SPEC-HOOKS-01~1 : docs/specs/hooks.md#SPEC-HOOKS-01
"""
```

**Phase 3:** Human reviewer checks code and spec; confirms WHAT matches code behavior; confirms SPEC-ID is correct. Updates `docs/specs/hooks.md` Implementing Modules table with `claude_mpm.hooks`. Marks spec as `Active`.

**Phase 4:** CI enforces: new patches to hooks.py must maintain WHAT/WHY/LINK.

For full details, see **[Backfill Workflow](../src/claude_mpm/skills/bundled/universal/spec-linked-docs/reference/backfill-workflow.md)**.

---

## 9b. Draft Specs / Incremental Backfill

When multiple subsystem specs are authored in parallel — before their implementing code is
backfilled — the CI UNCOVERED check would otherwise block every PR that adds a new spec
section.  The **draft-status exemption** allows spec text to be committed and reviewed
without failing CI.

### Marker Syntax

Place a `**Status:** draft` line immediately below the heading anchor in the spec section
body (anywhere within the section, before the next heading):

```markdown
## Hook Dispatch Subsystem {#SPEC-HOOKS-01~1}

**Status:** draft (pending backfill)

### Behavior Contract (WHAT)

...
```

The canonical form is `**Status:** draft (pending backfill)`.  Any text after `draft` is
ignored by the checker; only the word `draft` (case-insensitive) matters.

### What the Exemption Covers — and Does Not Cover

| Check | Draft exempt? |
|-------|--------------|
| **UNCOVERED** (no code ref to this spec ID) | Yes — draft sections may have no code refs |
| **ORPHANED** (code refs a non-existent spec ID) | No — always enforced |
| **OUTDATED** (code refs wrong revision of spec ID) | No — always enforced |

A section is draft-exempt for UNCOVERED only.  If any code already references the draft
spec ID, the revision in that reference must still match exactly; a stale revision is
flagged OUTDATED just as for active sections.

### Lifecycle

1. **Author** adds the spec section with `**Status:** draft (pending backfill)`.
   CI stays green — no UNCOVERED failure.
2. **Engineer** backfills `References` blocks in the implementing module docstrings.
3. **Reviewer** confirms semantic correctness (spec matches code behavior).
4. **Author** removes the `draft` marker (change to `**Status:** active` or delete the
   line).  Normal UNCOVERED enforcement immediately applies — if the backfill missed any
   reference, CI will catch it on the next run.

---

## 10. PR Review Checklist

Every pull request that modifies code in a module governed by an existing spec section must
include the following human verification step, in addition to the automated CI check:

```
[ ] Spec linkage verified: All References blocks in changed docstrings point to
    the correct spec sections. The CI check passes but I have confirmed that the
    links are semantically accurate, not just syntactically present.
[ ] Spec updated if behavior changed: If this PR changes the observable behavior
    of a governed subsystem, the relevant spec section has been updated and its
    ~{rev} has been incremented.
[ ] New subsystem spec drafted if applicable: If this PR introduces a new subsystem
    with no existing spec, a Draft spec section has been added to docs/specs/.
```

The third checklist item reinforces the spec-first discipline: specs should precede or
accompany implementing code in the same PR, not be added retroactively.

---

## 11. Enabling SLD in claude-mpm

SLD is enabled per-project via a single toggle in the project's
`.claude-mpm/configuration.yaml` file:

```yaml
workflow:
  spec_linked_docs:
    enabled: true   # opt-in: when true, engineer + documentation agents
                    # build SLD specs + traceability alongside code.
                    # Default: false (backward compatible)
```

**What the toggle does:**

When `enabled: true`, `AgentTemplateBuilder.build_agent_markdown()` appends
the SLD instruction block to assembled agent prompts at deploy/assembly time.
The wiring calls `get_sld_instruction_for_agent(agent_type, config)` in
`src/claude_mpm/services/agents/deployment/agent_template_builder.py`.

Agent types that **receive** the SLD block:
- `engineer` — covers all engineer-category agents (the `agent_type` frontmatter
  field is the category, not the slug; e.g. `rust-engineer.md` declares
  `agent_type: engineer`).
- `documentation` — covers all documentation-category agents.

Agent types that do **not** receive the SLD block:
- `ops`, `qa`, `research`, `security`, and any other type not in the target set.

The classifier `is_sld_target_agent_type()` in `sld_config.py` uses exact
category matching (the common case) plus a defensive suffix rule for
hypothetical hyphenated `agent_type` values such as `"python-engineer"`.

The block explains the References docstring format, the spec file structure,
and how to run the CI check.  When the flag is off or the agent type is not
in the target set, `get_sld_instruction_for_agent` returns `""`, making it
safe to concatenate unconditionally.

**When the effect takes place:**

The SLD block is injected whenever agents are **(re)deployed or assembled**,
i.e. whenever `build_agent_markdown()` is called — typically on startup or
when `claude-mpm deploy` is run.  Changes to the flag take effect after the
next deploy cycle; running agents are not patched in-place.

**Absence of the key = disabled.**  Any project without this key behaves
identically to before this feature was added.  No migration is required.

**To enable on a project:**

1. Open (or create) `.claude-mpm/configuration.yaml` in the project root.
2. Add the `workflow.spec_linked_docs.enabled: true` key shown above.
3. Run `claude-mpm deploy` (or restart the MPM session) to redeploy agents.

**To verify the wiring end-to-end:**

```bash
uv run pytest tests/test_sld_config.py tests/test_sld_integration.py -p no:xdist -v
```

All tests should pass.  The integration tests in `test_sld_integration.py`
call `build_agent_markdown()` directly with the real builder and confirm that:

- Engineer and documentation agents contain the SLD block when flag is ON.
- Ops, QA, and research agents do NOT contain the block even when flag is ON.
- No agent receives the block when flag is OFF or config is None.

---

## 12. Citations

**OpenFastTrace (primary lineage):**
- Repository: https://github.com/itsallcode/openfasttrace
- PyPI wrapper: https://pypi.org/project/oft-trace/
- License: GPL-3.0

**Requirements Traceability Matrix (RTM) discipline:**
- DO-178C RTM overview: https://rtmify.io/standards/do-178c
- ISO 26262 requirements traceability: https://www.parasoft.com/learning-center/iso-26262/requirements-traceability/
- "Why don't we trace? Barriers to software traceability in practice" (Springer, 2023):
  https://link.springer.com/article/10.1007/s00766-023-00408-9

**Doorstop:**
- Repository: https://github.com/doorstop-dev/doorstop
- Paper: https://www.researchgate.net/publication/276044183_Doorstop_Text-Based_Requirements_Management_Using_Version_Control

**StrictDoc:**
- Repository: https://github.com/strictdoc-project/strictdoc
- Documentation: https://strictdoc.readthedocs.io/

**AI traceability research (false-confidence risk):**
- TraceLLM (Springer Nature, 2026): https://link.springer.com/article/10.1007/s00766-026-00460-1
- TraceLLM preprint (arXiv:2602.01253): https://arxiv.org/html/2602.01253v1
- TRAIL: Automatic traceability maintenance via ML (arXiv:1807.06684): https://arxiv.org/pdf/1807.06684
- ReqToCode (arXiv:2603.13999): https://arxiv.org/html/2603.13999

**Complementary documentation frameworks (context, not lineage):**
- arc42: https://arc42.org/
- Diataxis: https://diataxis.fr/
- Docs-as-Code: https://www.writethedocs.org/guide/docs-as-code/

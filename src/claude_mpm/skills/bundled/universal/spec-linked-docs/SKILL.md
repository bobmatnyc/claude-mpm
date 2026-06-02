---
name: spec-linked-docs
description: "Spec-Linked Documentation (SLD): Language-agnostic discipline for maintaining bidirectional traceability between functional specifications and source-code docstrings via stable identifiers and CI validation. Optional/opt-in adoption. Builds on OpenFastTrace and DO-178C Requirements Traceability Matrix traditions."
agent_types: [engineer, documentation]
tags: [specification, traceability, documentation, requirements, best-practices, language-agnostic]
effort: high
progressive_disclosure:
  entry_point:
    summary: "Maintain synchronized specification-to-code traceability using stable identifiers and automated CI checks. Eliminates manual RTM burden by leveraging AI coding agents as atomic link maintainers."
    when_to_use: "When a project adopts SLD discipline (opt-in): engineer agents write code with spec IDs in docstrings; documentation agents maintain spec sections and Implementing Modules tables; CI validates bidirectional completeness."
    quick_start: "1. Understand the convention (spec sections, stable IDs, docstring References) 2. Review prior art lineage (OpenFastTrace, RTM, DO-178C) 3. Configure CI traceability check 4. Add spec IDs to module docstrings 5. Run CI validation"
  references:
    - prior-art-lineage.md
    - convention-v1.md
    - language-examples.md
    - ci-validation.md
    - wwl-granularity.md
    - backfill-workflow.md
    - engineer-workflow.md
    - documentation-workflow.md
---

# Spec-Linked Documentation (SLD)

## Overview

**Spec-Linked Documentation (SLD)** is a language-agnostic documentation discipline for maintaining **bidirectional traceability** between functional specifications and source-code docstrings. It is an **optional, opt-in** convention that projects adopt when they prioritize live, verified specification-to-code linkage.

**Core premise:** The manual cost of maintaining Requirements Traceability Matrices (RTMs) historically blocked traceability adoption outside regulated industries (80% of practitioners cite cost as the barrier). AI coding agents now make link maintenance atomic and cost-free: when an agent writes or modifies code, it updates the spec ID reference in the docstring as the same action. This removes the friction that historically made RTMs unmaintainable in fast-moving teams.

**SLD is not novel.** It is a **Python-idiomatic, lightweight instantiation** of the bidirectional traceability discipline formalized in [OpenFastTrace](https://github.com/itsallcode/openfasttrace) and mandated by regulated industries (DO-178C aviation, ISO 26262 automotive, IEC 62304 medical). The genuine innovation here is **placing spec ID references in docstrings** (first-class language objects, visible to `help()`, IDEs, type checkers) rather than in comments, and **using zero-dependency pytest** rather than external tools.

---

## ⚠️ Critical Upfront Disclosures

### On Honesty About Prior Art

SLD is **not your team's invention.** The core idea — stable spec IDs, code annotations, CI bidirectional validation — dates to:

- **OpenFastTrace (OFT):** 2017–present; production-ready; implements the exact four-status model (COVERED / UNCOVERED / ORPHANED / OUTDATED)
- **Doorstop:** 2012–present; text-based RTM with Git storage
- **StrictDoc:** 2018–present; Python-native requirements management with traceability
- **Regulated industries:** DO-178C (aviation), ISO 26262 (automotive), IEC 62304 (medical) mandate bidirectional RTMs since the 1980s–1990s

**What is distinctive about this instantiation:**

1. **Docstring as the annotation site** — OFT, StrictDoc, and Doorstop all use code comments. SLD places the reference in Python docstrings (`References: SPEC-ID` in a NumpyDoc `References` section), making it visible to autodoc, IDEs, and type checkers.
2. **Zero new runtime dependencies** — CI check uses only `re`, `pathlib`, and `ast` (stdlib). OFT requires Java 17; StrictDoc requires its own installation.
3. **Explicit WHAT/WHY/HOW separation as a prose rule** — OFT et al. are mechanical enforcement tools; SLD adds a documentation discipline (specs = WHAT + WHY; code = HOW).

**You are not pioneering traceability. You are adapting a decades-old discipline to a modern Python workflow, with AI agents as the maintainers.** This is good engineering, not invention. Claim it honestly.

### On the False-Confidence Risk

The CI check **validates that links exist, not that they are correct.** Specifically:

- **What it checks:** The string `SPEC-HOOKS-01` appears in a docstring; a matching spec section exists in `docs/specs/hooks.md`.
- **What it does NOT check:** The function actually implements the requirement named in the spec section.

If an AI coding agent, under time pressure or in a degraded context window, writes `References: SPEC-HOOKS-01` under the wrong function (or copies a reference from another function without updating), the CI check passes. The link looks correct. The human reader later inspects the trace and sees coverage — but the coverage is a lie.

**Published research on LLM trace link generation (TraceLLM, 2026, Springer Nature):** Precision ~0.52 in zero-shot settings; ~0.61 F2-score with few-shot improvement. **Roughly half of AI-generated trace links are incorrect.**

**Mitigation (necessary, not sufficient):**

1. Pair the CI check with a **PR review checklist item:** "Verify that spec references in changed docstrings point to the correct spec sections." The check is syntactic; humans provide semantic verification.
2. Design spec IDs to be **semantically descriptive** (`SPEC-HOOKS-PRETOOLUSE-DISPATCH` is better than `SPEC-001`) so that an obviously wrong reference jumps out during review.
3. Treat SLD as a **first-level verification layer** (mechanical link presence), not a substitute for code review (semantic correctness).

**This risk exists. It is manageable. It must be disclosed to every engineer and documentation agent who uses this skill.**

---

## 1. The Convention (SLD v1)

### 1.1 Specification Files

**Location:** One spec file per subsystem at `docs/specs/{subsystem}.md`.

**Structure of each spec file:**

```markdown
# {Subsystem Name} Specification

**Status:** Active | Draft | Superseded
**Last reviewed:** YYYY-MM-DD
**Supersedes:** (link to previous spec if applicable)

## Overview

One paragraph: what this subsystem does, why it exists.

---

## {Section Title} {#SPEC-{SUBSYSTEM}-{NN}}

**ID:** SPEC-{SUBSYSTEM}-{NN}~v1
**Status:** Active

### Behavior Contract

*WHAT: Observable behavior from the caller's perspective.*

- **Inputs:** ...
- **Outputs:** ...
- **Preconditions:** ...
- **Postconditions:** ...
- **Error conditions:** ...

### Rationale

*WHY: Design decisions and constraints.*

- Why this approach over alternatives...
- Key constraints driving the design...
- Performance or architectural implications...

### Implementing Modules

| Module | Role |
|--------|------|
| `claude_mpm.{module}` | Brief role description |
| `claude_mpm.{another}` | Brief role description |
```

**Key rules:**

- **Every section has a stable `SPEC-{SUBSYSTEM}-{NN}` ID** declared on the first line of the section body.
- **ID format:** `SPEC-{SUBSYSTEM}-{NN}~v{revision}` where `revision` is an integer bumped when the behavior contract changes (enables OUTDATED detection). Example: `SPEC-HOOKS-01~v1`.
- **Markdown anchor:** Use named anchor syntax `{#SPEC-HOOKS-01}` on the section heading for link resolution.
- **Behavior Contract is mandatory:** Describes observable behavior (WHAT), never implementation steps (HOW).
- **Rationale is mandatory:** Explains WHY this design; never implementation details.
- **The HOW lives only in code:** Specs are contracts, not tutorials. Implementation belongs in docstrings and code comments.
- **Implementing Modules table is maintained manually** but validated by CI — if a module is added/removed, the table must be updated in the same PR.

### 1.2 Code Link Site: Docstring References

**Module-level docstring** (every module whose behavior is governed by a spec):

```python
"""
{Module name} — {one-line summary of what this module does}.

WHAT: {Two to four sentences describing the module's observable behavior
contract — what callers can rely on, what inputs it accepts, what outputs
it produces.}

WHY: {One to three sentences explaining why this module exists and why
it is designed the way it is — constraints, performance targets,
architectural decisions.}

References
----------
{SPEC-ID}~v1 : docs/specs/{subsystem}.md#{SPEC-ID}
{SPEC-ID}~v1 : docs/specs/{subsystem}.md#{SPEC-ID}
"""
```

**For individual functions/classes** that implement a *specific* spec section distinct from the module-level spec:

```python
def some_function():
    """
    Brief description of what this function does.

    WHAT: Accepts {inputs}, returns {outputs}, raises {exceptions}.

    WHY: {Rationale for this function's existence or design choice}.

    :spec: SPEC-{SUBSYSTEM}-{NN}~v1
    """
```

**Docstring rules:**

- Docstrings describe **WHAT the function/class does** (observable behavior) and **WHY it is designed this way** (rationale), never **HOW it works** (implementation steps).
- Implementation detail belongs in inline comments (`# reason for this approach`) within the function body.
- WHAT sections use active voice, caller's perspective: "Accepts...", "Returns...", "Raises...".
- WHY sections explain constraints, not steps: "Centralizes routing logic *so that*...", not "First we do X, then Y".
- The `References` section follows NumpyDoc convention and is parseable by CI tools and Sphinx autodoc.
- Include the **revision number** in the spec ID: `SPEC-HOOKS-01~v1`. If the spec section's behavior contract changes, the revision bumps (`~v2`), and code that still references `~v1` fails the OUTDATED check.

---

## 2. Per-Language Link Site Examples

Choose ONE tag convention and apply it consistently across your codebase. The convention below uses **NumpyDoc `References` section** for module-level specs and **Sphinx `:spec:` field** for function-level specs (language-neutral and compatible with Sphinx autodoc).

### Python

**Module-level docstring (NumpyDoc format):**

```python
"""Hook event dispatcher — routes pre/post-tool-use events to handlers.

WHAT: Accepts a hook event dict, routes to the registered handler for that
event type, collects the response, and returns a structured response dict.

WHY: Centralizes event routing so individual handlers remain independently
testable and stateless. The dispatcher enforces a uniform interface for all
handlers (init, call, cleanup).

References
----------
SPEC-HOOKS-01~v1 : docs/specs/hooks.md#SPEC-HOOKS-01
SPEC-HOOKS-02~v1 : docs/specs/hooks.md#SPEC-HOOKS-02
"""
```

**Function-level (Sphinx field list):**

```python
def dispatch_hook(event: dict, context: dict) -> dict:
    """
    Route a hook event to its registered handler and return the response.

    WHAT: Given an event dict with 'event_type' and 'payload' keys, looks up
    the handler, invokes it, collects the response dict, and returns it.

    WHY: Decouples event routing from handler logic, enabling independent
    testing of handlers and future middleware (e.g., filtering, caching).

    Parameters
    ----------
    event : dict
        Hook event with 'event_type' and 'payload' keys.
    context : dict
        Request context (session, user, trace ID, etc.).

    Returns
    -------
    dict
        Handler response dict with 'success', 'data', and optional 'error' keys.

    Raises
    ------
    KeyError
        If 'event_type' not found in handlers registry.
    TimeoutError
        If handler exceeds timeout.

    :spec: SPEC-HOOKS-02~v1
    """
```

### JavaScript/TypeScript

**Module-level (JSDoc `@spec` tag):**

```javascript
/**
 * Hook event dispatcher — routes pre/post-tool-use events to handlers.
 *
 * WHAT: Accepts a hook event object, routes to the registered handler for that
 * event type, collects the response, and returns a structured response object.
 *
 * WHY: Centralizes event routing so individual handlers remain independently
 * testable. The dispatcher enforces a uniform interface (initialize, handle, cleanup).
 *
 * @spec SPEC-HOOKS-01~v1 {@link https://github.com/bobmatnyc/claude-mpm/blob/main/docs/specs/hooks.md#SPEC-HOOKS-01}
 * @spec SPEC-HOOKS-02~v1 {@link https://github.com/bobmatnyc/claude-mpm/blob/main/docs/specs/hooks.md#SPEC-HOOKS-02}
 */
```

**Function-level (JSDoc):**

```javascript
/**
 * Route a hook event to its registered handler and return the response.
 *
 * WHAT: Given an event object with 'eventType' and 'payload' properties,
 * looks up the handler, invokes it, collects the response object, and returns it.
 *
 * WHY: Decouples event routing from handler logic, enabling independent testing
 * of handlers and future middleware (filtering, caching).
 *
 * @param {Object} event - Hook event with 'eventType' and 'payload' properties.
 * @param {Object} context - Request context (session, user, traceId, etc.).
 * @returns {Object} Handler response object with 'success', 'data', optional 'error'.
 * @throws {KeyError} If 'eventType' not found in handlers registry.
 * @throws {TimeoutError} If handler exceeds timeout.
 * @spec SPEC-HOOKS-02~v1 {@link https://github.com/bobmatnyc/claude-mpm/blob/main/docs/specs/hooks.md#SPEC-HOOKS-02}
 */
export function dispatchHook(event, context) { ... }
```

### Java

**Class-level (Javadoc):**

```java
/**
 * Hook event dispatcher — routes pre/post-tool-use events to handlers.
 *
 * WHAT: Accepts a hook event object, routes to the registered handler for that
 * event type, collects the response, and returns a structured response object.
 *
 * WHY: Centralizes event routing so individual handlers remain independently
 * testable. The dispatcher enforces a uniform interface (initialize, handle, cleanup).
 *
 * @see <a href="docs/specs/hooks.md#SPEC-HOOKS-01">SPEC-HOOKS-01~v1</a>
 * @see <a href="docs/specs/hooks.md#SPEC-HOOKS-02">SPEC-HOOKS-02~v1</a>
 */
public class HookEventDispatcher { ... }
```

**Method-level (Javadoc):**

```java
/**
 * Route a hook event to its registered handler and return the response.
 *
 * WHAT: Given an event object with 'eventType' and 'payload' properties,
 * looks up the handler, invokes it, collects the response object, and returns it.
 *
 * WHY: Decouples event routing from handler logic, enabling independent testing
 * of handlers and future middleware (filtering, caching).
 *
 * @param event Hook event with 'eventType' and 'payload' properties.
 * @param context Request context (session, user, traceId, etc.).
 * @return Handler response object with 'success', 'data', optional 'error'.
 * @throws KeyError If 'eventType' not found in handlers registry.
 * @throws TimeoutError If handler exceeds timeout.
 * @see <a href="docs/specs/hooks.md#SPEC-HOOKS-02">SPEC-HOOKS-02~v1</a>
 */
public Map<String, Object> dispatchHook(Map<String, Object> event, Map<String, Object> context) { ... }
```

### Go

**Package-level (doc comment, conventional Go style):**

```go
// Package hooks provides hook event dispatch and handler registration.
//
// WHAT: Accepts a hook event struct, routes to the registered handler for that
// event type, collects the response, and returns a structured response struct.
//
// WHY: Centralizes event routing so individual handlers remain independently
// testable. The dispatcher enforces a uniform interface (Initialize, Handle, Cleanup).
//
// Spec: SPEC-HOOKS-01~v1 (docs/specs/hooks.md#SPEC-HOOKS-01)
// Spec: SPEC-HOOKS-02~v1 (docs/specs/hooks.md#SPEC-HOOKS-02)
package hooks
```

**Function-level (doc comment):**

```go
// DispatchHook routes a hook event to its registered handler and returns the response.
//
// WHAT: Given a HookEvent struct with EventType and Payload fields,
// looks up the handler, invokes it, collects the response struct, and returns it.
//
// WHY: Decouples event routing from handler logic, enabling independent testing
// of handlers and future middleware (filtering, caching).
//
// Spec: SPEC-HOOKS-02~v1 (docs/specs/hooks.md#SPEC-HOOKS-02)
func DispatchHook(event HookEvent, context Context) (HookResponse, error) { ... }
```

### Rust

**Module-level (rustdoc):**

```rust
//! Hook event dispatcher — routes pre/post-tool-use events to handlers.
//!
//! WHAT: Accepts a hook event struct, routes to the registered handler for that
//! event type, collects the response, and returns a structured response struct.
//!
//! WHY: Centralizes event routing so individual handlers remain independently
//! testable. The dispatcher enforces a uniform interface (initialize, handle, cleanup).
//!
//! # Spec References
//!
//! - [`SPEC-HOOKS-01~v1`](https://github.com/bobmatnyc/claude-mpm/blob/main/docs/specs/hooks.md#SPEC-HOOKS-01)
//! - [`SPEC-HOOKS-02~v1`](https://github.com/bobmatnyc/claude-mpm/blob/main/docs/specs/hooks.md#SPEC-HOOKS-02)
```

**Function-level (rustdoc):**

```rust
/// Route a hook event to its registered handler and return the response.
///
/// WHAT: Given a HookEvent struct with event_type and payload fields,
/// looks up the handler, invokes it, collects the response struct, and returns it.
///
/// WHY: Decouples event routing from handler logic, enabling independent testing
/// of handlers and future middleware (filtering, caching).
///
/// # Spec References
///
/// - [`SPEC-HOOKS-02~v1`](https://github.com/bobmatnyc/claude-mpm/blob/main/docs/specs/hooks.md#SPEC-HOOKS-02)
pub fn dispatch_hook(event: HookEvent, context: Context) -> Result<HookResponse, Error> { ... }
```

---

## 3. CI Traceability Validation

### 3.1 The Four-Status Model

Borrowed from OpenFastTrace:

| Status | Meaning | CI Outcome |
|--------|---------|-----------|
| COVERED | Spec section has at least one module/function with a matching `:spec:` or `References` entry | ✅ Pass |
| UNCOVERED | Spec section ID appears in `docs/specs/` but is not referenced in any code docstring | ❌ FAIL |
| ORPHANED | A code docstring references a spec ID that does not exist in `docs/specs/` | ❌ FAIL |
| OUTDATED | A code docstring references `SPEC-ID~v1` but the spec section exists at `SPEC-ID~v2` (revision mismatch) | ❌ FAIL |

### 3.2 Zero-Dependency pytest Checker

**File: `tests/test_spec_traceability.py`**

```python
"""Validate bidirectional spec-to-code traceability.

WHY: Ensures every spec section is implemented (COVERED) and every code
reference points to a real spec (no ORPHANED or OUTDATED links).

WHAT: Scans docs/specs/*.md for SPEC-* IDs, scans src/*.py for :spec: fields
and References blocks, verifies bidirectional completeness, and reports status.
"""

import re
from pathlib import Path

SPEC_DIR = Path("docs/specs")
SRC_DIR = Path("src")
SPEC_PATTERN = re.compile(r"SPEC-[A-Z0-9]+-\d+(?:~v\d+)?")


def collect_spec_ids():
    """Extract all SPEC-* IDs from docs/specs/ files."""
    ids = {}
    for md in SPEC_DIR.rglob("*.md"):
        for match in SPEC_PATTERN.finditer(md.read_text()):
            spec_id = match.group()
            ids[spec_id] = ids.get(spec_id, []) + [str(md)]
    return ids


def collect_docstring_refs():
    """Extract all :spec: and References entries from source docstrings."""
    refs = {}
    for py in SRC_DIR.rglob("*.py"):
        for match in SPEC_PATTERN.finditer(py.read_text()):
            spec_id = match.group()
            refs[spec_id] = refs.get(spec_id, []) + [str(py)]
    return refs


def test_no_dangling_spec_refs():
    """All SPEC-* IDs in docstrings must exist in docs/specs/."""
    defined = collect_spec_ids()
    referenced = collect_docstring_refs()
    dangling = set(referenced.keys()) - set(defined.keys())
    assert not dangling, f"Dangling spec refs (ORPHANED): {dangling}"


def test_no_unimplemented_specs():
    """Every SPEC-* ID in docs/specs/ must be referenced in at least one module."""
    defined = collect_spec_ids()
    referenced = collect_docstring_refs()
    unimplemented = set(defined.keys()) - set(referenced.keys())
    assert not unimplemented, f"Unimplemented specs (UNCOVERED): {unimplemented}"


def test_spec_id_format():
    """All IDs must match SPEC-[A-Z0-9]+-[0-9]+~v[0-9]+ format."""
    defined = collect_spec_ids()
    malformed = [sid for sid in defined if not re.match(r"^SPEC-[A-Z0-9]+-\d+(?:~v\d+)?$", sid)]
    assert not malformed, f"Malformed spec IDs: {malformed}"


def test_no_revision_mismatches():
    """All code references must match the revision of the spec section."""
    # This check requires parsing revision numbers from both spec and code.
    # Implementation depends on your revision numbering scheme.
    # Placeholder: if using SPEC-ID~vN format, extract N and compare.
    pass
```

**Run in CI:**

```bash
pytest tests/test_spec_traceability.py -v
```

---

## 4. Engineer Workflow

**When implementing a feature covered by a spec:**

1. **Check `docs/specs/`** for the governing spec section before writing code.
2. **Write the module-level docstring WHAT/WHY block** before writing the function body (spec-first discipline).
3. **Add `References` block to module docstring** with the relevant SPEC-IDs (include revision: `SPEC-HOOKS-01~v1`).
4. **Add `:spec:` field to functions/classes** implementing a specific spec section distinct from the module-level spec.
5. **Update the "Implementing Modules" table in the spec** if a new module is added.
6. **Run `make test`** (or `pytest tests/test_spec_traceability.py`) to verify CI checks pass.
7. **PR description must confirm:** "Spec linkage is consistent and CI traceability checks pass."

**If no spec exists for a new subsystem:**

1. **Draft the spec section in `docs/specs/{subsystem}.md`** first.
2. **Assign a SPEC-ID** following the existing numbering pattern (e.g., next available number for the subsystem).
3. **Write code**, then confirm the spec accurately describes the implemented behavior before merging.
4. **Verify CI traceability check passes** before merge.

**PR Review Checklist (Critical):**

- [ ] All `:spec:` and `References` entries in changed docstrings point to **correct** spec sections (not just existing spec sections).
- [ ] If spec content changed, the revision number was bumped (e.g., `~v1` → `~v2`).
- [ ] If spec IDs were changed, all code references were updated.
- [ ] CI traceability check passes (no UNCOVERED, ORPHANED, or OUTDATED).

---

## 5. Documentation Agent Workflow

**When reviewing or authoring spec documents:**

1. **Verify structure:** Every spec section has a stable SPEC-ID, Behavior Contract subsection, and Rationale subsection.
2. **Verify Implementing Modules table is current** — cross-check against actual modules in source code.
3. **Verify content level:** Specs are at the behavioral contract level (WHAT + WHY), not implementation level (HOW).
4. **Flag stale sections:** Any spec section that has been Active for more than 90 days without a "Last reviewed" update.
5. **Update revision numbers carefully:** If a spec section's behavior contract changes, bump the revision (`~v1` → `~v2`). Code references to `~v1` will trigger OUTDATED checks.
6. **Apply Diataxis framework:** Spec files are in the Explanation + Reference quadrants; do not add Tutorial or How-to content.

---

## 6. When NOT to Use SLD

- **Projects that have not explicitly adopted the discipline.** SLD is opt-in; do not impose it on a team without consent.
- **Rapid prototyping or spike work.** Spec linkage overhead is not justified for throwaway code.
- **Small, single-file scripts or utilities.** The cost of maintaining a spec is higher than the value for one-off tools.
- **Existing legacy codebases without specs.** Retrofitting specs onto mature code is expensive and often not justified. SLD works best for *greenfield* subsystems where specs precede code.

---

## 7. Troubleshooting

### "CI says UNCOVERED: SPEC-HOOKS-01 has no references"

**Cause:** A spec section ID exists but no function/module references it.

**Fix:**
1. Check if the spec section is actually implemented in code.
2. If yes, add a `:spec:` or `References` entry to the implementing function/module docstring.
3. Re-run CI.

If the spec is not yet implemented, mark it as `Status: Draft` in the spec file or delete it.

### "CI says ORPHANED: SPEC-HOOKS-01 referenced in code but not found in specs/"

**Cause:** A code docstring references a spec ID that does not exist in `docs/specs/`.

**Fix:**
1. Check for typos in the `:spec:` field or `References` block.
2. Verify the spec file exists and the ID is formatted correctly.
3. If the spec was renamed/deleted, update code references or create the missing spec.

### "CI says OUTDATED: code references SPEC-HOOKS-01~v1 but spec is at ~v2"

**Cause:** A spec section was revised (behavior contract changed), but code was not updated.

**Fix:**
1. Review the spec section change (read the "Rationale" to understand what changed).
2. Update the code reference in the docstring to the new revision: `SPEC-HOOKS-01~v2`.
3. If the code does NOT match the new spec behavior, do one of:
   - Modify code to match the new spec.
   - Revert the spec change and re-bump the revision.
   - Create a NEW spec section for the old behavior (if it still exists elsewhere).

---

## 8. Code-Level Granularity: The WWL Model

**See:** [wwl-granularity.md](./reference/wwl-granularity.md)

Not every function needs a spec link — that would create excessive maintenance burden. The **WWL (WHAT/WHY/LINK) Granularity Model** defines **when** code units require explicit linkage:

- **Module-level WHAT/WHY/References:** Always required for governed subsystems.
- **Function/Class/Method level:** Required when **either** lines of code > 50 (configurable) **or** cyclomatic complexity > 10 (NIST SP 500-235 threshold).
- **Below thresholds:** Optional; simple helpers and getters may omit WWL.

The thresholds are **configurable per-project** and tied to **published industry standards** (McCabe 1976, NIST SP 500-235, linter defaults).

### Backfill Gaps

During **backfill of existing codebases**, code units may exist without spec coverage. Use `LINK: none` to flag these gaps:

```python
def legacy_handler(event: dict) -> dict:
    """Legacy handler — backfill phase.
    
    WHAT: Accepts event dict, routes by type.
    WHY: Pre-SLD code; spec planned in next phase.
    LINK: none  # TODO: Add SPEC-ID when spec is ready
    """
```

The `LINK: none` annotation signals to CI and reviewers that this gap is **intentional and tracked**, not accidental.

---

## 9. Backfilling Existing Codebases

**See:** [backfill-workflow.md](./reference/backfill-workflow.md)

SLD adoption on existing projects requires a **five-phase backfill workflow** that keeps CI passing and maintains traceability throughout:

1. **Phase 0 (Baseline):** Record current state; prioritize subsystems for backfill.
2. **Phase 1 (Spec Authoring):** Documentation agent writes subsystem spec in `docs/specs/{subsystem}.md`.
3. **Phase 2 (Annotation):** Engineer agent annotates code with WHAT/WHY/LINK docstrings.
4. **Phase 3 (Verification):** Human reviewer verifies semantic correctness; baseline is recorded.
5. **Phase 4 (Enforcement):** CI enforces WWL on new code; full SLD discipline is active.

### Prioritization

Backfill **highest-churn / highest-complexity / most-central** modules first:

- **Tier 1:** High churn, high complexity, central to system (hooks, agents, services).
- **Tier 2:** Medium churn, public API (CLI, migrations).
- **Tier 3:** Low churn, internal utilities (leaf modules).

### False-Confidence Mitigation

**CRITICAL:** The CI check validates **presence** of links, not **correctness**. LLM-generated trace links have ~52% precision (TraceLLM, 2026). **Mitigation:**

1. **Engineer responsibility:** During Phase 2, engineer reads code and spec; personally verifies links are semantically correct (not copied from another function).
2. **Reviewer responsibility:** During Phase 3, human reviewer confirms WHAT/WHY prose matches actual behavior and LINK points to correct spec.
3. **PR checklist:** Every PR changing governed code must include semantic verification step (in addition to passing CI).

**Treat CI as a floor, not a ceiling.** The check catches missing and malformed links; human review catches wrong links.

---

## 10. Next Steps

1. **Understand the prior art:** Read `prior-art-lineage.md` to learn about OpenFastTrace, RTM, and the decades of traceability practice you are building on.
2. **Learn the convention in detail:** Read `convention-v1.md` for the complete specification format and docstring rules.
3. **Master code-level granularity:** Read `wwl-granularity.md` to understand when code units require WHAT/WHY/LINK annotations, thresholds, and per-language syntax.
4. **Plan your backfill:** Read `backfill-workflow.md` to understand the five-phase progression for bringing existing code into SLD compliance.
5. **Set up CI:** Copy `test_spec_traceability.py` to your `tests/` directory and add it to your CI pipeline.
6. **Add engineer guidance:** Share `engineer-workflow.md` with your engineering team.
7. **Add documentation guidance:** Share `documentation-workflow.md` with your documentation team.
8. **Adopt gradually:** Start with a single subsystem. Once the workflow is clear, expand to others.

---

## See Also

- **OpenFastTrace:** https://github.com/itsallcode/openfasttrace
- **DO-178C Traceability:** https://rtmify.io/standards/do-178c
- **ISO 26262 Traceability:** https://www.parasoft.com/learning-center/iso-26262/requirements-traceability/
- **Requirements Traceability Matrix (RTM):** https://www.trace.space/blog/traceability-in-compliance-projects

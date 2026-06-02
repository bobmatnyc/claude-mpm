# SLD Backfill Workflow

**Status:** Active  
**Version:** 1.0  
**Related:** [WWL Granularity Model](./wwl-granularity.md), [Engineer Workflow](./engineer-workflow.md)

---

## Overview

The **Backfill Workflow** is a concrete, agent-driven procedure for retroactively bringing an **existing codebase** into Spec-Linked Documentation (SLD) compliance. It is essential for projects that have accumulated subsystems without spec coverage.

This workflow is **not** a one-time migration. It is a **subsystem-by-subsystem, phase-by-phase progression** that keeps CI checks passing and maintains traceability throughout the process.

---

## Why Backfill Is Necessary

When SLD is first enabled in a project:

- **Existing subsystems have zero spec coverage.** Code exists, but no `docs/specs/{subsystem}.md` file documents its behavior contract.
- **Existing code has zero WWL annotations.** No module carries a `References` block; no function carries a `:spec:` field.
- **Blanket enforcement would fail immediately.** Running `pytest tests/test_spec_traceability.py` with `enforcement: strict` would fail on every module and function.

**Backfill solves this** by establishing a **priority order** for spec authoring and gradually moving code from uncovered to covered as specs are written and linked.

---

## The Backfill Progression

Each subsystem progresses through **five phases**:

```
Phase 0 (Baseline)  →  Phase 1 (Spec)  →  Phase 2 (Annotate)  →  Phase 3 (Verify)  →  Phase 4 (Enforce)
```

### Phase 0: Baseline (Initial State)

**What:** The subsystem exists. Code is written. No spec exists. No WWL annotations exist.

**Actions:**

- Record the current state: "This subsystem has zero spec coverage."
- Add subsystem name to the **backfill priority list** (see section 3).
- No code changes yet. CI is not enforced for this subsystem.

**Example:** The `hooks.py` module exists; no `docs/specs/hooks.md` file exists.

### Phase 1: Spec Authoring

**What:** The subsystem spec is authored and checked into `docs/specs/{subsystem}.md` with SPEC-IDs and sections.

**Responsibilities:**

- **Documentation agent** (or engineer) authors the subsystem spec.
- **Spec structure:** Every section has a behavior contract (WHAT) and rationale (WHY).
- **SPEC-IDs:** Stable identifiers like `SPEC-HOOKS-01~1`, `SPEC-HOOKS-02~1`, etc.
- **Implementing Modules table:** Lists the modules that implement each spec section (initially empty or estimated; filled in Phase 3).
- **Status:** Mark as `Draft` until Phase 3 verification is complete.

**Example:** Create `docs/specs/hooks.md` with sections:

```markdown
## Hook Event Dispatch {#SPEC-HOOKS-01~1}

**ID:** SPEC-HOOKS-01~1  
**Status:** Draft  

### Behavior Contract (WHAT)
...

### Rationale (WHY)
...

### Implementing Modules
| Module | Role |
|--------|------|
| (to be filled in Phase 3) | |
```

**CI Impact:** No CI failure yet; UNCOVERED specs are tolerated during backfill (see configuration in section 4).

### Phase 2: WWL Annotation

**What:** Code in the subsystem is annotated with WHAT/WHY/LINK docstrings, linking to the specs authored in Phase 1.

**Responsibilities:**

- **Engineer agent** reads the code and the spec.
- **For each module:** Add module-level WHAT/WHY/References block.
- **For each over-threshold function/class:** Add WHAT/WHY/:spec: field (see [WWL Granularity Model](./wwl-granularity.md) for thresholds).
- **Link to spec:** Every LINK field points to a SPEC-ID from Phase 1 (e.g., `SPEC-HOOKS-01~1`).
- **CRITICAL:** Do NOT fabricate a spec link without reading and understanding the code and the spec. See section 5 (false-confidence risk).

**Example:** Add to `hooks.py`:

```python
"""
Hook event dispatcher — routes pre/post-tool-use events to handlers.

WHAT: Accepts a hook event dict, routes to the registered handler for that
event type, collects the response, and returns a structured response dict.

WHY: Centralizes routing logic so individual handlers remain independently
testable and stateless. The dispatcher enforces a uniform interface for all
handlers.

References
----------
SPEC-HOOKS-01~1 : docs/specs/hooks.md#SPEC-HOOKS-01
SPEC-HOOKS-02~1 : docs/specs/hooks.md#SPEC-HOOKS-02
"""
```

**Commit style:** One file per commit; conventional commit messages.

```bash
git add src/claude_mpm/hooks.py
git commit -m "docs: annotate hooks.py with WWL and spec references

Phase 2 backfill of SPEC-HOOKS subsystem."
```

### Phase 3: Verification and Baseline Recording

**What:** Human and CI verification that specs and annotations are semantically correct. Baseline is recorded to allow enforcement mode to progress to Phase 4.

**Human Verification Checklist:**

- [ ] **Spec accuracy:** Read each spec section and verify it describes the actual behavior of the implementing code (not an aspirational or outdated behavior).
- [ ] **WHAT/WHY accuracy:** For each WHAT/WHY block, verify that the prose accurately describes the code's observable behavior and design rationale (not a copy-paste or wrong link).
- [ ] **Coverage completeness:** Check that every public function, class, or method that implements a spec section has a corresponding LINK.
- [ ] **No fabrication:** Confirm that an engineer (not an AI) has reviewed the code and spec and personally verified the links are semantically correct.
- [ ] **Implementing Modules table:** Update `docs/specs/{subsystem}.md` with the list of modules that implement each spec section, filling in the table from Phase 1.
- [ ] **Mark spec as Active:** Change `Status: Draft` → `Status: Active` in the spec file.

**CI Verification:**

```bash
pytest tests/test_spec_traceability.py -v
```

All checks should pass:

- **No ORPHANED specs:** No code references a non-existent spec.
- **No UNCOVERED specs:** Every spec section has at least one code reference.
- **No OUTDATED specs:** All code references match the current spec revision.

**Baseline Recording:**

If using `enforcement: baseline` mode, record the current set of over-threshold functions that have WWL annotations:

```yaml
# .claude-mpm/configuration.yaml
workflow:
  spec_linked_docs:
    enabled: true
    wwl:
      enforcement: baseline
      baseline_functions:  # functions with WWL annotations (as of commit ABC1234)
        hooks.py:
          - dispatch_hook
          - register_handler
          - unregister_handler
```

This baseline tells CI: "These functions had WWL as of commit ABC1234. Enforce WWL on new functions or changed functions, but do not fail on these legacy ones unless they are touched."

**Example Phase 3 commit:**

```bash
git add docs/specs/hooks.md
git commit -m "docs: mark SPEC-HOOKS as Active after Phase 3 verification

WHAT/WHY annotations in hooks.py reviewed and verified.
Implementing Modules table completed.
CI traceability checks pass."
```

### Phase 4: Enforcement

**What:** The subsystem is now **fully governed** by SLD. New code and changes must maintain WWL annotations; CI enforces this.

**Actions:**

- Change `enforcement` mode to `strict` (for this subsystem, or globally if all subsystems are ready).
- Remove the subsystem from the backfill priority list.
- Update documentation to note that new patches to this subsystem must include WHAT/WHY/LINK.

**Example configuration:**

```yaml
workflow:
  spec_linked_docs:
    enabled: true
    wwl:
      enforcement: strict  # All subsystems now enforced
```

**Going forward:**

- New code that exceeds thresholds must include WWL annotations.
- If a spec's behavior contract changes, the revision is bumped (e.g., `~1` → `~2`) and all code references must be updated.
- CI will fail if links are missing or mismatched.

---

## 3. Backfill Priority: Subsystems to Target First

Prioritize backfill based on **impact, churn, and complexity**:

### Tier 1 (Highest Priority)

- **Highest churn:** Subsystems with frequent commits and changes (query version control history).
- **Highest complexity:** Subsystems with high cyclomatic complexity or large modules (run static analysis).
- **Most central:** Subsystems that other subsystems depend on (draw a dependency graph).
- **Examples:** `hooks.py`, `agents.py`, `services/agents/`.

### Tier 2 (Medium Priority)

- **Medium churn:** Subsystems with occasional changes.
- **Public API surface:** Subsystems that are part of the project's public interface.
- **Examples:** `cli/`, `migrations/`.

### Tier 3 (Lower Priority)

- **Low churn:** Utility subsystems with rare changes.
- **Internal APIs:** Subsystems used only internally, not part of the public contract.
- **Leaf modules:** Modules with no downstream dependencies.
- **Examples:** `utils/`, `constants.py`.

**Prioritization rationale:**

- High-churn, high-complexity, central subsystems benefit the most from SLD discipline because spec linkage helps context window management for agents and makes code review faster.
- Leaf and internal utilities can wait; they are lower-risk and have less impact on system behavior.

**Create a prioritized list:**

```markdown
# Backfill Priority List

## Phase 1 (This Sprint)
- [ ] hooks.py (Tier 1: high churn, central)
- [ ] agents.py (Tier 1: high churn, complex)

## Phase 2 (Next Sprint)
- [ ] cli/ (Tier 2: public API)
- [ ] migrations/ (Tier 2: medium churn)

## Phase 3 (Future)
- [ ] utils/ (Tier 3: low churn)
- [ ] constants.py (Tier 3: leaf module)
```

---

## 4. Configuration: Backfill Mode

Enable backfill-friendly CI enforcement via `.claude-mpm/configuration.yaml`:

```yaml
workflow:
  spec_linked_docs:
    enabled: true
    wwl:
      file_level_required: true
      function_line_threshold: 50
      complexity_threshold: 10
      enforcement: baseline                    # Tolerant mode during backfill
      baseline_subsystems: [hooks, agents]     # Subsystems with recorded baselines
      baseline_functions:                      # Functions with WWL as of a recorded commit
        hooks.py:
          - dispatch_hook
          - register_handler
```

### Enforcement Modes During Backfill

| Mode | Behavior | When to Use |
|------|----------|-----------|
| `off` | No CI enforcement; backfill is voluntary. | Pilot phase; exploring SLD adoption. |
| `baseline` | Fail CI only on new/modified code in subsystems without a baseline. Once a baseline is recorded, only new code is enforced. | Active backfill: Tiers 1–2 have baseline, Tiers 3 are not yet enforced. |
| `strict` | Fail CI on any code unit exceeding thresholds without WWL, regardless of age. | Backfill complete; full enforcement. |

**Recommended backfill progression:**

1. **Week 1–2:** `enforcement: off`. Pilot backfill on Tier 1 subsystems (hooks, agents).
2. **Week 3:** `enforcement: baseline` with Tier 1 baselines recorded. Begin Tier 2 backfill.
3. **Week 4:** `enforcement: baseline` with Tiers 1–2 baselines. Tier 3 optional.
4. **Week 5+:** `enforcement: strict`. Full backfill complete; all new code follows SLD.

---

## 5. CRITICAL: False-Confidence Risk and Mitigation

### The Risk

During Phase 2 (Annotation), an engineer or AI agent may write a WHAT/WHY/LINK triple that is **syntactically correct** (passes CI) but **semantically wrong**:

- The LINK points to a spec section for a *different* function.
- The WHAT misrepresents the actual observable behavior.
- The WHY describes a design rationale that is not actually reflected in the code.

**Published research (TraceLLM, 2026, Springer Nature):** LLM-generated trace links have precision ~0.52 in zero-shot settings. **Roughly half of AI-generated links are incorrect.** The CI check cannot detect this.

### Mitigation

**The ONLY reliable mitigation is human code review.**

1. **ENGINEER RESPONSIBILITY (Phase 2):**
   - Engineer reads the **code** thoroughly (not just skimming).
   - Engineer reads the **spec section** thoroughly.
   - Engineer personally verifies that the code's observable behavior matches the spec's Behavior Contract section.
   - Engineer personally verifies that the code's design rationale matches the spec's Rationale section.
   - **Do not trust AI-generated WHAT/WHY/LINK.** If an AI agent wrote it, treat it as a draft and verify it carefully before committing.

2. **PR REVIEWER RESPONSIBILITY (Phase 3):**
   - During human verification, the reviewer checks:
     - [ ] WHAT prose accurately describes the code's observable behavior.
     - [ ] WHY prose accurately describes the design rationale.
     - [ ] LINK points to the correct spec section (not an adjacent one).
     - [ ] Spec section's WHAT matches the code's behavior.
   - **Do not rubber-stamp the CI check.** CI validates **presence and format** of links, not **correctness**.

3. **CONSEQUENCES OF SKIPPING VERIFICATION:**
   - False-confident coverage: The spec appears covered by code, but it is not.
   - Brittle maintenance: Future engineers assume the code implements the spec and may make changes based on the (incorrect) spec.
   - Wasted effort: The backfill phase is meant to establish a reliable foundation; skipping verification defeats the purpose.

### Example of Mislinked Code

**Scenario:** An engineer is annotating `hooks.py` and reads:

```python
def dispatch_hook(event: dict) -> dict:
    # This function routes a hook event to the registered handler
    # and returns the response.
    ...
```

The engineer sees two spec sections:
- `SPEC-HOOKS-01~1`: "Route a hook event to its registered handler and return the response."
- `SPEC-HOOKS-02~1`: "Validate a hook event structure before dispatch."

The engineer thinks "dispatch_hook sounds like routing, so I'll link to SPEC-HOOKS-01~1."

**But the code's first line is:**

```python
def dispatch_hook(event: dict) -> dict:
    # Validate the event structure
    if not _validate_event(event):
        raise ValueError(...)
    
    # Route to handler
    handler = _get_handler(event["type"])
    response = handler(event)
    return response
```

**The actual behavior is dual: validate AND dispatch.** The correct link is `SPEC-HOOKS-02~1` (which covers both validation and dispatch) *or* the engineer should have created a new spec section that explicitly covers both behaviors.

**Without verification,** the incorrect link is committed, and downstream reviewers assume the code is covered when it is not.

---

## 6. Agent Responsibilities During Backfill

### Engineer Agent

**During Phase 1 (Spec Authoring):**
- [NOT the engineer's responsibility — documentation agent owns this]

**During Phase 2 (WWL Annotation):**
- Read the code **thoroughly** (not skimming).
- Read the spec **thoroughly**.
- Write module-level WHAT/WHY/References for every module in the subsystem.
- Write function-level WHAT/WHY/:spec: for every function/class exceeding thresholds.
- **Verify semantic correctness:** Confirm that WHAT matches the code's behavior and LINK points to the right spec.
- Commit one file per commit; use conventional `docs:` prefix (or `feat:` if adding new code as part of backfill).
- Flag any uncertainties in the PR description: "This function's behavior is ambiguous; it could match SPEC-A or SPEC-B. I chose SPEC-A because..."

**During Phase 3 (Verification):**
- [NOT the engineer's responsibility — human reviewer owns this]

### Documentation Agent

**During Phase 1 (Spec Authoring):**
- Author the subsystem spec in `docs/specs/{subsystem}.md`.
- Write WHAT (Behavior Contract) and WHY (Rationale) for each spec section.
- Assign SPEC-IDs following the project's numbering convention.
- Mark status as `Draft`.
- Do **not** fill in the Implementing Modules table; that comes in Phase 3.
- Commit to `docs/specs/{subsystem}.md`; use conventional `docs:` prefix.

**During Phase 2 (WWL Annotation):**
- [NOT the documentation agent's responsibility — engineer owns this]

**During Phase 3 (Verification):**
- Review the PR that updates the Implementing Modules table.
- Confirm that the spec sections accurately describe the implemented behavior.
- Mark status as `Active`.
- Commit status change; use conventional `docs:` prefix.

### Code Reviewer / QA

**During Phase 3 (Verification):**
- Check the PR's semantic correctness:
  - [ ] WHAT/WHY prose in code docstrings matches the actual behavior (read the code).
  - [ ] LINK points to the correct spec section (read the spec).
  - [ ] No copy-paste errors or wrong links.
- Confirm that the CI traceability check passes.
- Approve the PR only after these checks pass.

---

## 7. Practical Example: Backfilling the Hooks Subsystem

### Phase 0: Initial State

```
hooks.py exists (200 LOC, complex dispatch logic)
docs/specs/hooks.md does not exist
No WHAT/WHY/LINK annotations in hooks.py
```

**Action:** Add "hooks" to the backfill priority list (Tier 1).

### Phase 1: Spec Authoring

**Documentation agent** creates `docs/specs/hooks.md`:

```markdown
# Hook Subsystem Specification

**Status:** Draft  
**Last reviewed:** 2026-06-02

## Overview

The hook subsystem provides a pre/post-tool-use event dispatch mechanism for
extending the behavior of tool execution without modifying the core execution
engine.

---

## Hook Event Dispatch {#SPEC-HOOKS-01~1}

**ID:** SPEC-HOOKS-01~1  
**Status:** Draft

### Behavior Contract (WHAT)

- **Inputs:** A hook event dict with 'event_type' and 'payload' keys.
- **Outputs:** A response dict with 'success', 'data', and optional 'error' keys.
- **Preconditions:** The event_type must correspond to a registered handler.
- **Postconditions:** The handler is invoked exactly once; side effects are captured.
- **Error conditions:** Raises KeyError if event_type is unknown; TimeoutError if handler exceeds timeout.

### Rationale (WHY)

Centralizes event routing so individual handlers remain independently testable
and stateless. The dispatcher enforces a uniform interface (initialize, call, cleanup)
so handlers cannot fail in unexpected ways.

### Implementing Modules

| Module | Role |
|--------|------|
| (to be filled in Phase 3) | |
```

**Commit:**

```bash
git add docs/specs/hooks.md
git commit -m "docs: add SPEC-HOOKS subsystem specification (Phase 1)

Spec authored with behavior contracts and rationale.
Status: Draft pending Phase 2–3 annotation and verification."
```

### Phase 2: WWL Annotation

**Engineer agent** reads `hooks.py` and `docs/specs/hooks.md`, then annotates:

```python
"""
Hook event dispatcher — routes pre/post-tool-use events to handlers.

WHAT: Accepts a hook event dict, routes to the registered handler for that
event type, collects the response, and returns a structured response dict.

WHY: Centralizes routing logic so individual handlers remain independently
testable and stateless. The dispatcher enforces a uniform interface.

References
----------
SPEC-HOOKS-01~1 : docs/specs/hooks.md#SPEC-HOOKS-01
"""

def dispatch_hook(event: dict) -> dict:
    """
    Route a hook event to its registered handler and return the response.
    
    WHAT: Given an event dict with 'event_type' and 'payload', looks up
           the handler, invokes it, and returns the response dict.
    
    WHY: Decouples routing logic from handler implementation so handlers
         can be tested independently without the full dispatch infrastructure.
    
    LINK: SPEC-HOOKS-01~1
    """
    # ... function body ...
```

**Commit:**

```bash
git add src/claude_mpm/hooks.py
git commit -m "docs: annotate hooks.py with WWL and spec references (Phase 2)

Module-level and function-level WHAT/WHY/LINK annotations added.
All non-trivial functions linked to SPEC-HOOKS-01~1."
```

### Phase 3: Verification and Baseline Recording

**Human reviewer** checks:
- [ ] Module-level WHAT/WHY accurately describes hooks.py's behavior.
- [ ] Function-level WHAT/WHY accurately describe dispatch_hook's behavior.
- [ ] LINK pointers are correct (point to SPEC-HOOKS-01~1, which matches the function's purpose).
- [ ] CI traceability check passes.

**Update spec with Implementing Modules table:**

```markdown
### Implementing Modules

| Module | Role |
|--------|------|
| `claude_mpm.hooks` | Dispatcher implementation |
```

**Mark spec as Active:**

```markdown
**Status:** Active
```

**Commit:**

```bash
git add docs/specs/hooks.md
git commit -m "docs: mark SPEC-HOOKS as Active after Phase 3 verification

Implementing Modules table completed.
WHAT/WHY annotations reviewed and verified semantically correct.
CI traceability checks pass."
```

### Phase 4: Enforcement

**Update configuration:**

```yaml
# .claude-mpm/configuration.yaml
workflow:
  spec_linked_docs:
    enabled: true
    wwl:
      enforcement: strict  # Now enforced
```

**From this point:** New patches to `hooks.py` must include or maintain WHAT/WHY/LINK annotations.

---

## 8. Handling Blocked Units (LINK: none)

If an engineer encounters a code unit that is part of the subsystem but the spec does not yet cover it, use `LINK: none` to flag the gap:

```python
def _internal_helper(x):
    """
    (Legacy helper function — backfill phase).
    
    WHAT: Accepts x, performs internal calculation.
    
    WHY: Historical utility; spec coverage planned in future phase.
    
    LINK: none
    """
```

**Why use `LINK: none` instead of omitting the LINK?**

- CI checker recognizes `LINK: none` as **intentionally uncovered** during backfill.
- Reviewers know the gap is **acknowledged**, not accidental.
- Backfill progress tracking is easier: search for `LINK: none` to find remaining gaps.

**Progression:** When the spec is updated to cover this unit, change `LINK: none` → `LINK: SPEC-ID~rev`.

---

## 9. Summary: Five-Phase Progression

| Phase | Owner | Action | CI Status | Outcome |
|-------|-------|--------|-----------|---------|
| 0 | — | Record initial state. Add to priority list. | No checks | Baseline established. |
| 1 | Documentation | Author subsystem spec in `docs/specs/{subsystem}.md`. | No enforcement | Spec sections exist with stable IDs. |
| 2 | Engineer | Annotate every module and over-threshold function with WHAT/WHY/LINK. | No enforcement | Code is linked to spec. |
| 3 | Reviewer | Human verification of semantic correctness. Record baseline. Mark spec as Active. | CI checks pass | Traceability is verified correct. |
| 4 | CI | Enforce WWL on new/changed code in this subsystem. | CI enforces | Full SLD discipline in effect. |

---

## See Also

- [WWL Granularity Model](./wwl-granularity.md) — Thresholds and syntax for WHAT/WHY/LINK blocks
- [Engineer Workflow](./engineer-workflow.md) — Writing WHAT/WHY/LINK as code is authored
- [Spec-Linked Documentation Convention (docs/specs/README.md)](../../../../docs/specs/README.md) — Full SLD discipline, false-confidence risk, and PR review checklist

# WWL Granularity Model

**Status:** Active  
**Version:** 1.0  
**Related:** [Backfill Workflow](./backfill-workflow.md), [Engineer Workflow](./engineer-workflow.md)

---

## Overview

The **WWL (WHAT/WHY/LINK) Granularity Model** defines the code-level, docstring-based form of SLD links and establishes rules for **which code units require explicit spec linkage**. It is the bridge between high-level specification documents and individual functions, methods, and classes.

**Core idea:** Not every line of code needs a spec link. Too much linkage creates maintenance burden; too little creates coverage gaps. The granularity model defines **thresholds** that determine when a function or class is significant enough to warrant its own spec reference, independent of module-level specs.

---

## 1. WWL Definition

Every code unit with an explicit spec link (module, function, class, or method) carries a **WWL block** in its docstring:

```
WHAT: [one line, observable behavior]
WHY:  [rationale]
LINK: [SPEC-{SUBSYSTEM}-{NN}~{rev} or "none" to flag a backfill gap]
```

### WHAT (Observable Behavior)

A single line or short sentence describing the **observable behavior** of the unit from the caller's perspective.

- **Caller-centric:** What can an external actor rely on?
- **Contract-level:** Inputs accepted, outputs produced, exceptions raised.
- **Concrete:** Avoid abstractions like "handles requests efficiently" — say "Accepts HTTP POST requests with JSON payload, validates schema, returns 200 + response body or 400 + error message."

**Example WHAT statements:**

```python
def validate_spec_id(spec_id: str) -> bool:
    """
    Validate the format and existence of a spec ID.
    
    WHAT: Accepts a string, returns True if it matches SPEC-{SUBSYSTEM}-{NN}~{rev} 
          pattern and a matching spec section exists in docs/specs/; False otherwise.
    """
```

### WHY (Rationale)

One to three sentences explaining **why this unit exists and why it is designed this way**.

- **Design decisions:** Why this approach over alternatives?
- **Constraints:** Performance targets, architectural requirements, security boundaries.
- **Integration:** How does this unit fit into the larger system?

**Never write HOW in the WHY.** "First validates the format, then checks the spec file" is HOW. "Centralized validation ensures all code uses the same rule set" is WHY.

**Example WHY statements:**

```python
def validate_spec_id(spec_id: str) -> bool:
    """
    Validate the format and existence of a spec ID.
    
    WHAT: Accepts a string, returns True if it matches SPEC-{SUBSYSTEM}-{NN}~{rev} 
          pattern and a matching spec section exists in docs/specs/; False otherwise.
    
    WHY: Centralizes format and existence checking so all code paths use the same 
         validation rules, reducing the risk of inconsistent ID handling. Separating 
         validation from lookup enables independent testing and future caching.
    """
```

### LINK (Specification Reference)

The **SPEC-ID** of the governing specification section, including revision.

- **Format:** `SPEC-{SUBSYSTEM}-{NN}~{rev}` (example: `SPEC-HOOKS-01~1`)
- **Backfill gap:** If the code unit exists but no spec yet covers it, write `LINK: none` to flag the gap for later backfilling.
- **Required for over-threshold units:** Functions/classes exceeding the line-count or complexity thresholds (see section 2) must have a LINK unless explicitly in backfill mode.

**Example LINK statements:**

```python
def validate_spec_id(spec_id: str) -> bool:
    """
    Validate the format and existence of a spec ID.
    
    WHAT: Accepts a string, returns True if it matches SPEC-{SUBSYSTEM}-{NN}~{rev} 
          pattern and a matching spec section exists in docs/specs/; False otherwise.
    
    WHY: Centralizes format and existence checking so all code paths use the same 
         validation rules, reducing the risk of inconsistent ID handling.
    
    LINK: SPEC-SLD-01~1
    """
```

---

## 2. Granularity Thresholds

The following thresholds determine **which units must carry a WWL block**:

### Module-Level Docstrings (Always Required)

Every module in a subsystem governed by a spec carries a module-level docstring with WWL + References block.

```python
"""
{Module name} — {one-line summary}.

WHAT: {Observable behavior from caller perspective.}

WHY: {Design decisions and constraints.}

References
----------
SPEC-{SUBSYSTEM}-{NN}~{rev} : docs/specs/{subsystem}.md#SPEC-{SUBSYSTEM}-{NN}
"""
```

### Pure Re-Export / Scaffolding Modules (Exempt)

`__init__.py` files and modules whose entire body consists of `__all__` assignments, re-exports, or empty stubs carry no independent logic. They need only a one-line module docstring (or none at all when the package structure is self-evident). Do not force WHAT/WHY/LINK on a file whose content is `from .foo import Bar` — there is nothing to document beyond what the imported names already say.

Examples that qualify for the exemption:

```python
# claude_mpm/hooks/__init__.py  — pure re-export, one-liner is enough
"""Public surface for the hooks package."""
from .dispatcher import dispatch_hook
from .registry import HandlerRegistry

__all__ = ["dispatch_hook", "HandlerRegistry"]
```

```python
# claude_mpm/utils/__init__.py  — empty scaffold, no docstring needed
```

This file (`wwl-granularity.md`) is the **authoritative home** for the proportionality and module-exemption rules. Cross-reference it from other files rather than duplicating the rule text.

### Function/Class/Method Level (Conditional)

A function, class, or method requires its own WWL block when **EITHER**:

- **Lines of Code (LOC) > threshold** (default: **50 LOC**)
- **Cyclomatic Complexity (CC) > threshold** (default: **10**)

When either threshold is exceeded, the unit must carry a WHAT/WHY/LINK docstring describing its specific behavior distinct from the module-level spec.

```python
def complex_function():
    """
    Brief description of what this function does.
    
    WHAT: {Observable behavior — what caller sees.}
    WHY: {Why this function is designed this way.}
    LINK: SPEC-{SUBSYSTEM}-{NN}~{rev}
    """
```

**When a unit is below both thresholds**, a WWL block is optional. Small helper functions, getters, setters, and simple utility functions may omit the WHAT/WHY/LINK block and instead rely on a single-line docstring.

```python
def get_id():
    """Return the spec ID string."""
    return self._id
```

---

## 3. Configurable Thresholds

The WWL enforcement thresholds are **configurable per-project** via the `.claude-mpm/configuration.yaml` file:

```yaml
workflow:
  spec_linked_docs:
    enabled: true
    wwl:
      file_level_required: true          # module-level WHAT/WHY always required
      function_line_threshold: 50        # functions > 50 LOC require WWL
      complexity_threshold: 10           # functions > complexity 10 require WWL
      enforcement: baseline              # off | baseline | strict
```

### Enforcement Modes

| Mode | Behavior |
|------|----------|
| `off` | No WWL enforcement; units may omit WHAT/WHY/LINK |
| `baseline` | Fail CI only on **new or modified code** that exceeds thresholds without WWL. Existing code is tolerated (measured against a recorded baseline). |
| `strict` | Fail CI on any code unit exceeding thresholds without WWL, regardless of age. |

**Baseline mode rationale:** Existing codebases have zero WWL coverage initially. Enforcement modes:

- `baseline` allows incremental adoption: as new code is added or changed, it must follow WWL discipline; legacy code is not penalized until it is touched.
- `strict` demands immediate full compliance (appropriate for new projects or after a formal migration period).
- `off` disables enforcement entirely (not recommended except during pilot phases).

---

## 4. Justification for Thresholds

### Function Line Count: 50 LOC

**Citation:** Industry-standard function length guidelines recommend 40–50 lines as an upper bound for human comprehension without mental state loss.

- **Cognitive load research:** Studies on code comprehension (e.g., "The Cognitive Complexity of Code," Cognitive Psychology literature) indicate that human working memory can hold ~7 ± 2 semantic chunks simultaneously. A function exceeding 50 LOC typically exceeds this capacity and benefits from explicit external documentation (WHAT/WHY block) to reduce cognitive load.
- **Linter consensus:** Popular linters and style guides adopt the 50-LOC threshold:
  - **Pylint (flake8-too-many-lines):** Default max function length = 50 LOC
  - **ESLint (max-lines-per-function):** Recommended max = 50 lines
  - **Checkstyle (MethodLength):** Default max = 150 lines (but 50 is more stringent and more commonly adopted in modern codebases)
  - **Google Python Style Guide:** "Avoid functions longer than 40 lines" (retrieved from https://google.github.io/styleguide/pyguide.html)

**Configurable:** Teams may adjust this to `75` for verbose languages (Java) or `25` for terse languages (Go), but 50 is a reasonable default across Python, TypeScript, and similar languages.

### Cyclomatic Complexity: 10

**Citation:** Cyclomatic complexity (CC) threshold of 10 is mandated by NIST in SP 500-235 "Structured Testing" and widely adopted in safety-critical systems.

- **NIST SP 500-235 (Structural Testing):** https://nvlpubs.nist.gov/nistpubs/Legacy/SP/nistspecialpublication500-235.pdf recommends CC ≤ 10 as a baseline threshold for code that must be individually tested (each path should be exercisable).
- **Academic precedent:** McCabe's original paper (McCabe, T. J., "A Complexity Measure," IEEE Transactions on Software Engineering, 1976) introduced the metric and suggested thresholds; a CC of 10 is the conventional "high complexity" cutoff across the literature.
- **Tool defaults:**
  - **Radon (Python complexity):** CC of 10–15 = "B" grade (moderate); 15+ = "C" grade (high)
  - **Pylint (max-locals):** Default = 15 local variables (proxy for CC)
  - **ESLint (complexity):** Recommended max = 10–15
  - **SonarQube:** "Critical" threshold = CC > 15, but CC > 10 is flagged for review

**Configurable:** Teams may use 8 (stricter) or 12 (lenient), but 10 aligns with NIST and academic consensus.

---

## 5. Per-Language Syntax

The WHAT/WHY/LINK block adapts to each language's docstring conventions:

### Python (NumpyDoc Format)

```python
def dispatch_hook(event: dict) -> dict:
    """
    Route a hook event to its registered handler and return the response.
    
    WHAT: Accepts a hook event dict with 'event_type' and 'payload' keys, 
           identifies the handler, invokes it, and returns the response dict.
    
    WHY: Centralizes routing logic so individual handlers remain stateless 
         and independently testable without depending on the full dispatch 
         infrastructure.
    
    LINK: SPEC-HOOKS-02~1
    
    Parameters
    ----------
    event : dict
        Hook event with 'event_type' and 'payload' keys.
    
    Returns
    -------
    dict
        Handler response dict.
    """
```

### JavaScript/TypeScript (JSDoc)

```javascript
/**
 * Route a hook event to its registered handler and return the response.
 *
 * WHAT: Accepts a hook event object with 'eventType' and 'payload' properties,
 *       identifies the handler, invokes it, and returns the response object.
 *
 * WHY: Centralizes routing logic so individual handlers remain stateless
 *      and independently testable without depending on the full dispatch
 *      infrastructure.
 *
 * @spec SPEC-HOOKS-02~1
 * @param {Object} event - Hook event object.
 * @returns {Object} Handler response object.
 */
export function dispatchHook(event) { ... }
```

### Java (Javadoc)

```java
/**
 * Route a hook event to its registered handler and return the response.
 *
 * WHAT: Accepts a hook event object with 'eventType' and 'payload' properties,
 *       identifies the handler, invokes it, and returns the response object.
 *
 * WHY: Centralizes routing logic so individual handlers remain stateless
 *      and independently testable without depending on the full dispatch
 *      infrastructure.
 *
 * @see <a href="docs/specs/hooks.md#SPEC-HOOKS-02">SPEC-HOOKS-02~1</a>
 * @param event Hook event object.
 * @return Handler response object.
 */
public Map<String, Object> dispatchHook(Map<String, Object> event) { ... }
```

### Go (Doc Comments)

```go
// DispatchHook routes a hook event to its registered handler and returns the response.
//
// WHAT: Given a HookEvent struct with EventType and Payload fields,
//       identifies the handler, invokes it, and returns the response struct.
//
// WHY: Centralizes routing logic so individual handlers remain stateless
//      and independently testable without depending on the full dispatch
//      infrastructure.
//
// Spec: SPEC-HOOKS-02~1
func DispatchHook(event HookEvent) (HookResponse, error) { ... }
```

### Rust (Rustdoc)

```rust
/// Route a hook event to its registered handler and return the response.
///
/// WHAT: Given a HookEvent struct with event_type and payload fields,
///       identifies the handler, invokes it, and returns the response struct.
///
/// WHY: Centralizes routing logic so individual handlers remain stateless
///      and independently testable without depending on the full dispatch
///      infrastructure.
///
/// # Spec References
/// - [`SPEC-HOOKS-02~1`](https://github.com/bobmatnyc/claude-mpm/blob/main/docs/specs/hooks.md#SPEC-HOOKS-02)
pub fn dispatch_hook(event: HookEvent) -> Result<HookResponse, Error> { ... }
```

---

## 6. Content Rules

### What Goes in WHAT

- Observable behavior **from the caller's perspective**.
- Inputs: what the unit accepts (types, preconditions, range of valid values).
- Outputs: what it produces (return types, postconditions, side effects if any).
- Exceptions: what it raises (and under what conditions).
- **No implementation steps.** "Validates the ID by checking if it matches the regex and exists in the file" is HOW. "Returns True if the ID is valid; False otherwise" is WHAT.

### What Goes in WHY

- **Design decisions:** Why did we choose this approach over alternatives?
- **Constraints:** Performance targets, security requirements, architectural decisions.
- **Integration:** How does this unit fit into the larger system?
- **Rationale for public vs. private:** Why is this unit exposed as public API?
- **No implementation steps.** "Separates validation from lookup so it can be tested independently and cached" is WHY. "First checks the format, then reads the file" is HOW.

### What Goes in Inline Comments (HOW)

Implementation details belong in **inline comments within the function body**, never in WHAT/WHY/LINK:

```python
def validate_spec_id(spec_id: str) -> bool:
    """
    Validate the format and existence of a spec ID.
    
    WHAT: Accepts a string, returns True if it matches SPEC-{SUBSYSTEM}-{NN}~{rev} 
          and exists in docs/specs/; False otherwise.
    
    LINK: SPEC-SLD-01~1
    """
    # First, check format against the regex pattern
    if not re.match(r"^SPEC-[A-Z0-9]+-\d+~\d+$", spec_id):
        return False
    
    # Then, check if the spec file and section ID exist by scanning docs/specs/
    spec_dir = Path("docs/specs")
    for md_file in spec_dir.glob("*.md"):
        if spec_id in md_file.read_text():
            return True
    
    return False
```

---

## 7. Backfill Gaps (LINK: none)

During the **backfill phase** of existing codebases (see [Backfill Workflow](./backfill-workflow.md)), a unit may exist but no spec yet governs it. In this case, use `LINK: none` to **flag the gap for later resolution**:

```python
def legacy_handler(event: dict) -> dict:
    """
    Legacy hook handler (backfill phase).
    
    WHAT: Accepts an event dict and routes it based on event_type.
    
    WHY: Part of the pre-SLD codebase; spec coverage planned in phase 2.
    
    LINK: none  # TODO: Add SPEC-ID when spec-hooks.md is complete
    """
```

The `LINK: none` line signals to the CI checker and future reviewers that this unit is **intentionally uncovered** during backfill, not accidentally undocumented.

**Backfill progression:**

1. **Phase 0 (Initial):** Code exists, no spec. `LINK: none`
2. **Phase 1 (Spec authored):** Spec section added. Change `LINK: none` → `LINK: SPEC-ID~rev`
3. **Phase 2 (CI validated):** Spec traceability check passes. Mark unit for removal from backfill list.

---

## 8. CI Enforcement

The SLD CI checker validates WWL blocks as follows:

| Rule | Condition | Failure |
|------|-----------|---------|
| **WHAT required** | Every module and over-threshold function/class has a WHAT block | Missing WHAT |
| **WHY required** | Every module and over-threshold function/class has a WHY block | Missing WHY |
| **LINK valid** | Every LINK is either `SPEC-{SUBSYSTEM}-{NN}~{rev}` or `none` | Invalid LINK |
| **LINK exists** | Every non-`none` LINK points to a declared spec section | Orphaned LINK |
| **LINK revision matches** | LINK revision equals the current spec revision | Outdated LINK |
| **No fabrication** | WHAT/WHY prose is read from code and not auto-generated | Requires human review (see False-Confidence Risk) |

The **no fabrication** rule is **not mechanically enforced by CI** — it is enforced by human code review (see section 9).

---

## 9. False-Confidence Risk and Mitigation

### The Risk

An AI coding agent may write a plausible-sounding WHAT/WHY/LINK triple that is **syntactically correct** (passes CI checks) but **semantically wrong** — the LINK points to the wrong spec, or the WHAT misrepresents the actual behavior.

Research on LLM traceability (TraceLLM, 2026, Springer Nature) reports precision ~0.52 for zero-shot link generation. **Roughly half of AI-generated trace links are incorrect.**

### Mitigation

1. **PR review checklist:** Every code change that adds or modifies a WHAT/WHY/LINK block must pass a human semantic check:
   ```
   [ ] WHAT/WHY prose accurately describes the unit's behavior (checked by reading the code).
   [ ] LINK points to the semantically correct spec section (checked by reading the spec).
   [ ] LINK is not a copy-paste from another unit without verification.
   ```

2. **Descriptive spec IDs:** Use meaningful subsystem names in IDs (`SPEC-HOOKS-DISPATCH` is better than `SPEC-001`) so that an obviously wrong reference jumps out during review.

3. **Spec-first discipline:** Author or review the spec section **before** the code is written, so human reviewers can verify alignment in the PR.

4. **Treat CI as a floor, not a ceiling:** The CI check is a necessary condition (mechanical completeness), not a sufficient condition (semantic correctness). Human review is the only mechanism for verifying semantic correctness.

---

## 10. Practical Example: Full Annotated Function

```python
def parse_spec_id(spec_id: str) -> tuple[str, int, int]:
    """
    Parse a spec ID into its components.
    
    WHAT: Accepts a SPEC-ID string like 'SPEC-HOOKS-02~1', parses it, and returns
           a tuple of (subsystem, seq_num, revision). Raises ValueError if the ID
           does not match the SPEC-{SUBSYSTEM}-{NN}~{rev} pattern.
    
    WHY: Centralizes ID parsing so all code paths use the same grammar, reducing
         the risk of inconsistent interpretation. Separates parsing from validation
         (see validate_spec_id) for independent testing and future performance
         optimization.
    
    LINK: SPEC-SLD-02~1
    
    Parameters
    ----------
    spec_id : str
        A spec ID string in the format SPEC-{SUBSYSTEM}-{NN}~{rev}.
    
    Returns
    -------
    tuple[str, int, int]
        (subsystem, seq_num, revision) e.g., ('HOOKS', 2, 1)
    
    Raises
    ------
    ValueError
        If spec_id does not match the expected pattern.
    
    Examples
    --------
    >>> parse_spec_id("SPEC-HOOKS-02~1")
    ('HOOKS', 2, 1)
    >>> parse_spec_id("SPEC-SESSIONS-15~3")
    ('SESSIONS', 15, 3)
    >>> parse_spec_id("invalid")
    Traceback (most recent call last):
        ...
    ValueError: Invalid spec ID format: invalid
    """
    # Regex pattern for SPEC-{SUBSYSTEM}-{NN}~{rev}
    # e.g., SPEC-HOOKS-02~1
    match = re.match(r"^SPEC-([A-Z0-9_-]+)-(\d+)~(\d+)$", spec_id)
    if not match:
        raise ValueError(f"Invalid spec ID format: {spec_id}")
    
    subsystem, seq_str, rev_str = match.groups()
    return (subsystem, int(seq_str), int(rev_str))
```

---

## 11. Summary

| Aspect | Rule |
|--------|------|
| **Module-level WHAT/WHY** | Always required |
| **Function WHAT/WHY** | Required if LOC > 50 OR CC > 10 (configurable) |
| **LINK field** | Required for all WHAT/WHY blocks; `SPEC-ID~rev` or `none` |
| **Thresholds** | Configurable per-project; defaults are 50 LOC, CC 10 (NIST/industry standard) |
| **Enforcement mode** | `off`, `baseline` (new code only), or `strict` (all code) |
| **Backfill gaps** | Use `LINK: none` during backfill; progress to LINK: SPEC-ID when spec is ready |
| **CI validation** | Syntactic (LINK exists, format correct); human review required for semantic correctness |

---

## See Also

- [Backfill Workflow](./backfill-workflow.md) — Retroactive SLD adoption for existing codebases
- [Engineer Workflow](./engineer-workflow.md) — Writing WHAT/WHY/LINK as code is authored
- [Spec-Linked Documentation Convention (docs/specs/README.md)](../../../../docs/specs/README.md) — Full SLD discipline and false-confidence risk

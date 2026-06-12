# Engineer Workflow: SLD Step-by-Step

When you are implementing a feature that is covered by a specification in `docs/specs/`, follow this workflow to maintain spec-to-code linkage.

## Before You Start Coding

### 1. Check for an existing spec

Navigate to `docs/specs/` and look for a specification file covering the subsystem you are about to implement.

**Example:**
```bash
# Implementing a new hook dispatcher?
cat docs/specs/hooks.md | grep "SPEC-HOOKS"
# Output:
# SPEC-HOOKS-01~v1 — Hook Event Dispatch
# SPEC-HOOKS-02~v1 — Handler Registration
```

**If a spec exists:** Note the relevant SPEC-ID (e.g., `SPEC-HOOKS-01~v1`) and the revision number. You will reference this in your docstrings.

**If no spec exists:** Create a spec section in the appropriate file or create a new spec file before you start coding. (See "If No Spec Exists" section below.) Specs are written *before* the code they govern, not documented retroactively.

### 2. Read the spec section carefully

Understand what the spec is committing to:
- **Behavior Contract (WHAT):** What are the observable inputs, outputs, and error conditions?
- **Rationale (WHY):** Why is this subsystem designed this way? What constraints must the code respect?

**Do not read HOW from the spec.** If the spec describes implementation steps, that is a spec bug — it should not. Implementation details belong in code comments and docstrings, not in the spec.

### 3. Verify the revision number

The spec ID includes a revision number: `SPEC-HOOKS-01~v1`.

- If you are implementing against this revision, you will reference `~v1` in your docstrings.
- If you discover during implementation that the spec needs to be changed (the behavior contract is wrong or incomplete), update the spec and bump the revision to `~v2`. Then update all references in code from `~v1` to `~v2`.

---

## While You Code

### 4. Write the module-level docstring FIRST

Before writing any function bodies, write the module-level docstring with WHAT and WHY blocks.

**Template:**

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
{SPEC-ID}~{revision} : docs/specs/{subsystem}.md#{SPEC-ID}
{SPEC-ID}~{revision} : docs/specs/{subsystem}.md#{SPEC-ID}
"""
```

**Example for `claude_mpm/hooks/dispatcher.py`:**

```python
"""Hook event dispatcher — routes pre/post-tool-use events to registered handlers.

WHAT: Accepts a hook event dict with 'event_type' and 'payload' keys, looks up
the registered handler for that event type, invokes the handler, collects the
response dict, and returns it. If no handler is registered for the event type,
raises KeyError.

WHY: Centralizes event routing logic so individual handlers remain stateless and
independently testable. The dispatcher enforces a uniform interface (event dict
in, response dict out) so handlers can be registered dynamically without
modifying dispatcher code.

References
----------
SPEC-HOOKS-01~v1 : docs/specs/hooks.md#SPEC-HOOKS-01
SPEC-HOOKS-02~v1 : docs/specs/hooks.md#SPEC-HOOKS-02
"""
```

**Why this order matters:** When you write WHAT/WHY before code, you clarify the module's contract *before* implementation. This forces you to think about the public interface and behavior, not just the code mechanics.

### 5. Write function/class docstrings for spec-referenced functions

For any function or class that implements a *specific* spec section (distinct from the module-level spec), add a `:spec:` field to the docstring.

**Coverage rule:** If a full specification is available, aim to link **at least the major classes and public entry-point functions** to the relevant spec sections — not necessarily every internal helper. Linkage density should be proportional to complexity: over-threshold units (LOC > 50 or cyclomatic complexity > 10; see `wwl-granularity.md §2`) require a `:spec:` link; simpler units may omit it.

**No-spec rule:** If **no** specification exists or is applicable for a unit, the docstring must state this explicitly rather than silently omitting the field:

```python
# Acceptable forms when no spec governs this unit:
# :spec: none
# or inline note:
# No governing spec — see wwl-granularity.md §7 for backfill guidance.
```

Silently omitting `:spec:` on an over-threshold unit is indistinguishable from an accidental omission. Using `:spec: none` (or an equivalent explicit note) signals intentional awareness, not negligence.

**Template:**

```python
def some_function(arg1, arg2):
    """
    {Brief description of what this function does}.

    WHAT: {What the function accepts, returns, and raises.}

    WHY: {Why this function is designed this way.}

    Parameters
    ----------
    arg1 : type
        Description.
    arg2 : type
        Description.

    Returns
    -------
    type
        Description.

    Raises
    ------
    ExceptionType
        Description.

    :spec: SPEC-{SUBSYSTEM}-{NN}~v{revision}
    """
```

**Example:**

```python
def dispatch_hook(event: dict, context: dict) -> dict:
    """
    Route a hook event to its registered handler and return the response.

    WHAT: Accepts an event dict with 'event_type' key, looks up the handler
    in the registry, invokes it with (event, context), and returns the response.
    Raises KeyError if event_type is not registered.

    WHY: Isolates event routing from handler logic, enabling independent testing
    and dynamic handler registration.

    Parameters
    ----------
    event : dict
        Hook event with 'event_type', 'payload', and optional 'metadata' keys.
    context : dict
        Request context (session, user, trace_id, etc.).

    Returns
    -------
    dict
        Handler response with 'success' (bool), 'data', and optional 'error' keys.

    Raises
    ------
    KeyError
        If 'event_type' not found in handlers registry.
    TimeoutError
        If handler exceeds timeout.

    :spec: SPEC-HOOKS-02~v1
    """
    # Implementation...
```

**Rule:** Do not describe HOW the function works inside the docstring. The docstring is for callers; implementation details belong in inline comments within the function body.

---

## Before You Push

### 6. Run the spec traceability check

Before committing, ensure the CI check will pass:

```bash
pytest tests/test_spec_traceability.py -v
```

**Expected output for a clean state:**

```
test_spec_traceability.py::test_no_dangling_spec_refs PASSED
test_spec_traceability.py::test_no_unimplemented_specs PASSED
test_spec_traceability.py::test_spec_id_format PASSED
test_spec_traceability.py::test_no_revision_mismatches PASSED
```

**If a check fails:**

- **ORPHANED (dangling spec refs):** A code docstring references a SPEC-ID that does not exist. Check for typos in the `:spec:` field or `References` block. Verify the spec file exists.
- **UNCOVERED (unimplemented specs):** A spec section ID is not referenced in any code. Either the code does not exist yet (expected for Draft specs), or a new module was added without updating the docstring. Add the missing reference.
- **Malformed ID:** A SPEC-ID does not match the format `SPEC-{SUBSYSTEM}-{NN}~v{N}`. Check for typos or missing revision numbers.

### 7. Update the spec's "Implementing Modules" table

If you created a new module, update the spec section's "Implementing Modules" table to list it:

```markdown
### Implementing Modules

| Module | Role |
|--------|------|
| `claude_mpm.hooks.dispatcher` | Event routing |
| `claude_mpm.hooks.handlers` | Handler registration and invocation |
```

Commit this update in the same PR as your code changes.

---

## In Your PR Description

### 8. Confirm spec linkage in the PR

Add a checklist item to your PR description (or include in the body):

```markdown
- [x] Spec linkage is consistent and CI traceability checks pass
- [x] Module docstrings include References blocks with SPEC-IDs
- [x] Function docstrings include :spec: fields where applicable
- [x] Spec "Implementing Modules" table was updated
- [x] All SPEC-ID revisions match the current spec section revision
```

Include a brief summary if you created or updated a spec:

```markdown
Spec updates:
- Updated SPEC-HOOKS-01~v1 Rationale section to reflect async handler dispatch
- Added SPEC-HOOKS-03~v1 for new timeout handling subsystem
```

### 9. Code review: Verify spec correctness (not just syntax)

During review, a human (ideally the documentation owner) should verify:

1. **Do the docstring spec references actually point to the correct spec sections?** The CI check verifies that the links exist, not that they are semantically correct. A wrong reference can slip through syntactic validation.

2. **Does the code behavior match what the spec promises in the Behavior Contract?** If the code does not match the WHAT section, either the code is wrong or the spec needs updating.

3. **If a spec was updated, do all downstream references make sense?** A revision bump (e.g., `~v1` → `~v2`) signals that the behavior contract changed. All code should have been updated to reference `~v2`. If some code still says `~v1`, that's either a bug or a sign that the code does not implement the new contract.

---

## If No Spec Exists

### Before implementing a new subsystem:

1. **Create or update the appropriate spec file** in `docs/specs/{subsystem}.md`.

2. **Write a spec section** with a stable SPEC-ID:

```markdown
## {Section Title} {#SPEC-{SUBSYSTEM}-{NN}}

**ID:** SPEC-{SUBSYSTEM}-{NN}~v1
**Status:** Draft (until code review is complete)

### Behavior Contract

- **Inputs:** ...
- **Outputs:** ...
- **Preconditions:** ...
- **Postconditions:** ...
- **Error conditions:** ...

### Rationale

- ...

### Implementing Modules

| Module | Role |
|--------|------|
| (to be filled during implementation) | |
```

3. **Mark the spec as Draft** until implementation is complete and reviewed.

4. **Implement the code** following steps 4–8 above.

5. **Update the spec Status to Active** once code review is complete and the implementation matches the spec.

---

## Common Patterns

### Pattern 1: Single module implementing one spec

**Spec:** `SPEC-HOOKS-01~v1`
**Module:** `claude_mpm/hooks/dispatcher.py`

```python
"""Hook dispatcher."""

"""
...
References
----------
SPEC-HOOKS-01~v1 : docs/specs/hooks.md#SPEC-HOOKS-01
"""
```

All functions in the module implicitly reference the module-level spec. No need for `:spec:` fields on individual functions unless they implement a *different* spec section.

### Pattern 2: One module implementing multiple specs

**Spec:** `SPEC-HOOKS-01~v1`, `SPEC-HOOKS-02~v1`
**Module:** `claude_mpm/hooks/dispatcher.py`

```python
"""Hook dispatcher."""

"""
...
References
----------
SPEC-HOOKS-01~v1 : docs/specs/hooks.md#SPEC-HOOKS-01
SPEC-HOOKS-02~v1 : docs/specs/hooks.md#SPEC-HOOKS-02
"""

def dispatch(event):
    """Route the event."""
    # Implements SPEC-HOOKS-01 (routing)
    # :spec: SPEC-HOOKS-01~v1

def register_handler(event_type, handler):
    """Register a handler."""
    # Implements SPEC-HOOKS-02 (registration)
    # :spec: SPEC-HOOKS-02~v1
```

Each function clarifies which specific spec section it implements.

### Pattern 3: Multiple modules implementing one spec

**Spec:** `SPEC-HOOKS-01~v1`
**Modules:** `claude_mpm/hooks/dispatcher.py`, `claude_mpm/hooks/registry.py`

Both modules list the spec in their module-level `References` block. The spec section's "Implementing Modules" table lists both:

```markdown
### Implementing Modules

| Module | Role |
|--------|------|
| `claude_mpm.hooks.dispatcher` | Event routing logic |
| `claude_mpm.hooks.registry` | Handler registry management |
```

---

## Troubleshooting

### "My code compiles but CI fails with ORPHANED"

A `:spec:` field or `References` block references a SPEC-ID that doesn't exist.

**Fix:**
1. Search `docs/specs/` for the SPEC-ID. Check spelling.
2. Verify the spec file exists and contains the section.
3. If the spec was renamed or deleted, update code references or restore the spec.

### "The spec changed but my code references the old revision"

A spec section's Behavior Contract changed (status upgraded from Draft to Active, or requirement refined). The revision should have been bumped (`~v1` → `~v2`).

**Fix:**
1. Update code references from `SPEC-ID~v1` to `SPEC-ID~v2`.
2. If the code behavior does NOT match the new spec, either:
   - Modify the code to match the new spec, OR
   - Revert the spec change and keep the `~v1` reference

### "Another function in my module implements a different spec"

Separate spec sections should be referenced explicitly to avoid confusion.

**Fix:**
```python
def function_a():
    """Implements SPEC-A."""
    # ...
    :spec: SPEC-SUBSYSTEM-01~v1

def function_b():
    """Implements SPEC-B."""
    # ...
    :spec: SPEC-SUBSYSTEM-02~v1
```

This makes it clear which function implements which spec, even if both functions are in the same module.

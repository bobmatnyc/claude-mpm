# Documentation Agent Workflow: SLD Step-by-Step

When you are authoring, reviewing, or maintaining specification documents in `docs/specs/`, follow this workflow to ensure specs are accurate, complete, and properly linked to implementation.

## When Authoring a New Spec Section

### 1. Assign a stable SPEC-ID

Choose a subsystem name (e.g., `HOOKS`, `AGENTS`, `SESSIONS`) and the next available number in that subsystem.

**Format:** `SPEC-{SUBSYSTEM}-{NN}~v1`

**Example:** `SPEC-HOOKS-03~v1` (third spec section in the hooks subsystem)

**Rules:**
- Use uppercase letters and digits in the subsystem name.
- Number sequentially within each subsystem.
- Start with `~v1` (revision 1). You will bump the revision if the behavior contract changes later.
- The ID must be globally unique across all spec files in `docs/specs/`.

### 2. Create the spec section structure

Use the canonical template:

```markdown
## {Section Title} {#SPEC-{SUBSYSTEM}-{NN}}

**ID:** SPEC-{SUBSYSTEM}-{NN}~v1
**Status:** Draft
**Last reviewed:** YYYY-MM-DD

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
- Why this behavior is important to the system...

### Implementing Modules

| Module | Role |
|--------|------|
| (to be filled during implementation) | |
```

**Why this structure?**

- **Behavior Contract is mandatory:** Specifies what the subsystem does (WHAT), from the caller's perspective. Observable, testable, no implementation details.
- **Rationale is mandatory:** Explains why this design was chosen (WHY), what constraints or goals it serves. Helps future maintainers understand the reasoning.
- **Implementing Modules table is maintained manually but validated by CI:** When engineers implement the spec, they add their modules to this table. CI checks ensure the table does not become stale.

### 3. Write clear, contract-focused behavior

**DO:**
- Describe inputs and outputs in terms of their observable properties.
- State preconditions and postconditions as testable assertions.
- Name error conditions explicitly.
- Focus on the contract as seen from outside the subsystem.

**Example (GOOD):**
```markdown
### Behavior Contract

- **Inputs:** A hook event dict with keys 'event_type' (str), 'payload' (dict), optional 'metadata' (dict).
- **Outputs:** A response dict with keys 'success' (bool), 'data' (JSON-serializable), optional 'error' (str).
- **Preconditions:** A handler must be registered for the event_type.
- **Postconditions:** The response is always a dict; never None.
- **Error conditions:**
  - If event_type is not registered, raise KeyError with message "Handler not found: {event_type}".
  - If the handler exceeds timeout (see Rationale), raise TimeoutError.
```

**DON'T:**
- Describe implementation steps ("First, we check the registry. Then, we invoke the handler...").
- Include code snippets or pseudo-code in the spec.
- Assume internal data structures (e.g., "The handler dict keys are...").

**Example (BAD):**
```markdown
### Behavior Contract

- **Steps:**
  1. Check if event_type is in the handlers dict.
  2. Get the handler function.
  3. Call handler(event, context).
  4. Return the response.
```

### 4. Write rationale that explains design choices

**DO:**
- Explain why this behavior is designed this way.
- State constraints (performance, compatibility, architectural).
- Reference related specs or architecture decisions.
- Explain what would happen if the design were different.

**Example (GOOD):**
```markdown
### Rationale

- **Why this interface?** Hook events must be JSON-serializable for cross-process relay via stdout/stdin. The dict format (event_type, payload, metadata) balances terseness with extensibility.
- **Why precondition on handler registration?** Failing fast (KeyError) on unregistered event types catches configuration errors early, rather than silently ignoring unknown events.
- **Why timeout?** Claude Code's hook system requires a sub-50ms response. A misbehaving handler could stall the entire IDE. The timeout (configurable; default 5s for testing) prevents indefinite waits.
- **Why async support?** Some handlers need to await I/O. The dispatcher must support async handlers transparently, not force synchronous-only.
```

**DON'T:**
- State the obvious ("We do this because it's the right thing to do").
- Include implementation rationale ("We use a dict because dicts are fast in Python").
- Leave the rationale empty or generic.

### 5. Fill the Implementing Modules table during review

As engineers implement the spec, they will add their modules to the `Implementing Modules` table. Your role is to **verify** the table is complete and accurate.

**Before merging the engineer's PR:**
1. Check that every module listed in the table actually exists in the codebase.
2. Verify each module has a docstring with a `References` block pointing to this spec.
3. Check that the Role column briefly explains what each module contributes to implementing the spec.

**Update template:**
```markdown
| Module | Role |
|--------|------|
| `claude_mpm.hooks.dispatcher` | Routes hook events to registered handlers |
| `claude_mpm.hooks.registry` | Manages handler registration and lookup |
| `claude_mpm.scripts.claude-hook-fast` | Shell script that invokes the dispatcher from Claude Code |
```

---

## When Reviewing Existing Specs

### 6. Check for spec drift

Every 90 days, review each spec section to verify it still matches the code.

**Checklist:**
- [ ] Does the Behavior Contract still match the code behavior? (Run the code; test the contract.)
- [ ] If the code behavior changed, was the spec updated and the revision bumped?
- [ ] Are all modules listed in "Implementing Modules" still implementing this spec? (Check for refactors, deletions, renames.)
- [ ] Does the Rationale still explain the current design? (Or has the design rationale changed?)

**If you find drift:**
1. Update the spec section to match current code.
2. Bump the revision: `~v1` → `~v2`.
3. Alert engineers that code referencing `~v1` will fail the OUTDATED check until they update their docstrings.
4. Update the "Last reviewed" date.

### 7. Verify WHAT/WHY/HOW boundaries

**Behavior Contract (WHAT) should:**
- Describe observable inputs, outputs, preconditions, postconditions.
- Be testable by a third party who hasn't read the code.
- Remain stable even if implementation details change.

**Rationale (WHY) should:**
- Explain design choices and constraints.
- Reference related specs or architecture decisions.
- Clarify why this behavior is important.

**Code (HOW) is in:**
- Docstrings: implementation-agnostic description of what the function does.
- Inline comments: the *reasoning* for non-obvious implementation choices.
- Code itself: the actual steps.

**If the spec describes HOW, rewrite it to focus on WHAT/WHY:**

**BAD (HOW in spec):**
```markdown
### Behavior Contract

The dispatcher maintains an internal dict `_handlers` where keys are event_type strings
and values are handler functions. When dispatch() is called, it looks up the event_type
in _handlers and invokes the function.
```

**GOOD (WHAT/WHY in spec):**
```markdown
### Behavior Contract

- **Inputs:** A hook event dict with 'event_type' key (str).
- **Outputs:** A response dict from the handler.
- **Preconditions:** A handler must be registered for the event_type.
- **Error conditions:** KeyError if event_type is not registered.

### Rationale

Handlers are registered by event_type to enable dynamic registration without
hardcoding handler dispatch logic.
```

### 8. Verify CI will pass

Before marking a spec section as Active, ensure it passes the CI traceability check:

```bash
pytest tests/test_spec_traceability.py::test_no_unimplemented_specs -v
```

**Expected behavior:**
- If the spec is marked `Status: Draft`, it's OK if no code references it yet.
- If the spec is marked `Status: Active`, at least one code module must reference it via `:spec:` or `References`.

**If CI fails with UNCOVERED:**
The spec section exists but no code references it. Either:
1. The code doesn't exist yet (mark the spec as Draft until implementation is ready), OR
2. Engineers implemented the code but forgot to add spec references to docstrings (ask them to update docstrings).

---

## When a Spec Section Needs to Change

### 9. Distinguish between minor clarifications and behavior changes

**Minor clarification (do NOT bump revision):**
- Typo fixes
- Rephrasing for clarity (meaning unchanged)
- Adding examples
- Improving Rationale

**Behavior change (DO bump revision):**
- Changing inputs, outputs, or error conditions
- Adding or removing preconditions/postconditions
- Changing constraints (e.g., timeout value)
- Changing the behavior contract in any way

### 10. Bump revision and alert engineers

When the behavior contract changes:

1. **Update the ID:** `SPEC-HOOKS-01~v1` → `SPEC-HOOKS-01~v2`
2. **Update the spec section:** Change `**ID:** SPEC-HOOKS-01~v1` to `**ID:** SPEC-HOOKS-01~v2`
3. **Update Markdown anchor:** Change `{#SPEC-HOOKS-01}` to `{#SPEC-HOOKS-01}` (no change needed; the anchor stays the same)
4. **Update "Last reviewed"** date.
5. **Alert engineers:** Any code referencing `SPEC-HOOKS-01~v1` will fail the OUTDATED check. They must update docstrings to `SPEC-HOOKS-01~v2`.

**Example of a PR that changes a spec:**
```
Title: docs: bump SPEC-HOOKS-01 to v2 — add timeout requirement

Content:
- Changed Behavior Contract: added timeout error condition
- Updated Rationale: explain new 5-second timeout constraint
- Version bumped: SPEC-HOOKS-01~v1 → SPEC-HOOKS-01~v2
- CI will flag code referencing ~v1 as OUTDATED until updated
```

---

## Applying the Diataxis Framework

SLD specifications should live in two of the four Diataxis quadrants:

| Quadrant | Content | Example |
|----------|---------|---------|
| **Explanation** | Why this design | Rationale section of spec |
| **Reference** | Precise contract definition | Behavior Contract section |
| **How-to** | Step-by-step procedures | **AVOID IN SPECS** — this belongs in tutorials or guides |
| **Tutorial** | "Learn by doing" | **AVOID IN SPECS** — this belongs in getting-started docs |

**Rule:** Spec sections should be **Explanation + Reference only.** Do not add How-to guides or tutorials to specs. Those belong in separate documentation files.

**Bad example (How-to in spec):**
```markdown
### Behavior Contract

To dispatch a hook:

1. Create an event dict.
2. Call dispatch_hook(event, context).
3. Check the response['success'] bool.
```

**Good example (Reference + Explanation):**
```markdown
### Behavior Contract

- **Inputs:** event dict with 'event_type' (str) and 'payload' (dict).
- **Outputs:** response dict with 'success' (bool) and 'data'.
- **Error conditions:** KeyError if event_type not registered.

### Rationale

The dispatcher is designed to handle unknown event types by failing fast,
making configuration errors visible immediately rather than silently dropping events.
```

---

## Common Patterns

### Pattern 1: Single, stable spec

The spec section covers a single, well-understood subsystem that rarely changes.

**Status:** Active
**Revision:** ~v1 (unchanged for months/years)
**Implementing Modules:** Stable list

**Example:** Hook dispatcher, which has been stable since 2024.

### Pattern 2: Rapidly evolving spec

The spec section covers new functionality that is still being designed and refined.

**Status:** Draft
**Revision:** Frequent bumps (~v1 → ~v2 → ~v3 as requirements clarify)
**Implementing Modules:** Table updated in lockstep with spec changes

**Example:** Session recovery, which is under active development.

### Pattern 3: Spec with multiple independent implementations

A single spec section is implemented by multiple teams/modules in different subsystems.

**Behavior Contract:** Describes a protocol or interface (e.g., "hook handler registration").
**Implementing Modules:** Lists all implementations.

**Example:**
```markdown
### Implementing Modules

| Module | Role |
|--------|------|
| `claude_mpm.hooks.dispatcher` | Pre-tool-use hook dispatcher |
| `claude_mpm.hooks.post_tool_dispatcher` | Post-tool-use hook dispatcher |
| `claude_mpm.sessions.lifecycle` | Session lifecycle hooks |
```

---

## Troubleshooting

### "CI says UNCOVERED: SPEC-HOOKS-01 has no code references"

The spec exists but no code docstring references it.

**Cause:** Either the code doesn't exist yet, or engineers implemented it but forgot to add spec references.

**Fix:**
1. If the code exists, ask engineers to add `:spec: SPEC-HOOKS-01~v1` to their docstrings.
2. If the code doesn't exist, mark the spec as `Status: Draft` until implementation is ready.

### "CI says ORPHANED: code references SPEC-HOOKS-01 but spec doesn't exist"

Code references a SPEC-ID that is not in `docs/specs/`.

**Cause:** Typo in code reference, or the spec was deleted/renamed.

**Fix:**
1. Check for typos in the code `:spec:` field.
2. If the spec was renamed, update code to reference the new ID.
3. If the spec was deleted intentionally, remove the `:spec:` field from code.

### "Code says ~v1 but the spec is at ~v2"

The spec's behavior changed, but code hasn't been updated yet.

**Cause:** Revision was bumped in the spec, but code references are stale.

**Fix:**
1. Engineers must update all `:spec: SPEC-HOOKS-01~v1` to `:spec: SPEC-HOOKS-01~v2` in docstrings.
2. Confirm the code behavior actually matches the new spec.
3. If code doesn't match the new spec, revert the revision bump and discuss with the code owner.

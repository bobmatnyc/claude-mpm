# Granularity Guide

How to decide whether a behavior is **one** spec ID, **several**, or **none** (folded into a
larger section). Agent-facing copy of [`docs/specs/AUTHORING.md` §5](../../../../../../../docs/specs/AUTHORING.md).
Granularity discipline is what keeps the traceability graph meaningful: too coarse and an ID
spans untestable territory; too fine and the spec drowns in trivia.

---

## 1. The litmus test

> **One spec ID = one independently-verifiable behavior.**
>
> *Could you write a single test that passes or fails against this section's Behavior Contract?*

- **Yes, one test** → one ID.
- **Needs several unrelated tests that pass/fail independently** → probably several IDs.
- **Cannot write any meaningful test in isolation** → too small; fold it into a larger section.

The test is about the **Behavior Contract**, not the code. A 300-line function with one
observable contract is one ID. Five 10-line functions that together implement one contract are
also one ID.

---

## 2. Too broad

**Symptom:** the section title is a subsystem summary, and the Behavior Contract lists
unrelated input/output clusters.

> ❌ "The hooks subsystem dispatches events."

You cannot write *one* test for it. PreToolUse enforcement, PostToolUse observability, and Stop
handling each have distinct inputs, outputs, and error modes.

**Fix — split** into:
- `SPEC-HOOKS-05~1` PreToolUse enforcement pipeline
- `SPEC-HOOKS-06~1` PostToolUse observability pipeline
- `SPEC-HOOKS-07~1` Stop lifecycle handler

Each now has a single, testable contract.

### Split when a section has

- Multiple, **unrelated** error-condition clusters.
- Distinct callers relying on distinct, **separable** outputs.
- Contract clauses that have no logical reason to change together (changing one would not
  ripple into the other).

---

## 3. Too narrow

**Symptom:** the section describes an implementation detail, not an externally observable
contract.

> ❌ "The dispatcher lowercases the event name before routing."

That is a step inside a larger behavior (event routing). It is not independently verifiable from
the caller's perspective — a caller cannot observe the lowercasing, only the routing result.

**Fix — merge** it into the WHAT of the routing section. It is a detail of `SPEC-HOOKS-03~1`
(event routing), not its own ID.

### Merge when sections share

- The **same inputs/outputs** and the **same implementing module**, differing only in incidental
  detail.
- A contract where changing one **inevitably** changes the other — they are one behavior
  described twice.

---

## 4. Worked examples

### Example A — correctly split

A session manager that (1) creates sessions and (2) resumes them from disk. Different inputs
(new vs. existing session ID), different outputs (fresh state vs. restored state), different
error modes (quota vs. corrupt-file). → **two IDs**: `SPEC-SESSIONS-01~1` (create),
`SPEC-SESSIONS-02~1` (resume).

### Example B — correctly merged

A validator that checks a config dict has keys `a`, `b`, and `c`. Three checks, but one
contract ("config is structurally valid"), one input, one output, one caller. → **one ID**; the
three checks are bullets inside the Behavior Contract's Preconditions/Error conditions.

### Example C — the gray zone

A retry wrapper that retries on 429 and on 5xx. Are these one behavior or two? Apply the test:
*does a single test exercise both?* If the retry policy is one function with one config, it is
**one ID** (`SPEC-…-NN~1`) whose Error conditions enumerate both triggers. If 429 and 5xx are
handled by separately-configured, separately-owned code paths, split.

---

## 5. `~rev` bumps

The `~{rev}` suffix tracks **material changes to the behavior contract** — inputs, outputs,
pre/postconditions, error conditions. Authority: [`README.md` §4](../../../../../../../docs/specs/README.md).

| Change | Bump `~rev`? |
|--------|--------------|
| Added a new error condition | **Yes** — contract changed |
| Changed an output type or guarantee | **Yes** |
| Tightened a precondition | **Yes** |
| Reworded the Rationale for clarity | No |
| Fixed a typo | No |
| Added an Implementing Modules row | No |

When you bump, any docstring still referencing the old `~rev` is flagged **OUTDATED** by the CI
checker — that is the intended signal that code must re-acknowledge the new contract.

---

## 6. Alignment with the SLD WWL model

Spec granularity and **code-link** granularity should be consistent. SLD's WWL model
([`README.md` §6a](../../../../../../../docs/specs/README.md)) says a function requires its own
WHAT/WHY/LINK docstring when it exceeds **50 LOC** or **cyclomatic complexity 10**.

Rule of thumb:

- A behavior that justifies its own spec ID usually governs code that crosses a WWL threshold.
- A behavior too small to warrant a WWL link is usually too small to warrant its own spec ID —
  fold it into a larger section's WHAT.

If you find a spec ID whose only implementing code is a 5-line helper below both thresholds,
that ID is probably too narrow (§3).

---

## 7. Quick checklist

Before finalizing a section's granularity:

- [ ] One Behavior Contract, one test could pass/fail against it.
- [ ] No unrelated error-condition clusters in the same section.
- [ ] No implementation-detail-only sections (those fold into a WHAT).
- [ ] Implementing code plausibly crosses a WWL threshold (else reconsider).
- [ ] If you split, each new ID has its own clean contract and a ToC row.

---

## See also

- [`spec-template.md`](spec-template.md) — the section structure you are sizing.
- [`category-taxonomy.md`](category-taxonomy.md) — which file the section(s) live in.
- [`docs/specs/AUTHORING.md` §5](../../../../../../../docs/specs/AUTHORING.md) — the authoritative rules.

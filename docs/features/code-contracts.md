# Code Contracts

## Overview

Code Contracts make the obligations of a function explicit and machine-checkable. A contract answers three questions: what must be true before calling a function (preconditions), what the function guarantees on return (postconditions), and what must remain true across every observable state of an object (invariants).

In an AI-assisted development workflow, contracts serve a second purpose beyond runtime safety: they are the specification the AI must satisfy. When a claude-mpm engineer agent implements a function with contracts already attached, the contracts constrain the implementation space and eliminate guessing. When the QA agent reviews the result, the contracts drive the test plan — one unit test per postcondition, one violation test per precondition, and property-based tests that encode the preconditions as generator constraints.

### Why contracts matter for AI-assisted development

- **Precision**: Contracts express intent that prose descriptions cannot. "Returns the top K elements" is ambiguous. `len(result) == min(k, len(items))` is not.
- **Testability**: Every contract produces at least two tests — a test that the contract is satisfied, and a test that violation raises an error.
- **Reviewability**: The code-critic agent can verify that an implementation satisfies its contracts mechanically, without relying on understanding the algorithm.
- **Persistence**: Contracts stay in the codebase after the AI context window closes. They document the spec for the next engineer, human or AI.

---

## The Three-Level Approach

Claude-mpm engineer agents write contracts alongside (or before) the implementation. QA agents then derive a three-level testing pyramid directly from those contracts.

### Level 1 — Contract-targeted unit tests

One focused test per postcondition. The test name is derived from the postcondition text. Both the happy path and boundary conditions for each postcondition are covered.

### Level 2 — Property-based tests

Each postcondition becomes a property assertion. Preconditions are encoded as generator constraints — not as filter/rejection logic. `hypothesis` (Python), `fast-check` (TypeScript/JS), and `quickcheck` (Rust) are the preferred frameworks.

### Level 3 — Precondition violation tests

One negative test per distinct precondition. The test verifies that the contract fails loudly with a useful error message, and that valid inputs never trigger spurious violations.

### When there are no contracts yet

If the function has no contracts, QA flags it for the engineer if the function is complex or critical, infers implicit contracts from the docstring and observable behavior, and writes property-based tests against the inferred properties.

---

## Language Reference

### Python — `icontract`

`icontract` is the preferred library. Unlike `assert`, it stays active under `python -O` and produces rich violation messages that include the failed expression and local variable values.

```python
pip install icontract
```

| Decorator | Purpose |
|-----------|---------|
| `@icontract.require(lambda ...: ...)` | Precondition — checked on entry |
| `@icontract.ensure(lambda result, ...: ...)` | Postcondition — checked on return |
| `@icontract.invariant(lambda self: ...)` | Class invariant — checked after `__init__` and every public method |

The `result` parameter in `@icontract.ensure` is bound to the return value. Capture pre-call state using `icontract.snapshot`.

### TypeScript / JavaScript — guard functions

No dominant contract library exists for TypeScript. The standard pattern is a guard function:

```typescript
function requires(condition: boolean, message: string): void {
  if (process.env.NODE_ENV !== 'production' && !condition) {
    throw new Error(`Precondition violated: ${message}`);
  }
}

function ensures(condition: boolean, message: string): void {
  if (process.env.NODE_ENV !== 'production' && !condition) {
    throw new Error(`Postcondition violated: ${message}`);
  }
}
```

For library code that needs contracts in production, the `ts-code-contracts` package provides decorator-style annotations.

### Rust — `debug_assert!` and the `contracts` crate

Use `debug_assert!` for conditions that should only be checked in development and test builds. Use `assert!` for production-critical invariants, particularly on security paths.

```rust
fn top_k(items: &[f64], k: usize) -> Vec<f64> {
    debug_assert!(!items.is_empty(), "items must be non-empty");
    debug_assert!(k > 0, "k must be positive");

    let mut sorted = items.to_vec();
    sorted.sort_by(|a, b| b.partial_cmp(a).unwrap());
    sorted.truncate(k);

    debug_assert!(sorted.len() <= items.len());
    sorted
}
```

The `contracts` crate provides `#[requires(...)]` and `#[ensures(...)]` proc-macro attributes for formal contract syntax.

### Java — Guava Preconditions

```java
import com.google.common.base.Preconditions;

public List<Double> topK(List<Double> items, int k) {
    Preconditions.checkArgument(!items.isEmpty(), "items must be non-empty");
    Preconditions.checkArgument(k > 0, "k must be positive, was %s", k);

    return items.stream()
        .sorted(Comparator.reverseOrder())
        .limit(k)
        .collect(Collectors.toList());
}
```

For postconditions in Java, use plain `assert` statements (enabled with `-ea` JVM flag) or explicit `if/throw` checks for conditions that must hold in production.

---

## Python Example — Full Contract Set

The following function collects the K largest elements from a list. All three contract elements are present.

```python
import icontract


@icontract.require(lambda items: len(items) > 0, "items must be non-empty")
@icontract.require(lambda k: k > 0, "k must be positive")
@icontract.ensure(lambda result, items: len(result) <= len(items))
@icontract.ensure(lambda result, k, items: len(result) == min(k, len(items)))
@icontract.ensure(lambda result, items: all(x in items for x in result))
def top_k(items: list[float], k: int) -> list[float]:
    """Return the K largest elements of items in descending order.

    Postconditions establish:
    - Result is a subset of the input (no fabricated values).
    - Result length is exactly min(k, len(items)) — not more, not fewer.
    """
    return sorted(items, reverse=True)[:k]
```

The contracts communicate three things that the type signature does not:

1. An empty `items` list is not a valid input.
2. `k=0` is not valid — the caller always wants at least one result.
3. The returned values come from `items` — the implementation cannot invent new values.

### Adding an invariant to a class

```python
@icontract.invariant(lambda self: self._size >= 0, "size must be non-negative")
@icontract.invariant(lambda self: self._size <= self._capacity, "size cannot exceed capacity")
class BoundedQueue:
    def __init__(self, capacity: int) -> None:
        self._capacity = capacity
        self._items: list = []
        self._size = 0

    @icontract.require(lambda item: item is not None)
    @icontract.ensure(lambda self: self._size == icontract.OLD(self._size) + 1)
    def enqueue(self, item: object) -> None:
        if self._size >= self._capacity:
            raise OverflowError("Queue is full")
        self._items.append(item)
        self._size += 1
```

`icontract.OLD` captures the value of an expression at method entry, enabling postconditions that describe mutations.

---

## Property-Based Testing

Property-based tests express what must be true for all valid inputs, not just the specific inputs in the example. The test framework generates hundreds of inputs that satisfy the preconditions and verifies that each postcondition holds.

### Python — `hypothesis`

```python
from hypothesis import given, settings
import hypothesis.strategies as st
import pytest

from mymodule import top_k


@given(
    items=st.lists(st.floats(allow_nan=False, allow_infinity=False), min_size=1),
    k=st.integers(min_value=1, max_value=1000),
)
def test_top_k_all_postconditions(items: list[float], k: int) -> None:
    result = top_k(items, k)

    # Postcondition 1: result is a subset of inputs
    assert all(x in items for x in result)

    # Postcondition 2: result length is exactly min(k, len(items))
    assert len(result) == min(k, len(items))

    # Postcondition 3: result is bounded by input length
    assert len(result) <= len(items)
```

The generator constraints (`min_size=1`, `min_value=1`) encode the preconditions. Do not filter with `hypothesis.assume()` when a generator constraint will do — `assume()` wastes generated inputs and slows shrinking.

The `icontract-hypothesis` package can automatically infer strategies from `icontract` decorators:

```python
from icontract_hypothesis import from_contracts

@given(from_contracts(top_k))
def test_top_k_auto(items: list[float], k: int) -> None:
    result = top_k(items, k)
    assert len(result) == min(k, len(items))
```

### TypeScript — `fast-check`

```typescript
import * as fc from 'fast-check';
import { topK } from './sorting';

test('topK postconditions hold for all valid inputs', () => {
  fc.assert(
    fc.property(
      fc.array(fc.float({ noNaN: true }), { minLength: 1 }),  // encodes: items non-empty
      fc.integer({ min: 1, max: 1000 }),                       // encodes: k > 0
      (items, k) => {
        const result = topK(items, k);

        // All results came from items
        expect(result.every(x => items.includes(x))).toBe(true);

        // Correct count
        expect(result.length).toBe(Math.min(k, items.length));
      }
    )
  );
});
```

---

## Production vs. Test

### Python `icontract` behavior

`icontract` raises `icontract.ViolationError` by default in all environments. Contracts can be globally disabled with:

```python
import icontract
icontract.DISABLE = True
```

This is appropriate only for verified production hot paths where profiling has confirmed the contract overhead is material. It must never be applied per-module or per-function selectively.

Plain Python `assert` is disabled when the interpreter runs with `-O` (optimize flag). Do not use `assert` for contracts that must hold in production.

### When to disable contracts

| Situation | Action |
|-----------|--------|
| Production hot path, profiling shows overhead | Disable globally with `icontract.DISABLE = True`, document why |
| All test environments | Contracts always enabled |
| Security-critical paths (auth, permissions, irreversible operations) | Contracts always enabled, never disabled |
| Development and CI | Contracts always enabled |

### TypeScript guard function behavior

The guard function pattern above checks `process.env.NODE_ENV !== 'production'`. This is a sensible default for client-side code, but server-side validation on API boundaries should use unconditional checks regardless of `NODE_ENV`:

```typescript
// Server-side API handler — check unconditionally
function processPayment(amount: number): void {
  if (amount <= 0) throw new Error('amount must be positive');
  // ...
}
```

---

## Anti-Patterns

### Side effects in contract expressions

Contract expressions must be pure. No logging, no mutation, no I/O.

```python
# WRONG — logs on every call, even passing calls
@icontract.require(lambda items: (print(f"checking {items}"), len(items) > 0)[1])

# CORRECT
@icontract.require(lambda items: len(items) > 0, "items must be non-empty")
```

### Restating type annotations

Contracts that duplicate what the type system already enforces add noise without value.

```python
# WRONG — the type annotation already says List[float]
@icontract.require(lambda items: isinstance(items, list))

# CORRECT — contracts express domain restrictions the type system cannot
@icontract.require(lambda items: len(items) > 0)
@icontract.require(lambda items: all(math.isfinite(x) for x in items))
```

### Postconditions that redescribe the implementation

A postcondition that is just a restatement of the implementation code provides no independent check.

```python
# WRONG — this is just the implementation written twice
@icontract.ensure(lambda result, items, k: result == sorted(items, reverse=True)[:k])

# CORRECT — verify properties, not the algorithm
@icontract.ensure(lambda result, items: all(x in items for x in result))
@icontract.ensure(lambda result, k, items: len(result) == min(k, len(items)))
```

### Untested contracts

Every contract needs a Level 3 violation test. A contract that is never exercised by a failing test may be silently incorrect.

```python
# A contract without a violation test
@icontract.require(lambda k: k > 0)  # Is this firing when k=0? Only a test proves it.
```

---

## How the Agents Use This

### Engineer agents

Engineer agents (`BASE_ENGINEER.md`) write contracts before or alongside the implementation. The decision of when to write contracts is part of the engineering process:

- **Complex algorithms**: Distributed systems, state machines, search and sort, consensus protocols.
- **Domain-restricted inputs**: Functions that reject a portion of the type's value space (positive numbers, non-empty collections, sorted arrays).
- **Module boundaries**: Public API functions that other modules depend on.
- **Any function an AI will implement**: The contract is the specification the AI must satisfy.
- **Security-sensitive functions**: These keep contracts active in production.

### QA agents (code-critic)

The code-critic agent (`code-critic.md`) applies the three-level pyramid when reviewing functions that carry contracts. The contracts are the test plan — the agent does not need to infer test cases from prose descriptions.

The agent also runs a contract review checklist during code review:

- Every postcondition references `result`, not just side effects.
- Relational postconditions are present (ordering, identity) — not just existence checks.
- No side effects in contract expressions.
- `OLD` / `icontract.OLD` is used where mutation postconditions reference pre-call state.
- Each contract has a corresponding Level 3 violation test.

If a complex or critical function has no contracts, the agent flags it for the engineer before writing tests.

---

## Related Documentation

- [Agent System](../agents/README.md) — Overview of engineer and QA agent roles
- [Creating Agents](../agents/creating-agents.md) — How to customize agent behavior
- [Domain Authority System](domain-authority-system.md) — Agent discovery and delegation

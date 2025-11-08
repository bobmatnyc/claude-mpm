---
name: Testing Anti-Patterns
description: Never test mock behavior. Never add test-only methods to production classes. Understand dependencies before mocking.
when_to_use: when writing or changing tests, adding mocks, or tempted to add test-only methods to production code
version: 2.0.0
progressive_disclosure:
  entry_point:
    summary: "Avoid testing mocks, test-only production methods, and incomplete mocking. Test real behavior, not mock behavior."
    when_to_use: "When writing tests, adding mocks, reviewing test failures, or tempted to add test-only methods to production code."
    quick_start: "1. Ask: 'Am I testing real behavior?' 2. Check: 'Is this method only for tests?' 3. Verify: 'Do I understand what I'm mocking?' 4. Confirm: 'Is my mock complete?' 5. Apply: TDD prevents these patterns"
  references:
    - core-anti-patterns.md
    - completeness-anti-patterns.md
    - detection-guide.md
    - tdd-connection.md
---

# Testing Anti-Patterns

## Overview

Tests must verify real behavior, not mock behavior. Mocks are a means to isolate, not the thing being tested.

**Core principle:** Test what the code does, not what the mocks do.

**Following strict TDD prevents these anti-patterns.** See [test-driven-development skill](../test-driven-development/) for the complete TDD workflow.

## When to Use This Skill

Activate this skill when you're:
- **Writing or changing tests** - Verify you're testing real behavior
- **Adding mocks** - Ensure mocking is necessary and correct
- **Reviewing test failures** - Check if mock behavior is the issue
- **Tempted to add test-only methods** - STOP and reconsider
- **Tests feel overly complex** - Sign of over-mocking

## The Iron Laws

```
1. NEVER test mock behavior
2. NEVER add test-only methods to production classes
3. NEVER mock without understanding dependencies
4. NEVER create incomplete mocks
5. NEVER treat tests as afterthought
```

## Core Anti-Pattern Categories

### 1. Testing Mock Behavior
Asserting on mock elements instead of real behavior. **Fix:** Test real component or don't mock it.
**→** [core-anti-patterns.md](references/core-anti-patterns.md#anti-pattern-1-testing-mock-behavior)

### 2. Test-Only Methods in Production
Methods in production classes only used by tests. **Fix:** Move to test utilities.
**→** [core-anti-patterns.md](references/core-anti-patterns.md#anti-pattern-2-test-only-methods-in-production)

### 3. Mocking Without Understanding
Mocking without understanding dependencies/side effects. **Fix:** Understand first, mock minimally.
**→** [core-anti-patterns.md](references/core-anti-patterns.md#anti-pattern-3-mocking-without-understanding)

### 4. Incomplete Mocks
Partial mocks missing fields downstream code needs. **Fix:** Mirror complete API structure.
**→** [completeness-anti-patterns.md](references/completeness-anti-patterns.md#anti-pattern-4-incomplete-mocks)

### 5. Tests as Afterthought
Implementation "complete" without tests. **Fix:** TDD - write test first.
**→** [completeness-anti-patterns.md](references/completeness-anti-patterns.md#anti-pattern-5-integration-tests-as-afterthought)

## Quick Detection Checklist

Run this checklist before committing any test:

```
□ Am I asserting on mock elements? (testId='*-mock')
  → If yes: STOP - Test real component or unmock

□ Does this method only exist for tests?
  → If yes: STOP - Move to test utilities

□ Do I fully understand what I'm mocking?
  → If no: STOP - Run with real impl first, then mock minimally

□ Is my mock missing fields the real API has?
  → If yes: STOP - Mirror complete API structure

□ Did I write implementation before test?
  → If yes: STOP - Delete impl, write test first (TDD)

□ Is mock setup >50% of test code?
  → If yes: Consider integration test with real components
```

**See:** [detection-guide.md](references/detection-guide.md) for comprehensive red flags and warning signs.

## The Bottom Line

**Mocks are tools to isolate, not things to test.**

If you're testing mock behavior, you've gone wrong. Fix: Test real behavior or question why you're mocking at all.

**TDD prevents these patterns.** Write test first → Watch fail → Minimal implementation → Pass → Refactor.

## Navigation

### Detailed Anti-Pattern Analysis
- **[Core Anti-Patterns](references/core-anti-patterns.md)** - Patterns 1-3: Mock behavior, test-only methods, uninformed mocking
- **[Completeness Anti-Patterns](references/completeness-anti-patterns.md)** - Patterns 4-5: Incomplete mocks, tests as afterthought

### Detection & Prevention
- **[Detection Guide](references/detection-guide.md)** - Red flags, warning signs, gate functions
- **[TDD Connection](references/tdd-connection.md)** - How test-driven development prevents these patterns

### Related Skills
- **[test-driven-development](../test-driven-development/)** - Complete TDD workflow (prevents these patterns)
- **[verification-before-completion](../../../productivity/verification-before-completion/)** - Testing is part of "done"

## Key Reminders

1. **Mocks isolate, don't prove** - Test real code, not mocks
2. **Production ignores tests** - No test-only methods
3. **Understand before mocking** - Know dependencies and side effects
4. **Complete mocks only** - Mirror full API structure
5. **Tests ARE implementation** - Not optional afterthought

## Red Flags - STOP

**STOP immediately if you find yourself:**
- Asserting on `*-mock` test IDs
- Adding methods only called in test files
- Mocking "just to be safe" without understanding
- Creating mocks from memory instead of API docs
- Saying "tests can wait" or "ready for testing"

**When mocks become too complex:** Consider integration tests with real components. Often simpler and more valuable.

## Integration with Other Skills

**Prerequisite:** [test-driven-development](../test-driven-development/) - TDD prevents anti-patterns
**Complementary:** [verification-before-completion](../../../productivity/verification-before-completion/) - Tests = done
**Domain-specific:** webapp-testing, backend-testing for framework patterns

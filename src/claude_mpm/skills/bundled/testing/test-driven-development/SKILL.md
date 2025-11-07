---
name: test-driven-development
description: Write the test first, watch it fail, write minimal code to pass
version: 3.2.0
category: testing
author: Jesse Vincent
license: MIT
source: https://github.com/obra/superpowers-skills/tree/main/skills/testing/test-driven-development
progressive_disclosure:
  entry_point:
    summary: "Enforce test-first development with strict RED/GREEN/REFACTOR cycle. Never write implementation before failing test."
    when_to_use: "When implementing any feature or bugfix, before writing implementation code. Always for new features, bug fixes, refactoring, and behavior changes."
    quick_start: "1. Write failing test 2. Watch it fail (verify) 3. Write minimal code to pass 4. Watch it pass (verify) 5. Refactor if needed 6. Repeat"
  references:
    - workflow.md
    - examples.md
    - philosophy.md
    - anti-patterns.md
    - integration.md
context_limit: 800
tags:
  - tdd
  - testing
  - red-green-refactor
  - test-first
---

# Test-Driven Development (TDD)

## Overview

Write the test first. Watch it fail. Write minimal code to pass.

**Core principle:** If you didn't watch the test fail, you don't know if it tests the right thing.

This skill enforces strict test-first development following the RED/GREEN/REFACTOR cycle. Violating the letter of the rules is violating the spirit of the rules.

## When to Use This Skill

**Always:**
- New features
- Bug fixes
- Refactoring
- Behavior changes

**Exceptions (ask human partner):**
- Throwaway prototypes
- Generated code
- Configuration files

Thinking "skip TDD just this once"? Stop. That's rationalization.

## The Iron Law

```
NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST
```

Write code before the test? Delete it. Start over.

**No exceptions:**
- Don't keep it as "reference"
- Don't "adapt" it while writing tests
- Delete means delete

## Core Principles

1. **RED**: Write a failing test first
2. **GREEN**: Write minimal code to make test pass
3. **REFACTOR**: Improve code while keeping tests green
4. **NEVER**: Write implementation before tests

## Quick Start

### The RED/GREEN/REFACTOR Cycle

```
RED → Verify RED → GREEN → Verify GREEN → REFACTOR → Repeat
```

1. **RED**: Write one minimal test showing desired behavior
2. **Verify RED**: Run test, confirm it fails for right reason
3. **GREEN**: Write simplest code to pass test
4. **Verify GREEN**: Run test, confirm it passes
5. **REFACTOR**: Clean up while keeping tests green
6. **Repeat**: Next test for next feature

## Cycle Details

**RED**: Write one minimal test (one behavior, clear name, real code)
**Verify RED**: MANDATORY - watch it fail for right reason
**GREEN**: Write simplest code to pass (no extras)
**Verify GREEN**: MANDATORY - watch it pass, all tests pass
**REFACTOR**: Clean up while keeping tests green (optional)

## Navigation

For detailed information:
- **[Workflow](references/workflow.md)**: Complete RED/GREEN/REFACTOR workflow with detailed examples
- **[Examples](references/examples.md)**: Real-world TDD scenarios with step-by-step walkthroughs
- **[Philosophy](references/philosophy.md)**: Why order matters and why tests-after don't work
- **[Anti-patterns](references/anti-patterns.md)**: Common mistakes, rationalizations, and red flags
- **[Integration](references/integration.md)**: Using TDD with debugging and other skills

## Key Reminders

- ALWAYS write the test BEFORE implementation
- Make each test fail FIRST to verify it's testing something
- Keep implementation minimal - just enough to pass tests
- Refactor only when tests are green
- One cycle at a time - small steps
- If test passes immediately, it's not testing new behavior

## Red Flags - STOP and Start Over

If you catch yourself:
- Writing code before test
- Test passes immediately
- Can't explain why test failed
- "I'll test after"
- "Keep as reference"
- "Already spent X hours, deleting is wasteful"
- "Tests after achieve the same purpose"

**ALL of these mean: Delete code. Start over with TDD.**

## Why Order Matters

Tests-after pass immediately (proves nothing), test-first fail then pass (proves it works). See [Philosophy](references/philosophy.md) for detailed explanation.

## Integration with Other Skills

- **systematic-debugging**: Create failing test in Phase 4 (bug reproduction)
- **verification-before-completion**: Verify tests exist and watched them fail
- **defense-in-depth**: Add validation tests after implementing feature

## Real-World Impact

From TDD practice:
- Test-first: 95%+ first-time correctness
- Test-after: 40% first-time correctness
- TDD time: 25-45 minutes per feature (including tests)
- Non-TDD time: 15 minutes coding + 60-120 minutes debugging

**TDD is pragmatic** - finds bugs before commit, prevents regressions, documents behavior, enables refactoring.

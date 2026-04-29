---
name: test-quality-inspector
description: "Verify that a test is actually testing what it claims to test: semantic correctness, mutation-style reasoning, and mock hygiene for any language or framework"
user-invocable: true
disable-model-invocation: false
version: 1.0.0
category: testing
license: Apache-2.0
compatibility: claude-code
tags:
  - testing
  - quality-assurance
  - test-review
  - mutation-testing
  - mocking
  - semantic-correctness
progressive_disclosure:
  entry_point:
    summary: "Inspect a test for semantic correctness: does it actually test what it claims? Would it catch real bugs?"
    when_to_use: "When reviewing a test file or test suite to verify it has meaningful assertions, correct coverage of the named behavior, and would genuinely fail if the implementation broke."
    quick_start: "1. Identify the test(s) to inspect (file path or pattern). 2. Read the test and the implementation. 3. Apply the five checks below. 4. Produce a verdict with evidence. 5. Suggest concrete fixes."
  references:
    - checks.md
    - verdicts.md
    - mock-hygiene.md
    - mutation-reasoning.md
---

# Test Quality Inspector

## Overview

A passing test is not the same as a good test. This skill inspects tests for **semantic correctness** — whether the test actually verifies the behavior it claims to verify, not just whether it runs without error.

Apply this skill to any test file or suite, in any language or framework.

## When to Use

Activate when:
- Reviewing a PR that includes new or modified tests
- A test passes but a bug still shipped
- Test names feel mismatched to their assertions
- Mocks seem unusually extensive
- Coverage numbers look good but confidence is low
- Preparing to refactor and needing to trust the test harness

## Arguments

This skill accepts optional arguments:
- **File path**: `path/to/test_file.py` — inspect a specific file
- **Test name pattern**: `test_user_*` — inspect tests matching the pattern
- **No args**: inspect all tests in the current context or most recently discussed test

## Five-Step Inspection Process

### Step 1: Read the Test

Read the test file completely. Identify:
- The test name and any docstring or description
- What the test sets up (fixtures, mocks, data)
- What action it performs (the "act")
- What it asserts (the "assert")
- What it does NOT assert

### Step 2: Read the Implementation

Find and read the actual code being tested. Identify:
- The function/method signature
- All return values and side effects
- Branches and edge cases in the implementation
- What could realistically go wrong

### Step 3: Apply the Five Checks

Run all five checks. See [checks.md](references/checks.md) for detailed guidance.

**Check 1 — Name-to-Assertion Alignment**
Does the test name describe what the assertions actually verify? A test named `test_returns_empty_list_when_no_results` that only asserts `len(result) == 0` without checking the type is subtly misleading.

**Check 2 — Meaningful Assertions (No Tautologies)**
Would the assertion pass even if the implementation returned garbage? Examples of hollow assertions:
- `assert result is not None` when the function always returns an object
- `assert len(result) >= 0` (always true for lists)
- `assertTrue(True)`

**Check 3 — Mutation Failure Check**
If the implementation were deliberately broken in the most obvious way (wrong return value, off-by-one, missing branch), would this test catch it? Mentally apply one mutation at a time and ask: does the test fail?

**Check 4 — Edge Case Coverage**
If the test name references edge cases ("when empty", "when None", "at boundary"), verify those conditions are actually set up in the arrange phase and exercised in the act phase.

**Check 5 — Mock Hygiene**
Are mocks replacing so much real behavior that the test no longer exercises the code under test? Signs of hollow mocking:
- The function under test is itself mocked
- All dependencies are stubbed with hardcoded return values that match the assertion exactly
- No real logic runs between the mock setup and the assertion

### Step 4: Produce a Verdict

Issue one of four verdicts with specific evidence. See [verdicts.md](references/verdicts.md) for verdict criteria and templates.

| Verdict | Meaning |
|---------|---------|
| **CORRECT** | Test accurately names its behavior, assertions are meaningful, would catch real bugs |
| **MISLEADING** | Test passes but the name or description does not match what is actually asserted |
| **INCOMPLETE** | Test covers some of the claimed behavior but misses important assertions or edge cases |
| **BROKEN** | Test would not catch an obvious bug in the code it claims to test |

### Step 5: Suggest Fixes

For any verdict other than CORRECT, provide:
- The specific line(s) causing the issue
- A concrete example of how to fix it
- If applicable, an example of a bug the current test would fail to catch

## Quick Check Summary

```
Would this test FAIL if I:
  - Changed the return value to None?        → Check assertions
  - Removed the main branch logic?           → Check coverage
  - Swapped two arguments in the call?       → Check specificity
  - Deleted the function entirely?           → Check mock depth
  - Added a new edge case to the spec?       → Check name accuracy
```

## Red Flags — STOP and Inspect

Stop and apply full inspection when:
- Test has no assertions (or only `assert True`)
- Every dependency is mocked
- Assertion checks a value that the mock itself returns
- Test name mentions a condition that doesn't appear in the arrange phase
- Test passes with an empty implementation
- Multiple behaviors tested in one test with a vague name

## Navigation

- **[Checks Reference](references/checks.md)** — Detailed guide for all five checks with examples in Python, JavaScript, Go, and Java
- **[Verdicts and Templates](references/verdicts.md)** — Verdict criteria, evidence format, and report templates
- **[Mock Hygiene](references/mock-hygiene.md)** — When mocking is appropriate vs. when it hollows out a test
- **[Mutation Reasoning](references/mutation-reasoning.md)** — How to apply mutation-testing mindset without a mutation framework

## Related Skills

- **universal-testing-test-driven-development** — Write tests correctly from the start
- **universal-debugging-verification-before-completion** — Verify your own work before claiming completion
- **universal-testing-testing-anti-patterns** — Broader catalog of test design mistakes

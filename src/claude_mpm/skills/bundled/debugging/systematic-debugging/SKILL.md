---
name: systematic-debugging
description: Methodical debugging instead of random changes
version: 2.2.0
category: debugging
author: Jesse Vincent
license: MIT
source: https://github.com/obra/superpowers-skills/tree/main/skills/debugging/systematic-debugging
progressive_disclosure:
  entry_point:
    summary: "Replace random code changes with systematic problem diagnosis using four-phase investigation framework"
    when_to_use: "When user reports bugs, errors, test failures, or unexpected behavior. ESPECIALLY when under time pressure or 'quick fixes' seem obvious."
    quick_start: "1. Read error messages completely 2. Reproduce consistently 3. Form specific hypothesis 4. Test with single change 5. Verify fix"
  references:
    - workflow.md
    - examples.md
    - troubleshooting.md
    - anti-patterns.md
context_limit: 800
tags:
  - debugging
  - problem-solving
  - root-cause
  - systematic
requires_tools:
  - debugger
---

# Systematic Debugging

## Overview

Random fixes waste time and create new bugs. Quick patches mask underlying issues.

**Core principle:** ALWAYS find root cause before attempting fixes. Symptom fixes are failure.

This skill enforces a four-phase systematic approach that ensures root cause investigation before any fix attempt. Violating the letter of this process is violating the spirit of debugging.

## When to Use This Skill

Activate when:
- User reports a bug or error
- Test failures occur
- Code behaves unexpectedly
- Performance problems arise
- Build or integration failures
- User says "it's not working"

**Use this ESPECIALLY when:**
- Under time pressure (emergencies make guessing tempting)
- "Just one quick fix" seems obvious
- You've already tried multiple fixes
- Previous fix didn't work

## The Iron Law

```
NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST
```

If you haven't completed Phase 1, you cannot propose fixes.

## Core Principles

1. **Reproduce First**: Ensure you can reliably reproduce the issue
2. **One Change at a Time**: Change only one thing between tests
3. **Hypothesis-Driven**: Form hypotheses before making changes
4. **Verify Fixes**: Confirm the fix works and doesn't break anything else

## Quick Start

1. **Read Error Messages**: Read completely, including stack traces
2. **Reproduce Consistently**: Create reliable reproduction steps
3. **Gather Evidence**: Add diagnostic instrumentation in multi-component systems
4. **Form Hypothesis**: State clearly "I think X because Y"
5. **Test Minimally**: Make smallest possible change
6. **Verify Fix**: Confirm resolution and no regressions

## The Four Phases

### Phase 1: Root Cause Investigation

**BEFORE attempting ANY fix:**
- Read error messages carefully (they often contain the solution)
- Reproduce consistently
- Check recent changes
- Gather evidence in multi-component systems
- Trace data flow back to source

### Phase 2: Pattern Analysis

Find working examples, compare against references, identify differences, understand dependencies.

### Phase 3: Hypothesis and Testing

Form single hypothesis, test minimally (one variable at a time), verify before continuing.

### Phase 4: Implementation

Create failing test case, implement single fix addressing root cause, verify fix works.

**If 3+ fixes fail:** STOP and question the architecture - this indicates architectural problems, not failed hypotheses.

## Navigation

For detailed information:
- **[Workflow](references/workflow.md)**: Complete four-phase debugging workflow with decision trees and detailed steps
- **[Examples](references/examples.md)**: Real-world debugging scenarios with step-by-step walkthroughs
- **[Troubleshooting](references/troubleshooting.md)**: Common debugging challenges and how to overcome them
- **[Anti-patterns](references/anti-patterns.md)**: Common mistakes, rationalizations, and red flags

## Key Reminders

- NEVER make random changes hoping they'll work
- ALWAYS reproduce the issue before attempting fixes
- Form hypothesis BEFORE making changes
- Change ONE thing at a time
- Verify fix actually resolves the issue
- Check for regressions after fixing
- If 3+ fixes fail, question the architecture

## Red Flags - STOP and Follow Process

If you catch yourself thinking:
- "Quick fix for now, investigate later"
- "Just try changing X and see if it works"
- "It's probably X, let me fix that"
- "I don't fully understand but this might work"
- "One more fix attempt" (when already tried 2+)
- Each fix reveals new problem in different place

**ALL of these mean: STOP. Return to Phase 1.**

## Integration with Other Skills

- **root-cause-tracing**: How to trace back through call stack
- **defense-in-depth**: Add validation after finding root cause
- **condition-based-waiting**: Replace timeouts identified in Phase 2
- **verification-before-completion**: Verify fix worked before claiming success
- **test-driven-development**: Create failing test case in Phase 4

## Real-World Impact

From debugging sessions:
- Systematic approach: 15-30 minutes to fix
- Random fixes approach: 2-3 hours of thrashing
- First-time fix rate: 95% vs 40%
- New bugs introduced: Near zero vs common

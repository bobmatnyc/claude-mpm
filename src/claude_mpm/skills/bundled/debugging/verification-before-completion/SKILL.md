---
name: Verification Before Completion
description: Run verification commands and confirm output before claiming success
version: 2.0.0
category: debugging
author: Jesse Vincent
license: MIT
source: https://github.com/obra/superpowers-skills/tree/main/skills/debugging/verification-before-completion
progressive_disclosure:
  entry_point:
    summary: "Evidence before claims: mandatory verification before ANY completion claim"
    when_to_use: "When about to claim work is complete, fixed, passing, or ready. ESPECIALLY before commits, PRs, or task completion."
    quick_start: "1. Identify verification command 2. Run FULL command 3. Read complete output 4. Verify results 5. THEN claim with evidence"
  references:
    - gate-function.md
    - verification-patterns.md
    - common-failures.md
context_limit: 800
tags:
  - verification
  - quality-assurance
  - honesty
  - evidence
requires_tools: []
---

# Verification Before Completion

## Overview

Claiming work is complete without verification is dishonesty, not efficiency.

**Core principle:** Evidence before claims, always.

**Violating the letter of this rule is violating the spirit of this rule.**

This skill enforces mandatory verification before ANY completion claim, preventing false positives, broken builds, and trust violations.

## When to Use This Skill

Activate ALWAYS before:
- ANY variation of success/completion claims
- ANY expression of satisfaction ("Great!", "Done!", "Perfect!")
- ANY positive statement about work state
- Committing, pushing, creating PRs
- Moving to next task
- Marking tasks complete
- Delegating to agents
- Reporting status to users

**Use this ESPECIALLY when:**
- Under time pressure (makes skipping tempting)
- Tired and wanting work over
- "Quick fix" seems obvious
- Confident in the solution
- Agent reports success
- Tests "should" pass

## The Iron Law

```
NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE
```

If you haven't run the verification command in this message, you cannot claim it passes.

## Core Principles

1. **Evidence Required**: Every claim needs supporting evidence
2. **Fresh Verification**: Must verify now, not rely on previous runs
3. **Complete Verification**: Full command, not partial checks
4. **Honest Reporting**: Report actual state, not hoped-for state

## Quick Start

The five-step gate function:

1. **IDENTIFY**: What command proves this claim?
2. **RUN**: Execute the FULL command (fresh, complete)
3. **READ**: Full output, check exit code, count failures
4. **VERIFY**: Does output confirm the claim?
   - If NO: State actual status with evidence
   - If YES: State claim WITH evidence
5. **ONLY THEN**: Make the claim

Skip any step = lying, not verifying.

## Common Failure Modes

| Claim | Requires | Not Sufficient |
|-------|----------|----------------|
| Tests pass | Test command output: 0 failures | Previous run, "should pass" |
| Linter clean | Linter output: 0 errors | Partial check, extrapolation |
| Build succeeds | Build command: exit 0 | Linter passing, logs look good |
| Bug fixed | Test original symptom: passes | Code changed, assumed fixed |
| Requirements met | Line-by-line checklist | Tests passing |

## Red Flags - STOP Immediately

If you catch yourself:
- Using "should", "probably", "seems to"
- Expressing satisfaction before verification
- About to commit/push/PR without verification
- Trusting agent success reports
- Relying on partial verification
- Thinking "just this once"
- Tired and wanting work over

**ALL of these mean: STOP. Run verification first.**

## Key Patterns

**Correct Pattern:**
```
✅ [Run pytest] [Output: 34/34 passed] "All tests pass"
```

**Incorrect Patterns:**
```
❌ "Should pass now"
❌ "Looks correct"
❌ "Tests were passing"
❌ "I'm confident it works"
```

## Navigation

For detailed information:
- **[Gate Function](references/gate-function.md)**: Complete five-step verification process with decision trees
- **[Verification Patterns](references/verification-patterns.md)**: Correct verification patterns for tests, builds, deployments, and more
- **[Common Failures](references/common-failures.md)**: Red flags, rationalizations, and real-world failure examples

## Why This Matters

From real-world failures:
- "I don't believe you" - trust broken with user
- Undefined functions shipped - would crash in production
- Missing requirements - incomplete features delivered
- Time wasted on false completion → redirect → rework
- Violates core value: "If you lie, you'll be replaced"

**Statistics from 24 failure memories:**
- Systematic verification: 15-30 minutes to confirm
- Skipped verification: 2-3 hours debugging afterwards
- Verification cost: 2 minutes
- Recovery cost: 120+ minutes (60x more expensive)

## Integration with Other Skills

- **systematic-debugging**: Verify fix works before claiming bug fixed
- **test-driven-development**: Verify red-green cycle before claiming test complete
- **condition-based-waiting**: Verify conditions met before claiming ready
- **root-cause-tracing**: Verify root cause identified before proposing fixes

## Real-World Impact

**Before this skill:**
- 40% of "complete" claims required rework
- Average 2-3 hours debugging false completions
- Trust issues with stakeholders
- Broken CI/CD pipelines

**After this skill:**
- 95% of completions verified accurate
- Average 2 minutes verification time
- High confidence in status reports
- Clean CI/CD pipelines

## The Bottom Line

**No shortcuts for verification.**

Run the command. Read the output. THEN claim the result.

This is non-negotiable.

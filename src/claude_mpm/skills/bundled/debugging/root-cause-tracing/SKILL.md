---
name: Root Cause Tracing
description: Systematically trace bugs backward through call stack to find original trigger
when_to_use: when errors occur deep in execution and you need to trace back to find the original trigger
version: 2.0.0
languages: all
progressive_disclosure:
  entry_point:
    summary: "Trace bugs backward through call chains to find original triggers instead of fixing symptoms"
    when_to_use: "When errors manifest deep in execution, unclear data origins, or long call chains. Use AFTER systematic-debugging Phase 1."
    quick_start: "1. Observe symptom 2. Find immediate cause 3. Ask what called this 4. Keep tracing up 5. Fix at source + add defense"
  references:
    - tracing-techniques.md
    - examples.md
    - advanced-techniques.md
    - integration.md
context_limit: 800
tags:
  - debugging
  - root-cause
  - tracing
  - call-stack
---

# Root Cause Tracing

## Overview

Bugs often manifest deep in the call stack (git init in wrong directory, file created in wrong location, database opened with wrong path). Your instinct is to fix where the error appears, but that's treating a symptom.

**Core principle:** Trace backward through the call chain until you find the original trigger, then fix at the source.

This skill is a specialized technique within the systematic-debugging workflow, typically applied during Phase 1 (Root Cause Investigation) when dealing with deep call stacks.

## When to Use This Skill

**Use root-cause-tracing when:**
- Error happens deep in execution (not at entry point)
- Stack trace shows long call chain
- Unclear where invalid data originated
- Need to find which test/code triggers the problem
- Symptom appears far from actual cause

**Relationship with systematic-debugging:**
- systematic-debugging: The overall framework (Phases 1-4)
- root-cause-tracing: A specific technique for Phase 1 investigation
- Use root-cause-tracing WITHIN systematic-debugging Phase 1

## The Iron Law

```
NEVER FIX JUST WHERE THE ERROR APPEARS
ALWAYS TRACE BACK TO FIND THE ORIGINAL TRIGGER
```

Fixing symptoms creates bandaid solutions that mask root problems.

## Core Principles

1. **Trace Backward**: Follow call chain from symptom to source
2. **Find Original Trigger**: Identify where bad data/state originated
3. **Fix at Source**: Address root cause, not symptom
4. **Defense-in-Depth**: Add validation at each layer after fixing source

## Quick Start

### The 5-Step Trace Process

1. **Observe the Symptom**: What error message? What failed operation?
2. **Find Immediate Cause**: What code directly causes this error?
3. **Ask What Called This**: Trace one level up the call stack
4. **Keep Tracing Up**: Continue until you find the original trigger
5. **Fix at Source + Defense**: Fix root cause and add layer validation

### Decision Tree

```
Error appears deep in stack?
  → Yes: Start tracing backward
    → Can identify caller? → Trace one level up → Repeat
    → Cannot identify caller? → Add instrumentation (see advanced-techniques.md)
  → No: May not need tracing (error at entry point)
```

## The Tracing Process

**Example: Git init in wrong directory**
```
Error symptom → execFileAsync('git', ['init'], { cwd: '' })
  ← WorktreeManager.createSessionWorktree(projectDir='')
  ← Session.create() → Project.create() → Test code
  ← ROOT CAUSE: setupCoreTest() returns { tempDir: '' } before beforeEach
```

**At each level ask:** Where did this value come from? Is this the origin?

**For detailed tracing methodology, see [Tracing Techniques](references/tracing-techniques.md)**
**For complete real-world examples, see [Examples](references/examples.md)**

## After Finding Root Cause

**Fix at source** (throw if accessed before initialization) + **Add defense-in-depth** (validate at Project.create, WorkspaceManager, environment guards, instrumentation).

This prevents similar bugs and catches issues earlier.

## Navigation

For detailed information:
- **[Tracing Techniques](references/tracing-techniques.md)**: Complete tracing methodology, patterns, and decision trees
- **[Examples](references/examples.md)**: Real-world debugging scenarios with full trace chains
- **[Advanced Techniques](references/advanced-techniques.md)**: Stack traces, instrumentation, test pollution detection
- **[Integration](references/integration.md)**: How to use with systematic-debugging and other skills

## Key Reminders

- NEVER fix just where the error appears
- ALWAYS trace back to find the original trigger
- Use `console.error()` for debugging in tests (logger may be suppressed)
- Log BEFORE the dangerous operation, not after it fails
- Include context: directory, cwd, environment, timestamps
- Add defense-in-depth after fixing source
- Document your trace as you go (write down the call chain)

## Red Flags - STOP

If you catch yourself thinking:
- "I'll just add validation here" (without finding source)
- "This will prevent the error" (symptom fix)
- "Too hard to trace back" (add instrumentation instead)
- "Quick fix for now" (creates technical debt)

**ALL of these mean: Continue tracing to find root cause.**

## Integration with Other Skills

- **systematic-debugging**: Use root-cause-tracing during Phase 1
- **defense-in-depth**: Add after finding root cause
- **verification-before-completion**: Verify fix worked at source
- **test-driven-development**: Write test for root cause, not symptom

See [Integration](references/integration.md) for complete workflow examples.

## Real-World Impact

From debugging session (2025-10-03):
- Found root cause through 5-level trace
- Fixed at source (getter validation)
- Added 4 layers of defense
- 1847 tests passed, zero pollution
- Time saved: 3+ hours vs symptom-fix approach

**Bottom line:** Tracing takes 15-30 minutes. Symptom fixes take hours of whack-a-mole.

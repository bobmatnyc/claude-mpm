---
name: Dispatching Parallel Agents
description: Use multiple Claude agents to investigate and fix independent problems concurrently
when_to_use: when facing 3+ independent failures that can be investigated without shared state or dependencies
version: 2.0.0
progressive_disclosure:
  entry_point:
    summary: "Dispatch one agent per independent problem domain to solve multiple unrelated failures concurrently"
    when_to_use: "When you have 3+ independent failures in different test files/subsystems with no shared state or dependencies"
    quick_start: "1. Identify independent domains 2. Create focused agent tasks 3. Dispatch in parallel 4. Review summaries 5. Verify no conflicts and integrate"
  references:
    - coordination-patterns.md
    - agent-prompts.md
    - examples.md
    - troubleshooting.md
---

# Dispatching Parallel Agents

## Overview

When you have multiple unrelated failures (different test files, different subsystems, different bugs), investigating them sequentially wastes time. Each investigation is independent and can happen in parallel.

**Core principle:** Dispatch one agent per independent problem domain. Let them work concurrently.

## When to Use This Skill

Activate this skill when you're facing:
- **3+ test files failing** with different root causes
- **Multiple subsystems broken** independently
- **Each problem is self-contained** - can be understood without context from others
- **No shared state** between investigations
- **Clear domain boundaries** - fixing one won't affect others

**Don't use when:**
- Failures are related (fix one might fix others)
- Need to understand full system state first
- Agents would interfere with each other (editing same files)
- Exploratory debugging (don't know what's broken yet)

## The Iron Law

```
One agent, one problem domain, one clear outcome.
Never overlap scopes. Never share state. Always integrate consciously.
```

## Core Principles

### Independence is Key
Problems must be truly independent - no shared files, no related root causes, no dependencies between fixes.

### Focus Over Breadth
Each agent gets narrow scope: one test file, one subsystem, one clear goal. Broad tasks lead to confusion.

### Clear Output Required
Every agent must return a summary: what was found, what was fixed, what changed. No silent fixes.

### Conscious Integration
Don't blindly merge agent work. Review summaries, check conflicts, run full suite, verify compatibility.

## Quick Start

### 1. Identify Independent Domains

Group failures by what's broken:
```
File A tests: Tool approval flow
File B tests: Batch completion behavior
File C tests: Abort functionality
```

Each domain is independent - fixing tool approval doesn't affect abort tests.

### 2. Create Focused Agent Tasks

Each agent gets:
- **Specific scope:** One test file or subsystem
- **Clear goal:** Make these tests pass
- **Constraints:** Don't change other code
- **Expected output:** Summary of what you found and fixed

**→** [agent-prompts.md](references/agent-prompts.md) for prompt templates and examples

### 3. Dispatch in Parallel

```typescript
// In Claude Code / AI environment
Task("Fix agent-tool-abort.test.ts failures")
Task("Fix batch-completion-behavior.test.ts failures")
Task("Fix tool-approval-race-conditions.test.ts failures")
// All three run concurrently
```

**→** [coordination-patterns.md](references/coordination-patterns.md) for dispatch strategies

### 4. Review and Integrate

When agents return:
- Read each summary - understand what changed
- Verify fixes don't conflict - check for same file edits
- Run full test suite - ensure compatibility
- Spot check changes - agents can make systematic errors

**→** [troubleshooting.md](references/troubleshooting.md) for conflict resolution

## Decision Tree

```
Multiple failures?
  └→ Are they independent?
      ├→ NO (related) → Single agent investigates all
      └→ YES → Can they work in parallel?
          ├→ NO (shared state) → Sequential agents
          └→ YES → Parallel dispatch ✓
```

## Key Benefits

1. **Parallelization** - Multiple investigations happen simultaneously
2. **Focus** - Each agent has narrow scope, less context to track
3. **Independence** - Agents don't interfere with each other
4. **Speed** - N problems solved in time of 1

## Navigation

### Pattern Reference
- **[Coordination Patterns](references/coordination-patterns.md)** - Dispatch strategies, domain identification, integration workflows

### Agent Management
- **[Agent Prompts](references/agent-prompts.md)** - Prompt structure, templates, common mistakes, constraints

### Learning Resources
- **[Examples](references/examples.md)** - Real-world scenarios, case studies, time savings analysis

### Problem Solving
- **[Troubleshooting](references/troubleshooting.md)** - Conflict resolution, verification strategies, common pitfalls

### Related Skills
- **[pm-workflow](../pm-workflow/)** - PM coordination and task management
- **[test-driven-development](../../testing/test-driven-development/)** - TDD patterns that benefit from parallel fixing
- **[verification-before-completion](../../productivity/verification-before-completion/)** - Integration verification

## Key Reminders

1. **Independence is mandatory** - Related failures need single-agent investigation
2. **Focus beats breadth** - Narrow scope per agent prevents confusion
3. **Always verify integration** - Don't blindly merge agent work
4. **Clear outputs required** - Every agent returns summary of changes
5. **Parallelization has overhead** - Only worth it for 3+ independent problems

## Red Flags - STOP

**STOP immediately if:**
- Agents are editing the same files (scope overlap)
- Fixes from one agent break another's work (hidden dependencies)
- You can't clearly separate problem domains (not independent)
- Agents return no summary (can't verify changes)
- Integration requires major refactoring (conflicts)

**When in doubt:** Start with one agent, understand the landscape, then dispatch if truly independent.

## Integration with Other Skills

**Prerequisite:** Basic understanding of problem domains and test structure
**Complementary:** [pm-workflow](../pm-workflow/) for coordinating multiple agents
**Domain-specific:** Testing skills for understanding test failures

## Real-World Impact

From debugging session (2025-10-03):
- **6 failures** across 3 test files
- **3 agents** dispatched in parallel
- **All investigations** completed concurrently
- **Zero conflicts** between agent changes
- **Time saved:** 3 problems solved in parallel vs sequentially

**→** [examples.md](references/examples.md) for detailed case study

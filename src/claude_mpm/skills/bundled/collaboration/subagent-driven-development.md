---
skill_id: subagent-driven-development
skill_version: 1.0.0
description: Execute implementation plans by dispatching fresh subagents per task with two-stage review (spec compliance, then code quality) after each
tags: [agents, workflow, implementation, review, quality, collaboration]
related_agents: [engineer, qa, version-control]
source: https://github.com/obra/superpowers/tree/main/skills/subagent-driven-development
license: MIT
---

# Subagent-Driven Development

Execute plan by dispatching fresh subagent per task, with two-stage review after each: spec compliance review first, then code quality review.

**Core principle:** Fresh subagent per task + two-stage review (spec then quality) = high quality, fast iteration

## When to Use

Use this skill when:
- You have an implementation plan with mostly independent tasks
- You want to stay in the current session (vs. spawning parallel sessions)
- Each task needs isolated context to avoid confusion

**vs. Parallel sessions:**
- Same session (no context switch)
- Fresh subagent per task (no context pollution)
- Two-stage review after each task: spec compliance first, then code quality
- Faster iteration (no human-in-loop between tasks)

## The Process

**Setup:** Read plan, extract all tasks with full text, note context, create task tracker.

**Per Task:**
1. Dispatch implementer subagent with complete task context
2. Answer any clarifying questions before work begins
3. Receive completed implementation with self-review
4. Run spec compliance review (confirm requirements met)
5. Run code quality review (ensure well-built implementation)
6. Manage review loops until both approvals obtained
7. Mark task complete in task tracker

**After all tasks:**
- Dispatch final code reviewer for entire implementation
- Use finishing-a-development-branch skill

## Model Selection

Use the least powerful model that can handle each role:

**Mechanical implementation tasks** (isolated functions, clear specs, 1-2 files): use a fast, cheap model. Most implementation tasks are mechanical when the plan is well-specified.

**Integration and judgment tasks** (multi-file coordination, pattern matching, debugging): use a standard model.

**Architecture, design, and review tasks**: use the most capable available model.

**Task complexity signals:**
- Touches 1-2 files with a complete spec → cheap model
- Touches multiple files with integration concerns → standard model
- Requires design judgment or broad codebase understanding → most capable model

## Handling Implementer Status

Implementer subagents report one of four statuses:

**DONE:** Proceed to spec compliance review.

**DONE_WITH_CONCERNS:** Read the concerns before proceeding. If about correctness or scope, address them before review. If observations only, note them and proceed.

**NEEDS_CONTEXT:** Provide the missing context and re-dispatch.

**BLOCKED:** Assess the blocker:
1. If a context problem, provide more context and re-dispatch with the same model
2. If task requires more reasoning, re-dispatch with a more capable model
3. If task is too large, break into smaller pieces
4. If the plan itself is wrong, escalate to the human

**Never** ignore an escalation or force the same model to retry without changes.

## Advantages

**vs. Manual execution:**
- Subagents follow TDD naturally
- Fresh context per task (no confusion)
- Parallel-safe (subagents don't interfere)
- Subagent can ask questions (before AND during work)

**Quality gates:**
- Self-review catches issues before handoff
- Two-stage review: spec compliance, then code quality
- Review loops ensure fixes actually work
- Spec compliance prevents over/under-building
- Code quality ensures implementation is well-built

## Red Flags

**Never:**
- Start implementation on main/master branch without explicit user consent
- Skip reviews (spec compliance OR code quality)
- Proceed with unfixed issues
- Dispatch multiple implementation subagents in parallel (conflicts)
- Ignore subagent questions (answer before letting them proceed)
- Accept "close enough" on spec compliance
- Skip review loops (reviewer found issues = implementer fixes = review again)
- **Start code quality review before spec compliance is approved** (wrong order)
- Move to next task while either review has open issues

**If reviewer finds issues:**
- Implementer (same subagent) fixes them
- Reviewer reviews again
- Repeat until approved
- Don't skip the re-review

## Integration

**Required workflow skills:**
- **git-worktrees** - REQUIRED: Set up isolated workspace before starting
- **finishing-a-development-branch** - Complete development after all tasks

**Subagents should use:**
- **test-driven-development** - Subagents follow TDD for each task

**Alternative workflow:**
- Use parallel session execution for tasks requiring independent parallel work

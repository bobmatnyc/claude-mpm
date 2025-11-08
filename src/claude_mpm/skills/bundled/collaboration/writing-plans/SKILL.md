---
name: Writing Plans
description: Create detailed implementation plans with bite-sized tasks for engineers with zero codebase context
when_to_use: when design is complete and you need detailed implementation tasks for engineers with zero codebase context
version: 2.2.0
progressive_disclosure:
  level: 1
  references:
    - path: references/plan-structure-templates.md
      title: Plan Structure & Templates
      description: Standard headers, task templates, and structure examples
    - path: references/best-practices.md
      title: Best Practices & Guidelines
      description: Writing for zero-context engineers, code completeness, test design patterns
---

# Writing Plans

## Overview

Write comprehensive implementation plans assuming the engineer has zero context for our codebase and questionable taste. Document everything they need to know: which files to touch for each task, code, testing, docs they might need to check, how to test it. Give them the whole plan as bite-sized tasks. DRY. YAGNI. TDD. Frequent commits.

Assume they are a skilled developer, but know almost nothing about our toolset or problem domain. Assume they don't know good test design very well.

**Announce at start:** "I'm using the Writing Plans skill to create the implementation plan."

**Context:** This should be run in a dedicated worktree (created by brainstorming skill).

**Save plans to:** `docs/plans/YYYY-MM-DD-<feature-name>.md`

## Quick Reference

**Plan header template:** See [Plan Structure & Templates](references/plan-structure-templates.md#standard-plan-document-header)

**Task template:** See [Plan Structure & Templates](references/plan-structure-templates.md#task-template-structure)

**Granularity guide:** Each step = 2-5 minutes. See [Best Practices](references/best-practices.md#bite-sized-task-granularity)

## Core Principles

- **Exact file paths always** - Not "in the user module" but "`src/models/user.py`"
- **Complete code in plan** - Not "add validation" but show the validation code
- **Exact commands with expected output** - "`pytest tests/file.py -v`" with what you'll see
- **Reference relevant skills** - Use @ syntax: `@skills/category/skill-name`
- **DRY, YAGNI, TDD, frequent commits** - Every task follows this pattern

For detailed guidance: [Best Practices & Guidelines](references/best-practices.md)

## Execution Handoff

After saving the plan, offer execution choice:

**"Plan complete and saved to `docs/plans/<filename>.md`. Two execution options:**

**1. Subagent-Driven (this session)** - I dispatch fresh subagent per task, review between tasks, fast iteration

**2. Parallel Session (separate)** - Open new session with executing-plans, batch execution with checkpoints

**Which approach?"**

**If Subagent-Driven chosen:**
- Use @skills/collaboration/subagent-driven-development
- Stay in this session
- Fresh subagent per task + code review

**If Parallel Session chosen:**
- Guide them to open new session in worktree
- New session uses @skills/collaboration/executing-plans

## Remember

- Write for zero-context engineers (specify everything)
- Complete code blocks, not instructions
- Exact commands with expected output
- Test first, then implement, then commit
- Reference existing patterns in codebase
- Keep tasks bite-sized (2-5 minutes each)

**Need examples?** See [Plan Structure & Templates](references/plan-structure-templates.md) for complete task examples.

**Need patterns?** See [Best Practices](references/best-practices.md) for error handling, logging, test design, and more.

---
name: Requesting Code Review
description: Dispatch code-reviewer subagent to review implementation against plan or requirements before proceeding
when_to_use: when completing tasks, implementing major features, or before merging, to verify work meets requirements
version: 1.2.0
progressive_disclosure:
  level: 1
  references:
    - path: references/code-reviewer-template.md
      title: Code Reviewer Template
      description: Complete subagent template with placeholders and review checklist
    - path: references/review-examples.md
      title: Review Examples & Workflows
      description: Good vs bad reviews, severity guidelines, complete workflow examples
---

# Requesting Code Review

Dispatch code-reviewer subagent to catch issues before they cascade.

**Core principle:** Review early, review often.

## When to Request Review

**Mandatory:**
- After each task in subagent-driven development
- After completing major feature
- Before merge to main

**Optional but valuable:**
- When stuck (fresh perspective)
- Before refactoring (baseline check)
- After fixing complex bug

## Quick Start

**1. Get git SHAs:**
```bash
BASE_SHA=$(git rev-parse HEAD~1)  # or origin/main
HEAD_SHA=$(git rev-parse HEAD)
```

**2. Dispatch code-reviewer subagent:**

Use Task tool with code-reviewer type, fill template at [Code Reviewer Template](references/code-reviewer-template.md)

**Required placeholders:**
- `{WHAT_WAS_IMPLEMENTED}` - What you just built
- `{PLAN_OR_REQUIREMENTS}` - What it should do
- `{BASE_SHA}` - Starting commit
- `{HEAD_SHA}` - Ending commit
- `{DESCRIPTION}` - Brief summary

**3. Act on feedback:**

| Severity | Action |
|----------|--------|
| **Critical** | Fix immediately, don't proceed |
| **Important** | Fix before next major task |
| **Minor** | Note for later, can proceed |

See [severity guidelines](references/review-examples.md#severity-guidelines) for details.

## Integration with Workflows

**Subagent-Driven Development:**
- Review after EACH task
- Catch issues before they compound
- Fix before moving to next task

**Executing Plans:**
- Review after each batch (3 tasks)
- Get feedback, apply, continue

**Ad-Hoc Development:**
- Review before merge
- Review when stuck

## Pushing Back on Reviews

**If reviewer wrong:**
- Push back with technical reasoning
- Show code/tests that prove it works
- Reference plan requirements
- Request clarification

See [pushing back examples](references/review-examples.md#pushing-back-on-reviews)

## Common Mistakes

**Never:**
- Skip review because "it's simple"
- Ignore Critical issues
- Proceed with unfixed Important issues
- Argue without technical justification

**Always:**
- Provide full context in review request
- Fix Critical issues immediately
- Document why you disagree (if you do)
- Re-review after fixing Critical issues

## Examples

**Need examples?** See [Review Examples & Workflows](references/review-examples.md) for:
- Complete review output examples
- Good vs bad review requests
- Review workflows for different scenarios
- How to act on different severity levels
- When and how to push back

**Need template?** See [Code Reviewer Template](references/code-reviewer-template.md) for the complete subagent dispatch template.

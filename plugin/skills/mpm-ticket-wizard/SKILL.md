---
name: mpm-ticket-wizard
description: "Interactive ticket creation wizard with Q&A flow for bugs, features, tasks, and epics"
version: 1.0.0
category: mpm
user-invocable: true
tags: [mpm, tickets, wizard, creation, pm-recommended]
triggers:
  - "create ticket"
  - "new ticket"
  - "ticket wizard"
  - "help me create"
  - "file a bug"
  - "request feature"
  - "create epic"
  - "create task"
---

# Ticket Creation Wizard

Interactive Q&A flow for creating well-formed tickets. Guides users through gathering essential details before delegating to ticketing agent.

## When to Use

Activate when user says:
- "Create a ticket" / "New ticket" / "File a ticket"
- "Help me create a bug report"
- "I want to request a feature"
- "Create an epic for..."
- "Ticket wizard" / "Help me create"

## Quick Start Flow

**Step 1: Determine Ticket Type**
```
What type of ticket are you creating?

1. Bug - Something is broken or not working as expected
2. Feature - New functionality or enhancement request
3. Task - Work item or to-do
4. Epic - Large initiative containing multiple issues
```

**Step 2: Gather Details** (varies by type - see templates in references)

**Step 3: Confirm and Create** - Review summary, then delegate to ticketing agent

## Minimum Required Fields by Type

| Type | Required Fields |
|------|-----------------|
| Bug | Title, Expected, Actual, Repro Steps, Severity |
| Feature | Title, Problem, Solution, Acceptance Criteria |
| Task | Title, Success Criteria |
| Epic | Title, Vision, Scope, Success Metrics |

## Q&A Flow Summary

### Bug Reports
1. Brief description (one sentence)
2. Expected vs actual behavior
3. Reproduction steps (numbered list)
4. Environment details (browser, device, OS)
5. Severity assessment (Critical/High/Medium/Low)

### Feature Requests
1. Feature summary (one sentence)
2. Problem statement (why is it needed?)
3. Proposed solution (how should it work?)
4. Acceptance criteria (how will we know it's done?)
5. Priority (Must-have/Should-have/Nice-to-have/Future)
6. Dependencies (optional)

### Tasks
1. Task description (one sentence)
2. Context (why is this needed?)
3. Success criteria
4. Parent issue (optional)
5. Estimate (Small/Medium/Large/X-Large)

### Epics
1. Epic title
2. Vision (high-level goal)
3. Problem space (what problems does this address?)
4. Success metrics
5. Scope (included deliverables)
6. Out of scope (exclusions)
7. Target timeline (optional)

## Priority Mapping

| User Says | Maps To |
|-----------|---------|
| Urgent, ASAP, Critical | `priority:critical` |
| Important, High, Blocking | `priority:high` |
| Normal, Medium, Standard | `priority:medium` |
| Low, Minor, Eventually | `priority:low` |

## Label Suggestions

Based on ticket content, suggest labels:

| Content Indicator | Suggested Labels |
|-------------------|------------------|
| Authentication, login | `auth`, `security` |
| UI, button, display | `frontend`, `ui` |
| API, endpoint | `backend`, `api` |
| Database, query | `backend`, `database` |
| Performance, slow | `performance` |
| Mobile, responsive | `mobile` |
| Documentation | `documentation` |
| Security, vulnerability | `security`, `priority:high` |

## Delegation Pattern

After gathering all information, delegate to ticketing agent:

```
Task:
  agent: "ticketing"
  task: "Create [type] ticket with the following details"
  context: |
    Type: [bug/feature/task/epic]
    Title: [title]
    [Full formatted ticket content from template]
    Priority: [priority]
    Labels: [suggested labels]
  acceptance_criteria:
    - Ticket created successfully
    - Ticket ID returned
    - Confirm ticket details match provided content
```

**IMPORTANT:** This wizard gathers information interactively but **ALWAYS** delegates actual ticket creation to ticketing-agent. PM never creates tickets directly.

## Navigation

For detailed templates and Q&A flows:

- **[Bug Report Template](./references/bug-template.md)** - Complete bug report Q&A flow and output format
- **[Feature Request Template](./references/feature-template.md)** - Feature request Q&A flow and output format
- **[Task Template](./references/task-template.md)** - Task creation Q&A flow and output format
- **[Epic Template](./references/epic-template.md)** - Epic creation Q&A flow and output format
- **[Smart Prompts](./references/smart-prompts.md)** - Eliciting better information from users

## Example Quick Flow

```
User: "I need to create a bug report"

PM: "I'll help you create a well-formed bug report.

**What type of issue?**
1. Bug  2. Feature  3. Task  4. Epic"

User: "1 - bug"

PM: "**Describe the bug in one sentence:**"

User: "Checkout button unclickable on Safari"

[Continue Q&A per bug template...]

PM: "Here's your bug report: [formatted summary]
**Ready to create this ticket?**"

User: "yes"

PM: [Delegates to ticketing-agent with full content]
```

See [ticketing-delegation.md](../../../../docs/guides/ticketing-delegation.md) for delegation protocol.

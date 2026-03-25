# Task Template

Complete Q&A flow and output format for tasks.

## Q&A Sequence

### Q1: Task Description
```
What needs to be done? (One sentence)
> [User provides: "Update API documentation for v2 endpoints"]
```

**Smart Prompt if vague:**
```
Can you be more specific about the work?
- What exactly needs to change?
- What's the scope of this task?
- Is this creating something new or updating something existing?
```

### Q2: Context
```
Why is this task needed? What's the background?
> [User provides context]
```

**Smart Prompt if missing:**
```
Help me understand the context:
- What prompted this task?
- Is this part of a larger effort?
- Who is asking for this?
```

### Q3: Success Criteria
```
How will we know this is done? List specific criteria:
- [ ] [Criterion 1]
- [ ] [Criterion 2]
```

**Smart Prompt for clarity:**
```
Let's make "done" clear:
- What deliverables should exist when complete?
- How will we verify it's correct?
- Any quality standards to meet?
```

### Q4: Parent Issue (Optional)
```
Is this part of a larger issue or epic?
> [User provides parent ticket ID or "None"]
```

### Q5: Assignee (Optional)
```
Who should work on this?
> [User provides name/team or "Unassigned"]
```

### Q6: Estimate (Optional)
```
Estimated effort:
- Small (< 2 hours)
- Medium (2-8 hours)
- Large (1-3 days)
- X-Large (> 3 days)
```

**Estimation Guidelines:**
| Size | Time | Examples |
|------|------|----------|
| Small | < 2 hours | Fix typo, update config, minor refactor |
| Medium | 2-8 hours | Add simple feature, write tests, update docs |
| Large | 1-3 days | Complex feature, significant refactor, integration |
| X-Large | > 3 days | Major feature, architectural change, migration |

### Q7: Due Date (Optional)
```
When should this be completed?
> [User provides date or "No specific deadline"]
```

### Q8: Blockers (Optional)
```
Is anything blocking this work?
> [User lists blockers or "None"]
```

## Output Template

```markdown
## Task: [Task Description]

### Description
[Detailed description of what needs to be done]

### Context
[Why this task is needed - background information]

### Success Criteria
- [ ] [Criterion 1 - specific and verifiable]
- [ ] [Criterion 2]
- [ ] [Criterion 3]

### Parent
[Parent issue/epic ID or "Standalone task"]

### Assignee
[Name/team or "Unassigned"]

### Estimate
[Small/Medium/Large/X-Large] - [Time estimate]

### Due Date
[Date or "No specific deadline"]

### Blockers
[List of blockers or "None"]

### Suggested Labels
[Auto-suggested based on content]
```

## Complete Example

### Input Q&A

```
PM: "What needs to be done?"
User: "Update API documentation for v2 endpoints"

PM: "Why is this needed?"
User: "We launched v2 APIs last week but the docs still show v1 examples"

PM: "How will we know it's done?"
User: "All v2 endpoints documented, examples updated, old v1 examples marked deprecated"

PM: "Is this part of a larger issue?"
User: "Yes, it's under PROJ-100 - API v2 Launch"

PM: "Estimated effort?"
User: "Medium - probably 4-6 hours"
```

### Output Ticket

```markdown
## Task: Update API documentation for v2 endpoints

### Description
Update the API documentation to reflect the newly launched v2 endpoints. All examples should use v2 syntax, and v1 examples should be marked as deprecated with migration guidance.

### Context
V2 APIs were launched last week, but the documentation still shows v1 examples. This is causing confusion for developers trying to integrate with our latest API version.

### Success Criteria
- [ ] All v2 endpoints are documented with accurate descriptions
- [ ] Request/response examples updated to v2 format
- [ ] Authentication examples use v2 patterns
- [ ] v1 examples marked with deprecation notices
- [ ] Migration guide from v1 to v2 included
- [ ] Documentation reviewed for accuracy
- [ ] Code samples tested and verified working

### Parent
PROJ-100 - API v2 Launch

### Assignee
Unassigned

### Estimate
Medium - 4-6 hours

### Due Date
End of current sprint

### Blockers
None

### Suggested Labels
`task`, `documentation`, `api`, `v2`
```

## Task Subtypes

### Documentation Task
```markdown
## Task: [Write/Update] [documentation for X]

### Scope
- Pages/sections to create/update
- Format requirements
- Review process

### Success Criteria
- [ ] Content is accurate and complete
- [ ] Examples are tested and working
- [ ] Reviewed by [stakeholder]
- [ ] Published to [location]
```

### Cleanup/Refactor Task
```markdown
## Task: [Refactor/Clean up] [component/area]

### Scope
- Files/areas affected
- Changes to make
- Things to preserve

### Success Criteria
- [ ] Existing tests still pass
- [ ] No functional changes introduced
- [ ] Code follows current standards
- [ ] [Specific improvements achieved]
```

### Research/Investigation Task
```markdown
## Task: [Investigate/Research] [topic]

### Questions to Answer
1. [Question 1]
2. [Question 2]
3. [Question 3]

### Success Criteria
- [ ] Findings documented in [location]
- [ ] Recommendations provided
- [ ] Next steps identified
```

### Configuration Task
```markdown
## Task: [Configure/Set up] [system/tool]

### Requirements
- [Requirement 1]
- [Requirement 2]

### Success Criteria
- [ ] Configuration complete and documented
- [ ] Tested in [environment]
- [ ] Access/permissions verified
```

## Label Suggestions for Tasks

| Content Pattern | Suggested Labels |
|-----------------|------------------|
| Documentation, docs | `documentation` |
| Refactor, cleanup | `refactor`, `tech-debt` |
| Research, investigate | `research` |
| Configuration, setup | `infrastructure` |
| Testing, test | `testing` |
| Bug fix, fix | `bug` |
| Update, upgrade | `maintenance` |
| Review, audit | `review` |

# Feature Request Template

Complete Q&A flow and output format for feature requests.

## Q&A Sequence

### Q1: Feature Summary
```
What feature are you requesting? (One sentence)
> [User provides: "Add dark mode to the dashboard"]
```

**Smart Prompt if vague:**
```
That sounds interesting! Can you help me understand:
- What would this feature do specifically?
- Who would use it?
- Is this a new feature or an improvement to something existing?
```

### Q2: Problem Statement
```
What problem does this solve? Why is it needed?
> [User explains the pain point or opportunity]
```

**Smart Prompt if unclear:**
```
Help me understand the "why":
- What's frustrating about the current experience?
- What would users be able to do that they can't today?
- Have you heard this request from others?
```

### Q3: Proposed Solution
```
How should this work? Describe your ideal solution:
> [User describes desired behavior]
```

**Smart Prompt for more detail:**
```
Let's make this concrete:
- Walk me through how a user would use this
- What should happen step by step?
- Any specific behaviors you're picturing?
```

### Q4: Acceptance Criteria
```
How will we know this is complete? List specific criteria:
- [ ] [Criterion 1]
- [ ] [Criterion 2]
- [ ] [Criterion 3]
```

**Smart Prompt if missing:**
```
Let's define "done" clearly. Consider:
- What should a user be able to do when this ships?
- What edge cases should we handle?
- Any performance requirements?
- How will we test this works?
```

### Q5: Priority Assessment
```
How important is this feature?

- Must-have: Critical for release/milestone, blocking other work
- Should-have: Important but not blocking, high user impact
- Nice-to-have: Would improve experience, moderate impact
- Future: Good idea for later consideration
```

**Priority Guidelines:**
| Scenario | Priority |
|----------|----------|
| Required for compliance/legal | Must-have |
| Blocking a major release | Must-have |
| Requested by many users | Should-have |
| Improves key workflow | Should-have |
| Quality of life improvement | Nice-to-have |
| Edge case enhancement | Nice-to-have |
| Future vision item | Future |

### Q6: User Stories (Optional)
```
Who would use this feature?
> As a [type of user], I want to [action] so that [benefit]
```

### Q7: Dependencies (Optional)
```
Does this depend on or relate to other work?
- Depends on: [ticket IDs that must be done first]
- Related to: [ticket IDs that are connected]
- Blocks: [ticket IDs waiting on this]
```

### Q8: Alternatives Considered (Optional)
```
Have you considered other approaches?
> [User describes alternatives they thought about]
```

## Output Template

```markdown
## Feature: [Feature Summary]

### Problem Statement
[Why this feature is needed - the pain point or opportunity]

### Proposed Solution
[How the feature should work - user-facing description]

### User Stories
As a [user type], I want to [action] so that [benefit].

### Acceptance Criteria
- [ ] [Criterion 1 - specific, testable]
- [ ] [Criterion 2]
- [ ] [Criterion 3]
- [ ] [Add more as needed]

### Priority
[Must-have/Should-have/Nice-to-have/Future]

### Dependencies
- Depends on: [related tickets this needs first]
- Related to: [connected tickets]
- Blocks: [tickets waiting on this]

### Alternatives Considered
[Other approaches that were considered and why this approach was chosen]

### Additional Context
[Mockups, references, technical notes, user research]

### Suggested Labels
[Auto-suggested based on content]
```

## Complete Example

### Input Q&A

```
PM: "What feature are you requesting?"
User: "Add dark mode to the dashboard"

PM: "What problem does this solve?"
User: "Users work late at night and the bright white UI causes eye strain. We've had multiple requests for this."

PM: "How should this work?"
User: "There should be a toggle in settings to switch between light and dark. The app should remember the preference. Ideally it could also follow system preference."

PM: "What are the acceptance criteria?"
User: "Toggle works, preference persists, all pages support dark colors, text is readable"

PM: "How important is this?"
User: "Should-have - many users have asked but it's not blocking release"
```

### Output Ticket

```markdown
## Feature: Add dark mode to dashboard

### Problem Statement
Users frequently work late at night and the bright white UI causes significant eye strain. We've received multiple user requests for this feature. Dark mode would improve accessibility and user comfort.

### Proposed Solution
Implement a dark mode option that:
- Adds a toggle in Settings to switch between light/dark themes
- Persists the user's preference across sessions
- Optionally follows system-level preference (OS dark mode)
- Applies dark color scheme to all dashboard pages

### User Stories
As a user who works at night, I want to enable dark mode so that I can reduce eye strain during extended sessions.

As a user who prefers dark interfaces, I want the app to respect my system preference so that it matches my other applications.

### Acceptance Criteria
- [ ] Toggle switch in Settings allows switching between Light/Dark themes
- [ ] Selected theme preference persists across browser sessions
- [ ] "Follow system" option respects OS-level dark mode setting
- [ ] All dashboard pages render correctly in dark mode
- [ ] Text maintains sufficient contrast for readability (WCAG AA)
- [ ] Charts and graphs remain legible in dark mode
- [ ] Loading states and empty states work in both modes
- [ ] Transition between modes is smooth (no flash of wrong colors)

### Priority
Should-have - High user demand but not blocking current release

### Dependencies
- Related to: #145 (Accessibility improvements epic)
- Blocks: #198 (User preference consolidation)

### Alternatives Considered
- Browser extension for forced dark mode (rejected - inconsistent, poor UX)
- CSS filter inversion (rejected - affects images negatively)
- Full theme customization (deferred - dark mode is MVP)

### Additional Context
- Design mockups needed before implementation
- Consider using CSS custom properties for maintainability
- Reference: Material Design dark mode guidelines

### Suggested Labels
`feature`, `ui`, `accessibility`, `settings`, `priority:medium`
```

## Label Suggestions for Features

| Content Pattern | Suggested Labels |
|-----------------|------------------|
| UI, visual, theme | `ui`, `frontend` |
| Accessibility, a11y | `accessibility` |
| Settings, preferences | `settings` |
| API, integration | `backend`, `api` |
| Performance, speed | `performance` |
| Mobile, responsive | `mobile` |
| Analytics, tracking | `analytics` |
| Security, auth | `security` |
| User request, feedback | `user-requested` |
| Dashboard, reporting | `dashboard` |

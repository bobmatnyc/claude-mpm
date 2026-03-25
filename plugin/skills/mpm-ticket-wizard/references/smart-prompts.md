# Smart Prompts

Techniques for eliciting better information from users when creating tickets.

## Core Principles

1. **Ask specific questions** - Vague questions get vague answers
2. **Provide examples** - Show what good input looks like
3. **Guide without leading** - Help users think, don't tell them what to say
4. **Be conversational** - Make it feel like a dialogue, not an interrogation
5. **Acknowledge and build** - Validate what they've said before asking for more

## Eliciting Better Bug Reports

### When Description is Vague

**User says:** "It's broken"

**Smart prompt:**
```
I want to help! Can you tell me:
- What were you trying to do?
- What happened (or didn't happen)?
- When did you first notice this?
```

---

**User says:** "Login doesn't work"

**Smart prompt:**
```
Thanks - let's dig into this:
- What error do you see (if any)?
- Does it fail silently or show a message?
- Does it fail every time or intermittently?
- When did this start happening?
```

### When Steps Are Incomplete

**User gives:** "I clicked the button and it broke"

**Smart prompt:**
```
Help me reproduce this exactly:
- What page were you on?
- What was the button labeled?
- What happened after you clicked?
- Did you see any error message?
```

### When Environment is Missing

**User forgets environment:**

**Smart prompt:**
```
Environment matters for debugging:
- Which browser? (Chrome, Safari, Firefox, Edge)
- Desktop or mobile?
- What operating system?
- Any special conditions? (VPN, incognito, ad blocker)
```

### When Severity is Unclear

**User says:** "It's really bad"

**Smart prompt:**
```
Let's assess the impact:
- How many users are affected?
- Is there a workaround?
- Is any data at risk?
- Is this blocking other work?

Based on that:
- Critical = Production down, data loss, security issue
- High = Major feature broken, no workaround
- Medium = Broken but workaround exists
- Low = Minor issue, edge case
```

## Eliciting Better Feature Requests

### When Problem is Unclear

**User says:** "We need dark mode"

**Smart prompt:**
```
That's a great idea! Help me understand the need:
- Who is asking for this? (users, team, you?)
- What problem does it solve for them?
- How often would they use it?
- What do they do today instead?
```

### When Solution is Too Vague

**User says:** "Make it faster"

**Smart prompt:**
```
Let's make this specific:
- Which part feels slow?
- What would "fast enough" look like?
- How long does it take now vs. how long should it take?
- Is this blocking specific workflows?
```

### When Acceptance Criteria Missing

**User skips criteria:**

**Smart prompt:**
```
Let's define "done" clearly. Consider:
- What should a user be able to do when this ships?
- What edge cases should we handle?
- Any performance requirements?
- How will we test that it works?

Try completing: "This feature is done when..."
```

### When Priority is Subjective

**User says:** "This is really important"

**Smart prompt:**
```
Help me understand the priority:
- Is this blocking a release or deadline?
- How many users are affected?
- What's the business impact if we don't do this?
- What's the opportunity cost of not doing other things?

That helps me categorize as:
- Must-have (blocking, critical)
- Should-have (important, high impact)
- Nice-to-have (improvement, moderate impact)
- Future (good idea for later)
```

## Eliciting Better Tasks

### When Scope is Unclear

**User says:** "Update the docs"

**Smart prompt:**
```
Let's scope this out:
- Which docs specifically? (API, user guide, README)
- What needs updating? (content, examples, structure)
- Is there a specific reason for the update?
- Who's the audience for these docs?
```

### When Success Criteria Missing

**User provides task without criteria:**

**Smart prompt:**
```
How will we know this is done?
- What deliverables should exist?
- How will we verify it's correct?
- Who needs to review/approve?
- Any quality standards to meet?
```

## Eliciting Better Epics

### When Vision is Abstract

**User says:** "Improve user experience"

**Smart prompt:**
```
Let's make the vision concrete:
- What specific experience are we improving?
- What's frustrating users today?
- What would "great" look like?
- Can you describe the ideal end state?
```

### When Scope is Too Broad

**User says:** "Fix everything about auth"

**Smart prompt:**
```
Let's break this down:
- What are the top 3-5 problems to solve?
- What's the most impactful change?
- What can we defer to a future effort?
- Is there a logical grouping or phasing?
```

### When Metrics are Missing

**User skips success metrics:**

**Smart prompt:**
```
How will we know this epic succeeded?
- What numbers will improve?
- What can we measure before/after?
- What's the target improvement?
- What leading indicators can we track?

Examples:
- "Reduce support tickets by X%"
- "Increase conversion rate by Y%"
- "Achieve Z compliance certification"
```

## Acknowledging and Building

Always acknowledge what the user provided before asking for more:

### Good Patterns

```
"That's a clear description. Now let me understand the environment..."
```

```
"Thanks - that helps! A few more details would make this actionable..."
```

```
"Great context. To make sure I capture this accurately..."
```

```
"That makes sense. Let's also document..."
```

### Patterns to Avoid

```
"You didn't tell me..." [accusatory]
```

```
"I need more information" [vague]
```

```
"That's not enough detail" [dismissive]
```

## Handling Common Responses

### "I don't know"

**Response:**
```
No worries! Let's work with what we know:
- [Suggest alternatives]
- [Offer to skip and revisit]
- [Provide example of what others say]
```

### "It's obvious"

**Response:**
```
It might be obvious to us, but this ticket will be read by others who don't have our context. Let's document it so anyone can understand.
```

### "Just fix it"

**Response:**
```
I want to fix it right! To do that, I need to understand:
- [Specific question]
- [Specific question]
That way the fix addresses the real issue.
```

### Resistance to Details

**Response:**
```
I know this feels like a lot of questions, but good ticket details:
- Help developers fix issues faster
- Prevent back-and-forth later
- Lead to better solutions

Let me ask just the essential questions...
```

## Formatting Suggestions

### For Lists
```
"Can you list these out? Like:
1. First thing
2. Second thing
3. Third thing"
```

### For Steps
```
"Walk me through it step by step:
1. I started on [page/screen]
2. Then I [action]
3. And then [result]"
```

### For Comparisons
```
"Help me understand the difference:
- Expected: [what should happen]
- Actual: [what does happen]"
```

## Quick Reference: Smart Prompt Templates

| Situation | Smart Prompt |
|-----------|-------------|
| Vague description | "Can you tell me what you were trying to do and what happened?" |
| Missing steps | "Walk me through it step by step, starting from..." |
| No environment | "What browser/device/OS were you using?" |
| Unclear severity | "How many users are affected and is there a workaround?" |
| Missing criteria | "How will we know this is done?" |
| Abstract vision | "What would success look like specifically?" |
| Too broad scope | "What are the top 3 things to tackle first?" |
| No metrics | "What numbers will improve when this is complete?" |

## Remember

- Every question should move toward a better ticket
- Acknowledge effort before asking for more
- Provide examples when asking for specific formats
- Keep the conversation collaborative, not interrogative
- It's okay to suggest answers based on context

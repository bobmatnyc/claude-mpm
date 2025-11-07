# Debugging Anti-Patterns

> **Part of**: [Systematic Debugging](../SKILL.md)
> **Category**: debugging
> **Reading Level**: Intermediate

## Purpose

Common debugging mistakes, rationalizations, and red flags to avoid. Learn to recognize when you're violating systematic debugging principles.

## Red Flags - Recognize and Stop

### "Quick Fix for Now, Investigate Later"

**What It Sounds Like**:
- "Let me just try this quick fix first"
- "We'll investigate the root cause after shipping"
- "This workaround will hold us over"

**Why It's Wrong**:
- "Later" never comes
- Quick fixes become permanent
- Masks underlying issues
- Creates technical debt

**Reality Check**:
```
Quick fix:     15 min → ships with bug hidden
Investigation: 30 min → bug returns different form
Total:         45 min + future debugging time

Systematic:    25 min → bug actually fixed
Total:         25 min, done forever
```

**What to Do Instead**: Spend 25 minutes finding root cause now vs 2+ hours fixing symptoms repeatedly.

### "Just Try Changing X and See If It Works"

**What It Sounds Like**:
- "Maybe if we change this..."
- "Let's try increasing the timeout"
- "What if we add try-catch here?"
- "Could we just restart the service?"

**Why It's Wrong**:
- Random changes waste time
- If it works, you don't know why
- If it fails, you learned nothing
- Creates more bugs

**Reality Check**:
```typescript
// Random attempt 1
setTimeout(() => process(), 5000);  // Didn't work

// Random attempt 2
setTimeout(() => process(), 10000); // Didn't work

// Random attempt 3
setTimeout(() => process(), 20000); // Works sometimes?

// You still don't know the actual problem
```

**What to Do Instead**: Gather evidence about why it's timing out, then fix root cause.

### "Add Multiple Changes, Run Tests"

**What It Sounds Like**:
- "Let me fix all these issues at once"
- "While I'm here, I'll also..."
- "These changes are all related"

**Why It's Wrong**:
- Can't isolate what actually fixed it
- If tests fail, which change broke it?
- If it works, which change was necessary?
- Makes debugging harder

**Reality Check**:
```
Changed: Auth logic, error handling, timeout value
Test passes
Which change fixed it? Unknown
Are all changes necessary? Unknown
Can we safely refactor? Unknown
```

**What to Do Instead**: One change at a time, verify each change independently.

### "I'll Write Test After Confirming Fix Works"

**What It Sounds Like**:
- "Let me verify the fix manually first"
- "I'll add tests once I know it works"
- "Testing can come after we fix it"

**Why It's Wrong**:
- Manual testing misses edge cases
- No regression protection
- Can't verify fix in CI
- Bug likely returns

**Reality Check**:
```
Manual test:
1. Try fix
2. Seems to work
3. Ship it
4. Bug returns in different scenario
5. Debug again

Test-first:
1. Write failing test
2. Fix until test passes
3. Test catches regressions forever
```

**What to Do Instead**: Write failing test reproducing bug, then fix until test passes.

### "It's Probably X, Let Me Fix That"

**What It Sounds Like**:
- "I'm pretty sure it's..."
- "This looks like that bug we had before"
- "Usually this means..."
- "Based on my experience..."

**Why It's Wrong**:
- "Probably" is not evidence
- Each bug is unique
- Assumptions lead to wrong fixes
- Wastes time on wrong solution

**Reality Check**:
```
Assumption: "Probably a caching issue"
Fix:         Clear cache
Result:      Still broken
Cause:       Actually a validation bug
Time wasted: 45 minutes
```

**What to Do Instead**: Gather evidence, form hypothesis based on data, test hypothesis.

### "One More Fix Attempt" (After 2+)

**What It Sounds Like**:
- "Let me try one more thing"
- "This fix should definitely work"
- "Third time's the charm"

**Why It's Wrong**:
- 3+ failures indicate architectural problem
- More symptom fixing won't help
- Digging deeper into wrong solution
- Need to question fundamentals

**Reality Check**:
```
Fix 1: Add retry logic         → Failed
Fix 2: Increase retry count    → Failed
Fix 3: Add exponential backoff → Failed

Pattern: Each fix assumes retrying will work
Reality: Problem isn't retry-able error
```

**What to Do Instead**: STOP. Question whether approach is fundamentally sound.

## Common Rationalizations

### "Issue Is Simple, Don't Need Process"

**The Rationalization**:
"This is obviously a simple typo/config issue, systematic debugging is overkill"

**Reality**:
- Simple issues have root causes too
- "Simple" bugs often hide deeper problems
- Process is fast for simple bugs (5-10 minutes)
- "Simple" assumption often wrong

**Counter-Example**:
```
Seems simple: Variable name typo
Following process reveals: Copy-pasted code in 5 places
Systematic fix: Abstract to shared function
Random fix: Fix one instance, bug persists elsewhere
```

### "Emergency, No Time for Process"

**The Rationalization**:
"Production is down, we need to fix NOW, can't follow slow process"

**Reality**:
- Systematic debugging is FASTER than guess-and-check
- Random fixes in emergencies often make it worse
- Process ensures you actually fix it
- Rushing guarantees longer downtime

**Time Comparison**:
```
"Quick Fix" Approach:
Attempt 1:  10 min → makes it worse
Attempt 2:  15 min → partially works
Attempt 3:  20 min → still broken
Call expert: 30 min
Total:       75 min downtime

Systematic Approach:
Phase 1:    10 min → identify root cause
Phase 4:    10 min → correct fix
Total:      20 min downtime
```

### "Reference Too Long, I'll Adapt the Pattern"

**The Rationalization**:
"I understand the general idea, don't need to read all the details"

**Reality**:
- Partial understanding guarantees bugs
- Details matter - that's why they're documented
- Adaptation without full understanding fails
- Reading takes 10 minutes, fixing bugs takes hours

**Counter-Example**:
```
Reference: "Initialize connection pool before server starts"
Skimmed:   "Initialize connection pool" ✓
Missed:    "Before server starts"
Result:    Race condition, intermittent failures
```

### "I See the Problem, Let Me Fix It"

**The Rationalization**:
"I can see what's wrong, no need to investigate further"

**Reality**:
- Seeing symptoms ≠ understanding root cause
- "Obvious" fixes often miss deeper issues
- What you see is rarely the actual problem
- Quick "fixes" become permanent workarounds

**Counter-Example**:
```
Symptom:    NullPointerException at line 45
"Obvious":  Add null check at line 45
Root cause: Function at line 23 returns null unexpectedly
Correct fix: Fix function at line 23
Your "fix":  Hides real problem, bug persists elsewhere
```

## Pattern Recognition: Bad Debugging

### Pattern: Timeout Spiral

**Progression**:
1. Operation times out
2. Increase timeout
3. Still times out
4. Increase timeout more
5. Eventually works (sometimes)
6. Actual problem never fixed

**Why It Fails**: Timeouts are symptoms, not root causes

**Correct Approach**:
1. Why is it timing out?
2. What operation is slow?
3. Fix slow operation
4. Remove arbitrary timeout

### Pattern: Try-Catch Cascade

**Progression**:
1. Error occurs
2. Add try-catch to hide error
3. Different error occurs
4. Add another try-catch
5. More errors appear elsewhere
6. Code full of error handling, problem not solved

**Why It Fails**: Catching errors doesn't fix causes

**Correct Approach**:
1. What's causing the error?
2. Fix root cause
3. Add error handling only for truly exceptional cases

### Pattern: Configuration Whack-a-Mole

**Progression**:
1. Doesn't work
2. Change config setting
3. Different failure
4. Change another setting
5. Previous failure returns
6. Config becomes mystery state

**Why It Fails**: Random config changes without understanding

**Correct Approach**:
1. What does this config control?
2. What's the correct value for our use case?
3. Why was previous value wrong?
4. Set correct value once

### Pattern: Copy-Paste from Stack Overflow

**Progression**:
1. Search error message
2. Find Stack Overflow answer
3. Copy-paste code
4. Seems to work
5. Causes subtle bugs later
6. Don't understand what it does

**Why It Fails**: Code without understanding

**Correct Approach**:
1. Find Stack Overflow answer
2. Read and understand it
3. Verify it applies to your case
4. Adapt it appropriately
5. Add comments explaining what and why

## Human Partner Signals

### Signal Categories

**Questions = You Assumed Without Verifying**
- "Is that not happening?"
- "Did you check...?"
- "Will it show us...?"
- "Are you sure...?"

**Commands = You're Off Track**
- "Stop guessing"
- "Gather evidence first"
- "One change at a time"
- "Write a test"

**Frustration = Your Approach Isn't Working**
- "We're stuck?"
- "This isn't working"
- "Let's try different approach"
- "Ultrathink this"

### How to Respond

**Don't**:
- Argue or defend
- Explain why you did it that way
- Continue with current approach
- Make excuses

**Do**:
- STOP immediately
- Acknowledge the redirect
- Return to Phase 1
- Gather evidence
- Ask for guidance if unclear

**Example Responses**:
```
Signal: "Is that not happening?"
Bad:    "I assumed it would..."
Good:   "Let me verify that with evidence"

Signal: "Stop guessing"
Bad:    "I'm not guessing, I think..."
Good:   "You're right, let me investigate root cause first"

Signal: "We're stuck?"
Bad:    "Let me try one more thing..."
Good:   "Let me reconsider the approach from Phase 1"
```

## Self-Assessment Questions

Ask yourself these questions to catch anti-patterns:

### Before Making Changes
- [ ] Have I gathered evidence about root cause?
- [ ] Do I have a specific hypothesis?
- [ ] Can I explain why this change should work?
- [ ] Am I changing only one thing?
- [ ] Have I written a test case?

### If Answer Is "No"
**STOP. Return to Phase 1.**

### After Multiple Attempts
- [ ] How many fixes have I tried? (If ≥3, STOP)
- [ ] Am I fixing symptoms or root cause?
- [ ] Is each fix revealing new problems?
- [ ] Should I question the architecture?

### If In Doubt
- [ ] Would systematic debugging be faster?
- [ ] Am I rationalizing shortcuts?
- [ ] What would I tell someone else to do?

## Recovery from Anti-Patterns

### If You Realize You're Doing It Wrong

**Immediate Actions**:
1. **STOP** - Don't make more random changes
2. **Revert** - Back to known good state
3. **Document** - What you tried (data for Phase 1)
4. **Restart** - Phase 1 with fresh perspective

**Don't**:
- Keep changes "that might help"
- Try "one more quick thing"
- Feel bad about time "wasted"
- Rush to "make up for lost time"

**Do**:
- Clean slate
- Systematic approach from start
- Use failed attempts as evidence
- Take time to do it right

### Sunk Cost Fallacy

**The Trap**:
"I've already spent 2 hours on random fixes, can't give up now"

**The Reality**:
- Those 2 hours are gone regardless
- Continuing wastes more time
- Starting over with systematic approach is faster
- 25 minutes systematic > 4 hours random

**The Decision**:
```
Option A: Continue random approach
Cost:     2 hours spent + 2 more hours likely
Result:   Maybe works, likely more bugs

Option B: Restart systematically
Cost:     2 hours spent + 25 minutes systematic
Result:   Definitely works, no new bugs

Option B is clearly better despite sunk cost
```

## Summary

**Common Anti-Patterns**:
- Quick fixes without investigation
- Random changes hoping they work
- Multiple simultaneous changes
- Tests after instead of before
- "Probably" instead of evidence
- Continuing after 3+ failures

**Common Rationalizations**:
- "Too simple for process"
- "Emergency, no time"
- "I'll adapt the pattern"
- "I see the problem"

**Recovery**:
- Recognize the pattern
- STOP immediately
- Revert to known state
- Restart Phase 1 systematically

**Remember**: Systematic debugging is faster, even when it feels slow. Random fixes always take longer.

## Related References

- [Workflow](workflow.md): Correct four-phase process
- [Examples](examples.md): Real-world systematic debugging
- [Troubleshooting](troubleshooting.md): When debugging gets hard

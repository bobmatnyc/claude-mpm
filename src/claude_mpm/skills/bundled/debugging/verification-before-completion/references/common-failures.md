# Common Failures and Red Flags

Understanding failure modes helps recognize when verification is being skipped.

## Common Failure Table

| Claim | Requires | Not Sufficient |
|-------|----------|----------------|
| Tests pass | Test command output: 0 failures | Previous run, "should pass" |
| Linter clean | Linter output: 0 errors | Partial check, extrapolation |
| Build succeeds | Build command: exit 0 | Linter passing, logs look good |
| Bug fixed | Test original symptom: passes | Code changed, assumed fixed |
| Regression test works | Red-green cycle verified | Test passes once |
| Agent completed | VCS diff shows changes | Agent reports "success" |
| Requirements met | Line-by-line checklist | Tests passing |
| Performance improved | Benchmark measurements | "Feels faster" |
| Security enhanced | Security scan results | "Looks secure" |
| Documentation complete | Fresh user successful | "Clear to me" |

## Red Flags - STOP Immediately

### Language Red Flags

If you catch yourself using:
- **"Should"** - "Should work now", "Should pass", "Should be fixed"
- **"Probably"** - "Probably works", "Probably passes"
- **"Seems to"** - "Seems to work", "Seems correct"
- **"Looks like"** - "Looks good", "Looks correct"
- **"I think"** - "I think it's fixed", "I think tests pass"
- **"Appears to"** - "Appears working", "Appears correct"

**ALL of these = NO VERIFICATION OCCURRED**

### Premature Satisfaction

Expressing satisfaction BEFORE verification:
- "Great!" before running tests
- "Perfect!" before checking build
- "Done!" before verifying completion
- "Excellent!" before confirming results
- "Success!" before reading output
- "Fixed!" before testing reproduction

**Satisfaction ONLY AFTER verification evidence**

### Process Red Flags

- About to commit without running tests
- About to push without verification
- About to create PR without checking
- Moving to next task without confirming current
- Trusting agent reports without checking
- Relying on partial verification ("just linter")
- Thinking "just this once" (no exceptions)
- Tired and wanting work to be over
- Time pressure making verification "optional"

## Rationalization Prevention

Common excuses and their realities:

| Excuse | Reality | Response |
|--------|---------|----------|
| "Should work now" | Speculation, not evidence | RUN the verification command |
| "I'm confident" | Confidence ≠ evidence | Evidence required regardless |
| "Just this once" | Creates bad precedent | No exceptions, ever |
| "Linter passed" | Linter ≠ compiler ≠ tests | Each verification separate |
| "Agent said success" | Agents can be wrong | Verify independently always |
| "I'm tired" | Fatigue ≠ excuse | Verification is non-negotiable |
| "Partial check enough" | Partial proves nothing | Full verification required |
| "Different wording" | Spirit over letter | Rule applies to all variants |
| "Time pressure" | Shortcuts create more work | Verification saves time |
| "Low risk change" | All changes need verification | Risk level irrelevant |
| "I tested locally" | Local ≠ CI ≠ production | Each environment separate |
| "Same as before" | Code changes, verify again | No assumptions |

## Why These Excuses Fail

### "Should work now"
- Software doesn't work on should
- Should = guess, not fact
- Run the command, get the fact

### "I'm confident"
- Confidence is feeling, not evidence
- Most confident when most wrong
- Evidence trumps confidence

### "Just this once"
- Once becomes habit
- Standards erode gradually
- No exceptions maintains discipline

### "Linter passed so build should work"
- Linter checks style, not compilation
- Build checks compilation, not runtime
- Tests check runtime, not requirements
- Each layer separate verification

### "Agent said success"
- Agents report what they believe
- Agents can misinterpret results
- Agents don't have full context
- Independent verification required

### "I'm tired"
- Fatigue increases error rate
- Makes verification MORE important
- Shortcutting when tired = guaranteed bugs
- Better to stop than skip verification

### "Partial verification enough"
- Partial verification = no verification
- Untested parts always break
- "Just the important parts" misjudges importance
- Full verification or none

## Real-World Failure Examples

From actual debugging sessions where verification was skipped:

### Example 1: "Tests should pass"
**What happened:**
- Claimed tests pass without running
- 4 tests actually failing
- Pushed to main, broke CI
- 2 hours debugging why CI fails

**Lesson:** "Should" ≠ "Do". Always run.

### Example 2: "Linter clean, so build works"
**What happened:**
- Linter passed (style check)
- Build failed (TypeScript errors)
- Assumed linter = build verification
- Deployment blocked

**Lesson:** Each verification layer separate.

### Example 3: Trusted agent report
**What happened:**
- Agent reported "tests passing"
- Didn't check git diff
- Agent introduced syntax error
- Tests couldn't even run

**Lesson:** Always verify agent work independently.

### Example 4: "I'm confident this fixes it"
**What happened:**
- Confident in fix logic
- Didn't test reproduction case
- Bug still present, different symptom
- Customer reported immediately

**Lesson:** Confidence ≠ evidence.

### Example 5: "Just one quick fix before verification"
**What happened:**
- Made "quick fix" without testing
- Introduced new bug
- Now debugging 2 bugs instead of 1
- Should have verified first fix first

**Lesson:** Never "one more fix" without verification.

## Pattern Recognition

**Healthy Pattern:**
```
Implement → Verify → Claim → Next
```

**Unhealthy Pattern:**
```
Implement → Implement → Implement → Assume → Claim
```

**Death Spiral Pattern:**
```
Implement → Fails → "One more fix" → Fails → "Just needs..." → Fails
```

When you see yourself in "one more fix" mode, STOP:
1. Return to root cause investigation
2. Question your understanding
3. Verify each assumption
4. Consider architectural issues

## Cultural Red Flags

Organizational patterns that enable verification skipping:

- "Move fast and break things" (without fixing)
- "We'll catch it in QA" (QA not a safety net)
- "Trust the developer" (trust + verify)
- "Time pressure" used as excuse
- "Good enough for now" acceptance
- Rewarding speed over correctness

**None of these excuse skipping verification.**

## The Bottom Line

Every excuse is a rationalization for:
1. Not wanting to verify
2. Hoping it works
3. Avoiding accountability
4. Wishful thinking

**Solution:** Run the command. Read the output. Then claim the result.

No shortcuts. No exceptions. No rationalizations.

# Red Flags and Common Failures

Understanding failure modes helps recognize when verification is being skipped.

## When to Use This Skill - Detailed Triggers

Activate verification ALWAYS before:
- **ANY variation of success/completion claims**: "Done", "Complete", "Finished", "Success", "Fixed", "Working", "Passing", "Clean", "Ready"
- **ANY expression of satisfaction**: "Great!", "Perfect!", "Excellent!", "Awesome!", "Nice!", "Good!"
- **ANY positive statement about work state**: "Looking good", "Should work", "Seems fine"
- **Version control operations**: Committing, pushing, creating PRs, merging branches
- **Task transitions**: Moving to next task, marking tasks complete, closing tickets
- **Delegation**: Handing off to agents, other developers, or automation
- **Status reporting**: Updating stakeholders, writing status updates, daily standups
- **Pre-deployment**: Before staging deployment, production deployment, releases
- **Documentation claims**: "Documentation complete", "README updated"
- **Performance claims**: "Optimization complete", "Performance improved"
- **Security claims**: "Security issue fixed", "Vulnerability patched"

**Use this ESPECIALLY when:**
- **Time pressure**: Deadlines making verification "optional"
- **Fatigue**: Tired and wanting work to be over
- **Confidence**: "Quick fix" seems obvious or you're very confident
- **Repetition**: "Done this before", familiar patterns
- **Agent reports**: Agent claims success or completion
- **Test expectations**: Tests "should" pass based on changes
- **Simple changes**: "Just one line", "trivial fix"
- **Review pressure**: Waiting reviewers or blocked team members
- **Multi-tasking**: Juggling multiple tasks simultaneously
- **Context switching**: Returning to work after interruption

## Common Failure Modes Table

| Claim | Requires | Not Sufficient | Time Cost if Wrong |
|-------|----------|----------------|-------------------|
| Tests pass | Test command output: 0 failures | Previous run, "should pass" | 120+ minutes debugging |
| Linter clean | Linter output: 0 errors | Partial check, extrapolation | 30-60 minutes cleanup |
| Build succeeds | Build command: exit 0 | Linter passing, logs look good | 60-90 minutes build debugging |
| Bug fixed | Test original symptom: passes | Code changed, assumed fixed | 180+ minutes investigation |
| Regression test works | Red-green cycle verified | Test passes once | 90-120 minutes false confidence |
| Agent completed | VCS diff shows changes + verification | Agent reports "success" | 120-180 minutes rework |
| Requirements met | Line-by-line checklist | Tests passing | 240+ minutes missing features |
| Performance improved | Benchmark measurements | "Feels faster" | 60+ minutes profiling |
| Security enhanced | Security scan results | "Looks secure" | Critical vulnerability risk |
| Documentation complete | Fresh user successful | "Clear to me" | User frustration, support tickets |
| API working | Integration test passes | Unit tests pass | 90-120 minutes integration issues |
| Database migration safe | Rollback tested, data verified | Migration runs once | 180+ minutes data recovery |
| Feature complete | All acceptance criteria met | Demo works once | 120+ minutes edge cases |
| Refactoring safe | Full test suite passes | "Logic unchanged" | 90+ minutes subtle bugs |
| Configuration correct | System runs with config | "Syntax valid" | 60-120 minutes troubleshooting |

## Red Flags - STOP Immediately

### Language Red Flags

If you catch yourself using:
- **"Should"** - "Should work now", "Should pass", "Should be fixed"
- **"Probably"** - "Probably works", "Probably passes"
- **"Seems to"** - "Seems to work", "Seems correct"
- **"Looks like"** - "Looks good", "Looks correct"
- **"I think"** - "I think it's fixed", "I think tests pass"
- **"Appears to"** - "Appears working", "Appears correct"
- **"Likely"** - "Likely fixed", "Likely working"
- **"Pretty sure"** - "Pretty sure it works"
- **"Confident"** - "Confident it passes"
- **"Expect"** - "Expect tests to pass"

**ALL of these = NO VERIFICATION OCCURRED**

### Premature Satisfaction

Expressing satisfaction BEFORE verification:
- "Great!" before running tests
- "Perfect!" before checking build
- "Done!" before verifying completion
- "Excellent!" before confirming results
- "Success!" before reading output
- "Fixed!" before testing reproduction
- "Nice!" before validation
- "Awesome!" before confirmation

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
- Confident based on similar past work
- "Quick change" doesn't need verification
- Demo worked, assuming production ready

## Rationalization Prevention

Common excuses and their realities:

| Excuse | Reality | Response | Time Wasted |
|--------|---------|----------|-------------|
| "Should work now" | Speculation, not evidence | RUN the verification command | 120+ min if wrong |
| "I'm confident" | Confidence ≠ evidence | Evidence required regardless | 90+ min recovery |
| "Just this once" | Creates bad precedent | No exceptions, ever | Habit formation |
| "Linter passed" | Linter ≠ compiler ≠ tests | Each verification separate | 60-90 min debugging |
| "Agent said success" | Agents can be wrong | Verify independently always | 120-180 min rework |
| "I'm tired" | Fatigue ≠ excuse | Verification is non-negotiable | 180+ min if error |
| "Partial check enough" | Partial proves nothing | Full verification required | 90+ min gaps |
| "Different wording" | Spirit over letter | Rule applies to all variants | Trust violation |
| "Time pressure" | Shortcuts create more work | Verification saves time | 2x-5x time multiplier |
| "Low risk change" | All changes need verification | Risk level irrelevant | Unexpected failures |
| "I tested locally" | Local ≠ CI ≠ production | Each environment separate | 60-120 min env issues |
| "Same as before" | Code changes, verify again | No assumptions | 90+ min subtle bugs |
| "Demo worked" | Demo ≠ production | Full verification required | Critical failures |
| "Quick fix" | Quick = higher error rate | More reason to verify | 120+ min debugging |
| "Obvious solution" | Obvious = overconfident | Verify anyway | 90+ min surprises |

## Why These Excuses Fail

### "Should work now"
- Software doesn't work on should
- Should = guess, not fact
- Run the command, get the fact
- **Real cost**: 120+ minutes debugging when wrong
- **Verification cost**: 2 minutes

### "I'm confident"
- Confidence is feeling, not evidence
- Most confident when most wrong (Dunning-Kruger effect)
- Evidence trumps confidence always
- **Real example**: "Confident" fix broke 4 tests, 2 hours recovery

### "Just this once"
- Once becomes habit
- Standards erode gradually
- No exceptions maintains discipline
- **Slippery slope**: First skip leads to regular skipping

### "Linter passed so build should work"
- Linter checks style, not compilation
- Build checks compilation, not runtime
- Tests check runtime, not requirements
- Each layer separate verification
- **Real example**: Clean linter, build failed (TypeScript errors), deployment blocked

### "Agent said success"
- Agents report what they believe
- Agents can misinterpret results
- Agents don't have full context
- Independent verification required
- **Real example**: Agent reported "tests passing", introduced syntax error, tests couldn't run

### "I'm tired"
- Fatigue increases error rate
- Makes verification MORE important
- Shortcutting when tired = guaranteed bugs
- Better to stop than skip verification
- **Statistics**: 3x higher error rate when fatigued

### "Partial verification enough"
- Partial verification = no verification
- Untested parts always break
- "Just the important parts" misjudges importance
- Full verification or none
- **Real example**: Verified auth, skipped API routes, 3 endpoints broken

### "Time pressure"
- Verification: 2-5 minutes
- Fixing unverified work: 60-180 minutes
- Verification SAVES time under pressure
- **Math**: 60x more expensive to skip

### "Demo worked"
- Demos use happy path only
- Production has edge cases, error paths
- Demo environment ≠ production environment
- **Real example**: Demo perfect, production crashed on null input

## Real-World Failure Examples with Time/Cost Data

### Example 1: "Tests should pass"
**Context**: Backend API development, deadline pressure
**What happened:**
- Claimed tests pass without running
- 4 tests actually failing (validation logic)
- Pushed to main, broke CI
- Blocked 3 other developers
**Time cost:**
- Would have taken: 2 minutes (run pytest)
- Actually took: 2 hours debugging + 30 minutes team coordination
- **Cost multiplier: 75x**
**Lesson:** "Should" ≠ "Do". Always run.

### Example 2: "Linter clean, so build works"
**Context**: TypeScript frontend, production deployment
**What happened:**
- Linter passed (style check)
- Build failed (TypeScript type errors)
- Assumed linter = build verification
- Deployment blocked, hotfix needed
**Time cost:**
- Would have taken: 3 minutes (npm run build)
- Actually took: 90 minutes (find errors, fix, re-deploy)
- **Cost multiplier: 30x**
**Lesson:** Each verification layer separate.

### Example 3: Trusted agent report
**Context**: Agent-assisted refactoring
**What happened:**
- Agent reported "tests passing"
- Didn't check git diff
- Agent introduced syntax error
- Tests couldn't even run
- Reverted all changes, manual redo
**Time cost:**
- Would have taken: 2 minutes (git diff + pytest)
- Actually took: 3 hours (debug, revert, redo work)
- **Cost multiplier: 90x**
**Lesson:** Always verify agent work independently.

### Example 4: "I'm confident this fixes it"
**Context**: Bug fix for customer-reported issue
**What happened:**
- Confident in fix logic
- Didn't test reproduction case
- Bug still present, different symptom
- Customer reported immediately
- Trust damaged with customer
**Time cost:**
- Would have taken: 5 minutes (test reproduction)
- Actually took: 4 hours (customer support, investigation, actual fix)
- **Cost multiplier: 48x**
- **Additional cost**: Customer trust violation
**Lesson:** Confidence ≠ evidence.

### Example 5: "Just one quick fix before verification"
**Context**: Race condition bug fix
**What happened:**
- Made "quick fix" without testing
- Introduced new bug (null pointer)
- Now debugging 2 bugs instead of 1
- Should have verified first fix first
**Time cost:**
- Would have taken: 3 minutes (run affected tests)
- Actually took: 2.5 hours (debug compound issue)
- **Cost multiplier: 50x**
**Lesson:** Never "one more fix" without verification.

### Example 6: "Linter passed, committed"
**Context**: Python API endpoint development
**What happened:**
- Ran ruff linter: clean
- Committed without running tests
- 6 tests failing (business logic errors)
- CI pipeline red, blocking team
**Time cost:**
- Would have taken: 2 minutes (pytest)
- Actually took: 90 minutes (find failures, fix, force push)
- **Cost multiplier: 45x**
**Lesson:** Linter ≠ tests. Run both.

### Example 7: "Demo worked perfectly"
**Context**: Feature demo to stakeholders
**What happened:**
- Demo used happy path only
- Didn't test error cases
- Deployed to staging
- Crashed on first null input
- Emergency rollback
**Time cost:**
- Would have taken: 10 minutes (edge case testing)
- Actually took: 3 hours (emergency response, fix, re-deploy)
- **Cost multiplier: 18x**
**Lesson:** Demo ≠ complete verification.

### Example 8: "Agent refactored successfully"
**Context**: Code cleanup with AI agent
**What happened:**
- Agent reported "refactoring complete"
- Didn't review changes (200 lines)
- Agent removed critical validation
- Security vulnerability introduced
**Time cost:**
- Would have taken: 5 minutes (git diff review)
- Actually took: 6 hours (security audit, fix, verification)
- **Cost multiplier: 72x**
- **Additional cost**: Security risk
**Lesson:** Always review agent changes.

### Example 9: "Too tired to run tests"
**Context**: Late night bug fix
**What happened:**
- Fixed bug at 11pm
- "Too tired" to run test suite
- Committed and went to bed
- Broke 3 unrelated features
- Morning crisis meeting
**Time cost:**
- Would have taken: 3 minutes (test suite)
- Actually took: 4 hours (morning debugging, team impact)
- **Cost multiplier: 80x**
- **Additional cost**: Team morale impact
**Lesson:** Too tired to verify = too tired to commit.

### Example 10: "Looks good in local dev"
**Context**: Database migration
**What happened:**
- Migration worked in local environment
- Deployed to staging without testing
- Production data structure different
- Migration corrupted data
- 2-day recovery process
**Time cost:**
- Would have taken: 10 minutes (staging test)
- Actually took: 16 hours (data recovery, investigation)
- **Cost multiplier: 96x**
- **Additional cost**: Data integrity incident
**Lesson:** Local ≠ staging ≠ production. Test each.

### Example 11: "Build succeeded, ready to deploy"
**Context**: Microservice deployment
**What happened:**
- Build passed successfully
- Didn't run integration tests
- Deployed to production
- Service couldn't connect to database
- Emergency rollback
**Time cost:**
- Would have taken: 5 minutes (integration tests)
- Actually took: 2 hours (rollback, debug, fix, re-deploy)
- **Cost multiplier: 24x**
**Lesson:** Build ≠ integration ≠ deployment ready.

### Example 12: "Performance should be better"
**Context**: API optimization work
**What happened:**
- Implemented caching layer
- Assumed performance improved
- Didn't benchmark
- Actually 20% slower (cache overhead)
- Reverted optimization
**Time cost:**
- Would have taken: 5 minutes (benchmark run)
- Actually took: 3 hours (deploy, discover, investigate, revert)
- **Cost multiplier: 36x**
**Lesson:** Measure performance, don't assume.

## Pattern Recognition

**Healthy Pattern:**
```
Implement → Verify → Claim → Next
Implement → Verify → Claim → Next
```

**Unhealthy Pattern:**
```
Implement → Implement → Implement → Assume → Claim
```

**Death Spiral Pattern:**
```
Implement → Fails → "One more fix" → Fails → "Just needs..." → Fails → "Almost there..." → Fails
```

When you see yourself in "one more fix" mode, STOP:
1. Return to root cause investigation
2. Question your understanding
3. Verify each assumption
4. Consider architectural issues
5. Get second opinion

## Cultural Red Flags

Organizational patterns that enable verification skipping:

- **"Move fast and break things"** (without fixing) - Chaos, not velocity
- **"We'll catch it in QA"** (QA not a safety net) - QA finds gaps, not basic verification
- **"Trust the developer"** (trust + verify) - Trust requires verification
- **"Time pressure"** used as excuse - Verification saves time
- **"Good enough for now"** acceptance - Technical debt accumulation
- **Rewarding speed over correctness** - Creates perverse incentives
- **"Ship and iterate"** (without verification) - Shipping broken code
- **"Fail fast"** (without learning) - Same failures repeated
- **Blaming individuals for systemic failures** - Process problem, not people

**None of these excuse skipping verification.**

## Cost-Benefit Analysis

### Verification Investment
- **Time per verification**: 2-5 minutes average
- **Frequency**: Every completion claim
- **Daily investment**: 10-20 minutes for typical developer

### Skipping Costs
- **Debug time when wrong**: 60-180 minutes average
- **Team impact**: 2-5 developer-hours blocked
- **Trust damage**: Immeasurable
- **Production incidents**: Critical severity
- **Customer impact**: Revenue/reputation loss

### ROI Calculation
- **Average cost multiplier**: 60x
- **False negative rate**: 40% of unverified claims fail
- **Expected value**: Verification ALWAYS saves time

**Mathematical certainty: Always verify.**

## The Bottom Line

Every excuse is a rationalization for:
1. Not wanting to verify
2. Hoping it works
3. Avoiding accountability
4. Wishful thinking

**Solution:** Run the command. Read the output. Then claim the result.

No shortcuts. No exceptions. No rationalizations.

**Remember**: 2 minutes now or 120 minutes later. Your choice.

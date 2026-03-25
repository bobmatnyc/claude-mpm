# Debugging Troubleshooting Guide

> **Part of**: [Systematic Debugging](../SKILL.md)
> **Category**: debugging
> **Reading Level**: Advanced

## Purpose

Solutions for common challenges that arise during systematic debugging, including what to do when you get stuck, when the process seems slow, or when human partners redirect you.

## Common Debugging Challenges

### Challenge 1: Cannot Reproduce Issue

**Problem**: Bug reported but can't trigger it reliably

**Solution Approach**:

1. **Gather More Context**
   ```
   Ask reporter:
   - Exact steps they took
   - Browser/OS/environment details
   - Screenshots or video
   - Error messages they saw
   - When it started happening
   ```

2. **Check for Environmental Factors**
   - Time of day (server load patterns)
   - User account state (permissions, data)
   - Network conditions (latency, failures)
   - Cache state (fresh vs cached)
   - Concurrent operations

3. **Add Comprehensive Logging**
   ```typescript
   // Log everything around suspected area
   logger.info('Function entry', { input, state });
   logger.info('Step 1 complete', { intermediate });
   logger.info('Decision point', { condition, willTake: path });
   logger.info('Function exit', { result });
   ```

4. **Monitor for Patterns**
   - Does it happen at specific times?
   - Only for certain users?
   - Only on certain data?
   - Percentage occurrence?

**When to Stop**: If truly irreproducible after thorough investigation, document findings and add defensive error handling.

### Challenge 2: Too Many Possible Causes

**Problem**: Multiple things could cause this issue

**Solution Approach**:

1. **Binary Search**
   ```
   Disable half the functionality
   → Still broken? Issue in remaining half
   → Fixed? Issue in disabled half
   Repeat until narrowed to single component
   ```

2. **Isolate Variables**
   ```typescript
   // Test each variable independently
   const test1 = processWithA(data);
   const test2 = processWithB(data);
   const test3 = processWithC(data);

   // Which fails?
   ```

3. **Priority by Likelihood**
   ```
   Most likely causes (based on evidence):
   1. Recent code changes → Check first
   2. Known fragile areas → Check second
   3. External dependencies → Check third
   4. Theoretical possibilities → Check last
   ```

4. **Eliminate Systematically**
   - Start with most likely cause
   - Test one hypothesis at a time
   - Document which causes ruled out
   - Don't test multiple theories simultaneously

### Challenge 3: Error Messages Are Cryptic

**Problem**: Error message doesn't clearly indicate root cause

**Solution Approach**:

1. **Search for Exact Error**
   ```bash
   # Google with quotes
   "exact error message text"

   # Search codebase
   grep -r "exact error message" src/

   # Check documentation
   # Stack Overflow, GitHub issues
   ```

2. **Understand Error Source**
   ```typescript
   // Where is error thrown?
   throw new Error('Cryptic message');

   // Check call stack - WHO called this?
   // Work backward from error
   ```

3. **Increase Verbosity**
   ```bash
   # Debug mode
   DEBUG=* npm start

   # Verbose flags
   command --verbose --debug

   # Enable all logging
   LOG_LEVEL=debug
   ```

4. **Read Library Source**
   - If error from library, read library code
   - Check library issue tracker
   - Look for related error messages

### Challenge 4: Fix Doesn't Work

**Problem**: Implemented fix but issue persists

**Solution Approach**:

1. **Verify Fix Actually Applied**
   ```typescript
   // Add logging to confirm
   if (condition) {
     console.log('FIX APPLIED: New code path');
     // new code
   }

   // Did you see the log? If not, fix not reached.
   ```

2. **Check Fix Location**
   - Fixed right file?
   - Fixed right function?
   - All instances fixed?
   - Code recompiled/reloaded?

3. **Verify Understanding**
   - Was hypothesis correct?
   - Did you misunderstand the problem?
   - Is there a deeper issue?

4. **Count Attempts**
   - Attempt 1 failed → Re-analyze
   - Attempt 2 failed → Deeper investigation
   - **Attempt 3 failed → STOP, question architecture**

### Challenge 5: Multiple Bugs Overlap

**Problem**: Fixing one bug reveals another

**Solution Approach**:

1. **Separate Issues**
   ```
   Bug A: Authentication fails
   Bug B: Authorization missing
   Bug C: Error handling wrong

   These are THREE separate bugs
   Fix ONE at a time
   ```

2. **Priority Order**
   - Fix deepest issue first (authentication)
   - Then dependent issues (authorization)
   - Then surface issues (error handling)

3. **Track Each Separately**
   ```
   Create separate:
   - Test cases
   - Fixes
   - Verifications

   Don't bundle fixes
   ```

4. **If They Keep Cascading**
   - This indicates architectural problem
   - STOP fixing symptoms
   - Discuss fundamental design with human partner

### Challenge 6: Debugging Takes Too Long

**Problem**: Hours spent, no progress

**Solution Approach**:

1. **Assess Current Phase**
   ```
   Still in Phase 1? → Not enough evidence gathered
   Stuck in Phase 3? → Hypotheses too vague
   Repeated Phase 4? → Wrong architecture
   ```

2. **Check for Red Flags**
   - Making random changes? → Return to Phase 1
   - Guessing without evidence? → Gather more data
   - Fixing symptoms? → Find root cause
   - 3+ fix attempts? → Question architecture

3. **Start Over**
   ```
   If stuck after 2+ hours:
   1. Write down everything you know
   2. List assumptions you've made
   3. Question each assumption
   4. Start Phase 1 fresh
   ```

4. **Ask for Help**
   - Explain to human partner
   - Describe evidence gathered
   - Share hypotheses tested
   - Ask for guidance

### Challenge 7: Human Partner Signals You're Wrong

**Problem**: Human partner redirects you with questions

**Common Signals**:

| Signal | Meaning | Your Action |
|--------|---------|-------------|
| "Is that not happening?" | You assumed without verifying | Add evidence gathering |
| "Will it show us...?" | You should have added diagnostics | Add logging/instrumentation |
| "Stop guessing" | You're proposing fixes without understanding | Return to Phase 1 |
| "Ultrathink this" | Question fundamentals, not symptoms | Question architecture |
| "We're stuck?" (frustrated) | Your approach isn't working | Change debugging strategy |

**Solution Approach**:

1. **Recognize the Signal**
   - Human partner is redirecting for a reason
   - They see something you're missing
   - Don't argue or defend

2. **STOP Current Approach**
   - Whatever you're doing isn't working
   - Return to Phase 1
   - Gather more evidence

3. **Respond Appropriately**
   ```
   Signal: "Is that not happening?"
   Response: "Let me verify that assumption with evidence"

   Signal: "Stop guessing"
   Response: "You're right, let me investigate the root cause first"

   Signal: "We're stuck?"
   Response: "Let me reconsider the approach from Phase 1"
   ```

4. **Learn the Pattern**
   - Note what triggered the redirect
   - Don't repeat that mistake
   - Adjust debugging approach

## When Systematic Approach Seems Slow

### Perception vs Reality

**Feeling**: "This process is taking too long, just try a quick fix"

**Reality**:
- Systematic: 15-45 minutes → correct fix
- Random: 2-4 hours thrashing → maybe works

**Remember**: Time spent in Phase 1 is time saved avoiding wrong fixes

### Time Breakdown

```
Phase 1 (Root Cause):    10-20 minutes
Phase 2 (Pattern):        5-10 minutes
Phase 3 (Hypothesis):     5-10 minutes
Phase 4 (Implementation): 5-15 minutes
TOTAL:                   25-55 minutes

Random Fix Approach:
Attempt 1:               15 min → fails
Attempt 2:               20 min → fails
Attempt 3:               30 min → partially works
Debug new issues:        60 min
TOTAL:                   125+ minutes
```

### When It Actually IS Slow

**If systematic approach taking 2+ hours:**

1. **Check Evidence Quality**
   - Logs detailed enough?
   - Reproduction reliable?
   - All layers instrumented?

2. **Check Hypothesis Quality**
   - Too vague?
   - Not testable?
   - Based on assumptions?

3. **Check Fix Scope**
   - Trying to fix too much at once?
   - Bundling multiple issues?
   - Over-engineering solution?

## Process Shortcuts (When Appropriate)

### Tiny Obvious Bugs

**When**: Typo in variable name, missing comma, etc.

**Shortcut**: Can fix immediately if:
- [ ] You can see exact problem in error message
- [ ] Fix is one-line change
- [ ] Can verify fix in <30 seconds
- [ ] Zero risk of side effects

**Still Required**: Quick verification that fix works

### Repeated Known Issues

**When**: Same bug pattern seen before

**Shortcut**: Can use known solution if:
- [ ] 100% certain it's identical issue
- [ ] Previous solution documented
- [ ] Can verify match with evidence
- [ ] Test case exists

**Still Required**: Verify it actually matches

### Development vs Production

**Development**: Can be slightly less rigorous
- Faster iteration acceptable
- Can test fixes quickly
- Easy rollback

**Production**: ALWAYS full systematic process
- High cost of being wrong
- Limited testing ability
- Difficult rollback

## Recovery Strategies

### If You Made Random Changes

**Situation**: Violated systematic process, made changes without investigation

**Recovery**:
1. **Revert ALL changes** - back to known state
2. **Document what you tried** - data for Phase 1
3. **Start Phase 1 fresh** - use failed attempts as evidence
4. **Don't keep "parts that might work"** - clean slate

### If You're in Guess Loop

**Situation**: Tried multiple fixes, none worked, now guessing

**Recovery**:
1. **Stop immediately** - more guesses won't help
2. **Count attempts** - 3+? Architecture problem
3. **Gather evidence** - instrument everything
4. **Question fundamentals** - is approach wrong?

### If Time Pressure Mounting

**Situation**: Manager wants it fixed NOW, pressure to skip process

**Recovery**:
1. **Communicate reality** - "Systematic is faster than guessing"
2. **Show progress** - "Phase 1 complete, identified root cause"
3. **Set expectation** - "15 more minutes for correct fix"
4. **Don't skip steps** - rushing guarantees rework

## Tools for When Stuck

### Rubber Duck Debugging

Explain problem out loud (or in writing):
1. What you're trying to debug
2. What you've discovered
3. What hypotheses you've tested
4. What you're confused about

Often reveals the issue.

### Five Whys

Keep asking "Why?" until you hit root cause:
```
Bug: Dashboard slow
Why? → API calls taking long
Why? → Database queries slow
Why? → Missing indexes
Why? → Recent migration didn't add them
Why? → Migration script had bug
```

### Minimal Reproduction

Strip everything until only broken part remains:
- Remove unrelated code
- Simplify inputs
- Isolate single operation
- Proves exact point of failure

## Summary

When debugging gets hard:
- Cannot reproduce → Gather more context, add logging
- Too many causes → Binary search, eliminate systematically
- Cryptic errors → Search, increase verbosity, read source
- Fix doesn't work → Verify applied, count attempts
- Multiple bugs → Separate and prioritize
- Taking too long → Assess phase, check for red flags
- Human redirects → Recognize signal, return to Phase 1

**Remember**: Systematic approach is FASTER than random fixes, especially when it seems slow.

## Related References

- [Workflow](workflow.md): Complete four-phase process
- [Examples](examples.md): Real-world scenarios
- [Anti-patterns](anti-patterns.md): What NOT to do

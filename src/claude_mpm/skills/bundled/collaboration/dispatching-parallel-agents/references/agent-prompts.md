# Agent Prompts

Complete guide to writing effective prompts for parallel agent dispatch.

## Prompt Structure

### The Four Essential Elements

Every agent prompt must include:

1. **Scope** - What domain/files the agent works on
2. **Goal** - What success looks like
3. **Constraints** - What the agent should NOT do
4. **Output** - What to return when complete

**Missing any element leads to:**
- Scope missing → Agent changes too much
- Goal missing → Agent doesn't know when done
- Constraints missing → Agent breaks other things
- Output missing → You can't verify what changed

### Template: Test File Fixing

```markdown
Fix the [N] failing tests in [file path]:

[List each failing test name and error message]

Context:
[Why these tests are failing - recent changes, library updates, etc.]

Your task:
1. Read the test file and understand what each test verifies
2. Identify root cause - is it the test or the implementation?
3. Fix by:
   [Specific guidance based on failure type]

Constraints:
- Only modify [allowed files]
- Do NOT change [protected files/APIs]
- [Other specific constraints]

Return:
- Summary of root cause
- List of files changed with brief explanation
- Confirmation all tests in scope now pass
```

### Template: Subsystem Investigation

```markdown
Investigate and fix issues in [subsystem name]:

Symptoms:
[List observed failures, errors, unexpected behavior]

Your scope:
[List files/modules in this subsystem]

Your task:
1. Reproduce the issue locally
2. Identify root cause through debugging
3. Implement minimal fix
4. Verify fix resolves symptoms

Constraints:
- Stay within [subsystem] boundaries
- Coordinate with me before changing shared utilities
- Don't modify external dependencies

Return:
- Root cause explanation
- Your fix approach and rationale
- List of changed files
- Verification steps you performed
```

### Template: Feature Bug Fix

```markdown
Fix bug in [feature name]:

Bug report:
[User-reported issue or test failure]

Expected behavior:
[What should happen]

Actual behavior:
[What currently happens]

Your task:
1. Locate where this behavior is implemented
2. Identify why actual ≠ expected
3. Fix the implementation or test expectations
4. Add test coverage if missing

Constraints:
- Maintain backward compatibility for [API/interface]
- Don't change [other features]
- Keep fix minimal and focused

Return:
- Root cause (why did this bug exist?)
- Your fix and why it's correct
- Test coverage added/modified
```

## Good vs Bad Prompts

### Example 1: Test Failures

**❌ Bad:**
```
Fix the tests that are failing.
```

**Problems:**
- No scope (which tests?)
- No context (why failing?)
- No constraints (can change anything)
- No output format

**✅ Good:**
```
Fix the 3 failing tests in src/auth/login.test.ts:

1. "should handle expired sessions" - TypeError: Cannot read property 'refresh' of undefined
2. "should refresh tokens" - Expected token to be defined, got undefined
3. "should logout on invalid token" - Expected logout() to be called

Context: These started failing after auth library upgrade v2→v3

Your task:
1. Review auth library v3 migration guide
2. Update TokenService usage to v3 API
3. Verify all 3 tests pass

Constraints:
- Only modify login.service.ts and login.test.ts
- Don't change TokenService (external library)

Return:
- What changed in v3 API
- Your implementation changes
- Test status after fix
```

### Example 2: Subsystem Issues

**❌ Bad:**
```
The payment stuff is broken, please fix.
```

**Problems:**
- "Payment stuff" too vague
- "Broken" undefined (what's the symptom?)
- No specific task

**✅ Good:**
```
Fix payment processing errors in checkout flow:

Errors observed:
- Stripe webhook receiving 500 responses
- Payment confirmations not saving to database
- Users not receiving email receipts

Your scope:
- src/payments/stripe-webhook.controller.ts
- src/payments/payment.service.ts
- src/payments/payment.model.ts

Your task:
1. Reproduce webhook failure with test events
2. Identify why confirmations aren't saving
3. Fix the payment processing pipeline
4. Verify webhooks return 200 and emails send

Constraints:
- Don't modify Stripe SDK usage (library is correct)
- Don't change payment.model.ts schema (requires migration)
- Keep email service calls async (don't block webhook)

Return:
- Root cause of each error
- Your fixes and verification
```

### Example 3: Investigation + Fix

**❌ Bad:**
```
Look into the performance problems.
```

**Problems:**
- What performance problems where?
- What's the success criteria?
- Should agent fix or just report?

**✅ Good:**
```
Investigate and fix slow response times in product search API:

Observed: /api/products/search takes 3-5 seconds (should be <500ms)

Your scope:
- src/products/search.service.ts
- src/products/search.controller.ts
- Database queries for product search

Your task:
1. Profile the search endpoint to identify bottleneck
2. Analyze database query performance
3. Optimize slow queries or add caching
4. Verify response time <500ms for typical searches

Constraints:
- Don't change API contract (request/response shape)
- Keep search results accurate (no false positives)
- If caching, implement proper invalidation

Return:
- Profiling results (what was slow)
- Your optimization approach
- Performance before/after measurements
```

## Context Provision

### What Context to Include

**Always include:**
- Exact error messages (copy-paste)
- Test names that are failing
- Recent changes that might be related
- Expected vs actual behavior

**Include when relevant:**
- Library/framework versions
- Environment differences (prod vs dev)
- User reports or bug tickets
- Related issues that were fixed

**Don't include:**
- Entire codebase (agent will search)
- Unrelated files
- Historical context beyond 1-2 changes back
- Speculation ("I think maybe...")

### Example: Rich Context

```markdown
Fix 3 failures in batch-completion-behavior.test.ts:

Test failures:
1. "should execute all tools in batch"
   Error: Expected 3 tool executions, received 0

2. "should complete batch when all tools finish"
   Error: Batch status is 'pending', expected 'completed'

3. "should handle partial batch completion"
   Error: completedCount is 0, expected 2

Context:
- Started failing after refactoring event emission (commit abc123)
- Changed from direct method calls to event-based architecture
- Other tests pass, only batch execution affected

Relevant code:
- src/batch/batch-executor.ts (execution logic)
- src/batch/batch.service.ts (status tracking)
- Tests use mock tools that resolve after 100ms

Your task:
1. Review how events are emitted in new architecture
2. Check if batch executor is listening to correct events
3. Verify event payload structure matches expectations
4. Fix event wiring or update tests if behavior changed intentionally

Constraints:
- Keep event-based architecture (don't revert to direct calls)
- Don't modify mock tools in tests
- Ensure fix works for both sync and async tools

Return:
- What was wrong with event wiring
- Your fix
- Verification all 3 tests pass
```

## Common Mistakes

### Mistake 1: Too Broad

**❌ Bad:**
```
Fix all the auth issues and make sure everything works.
```

**Why bad:**
- "All auth issues" could be 50 files
- "Everything works" has no definition
- Agent doesn't know where to start

**✅ Fix:**
```
Fix the 2 failing tests in auth/session.test.ts:
- Test 1: [specific test name and error]
- Test 2: [specific test name and error]

Success = both tests pass
```

### Mistake 2: No Context

**❌ Bad:**
```
Fix the race condition in agent-tool-abort.test.ts
```

**Why bad:**
- Which race condition?
- What's the symptom?
- What was changed recently?

**✅ Fix:**
```
Fix race condition in agent-tool-abort.test.ts:

Symptom: Test "should abort tool with partial output" is flaky
- Passes 70% of time, fails 30%
- When fails: expects 'interrupted at' in message, message is empty

Likely cause: Test doesn't wait for abort to complete before asserting

Your task: Replace arbitrary timeout with event-based waiting
```

### Mistake 3: Unclear Constraints

**❌ Bad:**
```
Fix the tests but don't break anything.
```

**Why bad:**
- "Don't break anything" is obvious but not actionable
- Doesn't specify what agent CAN change

**✅ Fix:**
```
Fix the tests in login.test.ts.

Allowed changes:
- login.service.ts (implementation)
- login.test.ts (test expectations)

NOT allowed:
- auth.controller.ts (API contract)
- user.model.ts (database schema)
- Shared utilities in /common

Coordinate with me before changing anything else.
```

### Mistake 4: No Output Specification

**❌ Bad:**
```
Fix the payment processing bugs.
```

**Why bad:**
- Agent might fix and not tell you what changed
- You can't verify the fix without reading all the code

**✅ Fix:**
```
Fix payment processing bugs.

When complete, return:
1. Root cause analysis - why were payments failing?
2. List of files you changed with brief explanation each
3. How you verified the fix (tests? manual testing?)
4. Any risks or edge cases to watch for
```

## Advanced Patterns

### Pattern: Investigate Then Fix

**Use when:** Root cause unknown, agent needs to explore

```markdown
Investigate why user profile updates are failing:

Symptoms:
- PUT /api/users/:id returns 200 but changes don't persist
- Database shows old values after update
- No errors in logs

Your approach:
1. **Investigate** (15-20 min):
   - Add debug logging to update flow
   - Check if database transaction commits
   - Verify request payload reaches database layer

2. **Report findings** to me:
   - What you discovered
   - Proposed fix approach

3. **Wait for confirmation** before implementing fix

4. **Implement** approved fix

This two-phase approach ensures we fix root cause, not symptoms.
```

### Pattern: Parallel Agents with Shared Learning

**Use when:** Multiple agents might discover related info

```markdown
[Agent 1 - Auth subsystem]
Fix auth issues, report any shared utility bugs you find.

[Agent 2 - Payment subsystem]
Fix payment issues, report any shared utility bugs you find.

[Agent 3 - Notification subsystem]
Fix notification issues, report any shared utility bugs you find.

If any agent finds a shared utility bug:
1. Report it immediately
2. Pause your other work
3. Wait for coordinator to decide if one agent should fix centrally
```

### Pattern: Staged Dispatch

**Use when:** Some problems must be fixed before others

```markdown
[Agent 1 - Priority 1]
Fix database connection pool exhaustion.
This is blocking other work - highest priority.

Return ASAP: Is it fixed?

[Agent 2 & 3 - Will dispatch after Agent 1]
Waiting for database fix before investigating:
- Agent 2: Session timeout issues (might be due to DB)
- Agent 3: Query performance (definitely due to DB)
```

## Prompt Checklist

Before dispatching any agent:

```
□ Scope clearly defined (files, boundaries)
□ Goal is specific and measurable
□ Context includes error messages and recent changes
□ Constraints specify what NOT to change
□ Output format specified (summary, file list, verification)
□ Agent knows when to ask for help vs decide independently
□ Integration plan considered (how will this merge with other agent work?)
```

## Template Library

### Quick Template: Single Test File

```markdown
Fix [N] failing tests in [file]:

Tests:
1. [test name] - [error]
2. [test name] - [error]

Task: [what to do]
Don't: [what not to change]
Return: Root cause + changes + verification
```

### Quick Template: Bug Investigation

```markdown
Investigate [symptom]:

Context: [when it happens, what changed]
Scope: [files to look at]
Task: Find root cause, propose fix, wait for approval
Return: Analysis + proposed solution + risks
```

### Quick Template: Performance Issue

```markdown
Optimize [slow operation]:

Current: [performance measurement]
Target: [performance goal]
Scope: [what to optimize]
Constraints: [what must stay the same]
Return: Bottleneck analysis + optimization + before/after
```

## Real-World Examples

### Example: Actual Parallel Dispatch

From debugging session (2025-10-03):

**Agent 1 Prompt:**
```markdown
Fix the 3 failing tests in src/agents/agent-tool-abort.test.ts:

1. "should abort tool with partial output capture" - expects 'interrupted at' in message
2. "should handle mixed completed and aborted tools" - fast tool aborted instead of completed
3. "should properly track pendingToolCount" - expects 3 results but gets 0

These are timing/race condition issues. Your task:

1. Read the test file and understand what each test verifies
2. Identify root cause - timing issues or actual bugs?
3. Fix by:
   - Replacing arbitrary timeouts with event-based waiting
   - Fixing bugs in abort implementation if found
   - Adjusting test expectations if testing changed behavior

Do NOT just increase timeouts - find the real issue.

Return: Summary of what you found and what you fixed.
```

**Agent 2 Prompt:**
```markdown
Fix the 2 failing tests in src/agents/batch-completion-behavior.test.ts:

1. "should execute all tools in batch" - expected 3 tool executions, received 0
2. "should complete batch when all tools finish" - batch status is 'pending', expected 'completed'

Context: These started failing after event refactoring.

Your task:
1. Verify event emission in batch executor
2. Check event listeners are set up correctly
3. Fix event wiring or update test expectations

Return: Summary of what you found and what you fixed.
```

**Agent 3 Prompt:**
```markdown
Fix the 1 failing test in src/agents/tool-approval-race-conditions.test.ts:

1. "should handle rapid tool approvals" - execution count is 0, expected 3

Likely cause: Test doesn't wait for async execution to complete.

Your task:
1. Add proper waiting for tool execution completion
2. Verify race conditions are actually handled (not just test timing)

Return: Summary of what you found and what you fixed.
```

**Results:**
- All agents returned clear summaries
- No scope overlap, no conflicts
- All fixes integrated cleanly
- Full test suite passed

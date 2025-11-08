# Troubleshooting

Complete guide to handling conflicts, verification strategies, and resolving common problems in parallel agent dispatch.

## Conflict Detection

### File-Level Conflicts

**Symptom:** Multiple agents modified the same file

**Detection:**
```bash
# After agent returns, check which files changed
git diff --name-only

# Compare with other agents' file lists
# If overlap exists → conflict potential
```

**Resolution strategy:**

```
Level 1: Non-overlapping changes
- Agent A changed lines 10-20
- Agent B changed lines 50-60
→ Git auto-merge handles this
→ Verify: Run tests after merge

Level 2: Nearby changes
- Agent A changed lines 10-20
- Agent B changed lines 25-35
→ Git might merge, but logic conflict possible
→ Verify: Review both changes for interaction
→ Test: Run full suite, check edge cases

Level 3: Overlapping changes
- Agent A changed lines 10-20
- Agent B changed lines 15-25
→ Git merge conflict
→ Verify: Understand both changes
→ Resolve: Manual merge or redesign
```

### Logic-Level Conflicts

**Symptom:** No merge conflicts, but changes interact poorly

**Example:**
```javascript
// Agent A changed function signature
function processPayment(userId, amount) { ... }
// Previously: processPayment(amount)

// Agent B added calls using old signature
processPayment(100); // Now breaks!
```

**Detection strategy:**

1. **Review all agent summaries** before integrating
2. **Identify interface changes** (function signatures, API contracts)
3. **Check if other agents** use those interfaces
4. **Run full test suite** after each integration
5. **Watch for new failures** in code you didn't touch

**Prevention:**

```markdown
Agent prompts should specify:

Constraints:
- Do NOT change public interfaces without coordination
- Do NOT modify shared utilities
- If you must change a signature, report it before implementing
```

### State-Level Conflicts

**Symptom:** Tests pass individually but fail when integrated

**Example:**
```
Agent A: Clears cache on startup
Agent B: Expects cache to be populated

Individually:
- Agent A tests: Cache clearing works ✓
- Agent B tests: Cache usage works ✓

Together:
- Agent B tests fail: Cache is empty ✗
```

**Detection:**
```bash
# Test each agent's changes in isolation
git checkout agent-A-branch
npm test # Pass ✓

git checkout agent-B-branch
npm test # Pass ✓

# Test integrated
git checkout integration-branch
npm test # Fail ✗ → State conflict detected
```

**Resolution:**
1. Understand state assumptions each agent made
2. Determine correct initialization order
3. Add explicit state setup in tests
4. Or refactor to remove shared state dependency

## Verification Strategies

### Strategy 1: Progressive Integration

**Approach:** Integrate one agent at a time, verify between each

```bash
# Start from clean main
git checkout main

# Integrate Agent 1
git merge agent-1-fixes
npm test # Verify Agent 1 only
# If pass: continue
# If fail: fix Agent 1 before integrating others

# Integrate Agent 2
git merge agent-2-fixes
npm test # Verify Agent 1 + 2
# If pass: continue
# If fail: identify which combination breaks

# Integrate Agent 3
git merge agent-3-fixes
npm test # Verify all 3
```

**Benefits:**
- Isolates which integration causes failures
- Easier to debug conflicts
- Clear rollback points

**Cost:**
- More integration steps
- Takes longer than all-at-once

**Use when:** High risk of conflicts, complex changes

### Strategy 2: Parallel Verification

**Approach:** Verify each agent's changes in parallel, then integrate all

```bash
# Parallel verification (can run simultaneously)
# Terminal 1
git checkout agent-1-fixes
npm test # Verify Agent 1 in isolation

# Terminal 2
git checkout agent-2-fixes
npm test # Verify Agent 2 in isolation

# Terminal 3
git checkout agent-3-fixes
npm test # Verify Agent 3 in isolation

# After all pass individually
git checkout integration-branch
git merge agent-1-fixes agent-2-fixes agent-3-fixes
npm test # Verify integrated
```

**Benefits:**
- Fast verification of individual agents
- All agents validated before integration
- Clear that issues are integration-specific

**Cost:**
- Integration failures are harder to isolate
- Might need to back out and use progressive approach

**Use when:** Low risk of conflicts, well-scoped agents

### Strategy 3: Staged Integration

**Approach:** Group related agents, integrate by groups

```bash
# Group 1: Test fixes (low conflict risk)
git merge agent-1-test-fixes agent-2-test-fixes
npm test

# Group 2: Implementation changes (higher conflict risk)
git merge agent-3-impl-changes
npm test

# Group 3: Refactoring (highest conflict risk)
git merge agent-4-refactor
npm test
```

**Benefits:**
- Balances speed and safety
- Groups likely-compatible changes
- Easier conflict isolation than all-at-once

**Use when:** Mixed risk levels across agents

## Common Problems

### Problem 1: Agent Changed Too Much

**Symptom:**
```
Agent task: "Fix login.test.ts (3 tests)"
Agent result: Changed 12 files, refactored auth module
```

**Why this happened:**
- Prompt was too vague
- No constraints specified
- Agent "improved" code beyond scope

**Immediate fix:**
1. Review changes - which are necessary for the task?
2. Extract only required changes
3. Discard "improvements" outside scope

**Prevention:**
```markdown
Better prompt:

Fix the 3 failing tests in login.test.ts.

Allowed changes:
- login.service.ts (if bug found)
- login.test.ts (if test expectations wrong)

NOT allowed:
- Other files in auth module
- Refactoring
- Code style changes

Stay focused on making the 3 tests pass.
```

### Problem 2: Agent Didn't Explain Changes

**Symptom:**
```
Agent: "Fixed the tests ✓"
You: "What did you change?"
Agent: [no summary provided]
```

**Immediate fix:**
1. Review git diff manually
2. Understand each change
3. Ask agent to explain (in follow-up)

**Prevention:**
```markdown
Agent prompt must include:

Return:
- Root cause explanation
- List of files changed with brief explanation EACH
- How you verified the fix
- Any risks or edge cases

Do NOT just say "fixed" - I need to understand what changed.
```

### Problem 3: Agents Have Conflicting Approaches

**Symptom:**
```
Agent A: Fixed race condition by adding mutex locks
Agent B: Fixed race condition by making operation synchronous

Both approaches work individually but conflict when integrated
```

**Why this happened:**
- Agents made independent architectural decisions
- No coordination on approach
- Both valid but incompatible

**Resolution:**
1. **Evaluate approaches:**
   - Which is more aligned with codebase patterns?
   - Which has better performance/correctness?
   - Which has fewer side effects?

2. **Choose one approach:**
   - Discard the other agent's changes
   - Or merge best parts of both

3. **Re-test with chosen approach:**
   - Verify all original issues resolved
   - Ensure no new issues introduced

**Prevention:**
```markdown
For architectural decisions, use two-phase approach:

Phase 1: Investigate and propose
- Agents research problem
- Agents propose solutions
- Coordinator reviews and aligns approaches

Phase 2: Implement approved solutions
- Agents implement with aligned approach
- No architectural conflicts
```

### Problem 4: Integration Introduces New Failures

**Symptom:**
```
Agent 1 tests: Pass ✓
Agent 2 tests: Pass ✓
Agent 3 tests: Pass ✓

Integrated: Agent 1 & 2 tests pass, but Agent 3 tests fail ✗
```

**Diagnosis process:**

```bash
# Identify which combination breaks
git checkout main
git merge agent-1-fixes # Test → Pass ✓
git merge agent-2-fixes # Test → Pass ✓
# So far so good

git merge agent-3-fixes # Test → Fail ✗
# Agent 3 conflicts with Agent 1 + 2 integration

# Isolate the conflict
# Test Agent 3 with each individually
git checkout main
git merge agent-1-fixes agent-3-fixes # Test → ?
git checkout main
git merge agent-2-fixes agent-3-fixes # Test → ?

# Identify which specific interaction breaks
```

**Common causes:**

1. **Initialization order dependency**
   ```
   Agent 1 & 2 changed initialization order
   Agent 3 assumes old order
   → Solution: Update Agent 3 to new order
   ```

2. **Shared state assumption**
   ```
   Agent 1 & 2 now clear state between tests
   Agent 3 assumes state persists
   → Solution: Update Agent 3 to set up its state
   ```

3. **Interface change**
   ```
   Agent 1 changed function signature
   Agent 3 uses old signature
   → Solution: Update Agent 3 calls to new signature
   ```

### Problem 5: Can't Reproduce Agent's Success

**Symptom:**
```
Agent: "All tests pass ✓"
You integrate: Tests fail ✗
```

**Possible causes:**

1. **Agent ran subset of tests**
   ```
   Agent ran: npm test login.test.ts
   You ran: npm test (all tests)

   Agent's tests pass, but broke other tests
   ```

2. **Environment difference**
   ```
   Agent: Used cached dependencies
   You: Fresh install

   Or vice versa
   ```

3. **State pollution**
   ```
   Agent: Tests passed in specific order
   You: Tests run in different order

   Agent's tests depend on state from previous tests
   ```

**Debugging steps:**

```bash
# 1. Exact reproduction
Run EXACTLY what agent ran:
- Same test command
- Same working directory
- Same git commit

# 2. Expand scope
Run broader test suite:
npm test # All tests
npm test --runInBand # Sequential execution
npm test --randomize # Random order

# 3. Clean environment
rm -rf node_modules package-lock.json
npm install
npm test

# 4. Check for state
npm test -- --forceExit # Kill process after tests
npm test -- --detectOpenHandles # Find state leaks
```

## Verification Checklist

### Pre-Integration

Before integrating any agent's work:

```
□ Agent provided clear summary of changes
□ Root cause explained and makes sense
□ Changed files list reviewed
□ Changes are within assigned scope
□ No unexpected files modified
□ No public interface changes (or coordinated if needed)
□ Agent verified their tests pass
```

### During Integration

While integrating each agent:

```
□ Git merge conflicts resolved correctly
□ Both agents' logic preserved (not just picked one side)
□ Ran tests after resolving conflicts
□ No new warnings or errors introduced
□ Code style consistent (linting passes)
```

### Post-Integration

After all agents integrated:

```
□ Full test suite passes
□ No new failures in unrelated tests
□ Performance hasn't degraded (if relevant)
□ All original issues resolved
□ No regressions introduced
□ Code review completed (if team process)
```

## Recovery Procedures

### Procedure 1: Rollback Individual Agent

**When:** One agent's changes cause issues

```bash
# Identify problematic agent
git log --oneline

# Revert that agent's merge
git revert -m 1 <merge-commit-hash>

# Or reset if not pushed yet
git reset --hard HEAD~1

# Re-test without that agent
npm test

# Fix or re-do that agent's work
```

### Procedure 2: Start Over with Integration

**When:** Multiple conflicts, unclear which combination breaks

```bash
# Save all agent branches
git branch agent-1-fixes-backup agent-1-fixes
git branch agent-2-fixes-backup agent-2-fixes
git branch agent-3-fixes-backup agent-3-fixes

# Reset integration branch
git checkout integration
git reset --hard main

# Try progressive integration instead of all-at-once
# (See Strategy 1: Progressive Integration)
```

### Procedure 3: Rebase and Retry

**When:** Conflicts due to diverged branches

```bash
# Update all agent branches from main
git checkout agent-1-fixes
git rebase main

git checkout agent-2-fixes
git rebase main

git checkout agent-3-fixes
git rebase main

# Now integrate with updated branches
# Conflicts should be reduced
```

## Advanced Conflict Resolution

### Conflict Type 1: Competing Implementations

**Scenario:**
```javascript
// Agent A's approach: Add caching layer
async function fetchUser(id) {
  const cached = cache.get(id);
  if (cached) return cached;
  const user = await db.query(id);
  cache.set(id, user);
  return user;
}

// Agent B's approach: Optimize database query
async function fetchUser(id) {
  return await db.query(id, {
    include: ['profile', 'settings'] // Single query vs N+1
  });
}
```

**Resolution:**
1. **Understand goals:**
   - Agent A: Reduce database load
   - Agent B: Reduce query count

2. **Evaluate compatibility:**
   - Can we do both?
   - Are they solving same problem differently?

3. **Best approach:**
   ```javascript
   // Combined: Optimized query + caching
   async function fetchUser(id) {
     const cached = cache.get(id);
     if (cached) return cached;
     const user = await db.query(id, {
       include: ['profile', 'settings']
     });
     cache.set(id, user);
     return user;
   }
   ```

### Conflict Type 2: Test Expectations

**Scenario:**
```javascript
// Agent A: Made function async
async function validateEmail(email) { ... }

// Agent B: Test expects synchronous
test('validates email', () => {
  const result = validateEmail('test@example.com');
  expect(result).toBe(true); // Fails: result is Promise
});
```

**Resolution:**
1. **Identify which is correct:**
   - Should function be async? (Agent A)
   - Or should test be updated? (Agent B)

2. **Fix approach:**
   ```javascript
   // Update test to handle async
   test('validates email', async () => {
     const result = await validateEmail('test@example.com');
     expect(result).toBe(true);
   });
   ```

### Conflict Type 3: Shared Utility Changes

**Scenario:**
```javascript
// Shared utility
function formatDate(date) { ... }

// Agent A: Changed signature to add timezone
function formatDate(date, timezone) { ... }

// Agent B: Added calls without timezone
const formatted = formatDate(new Date()); // Breaks!
```

**Resolution options:**

**Option 1: Backward compatible**
```javascript
function formatDate(date, timezone = 'UTC') {
  // Default timezone maintains backward compatibility
}
```

**Option 2: Update Agent B's calls**
```javascript
// Find all Agent B's calls and update
const formatted = formatDate(new Date(), 'UTC');
```

**Option 3: Coordination**
```markdown
Prevention: Agent prompts should say:
"Do NOT change shared utilities. If needed, coordinate first."
```

## Monitoring Integration Health

### Health Indicators

**Green (healthy integration):**
```
✓ All agents completed on time
✓ All summaries clear and detailed
✓ No file overlaps between agents
✓ All individual tests pass
✓ Full suite passes after integration
✓ No new warnings or errors
✓ Integration took <10 min
```

**Yellow (caution):**
```
⚠ Some agents took longer than expected
⚠ Minor file overlaps (non-conflicting)
⚠ Had to resolve 1-2 merge conflicts
⚠ Integration took 10-20 min
⚠ Found one unexpected test failure (quickly fixed)
```

**Red (problematic integration):**
```
✗ Multiple agents overlapped significantly
✗ Many merge conflicts
✗ Logic conflicts (no git conflicts but breaks)
✗ New test failures in unrelated code
✗ Integration took >30 min
✗ Had to rollback and restart
```

### Post-Mortem Template

After problematic integration:

```markdown
## What Went Wrong

[Describe the issue]

## Root Cause

[Why did this happen?]
- Unclear scope definition?
- Missed dependency?
- Agents made incompatible decisions?

## What We Learned

[Specific learnings from this incident]

## Prevention Strategy

[How to prevent this in future dispatches]
- Better prompt structure?
- More investigation before dispatch?
- Different grouping of problems?

## Action Items

[Concrete changes to process]
```

## Best Practices

### Do's

✓ **Verify independence** before dispatching
✓ **Define clear scopes** for each agent
✓ **Request detailed summaries** from agents
✓ **Integrate progressively** when high risk
✓ **Test after each integration** step
✓ **Document conflicts** and resolutions
✓ **Learn from issues** and improve process

### Don'ts

✗ **Don't dispatch without investigation** if independence unclear
✗ **Don't allow vague prompts** ("fix the issues")
✗ **Don't integrate blindly** without reviewing summaries
✗ **Don't skip verification** steps to save time
✗ **Don't ignore warning signs** (overlapping files, etc.)
✗ **Don't let agents change shared code** without coordination
✗ **Don't forget to run full suite** after integration

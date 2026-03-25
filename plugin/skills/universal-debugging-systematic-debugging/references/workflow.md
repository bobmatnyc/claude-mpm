# Complete Debugging Workflow

> **Part of**: [Systematic Debugging](../SKILL.md)
> **Category**: debugging
> **Reading Level**: Intermediate

## Purpose

Complete step-by-step workflow for all four phases of systematic debugging, including detailed instructions, decision trees, and verification criteria.

## Phase 1: Root Cause Investigation

**Goal**: Understand WHAT and WHY before attempting fixes.

### Step 1: Read Error Messages Carefully

**Don't skip past errors or warnings:**
- Read stack traces completely
- Note line numbers, file paths, error codes
- Error messages often contain the exact solution
- Write down exact error text

### Step 2: Reproduce Consistently

**Can you trigger it reliably?**

```
Can you reproduce the issue?
├─ Yes → Proceed to Step 3
├─ Intermittent → Gather more data
│  ├─ Check for race conditions
│  ├─ Look for environmental factors
│  ├─ Add logging around suspected area
│  └─ Document patterns (time of day, load, etc.)
└─ No → Issue may be environmental
   ├─ Check configuration differences
   ├─ Verify dependencies
   └─ Compare runtime environments
```

**Document:**
- Exact steps to reproduce
- Required preconditions
- Expected vs actual behavior
- Success rate (every time? 50%? 10%?)

### Step 3: Check Recent Changes

**What changed that could cause this?**

```bash
# Git history
git log --oneline --since="1 week ago"
git diff HEAD~5 -- path/to/relevant/file

# Recent commits
git show <commit-hash>

# Blame for specific line
git blame path/to/file.ts | grep -A5 -B5 "problem line"
```

**Look for:**
- Code changes in affected area
- New dependencies added
- Configuration changes
- Environmental differences (dev vs prod)
- Database schema changes
- API version changes

### Step 4: Gather Evidence in Multi-Component Systems

**WHEN system has multiple components (CI → build → signing, API → service → database):**

**BEFORE proposing fixes, add diagnostic instrumentation:**

```
For EACH component boundary:
  - Log what data enters component
  - Log what data exits component
  - Verify environment/config propagation
  - Check state at each layer

Run once to gather evidence showing WHERE it breaks
THEN analyze evidence to identify failing component
THEN investigate that specific component
```

**Example: Multi-layer System**

```bash
# Layer 1: Workflow
echo "=== Secrets available in workflow: ==="
echo "IDENTITY: ${IDENTITY:+SET}${IDENTITY:-UNSET}"
echo "API_KEY: ${API_KEY:+SET}${API_KEY:-UNSET}"

# Layer 2: Build script
echo "=== Environment vars in build script: ==="
env | grep IDENTITY || echo "IDENTITY not in environment"
env | grep API_KEY || echo "API_KEY not in environment"

# Layer 3: Service layer
echo "=== Service initialization: ==="
echo "Config loaded: $CONFIG_PATH"
echo "Database connection: $DB_HOST:$DB_PORT"

# Layer 4: Actual operation
echo "=== Operation execution: ==="
set -x  # Enable command tracing
./actual-operation --verbose
set +x
```

**This reveals**: Which layer fails (secrets → workflow ✓, workflow → build ✗)

### Step 5: Trace Data Flow

**WHEN error is deep in call stack:**

**Backward tracing technique:**
1. Where does bad value originate?
2. What called this function with bad value?
3. Keep tracing up until you find the source
4. Fix at source, not at symptom

**Example:**

```
Error: Cannot read property 'id' of undefined
  at processUser (user.service.ts:45)
  at handleRequest (request.handler.ts:23)
  at middleware (auth.middleware.ts:12)

Investigation:
45: const userId = user.id;  // user is undefined - WHERE did it come from?
23: processUser(req.user);   // req.user is undefined - WHERE set?
12: req.user = await getUser(token);  // getUser returned undefined - WHY?

Root cause: getUser returns undefined when token expired
Fix: Handle undefined in getUser, not at usage site
```

## Phase 2: Pattern Analysis

**Goal**: Find working examples and identify differences.

### Step 1: Find Working Examples

**Locate similar working code in same codebase:**

```bash
# Find similar patterns
grep -r "similar_function" src/
grep -r "similar_pattern" src/

# Find similar test cases
find tests/ -name "*similar*test*"
```

**Questions:**
- What works that's similar to what's broken?
- How is working code different?
- What dependencies does working code use?

### Step 2: Compare Against References

**If implementing pattern, read reference implementation COMPLETELY:**

**DON'T:**
- Skim the documentation
- Copy-paste without understanding
- "Adapt" the pattern without reading fully

**DO:**
- Read every line of reference
- Understand WHY each part exists
- Note all dependencies and setup
- Check for hidden requirements

### Step 3: Identify Differences

**List every difference, however small:**

```
Working Code          | Broken Code
---------------------|--------------------
Uses async/await     | Uses callbacks
Has error handling   | No error handling
Validates input      | Assumes valid input
Imports from '@lib'  | Imports from '../lib'
```

**Don't assume "that can't matter"** - small differences often cause bugs.

### Step 4: Understand Dependencies

**What other components does this need?**
- Required packages and versions
- Configuration settings
- Environment variables
- Database schema
- External services
- Initialization order

## Phase 3: Hypothesis and Testing

**Goal**: Form and test specific hypotheses scientifically.

### Step 1: Form Single Hypothesis

**Write it down explicitly:**

❌ Bad: "Something is wrong with the database"
✅ Good: "Database connection times out because connection pool is exhausted"

❌ Bad: "The calculation is incorrect"
✅ Good: "Division by zero when denominator is empty list"

**Good hypothesis characteristics:**
- **Specific**: Names exact variable/function/line
- **Testable**: Can be verified with single change
- **Falsifiable**: Could be proven wrong
- **Evidence-Based**: Supported by logs/observations

### Step 2: Test Minimally

**Make the SMALLEST possible change to test hypothesis:**

```typescript
// Hypothesis: Function fails when input array is empty

// Minimal test
if (array.length === 0) {
  console.log('HYPOTHESIS TEST: Empty array detected');
}

// DON'T bundle multiple changes
if (array.length === 0) {
  throw new Error('Empty array');  // Multiple changes
}
```

**One variable at a time:**
- Change only what tests hypothesis
- Keep changes minimal
- Comment your reasoning
- Revert if hypothesis wrong

### Step 3: Verify Before Continuing

**Execute reproduction case and observe outcome:**

```bash
# Run specific test
npm test path/to/failing.test.ts

# Or run reproduction script
node reproduce-bug.js
```

**Outcomes:**
- **Hypothesis Confirmed** → Proceed to Phase 4
- **Hypothesis Rejected** → Return to Phase 3 Step 1 with new data
- **Inconclusive** → Refine test or gather more data

### Step 4: When You Don't Know

**Be honest about knowledge gaps:**
- Say "I don't understand X"
- Don't pretend to know
- Ask for help
- Research more before forming hypothesis

**Better to say "I need to investigate further" than propose wrong fix.**

## Phase 4: Implementation

**Goal**: Fix the root cause, not the symptom.

### Step 1: Create Failing Test Case

**Simplest possible reproduction:**

```typescript
// Good: Minimal failing test
test('handles empty array', () => {
  const result = processArray([]);
  expect(result).toEqual([]);
});

// Bad: Too complex
test('complex scenario', () => {
  const db = setupDatabase();
  const user = createUser(db);
  const items = fetchItems(user);
  const result = processArray(items);
  // What exactly are we testing?
});
```

**Requirements:**
- Automated test if framework available
- One-off test script if no framework
- MUST have before fixing
- Should be fast to run

### Step 2: Implement Single Fix

**Address the root cause identified:**

```typescript
// Good: Fixes root cause
function processArray(items: Item[]): Result[] {
  if (items.length === 0) {
    return [];  // Handle edge case
  }
  return items.map(transform);
}

// Bad: Fixes symptom
function processArray(items: Item[]): Result[] {
  try {
    return items.map(transform);
  } catch (e) {
    return [];  // Hides real problem
  }
}
```

**Rules:**
- ONE change at a time
- No "while I'm here" improvements
- No bundled refactoring
- Focus only on the bug

### Step 3: Verify Fix

**Run full verification:**

```bash
# Test passes now?
npm test path/to/test.test.ts

# No other tests broken?
npm test

# Issue actually resolved?
node reproduce-bug.js  # Should work now
```

**Checklist:**
- [ ] Failing test now passes
- [ ] All other tests still pass
- [ ] Original bug no longer occurs
- [ ] No new warnings or errors
- [ ] Performance not degraded

### Step 4: If Fix Doesn't Work

**STOP and reassess:**

**Track attempts:**
- Fix #1 failed → Return to Phase 1, re-analyze
- Fix #2 failed → Return to Phase 1, gather more evidence
- Fix #3 failed → **STOP: Architecture problem**

**DON'T attempt Fix #4 without architectural discussion.**

### Step 5: If 3+ Fixes Failed - Question Architecture

**Pattern indicating architectural problem:**
- Each fix reveals new shared state/coupling in different place
- Fixes require "massive refactoring" to implement
- Each fix creates new symptoms elsewhere
- You're "fighting the framework"

**STOP and question fundamentals:**
- Is this pattern fundamentally sound?
- Are we "sticking with it through sheer inertia"?
- Should we refactor architecture vs continue fixing symptoms?

**Discuss with human partner before attempting more fixes.**

**This is NOT a failed hypothesis - this is wrong architecture.**

## Verification Checklist

Before marking debugging complete:

- [ ] Root cause identified (not just symptoms)
- [ ] Hypothesis formed and tested
- [ ] Fix addresses root cause
- [ ] Test case created
- [ ] Test passes
- [ ] No regressions introduced
- [ ] Solution documented
- [ ] Learned from the issue

## Summary

- Phase 1 (Root Cause): Read, reproduce, gather evidence
- Phase 2 (Pattern): Find working examples, compare
- Phase 3 (Hypothesis): Form theory, test minimally
- Phase 4 (Implementation): Create test, fix, verify
- If 3+ fixes fail: Question architecture

## Related References

- [Examples](examples.md): Real-world debugging scenarios
- [Troubleshooting](troubleshooting.md): Common debugging challenges
- [Anti-patterns](anti-patterns.md): Common mistakes to avoid

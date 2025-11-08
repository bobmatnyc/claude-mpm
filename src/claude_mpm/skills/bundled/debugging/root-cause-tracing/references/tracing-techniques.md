# Tracing Techniques

Complete methodology for tracing bugs backward through call chains to find original triggers.

## The Tracing Methodology

### Overview

Root cause tracing follows a systematic approach to walk backward through code execution until you find where bad data or invalid state originated.

**Key insight:** The place where an error manifests is rarely where the bug actually lives.

## Manual Tracing Process

### Step 1: Observe the Symptom

**What to capture:**
- Exact error message
- Stack trace (if available)
- Failed operation
- Wrong value/state
- Location where error occurred

**Example:**
```
Error: git init failed in /Users/jesse/project/packages/core
  at WorktreeManager.createSessionWorktree (worktree-manager.ts:45)
```

**Questions to ask:**
- What operation failed?
- What was the expected behavior?
- What value/state is wrong?
- Where did the error manifest?

### Step 2: Find Immediate Cause

Look at the code where the error occurs.

**Example:**
```typescript
async function createSessionWorktree(projectDir: string, sessionId: string) {
  // This is where it fails
  await execFileAsync('git', ['init'], { cwd: projectDir });
}
```

**Questions to ask:**
- What code directly causes this error?
- What parameters does it receive?
- What assumptions does it make?
- Are the parameters valid?

### Step 3: Identify the Caller

Trace one level up the call stack.

**From stack trace:**
```
  at WorktreeManager.createSessionWorktree (worktree-manager.ts:45)
  at Session.initializeWorkspace (session.ts:78)
  at Session.create (session.ts:34)
  at Test.<anonymous> (project.test.ts:12)
```

**Manual code inspection:**
```typescript
// In session.ts
static async create(name: string, projectDir: string) {
  const session = new Session(name);
  await session.initializeWorkspace(projectDir); // ← Caller
  return session;
}
```

**Questions to ask:**
- What function called this?
- What value did it pass?
- Where did that value come from?

### Step 4: Continue Tracing Up

Repeat step 3 for each caller until you find the source.

**Trace chain example:**
```
Test code (project.test.ts:12)
  → Project.create(name, context.tempDir)
    → Session.create(name, projectDir)
      → Session.initializeWorkspace(projectDir)
        → WorktreeManager.createSessionWorktree(projectDir, sessionId)
          → execFileAsync('git', ['init'], { cwd: projectDir })
            → ERROR: projectDir is empty string
```

**Working backward:**
- Where did `projectDir = ''` come from? → Session.create()
- Where did Session.create() get it? → Project.create()
- Where did Project.create() get it? → Test code
- Where did test code get it? → `context.tempDir`
- Where did `context.tempDir = ''` come from? → **ROOT CAUSE FOUND**

### Step 5: Identify Root Cause

The root cause is where bad data/state originates.

**Common root causes:**
- Uninitialized variables accessed too early
- Configuration not loaded
- Null/undefined not handled
- Wrong default value
- Timing issue (race condition)
- Environment-specific behavior

**In our example:**
```typescript
// Root cause: Getter returns empty string before initialization
function setupCoreTest() {
  let _tempDir = ''; // ← BAD: Empty string default

  beforeEach(() => {
    _tempDir = createTempDir(); // ← Set later
  });

  return { tempDir: _tempDir }; // ← Returns '' initially!
}

// Test code runs at module load time
const context = setupCoreTest();
const PROJECT_DIR = context.tempDir; // ← '' before beforeEach runs!
```

## Tracing Patterns

### Pattern 1: Data Flow Tracing

**When to use:** Invalid data appears somewhere in execution

**Process:**
1. Identify the invalid data at error point
2. Trace backward to find where it was set
3. Continue to where it originated
4. Fix at origin

**Example:**
```
userId = 0 (invalid) at database query
  ← from request.userId
    ← from parseRequest(req)
      ← from req.headers['user-id']
        ← ROOT: Header not validated/defaulted
```

### Pattern 2: Call Chain Tracing

**When to use:** Error happens deep in call stack

**Process:**
1. Start at error location
2. Examine immediate caller
3. Move up one level
4. Repeat until finding where invalid call originates

**Example:**
```
Error in database.execute(query)
  ← from UserService.findUser(id)
    ← from AuthMiddleware.authenticate()
      ← from Router.handleRequest()
        ← ROOT: No authentication check before calling
```

### Pattern 3: State Mutation Tracing

**When to use:** Object/variable has wrong value at some point

**Process:**
1. Identify when state is wrong
2. Find all places that mutate state
3. Trace backward to find which mutation caused it
4. Find why that mutation happened

**Example:**
```
config.database = undefined at startup
  ← config.database set to undefined in validateConfig()
    ← because env.DATABASE_URL is undefined
      ← ROOT: Environment variable not set
```

### Pattern 4: Timing/Ordering Tracing

**When to use:** Issue involves race conditions or execution order

**Process:**
1. Identify operations that ran in wrong order
2. Trace why the order is wrong
3. Find what controls the ordering
4. Fix ordering logic

**Example:**
```
Database query before connection established
  ← query() called in constructor
    ← constructor runs immediately
      ← connection.connect() called async in initialize()
        ← ROOT: Constructor doesn't wait for async initialization
```

## Decision Trees

### When Manual Tracing is Sufficient

```
Can you see the code path?
  → Yes: Use manual tracing
    → Stack trace available?
      → Yes: Follow stack trace
      → No: Inspect caller manually
  → No: Add instrumentation (see advanced-techniques.md)

Is error reproducible?
  → Yes: Can trace reliably
  → No: Must make reproducible first
    → Add logging to capture when it happens
    → Use instrumentation to understand timing
```

### How Deep to Trace

```
Found where bad value originates?
  → Yes: Root cause found
  → No: Continue tracing
    → At system boundary (entry point)?
      → Yes: Root cause is at boundary
      → No: Keep tracing backward

Multiple callers with same issue?
  → Yes: Root cause is in shared caller
  → No: Root cause is in specific caller path
```

### Fixing vs Adding Defense

```
Found root cause?
  → Yes:
    → Fix at source: YES
    → Add validation at intermediate layers: YES
    → Fix only at error point: NO
  → No:
    → Add defense at error point: TEMPORARY
    → Continue tracing: YES
```

## Common Tracing Challenges

### Challenge 1: Long Call Chains

**Problem:** 10+ levels in call stack
**Solution:**
- Use binary search: check middle of chain first
- Skip obviously correct intermediate calls
- Focus on where data changes

### Challenge 2: Async/Callback Hell

**Problem:** Callbacks and promises obscure call chain
**Solution:**
- Use async stack traces (Node.js: `--async-stack-traces`)
- Add trace IDs to log all operations
- Use debugger to step through promises

### Challenge 3: Multiple Code Paths

**Problem:** Error could come from multiple callers
**Solution:**
- Add conditional logging at error point
- Use instrumentation to capture caller info
- Reproduce with minimal test case

### Challenge 4: External Dependencies

**Problem:** Issue might be in third-party library
**Solution:**
- Verify inputs to library are correct
- Check library version/compatibility
- Read library source if needed
- Consider if misusing library API

### Challenge 5: No Stack Trace

**Problem:** Error doesn't produce stack trace
**Solution:**
- Add stack capture: `new Error().stack`
- Use debugger to pause at error point
- Add logging at suspected callers
- Use process of elimination

## Tips for Effective Tracing

### Use Your Tools

**IDE navigation:**
- "Find References" to see all callers
- "Go to Definition" to jump to implementation
- Call hierarchy view
- Type hierarchy for inheritance

**Debugger:**
- Set breakpoint at error point
- Step out to see caller
- Examine call stack panel
- Watch variables as they change

**Version control:**
- `git blame` to see when code changed
- `git log` to see recent changes
- `git bisect` to find when bug was introduced

### Document Your Trace

As you trace, write down the call chain:

```
ERROR: git init in wrong directory
  ← execFileAsync('git', ['init'], { cwd: '' })
  ← WorktreeManager.createSessionWorktree(projectDir='')
  ← Session.initializeWorkspace(projectDir='')
  ← Session.create(name, projectDir='')
  ← Project.create(name, context.tempDir='')
  ← Test: const PROJECT_DIR = context.tempDir
  ← ROOT: setupCoreTest() returns { tempDir: '' } before beforeEach
```

This helps you:
- Remember where you are in the trace
- Communicate findings to others
- Verify your understanding
- Identify patterns

### Know When to Stop Tracing

**Stop when you find:**
- The origin of bad data
- The first place where invariant is violated
- The entry point where validation should happen
- The configuration/initialization that sets wrong value

**Don't stop at:**
- Where error manifests
- Where symptom is visible
- Intermediate validation that fails
- Defensive checks that catch the issue

## Verification After Tracing

Once you think you've found the root cause:

1. **Verify understanding:**
   - Can you explain how the bug happens?
   - Does your explanation match all symptoms?
   - Can you predict what will happen if you fix it?

2. **Test your hypothesis:**
   - Add temporary fix at suspected root cause
   - Does it resolve the issue?
   - Does it resolve ALL instances of the issue?

3. **Implement proper fix:**
   - Fix at root cause
   - Add tests for root cause
   - Add defense-in-depth at intermediate layers
   - Verify no regressions

## Summary

**Manual tracing process:**
1. Observe symptom → 2. Find immediate cause → 3. Identify caller → 4. Trace up → 5. Find root cause

**Key principles:**
- Trace backward from symptom to source
- Don't stop at first "cause" - find original trigger
- Fix at source, add defense at layers
- Document your trace for clarity

**When to use advanced techniques:**
- Can't manually trace (see advanced-techniques.md)
- Need to identify which test pollutes (see advanced-techniques.md)
- Multiple async operations involved (see advanced-techniques.md)

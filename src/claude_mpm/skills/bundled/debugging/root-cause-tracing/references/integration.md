# Integration with Other Skills

How root-cause-tracing integrates with systematic-debugging and other debugging skills to form a complete debugging toolkit.

## Relationship with Systematic Debugging

### The Big Picture

**systematic-debugging** is the overall framework:
- Phase 1: Root Cause Investigation
- Phase 2: Pattern Analysis
- Phase 3: Hypothesis and Testing
- Phase 4: Implementation

**root-cause-tracing** is a specialized technique used within **Phase 1** when dealing with deep call stacks and unclear data origins.

### When to Use Which Skill

```
User reports bug
  ↓
Activate: systematic-debugging
  ↓
Phase 1: Root Cause Investigation
  ↓
Error deep in call stack?
  → Yes: Use root-cause-tracing
    → Trace backward to find source
    → Return to systematic-debugging Phase 2
  → No: Continue with Phase 1
    → Read error messages
    → Check recent changes
    → Continue to Phase 2
```

### Integration Flow

#### Example: Database Connection Error

**1. Start with systematic-debugging Phase 1:**
- Read error message: "Connection failed: database 'undefined' does not exist"
- Reproduce consistently: Yes, happens every time
- Check recent changes: No recent changes to database code

**2. Recognize need for root-cause-tracing:**
- Error happens deep in execution (database.connect())
- Unclear where "undefined" value originates
- Long call chain from app startup to connection

**3. Apply root-cause-tracing:**
- Step 1: Observe symptom → database name is "undefined"
- Step 2: Find immediate cause → Database constructor receives undefined
- Step 3: Trace to caller → Config object has undefined database field
- Step 4: Continue tracing → Environment variable not set
- Step 5: Root cause → Missing DATABASE_NAME env var

**4. Return to systematic-debugging Phase 2:**
- Find working examples: Other services have DATABASE_NAME set
- Compare differences: This service's .env missing the variable
- Understand dependencies: App requires DATABASE_NAME to start

**5. Proceed to Phase 3 (Hypothesis):**
- Hypothesis: Adding DATABASE_NAME env var will fix the issue
- Test minimally: Add DATABASE_NAME=testdb to .env
- Verify: App starts successfully

**6. Continue to Phase 4 (Implementation):**
- Write test: App startup should fail if DATABASE_NAME missing
- Implement fix: Add validation for required env vars
- Verify: All tests pass, app fails fast with clear error

## Integration with Defense-in-Depth

**After finding root cause with tracing, apply defense-in-depth pattern.**

### The Pattern

1. **Fix at source** (what root-cause-tracing finds)
2. **Add validation at intermediate layers** (defense-in-depth)
3. **Fail fast with clear errors** (both skills)

### Example: Git Init in Wrong Directory

**Root-cause-tracing finds:**
- Source: `setupCoreTest()` returns empty tempDir before initialization

**Defense-in-depth adds layers:**
```typescript
// Layer 0: Fix at source (root-cause-tracing result)
get tempDir(): string {
  if (!this._tempDir) {
    throw new Error('tempDir accessed before initialization');
  }
  return this._tempDir;
}

// Layer 1: Validate at entry point
static async create(name: string, directory: string) {
  if (!directory) throw new Error('Directory required');
  // ...
}

// Layer 2: Validate at workspace level
async initializeWorkspace(projectDir: string) {
  if (!projectDir) throw new Error('projectDir required');
  // ...
}

// Layer 3: Environment guard
async function gitInit(directory: string) {
  if (process.env.NODE_ENV === 'test' && !directory.includes('tmp')) {
    throw new Error('Test safety: refusing git init outside tmpdir');
  }
  // ...
}

// Layer 4: Instrumentation
async function gitInit(directory: string) {
  if (!directory || directory === process.cwd()) {
    console.error('SUSPICIOUS git init', { directory, stack: new Error().stack });
  }
  // ...
}
```

**Result:** Bug impossible at multiple levels

## Integration with Verification-Before-Completion

**After implementing fix, verify it worked.**

### The Pattern

1. **Find root cause** (root-cause-tracing)
2. **Implement fix** (systematic-debugging Phase 4)
3. **Verify fix** (verification-before-completion)

### Verification Checklist

```typescript
// After fixing root cause, verify:

// ✓ 1. Fix addresses root cause (not symptom)
const fix = 'Added validation for tempDir before access';
const rootCause = 'tempDir accessed before initialization';
// Matches? YES

// ✓ 2. All tests pass
npm test
// Result: 1847 tests passed

// ✓ 3. Specific test case for root cause
it('should throw if tempDir accessed before beforeEach', () => {
  const context = setupCoreTest();
  expect(() => context.tempDir).toThrow('before initialization');
});

// ✓ 4. No pollution/side effects
ls -la src/
// No .git directory in source

// ✓ 5. Defense layers working
// Each validation layer tested independently
```

**Only after ALL checks pass:** Mark as complete

## Integration with Test-Driven-Development

**Use TDD to create test for root cause (not symptom).**

### The Pattern

1. **Find root cause** (root-cause-tracing)
2. **Write failing test for root cause** (TDD)
3. **Fix root cause** (systematic-debugging)
4. **Verify test passes** (verification-before-completion)

### Example: Writing Test for Root Cause

**Symptom:** Git init in wrong directory
**Root cause:** tempDir accessed before initialization

**WRONG: Test for symptom**
```typescript
// ❌ Tests symptom, not root cause
it('should not create .git in source directory', async () => {
  await Project.create('test', '');
  expect(fs.existsSync('.git')).toBe(false);
});
```

**RIGHT: Test for root cause**
```typescript
// ✅ Tests root cause
it('should throw if tempDir accessed before initialization', () => {
  const context = setupCoreTest();
  expect(() => context.tempDir).toThrow('before initialization');
});

// ✅ Test defense layer
it('should validate directory parameter', async () => {
  await expect(Project.create('test', ''))
    .rejects.toThrow('Directory required');
});
```

**Why this matters:**
- Root cause test fails if bug reintroduced
- Symptom test might pass even if bug exists (different code path)
- Root cause test documents the actual issue

## Integration with Condition-Based-Waiting

**Sometimes root cause is a timing/race condition.**

### The Pattern

1. **Trace reveals race condition** (root-cause-tracing)
2. **Replace timeouts with condition-based waiting** (condition-based-waiting)

### Example: Database Query Before Connection

**Trace finds:**
```
Error: Connection not established
  ← database.query() called
    ← from constructor initialization
      ← constructor doesn't wait for connection
```

**Root cause:** Query runs before connection completes

**WRONG: Add timeout**
```typescript
constructor() {
  this.connect();
  await new Promise(resolve => setTimeout(resolve, 100)); // ❌ Race condition
}
```

**RIGHT: Condition-based waiting**
```typescript
private connectionReady: Promise<void>;

constructor() {
  this.connectionReady = this.connect();
}

async query(sql: string) {
  await this.connectionReady; // ✅ Wait for actual condition
  return this.db.execute(sql);
}
```

## Skill Activation Decision Tree

```
User reports bug
  ↓
Use: systematic-debugging (overall framework)
  ↓
Phase 1: Root Cause Investigation
  ↓
Is error deep in call stack?
  → Yes: Apply root-cause-tracing
    → Manual tracing sufficient?
      → Yes: Use tracing-techniques.md
      → No: Use advanced-techniques.md
    → Root cause found? → Continue to Phase 2
  → No: Continue Phase 1 investigation
  ↓
Phase 2: Pattern Analysis
  → Timing issue found?
    → Yes: Consider condition-based-waiting
  ↓
Phase 3: Hypothesis and Testing
  ↓
Phase 4: Implementation
  → Write test: Use test-driven-development
  → Add defense: Use defense-in-depth
  → Verify: Use verification-before-completion
```

## Complete Debugging Toolkit

### The Core Skills

1. **systematic-debugging**: Overall debugging framework (Phases 1-4)
2. **root-cause-tracing**: Technique for Phase 1 (deep call stacks)
3. **defense-in-depth**: Pattern for Phase 4 (multiple validation layers)
4. **verification-before-completion**: Ensures fix worked before claiming success
5. **test-driven-development**: Write tests for root cause, not symptoms

### When to Use Each

| Situation | Primary Skill | Supporting Skills |
|-----------|--------------|-------------------|
| Any bug report | systematic-debugging | All others |
| Deep call stack | root-cause-tracing | systematic-debugging Phase 1 |
| After finding root cause | defense-in-depth | verification-before-completion |
| Writing fix | test-driven-development | verification-before-completion |
| Timing/race conditions | condition-based-waiting | root-cause-tracing |
| Test pollution | root-cause-tracing (advanced) | systematic-debugging |

## Real-World Workflow Example

### Bug: Application Crashes on Startup

**Step 1: Activate systematic-debugging**
- Read error: "TypeError: Cannot read property 'host' of undefined"
- Reproduce: Yes, happens every time
- Recent changes: None

**Step 2: Recognize deep call stack → Use root-cause-tracing**
```
Error at database.connect()
  ← from DatabaseService.initialize()
    ← from App.start()
      ← from main()
```

**Step 3: Trace backward**
- database.connect() receives undefined config
- DatabaseService.initialize() gets config from ConfigService
- ConfigService.load() returns undefined
- Root cause: Config file not loaded before DatabaseService initialized

**Step 4: Return to systematic-debugging Phase 2**
- Find working examples: Other apps load config in main()
- Compare: This app tries to load config in service initialization
- Pattern: Initialization order problem

**Step 5: Phase 3 - Hypothesis**
- Hypothesis: Loading config before services will fix issue
- Test: Move config loading to top of main()
- Result: Works!

**Step 6: Phase 4 - Implementation with TDD**
```typescript
// Test for root cause
it('should load config before initializing services', () => {
  expect(ConfigService.isLoaded()).toBe(true);
});

// Test defense layer
it('should throw if DatabaseService initialized before config', () => {
  ConfigService.reset();
  expect(() => new DatabaseService()).toThrow('Config not loaded');
});
```

**Step 7: Add defense-in-depth**
- Layer 1: Load config first in main()
- Layer 2: DatabaseService validates config on init
- Layer 3: ConfigService throws if accessed before loaded

**Step 8: verification-before-completion**
- ✓ All tests pass
- ✓ App starts successfully
- ✓ Config loaded before services
- ✓ Clear error if config missing

**Result:** Bug fixed at root cause with multiple defensive layers

## Common Anti-Patterns

### Anti-Pattern 1: Tracing Without Framework

**Wrong:**
```
Use root-cause-tracing alone
  → Find root cause
  → Quick fix
  → No verification
  → Bug reappears later
```

**Right:**
```
Use systematic-debugging framework
  → Use root-cause-tracing in Phase 1
  → Continue through all phases
  → Verify fix
  → Bug stays fixed
```

### Anti-Pattern 2: Symptom Tests

**Wrong:**
```
Root cause: Config not loaded
Test: "Should not crash on startup"
```

**Right:**
```
Root cause: Config not loaded
Test: "Should throw if config accessed before load"
Test: "Should load config before services"
```

### Anti-Pattern 3: Fix Without Defense

**Wrong:**
```
Find root cause
  → Fix at source only
  → No validation at layers
  → Similar bug appears elsewhere
```

**Right:**
```
Find root cause
  → Fix at source
  → Add defense-in-depth
  → Test each layer
  → Similar bugs prevented
```

## Summary

**Root-cause-tracing is a technique, not a complete framework:**
- Use within systematic-debugging Phase 1
- Combine with defense-in-depth after finding root cause
- Write tests for root cause with test-driven-development
- Verify fix with verification-before-completion
- Use condition-based-waiting for timing issues

**The complete workflow:**
1. systematic-debugging (framework)
2. root-cause-tracing (investigation technique)
3. test-driven-development (test root cause)
4. defense-in-depth (multiple layers)
5. verification-before-completion (ensure success)

**Result:** Bugs fixed permanently with comprehensive prevention

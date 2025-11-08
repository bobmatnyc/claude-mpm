# Core Testing Anti-Patterns

The three most critical testing anti-patterns that violate fundamental testing principles. These patterns test mock behavior instead of real behavior, pollute production code with test concerns, or mock without understanding dependencies.

## Anti-Pattern 1: Testing Mock Behavior

**The violation:**
```typescript
// ❌ BAD: Testing that the mock exists
test('renders sidebar', () => {
  render(<Page />);
  expect(screen.getByTestId('sidebar-mock')).toBeInTheDocument();
});
```

**Why this is wrong:**
- You're verifying the mock works, not that the component works
- Test passes when mock is present, fails when it's not
- Tells you nothing about real behavior
- False confidence - production may still be broken

**your human partner's correction:** "Are we testing the behavior of a mock?"

**The fix:**
```typescript
// ✅ GOOD: Test real component or don't mock it
test('renders sidebar', () => {
  render(<Page />);  // Don't mock sidebar
  expect(screen.getByRole('navigation')).toBeInTheDocument();
});

// OR if sidebar must be mocked for isolation:
// Don't assert on the mock - test Page's behavior with sidebar present
test('page layout includes sidebar area', () => {
  render(<Page />);  // Sidebar mocked for speed
  expect(screen.getByRole('main')).toHaveClass('with-sidebar-layout');
});
```

### Detection Strategy

**Red flags:**
- Assertions check for `*-mock` in test IDs
- Test IDs contain "mock", "stub", "fake"
- Test fails when you remove the mock
- Can't explain what real behavior you're testing

**Gate Function:**

```
BEFORE asserting on any mock element:
  Ask: "Am I testing real component behavior or just mock existence?"

  IF testing mock existence:
    STOP - Delete the assertion or unmock the component

  Ask: "What would this test verify in production?"

  IF answer is "nothing" or unclear:
    STOP - Rethink what you're testing

  Test real behavior instead
```

### When Mocking is Appropriate

**Good reasons to mock:**
- Isolate slow external dependencies (network, filesystem, DB)
- Control non-deterministic behavior (time, randomness)
- Simulate error conditions hard to trigger
- Speed up test execution

**Bad reasons to mock:**
- "Might be slow" (without measuring)
- "To be safe"
- "Everyone mocks this"
- To avoid understanding dependencies

**Rule:** Mock at the boundary of slow/external operations, not high-level application logic.

## Anti-Pattern 2: Test-Only Methods in Production

**The violation:**
```typescript
// ❌ BAD: destroy() only used in tests
class Session {
  async destroy() {  // Looks like production API!
    await this._workspaceManager?.destroyWorkspace(this.id);
    await this._messageRouter?.cleanup();
    this._isDestroyed = true;
  }
}

// In tests
afterEach(() => session.destroy());
```

**Why this is wrong:**
- Production class polluted with test-only code
- Dangerous if accidentally called in production
- Violates YAGNI (You Aren't Gonna Need It)
- Violates separation of concerns
- Confuses object lifecycle with entity lifecycle
- Creates maintenance burden (unused code in production)

**The fix:**
```typescript
// ✅ GOOD: Test utilities handle test cleanup
// Session has no destroy() - it's stateless in production

// In test-utils/session-helpers.ts
export async function cleanupSession(session: Session) {
  const workspace = session.getWorkspaceInfo();
  if (workspace) {
    await workspaceManager.destroyWorkspace(workspace.id);
  }

  const router = session.getMessageRouter();
  if (router) {
    await router.cleanup();
  }
}

// In tests
afterEach(() => cleanupSession(session));
```

### When Test Utilities Make Sense

**Good candidates for test utilities:**
- Setup/teardown operations
- Test data builders
- Assertion helpers
- Test-specific configurations
- Lifecycle management for tests

**Keep in production:**
- Methods used by application code
- Proper public API
- Business logic
- Real lifecycle methods (close, dispose)

**Key distinction:** If it's never called outside test files, it shouldn't be in production code.

### Detection Strategy

**Red flags:**
- Method only called in `*.test.*` or `*.spec.*` files
- Method name suggests testing (reset, clear, destroy, mock)
- Comments say "for testing only"
- Method has no production use case

**Gate Function:**

```
BEFORE adding any method to production class:
  Ask: "Is this only used by tests?"

  IF yes:
    STOP - Don't add it
    Put it in test utilities instead (test-utils/, test-helpers/)

  Ask: "Does this class own this resource's lifecycle?"

  IF no:
    STOP - Wrong class for this method
    Resource owner should manage lifecycle

  Ask: "Would production code ever call this?"

  IF no:
    STOP - Belongs in test utilities
```

### Refactoring Existing Test-Only Methods

**Step-by-step:**

1. **Identify** - Find methods only called in test files
2. **Extract** - Create test utility function with same logic
3. **Migrate** - Update tests to use utility
4. **Remove** - Delete test-only method from production
5. **Verify** - Production builds/bundles are cleaner

**Example refactoring:**

```typescript
// Before: Production class polluted
class Database {
  async reset() { /* only for tests */ }
}

// After: Clean separation
// database.ts - production
class Database {
  // No reset() method
}

// test-utils/database.ts - tests only
export async function resetTestDatabase(db: Database) {
  // Use public API to achieve reset
  await db.executeRaw('TRUNCATE ALL TABLES');
}
```

## Anti-Pattern 3: Mocking Without Understanding

**The violation:**
```typescript
// ❌ BAD: Mock breaks test logic
test('detects duplicate server', async () => {
  // Mock prevents config write that test depends on!
  vi.mock('ToolCatalog', () => ({
    discoverAndCacheTools: vi.fn().mockResolvedValue(undefined)
  }));

  await addServer(config);
  await addServer(config);  // Should throw - but won't!
  // Test expects duplicate detection, but mock broke it
});
```

**Why this is wrong:**
- Mocked method had side effect test depended on (writing config)
- Over-mocking to "be safe" breaks actual behavior
- Test passes for wrong reason or fails mysteriously
- You're testing mock behavior, not real behavior

**The fix:**
```typescript
// ✅ GOOD: Mock at correct level
test('detects duplicate server', async () => {
  // Mock the slow part, preserve behavior test needs
  vi.mock('MCPServerManager'); // Just mock slow server startup
  // Config writing preserved - duplicate detection works

  await addServer(config);  // Config written
  await expect(addServer(config)).rejects.toThrow('already exists');
});
```

### Understanding Dependencies Before Mocking

**Questions to ask BEFORE mocking:**

1. **What does the real method do?**
   - Read the implementation
   - Check for side effects
   - Identify return values
   - Note error conditions

2. **What side effects exist?**
   - Filesystem writes
   - Database updates
   - Cache modifications
   - State changes
   - Event emissions

3. **What does THIS test need?**
   - Which side effects matter?
   - What behavior am I testing?
   - What can be safely isolated?

4. **Where should I mock?**
   - At the boundary of slow operations
   - Below the logic being tested
   - At external system interfaces

### Dependency Analysis Example

```typescript
// Analyzing: Should I mock discoverAndCacheTools()?

// 1. Read implementation
async function discoverAndCacheTools(serverConfig) {
  const tools = await fetchToolsFromServer(serverConfig);  // Slow
  await cacheTools(serverConfig.id, tools);                // Side effect!
  return tools;
}

// 2. Identify side effects
// - Network call (slow)
// - Cache write (side effect tests may depend on)

// 3. Determine test needs
test('server registration prevents duplicates', () => {
  // Needs: Config persistence to detect duplicate
  // Doesn't need: Actual tool discovery (slow)
});

// 4. Mock at correct level
// ✅ Mock network, preserve cache
vi.mock('server-connection', () => ({
  fetchToolsFromServer: vi.fn().mockResolvedValue([])
}));
// cacheTools() runs - test logic intact
```

### Gate Function

```
BEFORE mocking any method:
  STOP - Don't mock yet

  1. Ask: "What side effects does the real method have?"
     Action: Read implementation, list all side effects

  2. Ask: "Does this test depend on any of those side effects?"
     Action: Identify which side effects test logic needs

  3. Ask: "Do I fully understand what this test needs?"
     Action: Write down test's dependencies

  IF depends on side effects:
    Mock at lower level (the actual slow/external operation)
    OR use test doubles that preserve necessary behavior
    NOT the high-level method the test depends on

  IF unsure what test depends on:
    Run test with real implementation FIRST
    Observe what actually needs to happen
    THEN add minimal mocking at the right level

  Red flags:
    - "I'll mock this to be safe"
    - "This might be slow, better mock it"
    - Mocking without reading implementation
    - Mocking without understanding dependency chain
```

### Levels of Mocking

**Choose the right level:**

```typescript
// ❌ Too high - breaks test logic
vi.mock('UserService');  // Mocks everything, including state changes

// ❌ Too high - over-mocking
vi.mock('DatabaseAdapter');  // Could use in-memory DB instead

// ✅ Right level - isolates slow operation
vi.mock('HTTPClient');  // Mock network, preserve business logic

// ✅ Right level - controls non-determinism
vi.spyOn(Date, 'now').mockReturnValue(fixedTimestamp);
```

**Mocking hierarchy (top to bottom):**
1. **Application logic** - Never mock (this is what you're testing)
2. **Business layer** - Rarely mock (needed for test assertions)
3. **Adapter layer** - Sometimes mock (if slow, use test doubles)
4. **I/O boundaries** - Usually mock (network, filesystem, external APIs)
5. **Infrastructure** - Always mock (actual servers, databases in unit tests)

### Common Mocking Mistakes

**Mistake 1: Mocking what you're testing**
```typescript
// ❌ BAD
test('user registration validates email', () => {
  vi.mock('UserValidator');  // You're testing this!
  await registerUser(email);
});

// ✅ GOOD
test('user registration validates email', () => {
  vi.mock('EmailService');  // Mock email sending, test validation
  await expect(registerUser('invalid')).rejects.toThrow();
});
```

**Mistake 2: Mocking too broadly**
```typescript
// ❌ BAD - mocks entire module
vi.mock('./user-service');

// ✅ GOOD - mocks specific slow operation
vi.mock('./email-client', () => ({
  sendEmail: vi.fn()  // Just the network call
}));
```

**Mistake 3: Mocking based on assumptions**
```typescript
// ❌ BAD - assumption without measurement
// "Database queries are slow, better mock"
vi.mock('./database');

// ✅ GOOD - measure first
// Run test unmocked: 2ms (fast enough!)
// Don't mock unless proven slow
```

## Prevention Through TDD

**How TDD prevents these anti-patterns:**

1. **Write test first** → Forces you to think about what you're actually testing
2. **Watch it fail** → Confirms test tests real behavior, not mocks
3. **Minimal implementation** → No test-only methods creep in
4. **Real dependencies** → You see what the test actually needs before mocking

**If you're testing mock behavior, you violated TDD** - you added mocks without watching test fail against real code first.

**TDD workflow prevents:**
- Testing mock behavior (test fails for real reasons first)
- Test-only methods (minimal implementation doesn't add them)
- Uninformed mocking (you understand needs before mocking)

See [test-driven-development skill](../../test-driven-development/) for complete TDD workflow.

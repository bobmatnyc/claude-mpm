# How TDD Prevents Testing Anti-Patterns

Test-Driven Development (TDD) is not just a testing methodology - it's a design methodology that naturally prevents all five testing anti-patterns. This guide explains the deep connection between TDD and anti-pattern prevention.

## Overview

**Core insight:** If you follow strict TDD, testing anti-patterns become nearly impossible to create.

**Why:** TDD forces you to think about real behavior before implementation, making mock-testing and test-only methods unnatural.

## TDD Fundamentals

### The RED/GREEN/REFACTOR Cycle

```
1. RED: Write failing test
   - Test doesn't compile or fails
   - Verify failure reason is correct
   - No implementation exists yet

2. GREEN: Write minimal code to pass
   - Simplest implementation
   - Just enough to pass test
   - No gold plating

3. REFACTOR: Improve code
   - Clean up duplication
   - Improve names
   - Tests still pass

4. REPEAT: Next test
```

**Critical rule:** Never write implementation without failing test first.

See [test-driven-development skill](../../test-driven-development/) for complete workflow.

## How TDD Prevents Each Anti-Pattern

### Anti-Pattern 1: Testing Mock Behavior

**How TDD prevents it:**

```
TDD Step 1: Write test for real behavior
  ↓
Test fails because feature doesn't exist
  ↓
TDD Step 2: Implement minimal code
  ↓
Test passes - you tested real code, not mock

If you tested mock:
  ↓
Test would pass immediately (mock exists)
  ↓
Violation of TDD - didn't see failure
```

**Example workflow:**

```typescript
// TDD Step 1: Write failing test
test('renders sidebar with navigation', () => {
  render(<Page />);
  expect(screen.getByRole('navigation')).toBeInTheDocument();
});
// ❌ Fails - Page doesn't render sidebar yet

// TDD Step 2: Implement
function Page() {
  return <div><Sidebar role="navigation" /></div>;
}
// ✅ Passes - tested real component

// WRONG way (not TDD):
test('renders sidebar mock', () => {
  render(<Page />);
  expect(screen.getByTestId('sidebar-mock')).toBeInTheDocument();
});
// ✅ Passes immediately - you never saw it fail!
// This violates TDD - test must fail first
```

**TDD guarantee:** If test passes immediately, you're testing mock behavior.

### Anti-Pattern 2: Test-Only Methods in Production

**How TDD prevents it:**

```
TDD Step 1: Write test for needed behavior
  ↓
Test describes what production needs
  ↓
TDD Step 2: Minimal implementation
  ↓
Only code test needs is written

If method only for tests:
  ↓
No production test would need it
  ↓
TDD wouldn't add it
```

**Example workflow:**

```typescript
// TDD Step 1: Write test for production behavior
test('session expires after timeout', async () => {
  const session = new Session();
  await advanceTime(SESSION_TIMEOUT);
  expect(session.isActive()).toBe(false);
});
// ❌ Fails - Session doesn't handle expiry

// TDD Step 2: Implement expiry (production feature)
class Session {
  isActive() {
    return Date.now() < this.expiresAt;
  }
}
// ✅ Passes - implemented real behavior

// WRONG way (not TDD):
// "I need to cleanup in tests"
class Session {
  destroy() { /* for tests */ }  // ❌ Not driven by test!
}
```

**TDD guarantee:** Minimal implementation doesn't add untested code.

**Test cleanup belongs in test utilities:**
```typescript
// test-utils/session.ts
export async function cleanupSession(session: Session) {
  // Use public API for cleanup
  session.logout();
  // Clear any test-specific state
}
```

### Anti-Pattern 3: Mocking Without Understanding

**How TDD prevents it:**

```
TDD Step 1: Write test with real implementation
  ↓
Test runs - you see what it does
  ↓
Identify what's slow/external
  ↓
TDD Step 2: Mock at correct level
  ↓
Mock only slow part, preserve behavior

If you mock first:
  ↓
Never saw real behavior
  ↓
Don't understand dependencies
  ↓
Mock breaks test logic
```

**Example workflow:**

```typescript
// TDD Step 1: Write test with real implementation
test('detects duplicate server', async () => {
  await addServer(config);
  await expect(addServer(config))
    .rejects.toThrow('already exists');
});
// Run test - takes 2 seconds (server startup slow)
// Observe: Config written, duplicate detected
// Understand: Test depends on config persistence

// TDD Step 2: Mock at correct level
test('detects duplicate server', async () => {
  vi.mock('MCPServerManager');  // Mock slow startup only
  // Config writing preserved - test logic intact

  await addServer(config);
  await expect(addServer(config))
    .rejects.toThrow('already exists');
});
// ✅ Fast test, correct behavior

// WRONG way (not TDD):
// "Let me mock this upfront"
vi.mock('ToolCatalog', () => ({
  discoverAndCacheTools: vi.fn()  // Breaks test logic!
}));
// Never saw real behavior - don't know what test needs
```

**TDD guarantee:** You understand dependencies before mocking them.

### Anti-Pattern 4: Incomplete Mocks

**How TDD prevents it:**

```
TDD Step 1: Write test with real API
  ↓
See complete response structure
  ↓
TDD Step 2: Mock with complete structure
  ↓
Test still passes - mock is complete

If mock incomplete:
  ↓
Test fails - mock missing fields
  ↓
TDD forces you to complete mock
```

**Example workflow:**

```typescript
// TDD Step 1: Test with real API (or type)
test('displays user profile', async () => {
  const user = await api.getUser('123');
  // TypeScript shows complete User type
  render(<Profile user={user} />);
  expect(screen.getByText(user.name)).toBeInTheDocument();
  expect(screen.getByText(user.profile.timezone)).toBeInTheDocument();
});
// Observe complete structure

// TDD Step 2: Mock with complete structure
test('displays user profile', async () => {
  const mockUser: User = {  // TypeScript enforces completeness
    id: '123',
    name: 'Alice',
    email: 'alice@example.com',
    profile: {
      timezone: 'UTC',
      locale: 'en-US',
      avatar: null
    },
    metadata: { /* complete */ }
  };

  render(<Profile user={mockUser} />);
  expect(screen.getByText('Alice')).toBeInTheDocument();
});
// ✅ Complete mock, test passes

// WRONG way (not TDD):
const mockUser = { id: '123', name: 'Alice' };  // Incomplete
// Later breaks when profile.timezone accessed
```

**TDD guarantee:** Test with real data first reveals complete structure.

**Use TypeScript to enforce completeness:**
```typescript
// Define complete type from API
interface User {
  id: string;
  name: string;
  email: string;
  profile: UserProfile;
  metadata: UserMetadata;
}

// TypeScript errors if incomplete
const mock: User = {
  id: '123',
  name: 'Alice'
  // ❌ TypeScript error - missing fields
};
```

### Anti-Pattern 5: Tests as Afterthought

**How TDD prevents it:**

```
TDD Step 1: MUST write test first
  ↓
No implementation without test
  ↓
Test IS implementation process

If implementation first:
  ↓
Violated TDD - broke the cycle
```

**TDD makes tests as afterthought impossible:**

```typescript
// TDD Way - tests ARE implementation
// 1. RED
test('user registration validates email', async () => {
  await expect(registerUser('invalid'))
    .rejects.toThrow('Invalid email');
});
// ❌ Fails - registerUser doesn't exist

// 2. GREEN
async function registerUser(email: string) {
  if (!isValidEmail(email)) {
    throw new Error('Invalid email');
  }
  // ... registration
}
// ✅ Passes

// 3. REFACTOR
// Improve validation logic, tests still pass

// NOT TDD (anti-pattern):
// 1. Implement registerUser
// 2. "Feature complete, need to add tests"  ← Afterthought
```

**TDD workflow:**
- Tests first = tests are implementation
- No "testing phase" - tests are development
- Feature complete = tests passing
- Can't forget tests - can't write code without them

## TDD Workflow Prevents Anti-Patterns

### Complete TDD Cycle

```typescript
// Feature: User registration with email validation

// ========================================
// CYCLE 1: Email validation
// ========================================

// RED: Write failing test
test('rejects invalid email', async () => {
  await expect(registerUser('invalid'))
    .rejects.toThrow('Invalid email');
});
// ❌ Fails - registerUser doesn't exist

// GREEN: Minimal implementation
async function registerUser(email: string) {
  if (!email.includes('@')) {
    throw new Error('Invalid email');
  }
}
// ✅ Passes

// REFACTOR: Improve validation
async function registerUser(email: string) {
  if (!isValidEmail(email)) {  // Better validator
    throw new Error('Invalid email');
  }
}
// ✅ Still passes

// ========================================
// CYCLE 2: Database integration
// ========================================

// RED: Write failing test
test('saves user to database', async () => {
  const user = await registerUser('alice@example.com');
  const saved = await db.users.findById(user.id);
  expect(saved.email).toBe('alice@example.com');
});
// ❌ Fails - no database integration

// GREEN: Add database
async function registerUser(email: string) {
  if (!isValidEmail(email)) {
    throw new Error('Invalid email');
  }
  const user = await db.users.create({ email });  // Added
  return user;
}
// ✅ Passes

// REFACTOR: Extract repository pattern
// Tests still pass

// ========================================
// CYCLE 3: Duplicate prevention
// ========================================

// RED: Write failing test
test('prevents duplicate email', async () => {
  await registerUser('alice@example.com');
  await expect(registerUser('alice@example.com'))
    .rejects.toThrow('Email already exists');
});
// ❌ Fails - no duplicate check

// GREEN: Add check
async function registerUser(email: string) {
  if (!isValidEmail(email)) {
    throw new Error('Invalid email');
  }
  const existing = await db.users.findByEmail(email);
  if (existing) {
    throw new Error('Email already exists');  // Added
  }
  return await db.users.create({ email });
}
// ✅ Passes

// REFACTOR: Improve error handling
// Tests still pass
```

**Notice:**
- ✅ No mock behavior testing - real code tested
- ✅ No test-only methods - only what tests needed
- ✅ No uninformed mocking - saw real behavior first
- ✅ No incomplete mocks - used real structures
- ✅ No afterthought tests - tests first always

## TDD Mindset: Test-First Thinking

### Mental Model

**NOT TDD thinking:**
```
"How do I implement this feature?"
  ↓
Implement code
  ↓
"How do I test this?"
  ↓
Write tests
  ↓
Anti-patterns emerge
```

**TDD thinking:**
```
"How will I verify this works?"
  ↓
Write test
  ↓
"What's minimal code to pass?"
  ↓
Implement
  ↓
Anti-patterns prevented
```

### Test-First Benefits

**Design benefits:**
- API designed from consumer perspective
- Testable code (loose coupling)
- Clear interfaces
- Minimal implementation

**Quality benefits:**
- Verified behavior
- Edge cases caught early
- Regression prevention
- Living documentation

**Anti-pattern prevention:**
- Can't test mocks (test fails first against real code)
- No test-only methods (minimal implementation)
- Must understand dependencies (see real behavior)
- Complete structures (test with real data first)
- Tests ARE implementation (not afterthought)

## When TDD is Violated

**Signs you're not following TDD:**

```
🚩 Writing implementation before test
🚩 Test passes immediately
🚩 Skipping "watch it fail" step
🚩 Mocking before running test
🚩 "Implementation done, adding tests"
```

**Consequences:**
- All five anti-patterns become possible
- Test quality degrades
- False confidence
- Design issues

**Recovery:**
1. Stop adding features
2. Return to TDD workflow
3. Write test first for next feature
4. Watch it fail
5. Minimal implementation
6. Maintain discipline

## TDD and Mocking Strategy

### TDD-Compliant Mocking

**The right way:**

```typescript
// 1. Write test with real implementation
test('user registration sends welcome email', async () => {
  await registerUser('alice@example.com');
  // Observe: Email sending is slow (2 seconds)
});

// 2. Identify slow operation
// emailService.send() is slow (network call)

// 3. Mock at correct level
test('user registration sends welcome email', async () => {
  vi.spyOn(emailService, 'send').mockResolvedValue();

  await registerUser('alice@example.com');

  expect(emailService.send).toHaveBeenCalledWith({
    to: 'alice@example.com',
    subject: 'Welcome'
  });
});
// Test runs fast, verifies email logic
```

**TDD mocking principles:**

1. **Run with real implementation first** - See actual behavior
2. **Measure performance** - Mock only if slow
3. **Mock at boundaries** - I/O, network, filesystem
4. **Preserve business logic** - Don't mock what you're testing
5. **Verify behavior, not mocks** - Test results, not mock calls

### Mocking Levels in TDD

```
Layer 1: Business Logic
  → NEVER mock (this is what you're testing)

Layer 2: Application Services
  → RARELY mock (needed for assertions)

Layer 3: Adapters
  → SOMETIMES mock (if slow)

Layer 4: External I/O
  → USUALLY mock (network, DB, filesystem)

Layer 5: Infrastructure
  → ALWAYS mock in unit tests (servers, APIs)
```

## Common TDD Mistakes

### Mistake 1: Not Watching Test Fail

```typescript
// ❌ WRONG
test('feature works', () => {
  expect(true).toBe(true);  // Passes immediately
});
// Didn't verify test tests right thing

// ✅ RIGHT
test('validates email', async () => {
  await expect(register('invalid'))
    .rejects.toThrow('Invalid email');
});
// ❌ Fails first - register doesn't exist
// Then implement
// ✅ Passes - verified test works
```

### Mistake 2: Overly Complex Implementation

```typescript
// ❌ WRONG (not minimal)
test('adds numbers', () => {
  expect(add(2, 3)).toBe(5);
});

function add(a: number, b: number): number {
  // Not minimal - over-engineered
  return Array(b).fill(a).reduce((sum, n) => sum + n, 0);
}

// ✅ RIGHT (minimal)
function add(a: number, b: number): number {
  return a + b;  // Simplest solution
}
```

### Mistake 3: Testing Implementation Details

```typescript
// ❌ WRONG
test('uses cache', () => {
  const cache = new Cache();
  service.setCache(cache);  // Testing how it works
  expect(service.cache).toBe(cache);
});

// ✅ RIGHT
test('returns cached result', () => {
  service.get('key');
  service.get('key');
  expect(slowOperation).toHaveBeenCalledOnce();  // Testing behavior
});
```

## TDD Discipline

### Maintaining TDD Practice

**Commit to:**
- Test first, always
- Watch it fail, every time
- Minimal implementation, no gold plating
- Refactor with confidence

**When tempted to skip TDD:**
- "Just a small change" → Write test first
- "I know it works" → Write test to prove it
- "This is hard to test" → Design issue, fix it
- "Tests can wait" → No, they can't

**TDD is not optional:**
- Not a suggestion
- Not for later
- Not just for new features
- Not "when I have time"

**TDD is how you write code.**

## Integration with Other Skills

**Prerequisite skills:**
- [test-driven-development](../../test-driven-development/) - Complete TDD workflow

**Complementary skills:**
- [verification-before-completion](../../../productivity/verification-before-completion/) - Definition of "done"

**Anti-pattern prevention:**
- This skill - What TDD prevents

## Summary: TDD as Anti-Pattern Prevention

| Anti-Pattern | TDD Prevention Mechanism |
|--------------|---------------------------|
| Testing Mock Behavior | Must watch test fail against real code first |
| Test-Only Methods | Minimal implementation doesn't add them |
| Mocking Without Understanding | Run with real impl first, understand dependencies |
| Incomplete Mocks | Test with real data first, see complete structure |
| Tests as Afterthought | Tests first is the workflow, impossible to skip |

**The bottom line:** Strict TDD adherence makes testing anti-patterns nearly impossible to create.

If you find yourself with these anti-patterns, you've violated TDD. Return to the RED/GREEN/REFACTOR cycle.

## Quick Reference

**TDD Cycle:**
```
RED → Write failing test
GREEN → Minimal implementation
REFACTOR → Improve code
REPEAT → Next test
```

**Anti-pattern prevention:**
```
Test first → Prevents afterthought
Watch fail → Prevents mock testing
Minimal code → Prevents test-only methods
Real impl first → Prevents uninformed mocking
Real data first → Prevents incomplete mocks
```

**TDD discipline:**
```
Always test first
Always watch fail
Always minimal implementation
Always refactor
Never skip the cycle
```

See [test-driven-development skill](../../test-driven-development/) for complete TDD workflow and examples.

# TDD Anti-Patterns

> **Part of**: [Test-Driven Development](../SKILL.md)
> **Category**: testing
> **Reading Level**: Intermediate

## Purpose

Common TDD mistakes, rationalizations, and red flags to avoid. Learn to recognize when you're violating test-driven development principles.

## Red Flags - Recognize and Stop

### "I'll Write Tests After to Verify It Works"

**What It Sounds Like:**
- "Let me confirm this works first, then I'll test"
- "I'll add tests once the feature is done"
- "Tests are part of cleanup, I'll do them later"

**Why It's Wrong:**
- Tests passing immediately prove nothing
- Didn't watch test fail = don't know if test works
- Implementation may be hard to test (too late to redesign)
- "Later" often becomes "never"

**Reality Check:**
```typescript
// Test-after: Passes immediately
test('validates email', () => {
  expect(validateEmail('test@example.com')).toBe(true);
});
// ✓ PASS

// But you never saw it fail!
// Does it actually test anything? Unknown.
```

**What to Do Instead:**
```typescript
// Test-first: Watch it fail
test('validates email', () => {
  expect(validateEmail('test@example.com')).toBe(true);
});
// ✗ FAIL: validateEmail is not defined

// Implement
function validateEmail(email: string): boolean {
  return email.includes('@');
}

// ✓ PASS: Now you know test works
```

### "Keep as Reference, Write Tests First"

**What It Sounds Like:**
- "I'll keep this code as a reference while writing tests"
- "I'll adapt this implementation while test-driving"
- "Let me look at what I built to write better tests"

**Why It's Wrong:**
- You WILL adapt existing code (human nature)
- "Adapt" = testing after, not testing first
- Reference biases your test design
- Defeats purpose of TDD

**Reality Check:**
```typescript
// You wrote this "reference":
function processUser(user: any) {
  const valid = user.email && user.age >= 18 && user.name;
  if (!valid) throw new Error('Invalid');
  return { id: generateId(), ...user };
}

// Now you write "test-first" while looking at it:
test('processes valid user', () => {
  const user = { email: 'test@example.com', age: 25, name: 'Test' };
  const result = processUser(user);
  expect(result.id).toBeDefined();
});

// You just tested what you built, not what it should do
```

**What to Do Instead:**
```
Delete the code. Seriously. Delete it.

Then write test describing what SHOULD happen:
test('creates user with required fields', () => {
  const user = createUser({
    email: 'test@example.com',
    age: 25,
    name: 'Test User'
  });

  expect(user).toMatchObject({
    id: expect.any(String),
    email: 'test@example.com',
    age: 25,
    name: 'Test User'
  });
});

Now implement fresh from test.
```

### "Already Spent X Hours, Deleting Is Wasteful"

**What It Sounds Like:**
- "I can't throw away 4 hours of work"
- "Let me just add tests to verify what I built"
- "Rewriting would take too long"

**Why It's Wrong:**
- Sunk cost fallacy
- Time already gone, can't recover it
- Keeping unverified code = technical debt
- Will spend more time debugging

**Reality Check:**
```
Time spent: 4 hours
Code quality: Unknown
Test coverage: None
Technical debt: High

Option A: Keep it and test after
Time: 4 hours (sunk) + 30 min (weak tests) + 120 min (future debugging)
Total: 6.5 hours
Quality: Low

Option B: Delete and TDD
Time: 4 hours (sunk) + 2 hours (TDD rewrite)
Total: 6 hours
Quality: High

Option B is objectively better.
```

**What to Do Instead:**
- Accept sunk cost
- Treat it as learning time
- Delete code
- Rewrite with TDD (will be faster, you know the problem now)

### "Tests After Achieve the Same Purpose"

**What It Sounds Like:**
- "I'll have 100% coverage either way"
- "Tests-after verify correctness just as well"
- "It's about the spirit, not the ritual"
- "Being pragmatic means adapting"

**Why It's Wrong:**
- Coverage ≠ quality
- Tests-after verify what you remembered
- Can't achieve TDD spirit without TDD practice
- Tests-after is optimistic gambling, not pragmatic

**Reality Check:**
```typescript
// Test-after: 100% coverage, useless
function add(a: number, b: number): number {
  return a - b;  // BUG
}

test('add function', () => {
  add(2, 3);  // 100% coverage!
  // But doesn't verify result
});

// Test-first: Forces verification
test('adds two numbers', () => {
  expect(add(2, 3)).toBe(5);  // Must verify behavior
});
```

See [Philosophy](philosophy.md) for detailed explanation.

### "This Is Different Because..."

**What It Sounds Like:**
- "This is too simple for TDD"
- "This is too complex for TDD"
- "This is exploratory code"
- "This is just a quick bug fix"
- "This is legacy code (can't test)"

**Why It's Wrong:**
- Every situation has an excuse
- All excuses are invalid
- "Just this once" becomes "always"

**Reality Check:**

| Excuse | Truth |
|--------|-------|
| "Too simple" | Simple code breaks too |
| "Too complex" | Complex code NEEDS tests |
| "Exploratory" | Exploration teaches what to test |
| "Quick fix" | Quick fixes need regression protection |
| "Legacy code" | Characterization tests enable refactoring |

**What to Do Instead:**
- Stop rationalizing
- Follow TDD process
- Every. Single. Time.

## Common Anti-Patterns

### Pattern: Testing Implementation, Not Behavior

**Bad:**
```typescript
test('uses regex to validate email', () => {
  const validator = new EmailValidator();
  expect(validator.pattern).toBe(/^[^\s@]+@[^\s@]+\.[^\s@]+$/);
});
```

**Why Wrong:** Tests HOW, not WHAT. Prevents refactoring.

**Good:**
```typescript
test('accepts valid email format', () => {
  expect(validateEmail('user@example.com')).toBe(true);
});

test('rejects email without @ symbol', () => {
  expect(validateEmail('userexample.com')).toBe(false);
});
```

**Why Right:** Tests behavior. Implementation can change freely.

### Pattern: Mocking Everything

**Bad:**
```typescript
test('processes user data', () => {
  const mockValidator = jest.fn().mockReturnValue(true);
  const mockRepository = jest.fn().mockResolvedValue({ id: 1 });
  const mockLogger = jest.fn();

  const service = new UserService(mockValidator, mockRepository, mockLogger);

  service.createUser({ name: 'Test' });

  expect(mockValidator).toHaveBeenCalled();
  expect(mockRepository).toHaveBeenCalled();
  expect(mockLogger).toHaveBeenCalled();
});
```

**Why Wrong:**
- Tests mock interactions, not real code
- Doesn't verify actual behavior
- Brittle (breaks on implementation changes)

**Good:**
```typescript
test('creates user with valid data', async () => {
  const service = new UserService();

  const user = await service.createUser({
    name: 'Test User',
    email: 'test@example.com'
  });

  expect(user.id).toBeDefined();
  expect(user.name).toBe('Test User');
  expect(user.email).toBe('test@example.com');
});
```

**Why Right:** Tests real behavior using real objects.

**When to Mock:** Only external dependencies you don't control (APIs, databases, file system).

### Pattern: One Giant Test

**Bad:**
```typescript
test('user registration flow', async () => {
  // Test validates email
  expect(validateEmail('test@example.com')).toBe(true);

  // Test validates password
  expect(validatePassword('Pass123')).toBe(true);

  // Test creates user
  const user = await createUser({...});
  expect(user.id).toBeDefined();

  // Test sends welcome email
  expect(emailsSent).toContain('welcome');

  // Test logs activity
  expect(logs).toContain('user_created');
});
```

**Why Wrong:**
- Tests multiple behaviors
- If fails, unclear what broke
- Hard to understand what's being tested
- Violates "one test, one behavior"

**Good:**
```typescript
test('validates email format', () => {
  expect(validateEmail('test@example.com')).toBe(true);
});

test('validates password strength', () => {
  expect(validatePassword('Pass123')).toBe(true);
});

test('creates user with valid data', async () => {
  const user = await createUser({...});
  expect(user.id).toBeDefined();
});

test('sends welcome email after registration', async () => {
  await createUser({...});
  expect(emailsSent).toContain('welcome');
});
```

**Why Right:** Each test has single, clear purpose.

### Pattern: Vague Assertions

**Bad:**
```typescript
test('processes array', () => {
  const result = processArray([1, 2, 3]);
  expect(result).toBeDefined();
  expect(result.length).toBeGreaterThan(0);
});
```

**Why Wrong:**
- Doesn't verify actual behavior
- Many wrong implementations would pass
- Provides false confidence

**Good:**
```typescript
test('doubles each element in array', () => {
  const result = processArray([1, 2, 3]);
  expect(result).toEqual([2, 4, 6]);
});
```

**Why Right:** Precise assertion. Only correct implementation passes.

### Pattern: Skipping Verification Steps

**Bad:**
```typescript
// Write test
test('retries on failure', async () => {
  const result = await withRetry(operation);
  expect(result).toBe('success');
});

// Implement immediately without running test
async function withRetry(fn) {
  try {
    return await fn();
  } catch (e) {
    return await fn();
  }
}

// Run both tests together
// PASS: Both pass

// You never saw test fail!
```

**Why Wrong:**
- Don't know if test actually tests anything
- Implementation might have already existed
- Test might be broken

**Good:**
```typescript
// Write test
test('retries on failure', async () => {
  const result = await withRetry(operation);
  expect(result).toBe('success');
});

// MANDATORY: Run test FIRST
// FAIL: withRetry is not defined
// ✓ Good - test works

// Implement
async function withRetry(fn) {
  try {
    return await fn();
  } catch (e) {
    return await fn();
  }
}

// Run test AGAIN
// PASS
// ✓ Good - implementation works
```

**Why Right:** Verified test fails, verified test passes. Confidence high.

## Rationalization Detection

### Self-Assessment Questions

Ask yourself:

**Before skipping RED phase:**
- [ ] Am I making excuses?
- [ ] Do I think "just this once"?
- [ ] Am I under time pressure? (More reason for TDD!)
- [ ] Do I feel the process is "too slow"? (It's faster overall)

**After writing implementation first:**
- [ ] Did I write code before test?
- [ ] Am I now writing test to verify existing code?
- [ ] Will my test pass immediately?
- [ ] Did I watch the test fail first?

**When reviewing tests:**
- [ ] Did I watch each test fail before implementing?
- [ ] Does each test verify behavior, not implementation?
- [ ] Could I refactor without breaking tests?
- [ ] Do tests use real code (not excessive mocks)?

### If Any Answer Is "No"

**STOP. You're not doing TDD.**

Options:
1. Delete implementation, start with test
2. Admit you're not doing TDD, accept consequences
3. Ask for help understanding how to TDD this

## Recovery from Anti-Patterns

### If You Wrote Code First

**Option 1: Characterization Tests (if code works)**
```typescript
// Write tests for current behavior
test('current behavior for case A', () => {
  expect(existingFunction(inputA)).toBe(currentOutputA);
});

// Then refactor with test protection
// Then delete and rewrite with TDD for new features
```

**Option 2: Delete and Restart (if code not verified)**
```typescript
// Delete implementation
// Write failing test
// Implement from test
```

### If Tests Are Too Broad

**Refactor tests:**
```typescript
// Before: One giant test
test('user registration', () => {
  // 50 lines of test code
});

// After: Multiple focused tests
describe('User Registration', () => {
  test('validates email format', () => {...});
  test('validates password strength', () => {...});
  test('creates user record', () => {...});
  test('sends welcome email', () => {...});
});
```

### If Tests Are Brittle

**Refactor to test behavior:**
```typescript
// Before: Tests implementation
test('uses bcrypt with 10 rounds', () => {
  expect(hasher.algorithm).toBe('bcrypt');
  expect(hasher.rounds).toBe(10);
});

// After: Tests behavior
test('hashes password securely', () => {
  const hash1 = hashPassword('password');
  const hash2 = hashPassword('password');

  expect(hash1).not.toBe('password');  // Actually hashed
  expect(hash1).not.toBe(hash2);       // Salted
  expect(verifyPassword('password', hash1)).toBe(true);  // Verifiable
});
```

## Summary

**Red Flags:**
- Code before test
- Test passes immediately
- "I'll test after"
- "Keep as reference"
- "Deleting is wasteful"
- "Tests-after are equivalent"
- "This is different because..."

**Anti-Patterns:**
- Testing implementation not behavior
- Mocking everything
- One giant test
- Vague assertions
- Skipping verification steps

**Recovery:**
- Recognize the anti-pattern
- STOP immediately
- Delete or refactor
- Restart with proper TDD

**Remember:** Proper TDD requires discipline but saves time. Shortcuts feel faster but waste time.

## Related References

- [Workflow](workflow.md): Correct TDD process
- [Examples](examples.md): Real-world TDD practice
- [Philosophy](philosophy.md): Why TDD works
- [Integration](integration.md): TDD with other skills

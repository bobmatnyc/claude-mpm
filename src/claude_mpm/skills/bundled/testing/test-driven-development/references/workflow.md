# Complete TDD Workflow

> **Part of**: [Test-Driven Development](../SKILL.md)
> **Category**: testing
> **Reading Level**: Intermediate

## Purpose

Complete step-by-step workflow for the RED/GREEN/REFACTOR cycle, with detailed instructions, examples, and verification criteria for each phase.

## The Complete Cycle

```
┌──────────────────────────────────────────────────────┐
│                   TDD CYCLE                          │
├──────────────────────────────────────────────────────┤
│                                                      │
│  RED: Write Failing Test                            │
│    ↓                                                 │
│  VERIFY RED: Watch it fail correctly                │
│    ↓                                                 │
│  GREEN: Minimal implementation                      │
│    ↓                                                 │
│  VERIFY GREEN: Watch it pass                        │
│    ↓                                                 │
│  REFACTOR: Improve code (optional)                  │
│    ↓                                                 │
│  REPEAT: Next test for next feature                 │
│                                                      │
└──────────────────────────────────────────────────────┘
```

## Phase 1: RED - Write Failing Test

### Goal
Create one minimal test that describes desired behavior.

### Steps

**1. Identify Single Behavior**
```
Ask: What is ONE thing this code should do?
Not: "Handle user authentication and authorization and validation"
But: "Validate email format"
```

**2. Write Clear Test Name**
```typescript
// Good: Describes behavior
test('rejects email without @ symbol', () => {})
test('accepts valid email format', () => {})
test('trims whitespace from email', () => {})

// Bad: Vague or implementation-focused
test('test1', () => {})
test('email validation works', () => {})
test('uses regex pattern', () => {})
```

**3. Write Test Body**

**Structure:**
```typescript
test('behavior description', () => {
  // Arrange: Set up test data
  const input = 'test data';

  // Act: Call the function
  const result = functionUnderTest(input);

  // Assert: Verify behavior
  expect(result).toBe(expected);
});
```

**Good Example:**
```typescript
test('retries failed operations 3 times', async () => {
  let attempts = 0;
  const operation = () => {
    attempts++;
    if (attempts < 3) throw new Error('fail');
    return 'success';
  };

  const result = await retryOperation(operation);

  expect(result).toBe('success');
  expect(attempts).toBe(3);
});
```

**Bad Example:**
```typescript
test('retry works', async () => {
  const mock = jest.fn()
    .mockRejectedValueOnce(new Error())
    .mockRejectedValueOnce(new Error())
    .mockResolvedValueOnce('success');
  await retryOperation(mock);
  expect(mock).toHaveBeenCalledTimes(3);
});
// Problem: Tests mock behavior, not real code
```

### Test Quality Checklist

- [ ] Tests ONE behavior
- [ ] Name clearly describes what should happen
- [ ] Uses real code (mocks only if unavoidable)
- [ ] Arrange/Act/Assert structure clear
- [ ] Easy to understand what's being tested

## Phase 2: VERIFY RED - Watch It Fail

### Goal
Confirm test fails for the RIGHT reason.

### Steps

**1. Run Test**
```bash
# Run specific test file
npm test path/to/test.test.ts

# Or run single test
npm test -- -t "behavior description"
```

**2. Verify Failure Type**

**✓ Good Failure (Feature Missing):**
```
FAIL: retries failed operations 3 times
ReferenceError: retryOperation is not defined

Expected: 'success'
Received: undefined
```

**✗ Bad Failure (Test Error):**
```
FAIL: retries failed operations 3 times
SyntaxError: Unexpected token
TypeError: Cannot read property 'x' of undefined
```

**✗ Bad Outcome (Test Passes):**
```
PASS: retries failed operations 3 times
```
→ You're testing existing behavior, not new feature

### What to Check

| Outcome | Meaning | Action |
|---------|---------|--------|
| Test fails with "not defined" | ✓ Good - feature missing | Proceed to GREEN |
| Test fails with "Expected X, got Y" | ✓ Good - behavior wrong | Proceed to GREEN |
| Test errors (syntax, type) | ✗ Fix test | Fix error, rerun VERIFY RED |
| Test passes | ✗ Testing existing behavior | Rewrite test for NEW behavior |

### Common Issues

**Issue: Test Passes Immediately**

```typescript
// Problem: Testing existing code
test('processes array', () => {
  const result = processArray([1, 2, 3]);
  expect(result).toBeDefined();  // Already works!
});

// Fix: Test NEW behavior
test('processes empty array', () => {
  const result = processArray([]);
  expect(result).toEqual([]);  // Currently fails
});
```

**Issue: Test Errors Instead of Failing**

```typescript
// Problem: Typo in test
test('validates email', () => {
  const result = validateEmial('test@example.com');  // Typo
  expect(result).toBe(true);
});

// Fix: Correct typo, rerun
test('validates email', () => {
  const result = validateEmail('test@example.com');
  expect(result).toBe(true);
});
```

## Phase 3: GREEN - Minimal Implementation

### Goal
Write simplest code to make test pass.

### Steps

**1. Write Minimal Code**

**Good (Minimal):**
```typescript
async function retryOperation<T>(fn: () => Promise<T>): Promise<T> {
  for (let i = 0; i < 3; i++) {
    try {
      return await fn();
    } catch (e) {
      if (i === 2) throw e;
    }
  }
  throw new Error('unreachable');
}
```

**Bad (Over-engineered):**
```typescript
async function retryOperation<T>(
  fn: () => Promise<T>,
  options?: {
    maxRetries?: number;
    backoff?: 'linear' | 'exponential';
    onRetry?: (attempt: number) => void;
    timeout?: number;
  }
): Promise<T> {
  // YAGNI - You Aren't Gonna Need It
}
```

**2. Resist Temptations**

**DON'T:**
- Add features not tested
- Refactor other code
- "Improve" beyond test requirements
- Add configuration options "for flexibility"
- Handle edge cases not in test

**DO:**
- Write exactly enough to pass test
- Keep it simple
- Save improvements for REFACTOR phase
- Trust that next test will drive next feature

### Implementation Patterns

**Pattern: Hardcode First**

```typescript
// Test: User can login with valid credentials
test('logs in with valid credentials', async () => {
  const result = await login('user@example.com', 'password123');
  expect(result.success).toBe(true);
});

// First implementation: Hardcode it
function login(email: string, password: string) {
  return { success: true };  // Simplest thing that passes
}

// Next test will force real implementation
test('rejects invalid credentials', async () => {
  const result = await login('user@example.com', 'wrongpass');
  expect(result.success).toBe(false);
});

// Now implement for real
function login(email: string, password: string) {
  const valid = checkCredentials(email, password);
  return { success: valid };
}
```

**Pattern: Fake It Then Make It**

```typescript
// Iteration 1: Fake it
function calculateTotal(items: Item[]) {
  return 100;  // Hardcoded to pass first test
}

// Iteration 2: Make it real
function calculateTotal(items: Item[]) {
  return items.reduce((sum, item) => sum + item.price, 0);
}
```

## Phase 4: VERIFY GREEN - Watch It Pass

### Goal
Confirm test passes and nothing broke.

### Steps

**1. Run Test**
```bash
npm test path/to/test.test.ts
```

**2. Verify Success**

**✓ Good:**
```
PASS: retries failed operations 3 times
```

**✗ Bad (Still Failing):**
```
FAIL: retries failed operations 3 times
```
→ Fix implementation, don't change test

**✗ Bad (New Test Passes, Old Tests Fail):**
```
PASS: retries failed operations 3 times
FAIL: handles immediate success
```
→ Fix regression immediately

**3. Run Full Test Suite**
```bash
# Run ALL tests
npm test

# Verify output
All tests passed? → Proceed to REFACTOR
Some tests failed? → Fix regressions before continuing
```

### What to Check

- [ ] New test passes
- [ ] All existing tests pass
- [ ] No warnings in output
- [ ] No console errors
- [ ] Build succeeds

### Common Issues

**Issue: Test Still Fails**

```typescript
// Test expects 3 retries
expect(attempts).toBe(3);

// But implementation only does 2
for (let i = 0; i < 2; i++) {
  // Fix: Change to 3
}
```

**Issue: Other Tests Break**

```typescript
// New code breaks existing functionality
function processArray(arr: number[]) {
  return arr.map(x => x * 2);  // Breaks test expecting sum
}

// Fix implementation to satisfy both tests
function processArray(arr: number[], operation: 'sum' | 'double') {
  if (operation === 'sum') return arr.reduce((a, b) => a + b);
  return arr.map(x => x * 2);
}
```

## Phase 5: REFACTOR - Improve Code

### Goal
Clean up code while keeping tests green.

### When to Refactor

**Do refactor when:**
- Code is duplicated
- Names are unclear
- Logic is complex
- Structure is messy

**Don't refactor when:**
- Tests are red
- Adding new behavior
- Time pressure (do it next cycle)

### Refactoring Steps

**1. Identify Improvements**

```typescript
// Before: Duplication
function validateEmail(email: string) {
  if (!email.includes('@')) return false;
  if (email.indexOf('@') !== email.lastIndexOf('@')) return false;
  return true;
}

function validateUsername(username: string) {
  if (username.length < 3) return false;
  if (username.length > 20) return false;
  return true;
}

// After: Extract common pattern
function validateLength(str: string, min: number, max: number) {
  return str.length >= min && str.length <= max;
}

function validateEmail(email: string) {
  return email.includes('@') &&
         email.indexOf('@') === email.lastIndexOf('@');
}

function validateUsername(username: string) {
  return validateLength(username, 3, 20);
}
```

**2. Refactor Incrementally**

```
Make ONE change → Run tests → Green? → Next change
```

**DON'T:** Make multiple changes then run tests
**DO:** Change → Test → Change → Test

**3. Keep Tests Green**

If tests turn red during refactoring:
- STOP
- Revert change
- Try smaller change
- Keep tests green at all times

### Common Refactorings

**Extract Method:**
```typescript
// Before
function processUser(user: User) {
  const valid = user.email.includes('@') &&
                user.age >= 18 &&
                user.name.length > 0;
  if (!valid) throw new Error('Invalid');
  // ...
}

// After
function validateUser(user: User): boolean {
  return user.email.includes('@') &&
         user.age >= 18 &&
         user.name.length > 0;
}

function processUser(user: User) {
  if (!validateUser(user)) throw new Error('Invalid');
  // ...
}
```

**Rename for Clarity:**
```typescript
// Before
function proc(d: any) {
  const x = d.a * d.b;
  return x;
}

// After
function calculateArea(dimensions: Dimensions) {
  const area = dimensions.width * dimensions.height;
  return area;
}
```

## Phase 6: REPEAT - Next Test

### Goal
Continue cycle for next behavior.

### Steps

**1. Identify Next Behavior**

```
Current: Validates email format
Next: Validates password strength
Future: Checks username availability
```

**2. Start New Cycle**

Return to Phase 1 (RED) with new test:

```typescript
test('rejects weak passwords', () => {
  const result = validatePassword('123');
  expect(result.valid).toBe(false);
  expect(result.error).toBe('Password too short');
});
```

**3. Small Increments**

Each test should be small step:
- ✓ Add email validation
- ✓ Add password validation
- ✓ Add username validation

Not:
- ✗ Add complete user registration system

## Complete Example: Building Retry Function

### Iteration 1: Basic Retry

**RED:**
```typescript
test('retries failed operation once', async () => {
  let attempts = 0;
  const operation = () => {
    attempts++;
    if (attempts < 2) throw new Error('fail');
    return 'success';
  };

  const result = await retryOperation(operation);
  expect(attempts).toBe(2);
});
```

**GREEN:**
```typescript
async function retryOperation<T>(fn: () => Promise<T>): Promise<T> {
  try {
    return await fn();
  } catch (e) {
    return await fn();  // Retry once
  }
}
```

### Iteration 2: Multiple Retries

**RED:**
```typescript
test('retries failed operation 3 times', async () => {
  let attempts = 0;
  const operation = () => {
    attempts++;
    if (attempts < 3) throw new Error('fail');
    return 'success';
  };

  const result = await retryOperation(operation);
  expect(attempts).toBe(3);
});
```

**GREEN:**
```typescript
async function retryOperation<T>(fn: () => Promise<T>): Promise<T> {
  for (let i = 0; i < 3; i++) {
    try {
      return await fn();
    } catch (e) {
      if (i === 2) throw e;
    }
  }
  throw new Error('unreachable');
}
```

### Iteration 3: Handle Final Failure

**RED:**
```typescript
test('throws error after all retries exhausted', async () => {
  const operation = () => {
    throw new Error('persistent failure');
  };

  await expect(retryOperation(operation)).rejects.toThrow('persistent failure');
});
```

**GREEN:**
```typescript
// Already passes! Implementation handles this.
```

**REFACTOR:**
```typescript
async function retryOperation<T>(
  fn: () => Promise<T>,
  maxRetries: number = 3
): Promise<T> {
  let lastError: Error;

  for (let attempt = 0; attempt < maxRetries; attempt++) {
    try {
      return await fn();
    } catch (error) {
      lastError = error as Error;
    }
  }

  throw lastError!;
}
```

## Summary

**The Cycle:**
1. RED: Write failing test
2. VERIFY RED: Watch it fail correctly
3. GREEN: Minimal implementation
4. VERIFY GREEN: Watch it pass
5. REFACTOR: Improve code
6. REPEAT: Next behavior

**Key Points:**
- Each phase is mandatory
- Watch tests run (don't skip verification)
- Keep implementations minimal
- Refactor only when green
- Small increments, one behavior at a time

## Related References

- [Examples](examples.md): Real-world TDD scenarios
- [Philosophy](philosophy.md): Why order matters
- [Anti-patterns](anti-patterns.md): Common mistakes
- [Integration](integration.md): TDD with other skills

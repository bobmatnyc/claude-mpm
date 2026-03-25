# TDD Integration with Other Skills

> **Part of**: [Test-Driven Development](../SKILL.md)
> **Category**: testing
> **Reading Level**: Intermediate

## Purpose

How to integrate test-driven development with other development skills and workflows, including debugging, refactoring, and defensive programming.

## TDD + Systematic Debugging

### Integration Point: Bug Reproduction

When a bug is found, combine TDD with systematic debugging:

**Process:**

1. **Systematic Debugging Phase 1**: Investigate root cause
   - Read error messages
   - Reproduce consistently
   - Gather evidence
   - Form hypothesis

2. **TDD RED**: Write failing test reproducing bug
   ```typescript
   test('handles empty array without error', () => {
     const result = processArray([]);
     expect(result).toEqual([]);  // Currently fails
   });
   ```

3. **Systematic Debugging Phase 4**: Verify hypothesis
   - Test confirms bug exists
   - Test shows exact failing case

4. **TDD GREEN**: Fix implementation
   ```typescript
   function processArray(items: Item[]): Result[] {
     if (items.length === 0) {
       return [];  // Fix edge case
     }
     return items.map(transform);
   }
   ```

5. **TDD Verify GREEN**: Confirm fix
   - Test passes
   - Bug resolved
   - Regression protection added

### Example: Complete Bug Fix Workflow

**Bug Report:** "Application crashes when user has no items"

**Step 1: Systematic Investigation**
```
Error: Cannot read property 'map' of undefined
Stack trace shows: processArray called with undefined

Root cause: items parameter is undefined when user has no items
```

**Step 2: Write Failing Test**
```typescript
test('handles undefined items gracefully', () => {
  const result = processArray(undefined);
  expect(result).toEqual([]);
});

// Run test
// FAIL: TypeError: Cannot read property 'map' of undefined
// ✓ Test reproduces bug
```

**Step 3: Minimal Fix**
```typescript
function processArray(items?: Item[]): Result[] {
  if (!items || items.length === 0) {
    return [];
  }
  return items.map(transform);
}
```

**Step 4: Verify Fix**
```bash
$ npm test
PASS: handles undefined items gracefully
PASS: processes normal array (existing test)
```

**Benefit:** Bug fixed with permanent regression protection.

## TDD + Refactoring

### Integration Point: Safe Refactoring

Tests enable confident refactoring by catching breaks immediately.

**Workflow:**

1. **Ensure Tests Exist**: Before refactoring, verify comprehensive test coverage
2. **Verify GREEN**: All tests pass before starting
3. **Refactor**: Make structural changes
4. **Verify GREEN**: Tests still pass = behavior preserved
5. **Repeat**: Continue refactoring with confidence

### Example: Extract Service Layer

**Before Refactoring:**
```typescript
// All logic in controller
class UserController {
  async register(req, res) {
    // Validation
    if (!req.body.email.includes('@')) {
      return res.status(400).json({ error: 'Invalid email' });
    }

    // Business logic
    const user = await db.users.create(req.body);

    // Response
    return res.json({ user });
  }
}

// Tests exist
describe('User Registration', () => {
  test('registers valid user', async () => {
    const response = await request(app)
      .post('/register')
      .send({ email: 'test@example.com', name: 'Test' });

    expect(response.status).toBe(200);
    expect(response.body.user).toBeDefined();
  });

  test('rejects invalid email', async () => {
    const response = await request(app)
      .post('/register')
      .send({ email: 'invalid', name: 'Test' });

    expect(response.status).toBe(400);
  });
});
```

**Refactoring Process:**

1. **Verify GREEN**: Tests pass ✓

2. **Extract validation**:
   ```typescript
   function validateEmail(email: string): boolean {
     return email.includes('@');
   }

   class UserController {
     async register(req, res) {
       if (!validateEmail(req.body.email)) {
         return res.status(400).json({ error: 'Invalid email' });
       }
       const user = await db.users.create(req.body);
       return res.json({ user });
     }
   }
   ```

3. **Verify GREEN**: Tests pass ✓

4. **Extract service**:
   ```typescript
   class UserService {
     async createUser(data: UserData): Promise<User> {
       if (!validateEmail(data.email)) {
         throw new Error('Invalid email');
       }
       return db.users.create(data);
     }
   }

   class UserController {
     async register(req, res) {
       try {
         const user = await this.userService.createUser(req.body);
         return res.json({ user });
       } catch (error) {
         return res.status(400).json({ error: error.message });
       }
     }
   }
   ```

5. **Verify GREEN**: Tests pass ✓

**Result:** Refactored safely, behavior preserved, tests confirm correctness.

## TDD + Defense in Depth

### Integration Point: Validation at Boundaries

After TDD implementation, add defensive validation layers.

**Workflow:**

1. **TDD Implementation**: Build feature with tests
2. **Add Input Validation**: Test-drive validation at entry points
3. **Add Precondition Checks**: Test-drive assertions in functions
4. **Add Error Handling**: Test-drive error cases

### Example: Building Robust Payment Processing

**Phase 1: Core Functionality (TDD)**
```typescript
test('processes payment successfully', async () => {
  const result = await processPayment({
    amount: 100,
    cardNumber: '4111111111111111',
    cvv: '123'
  });

  expect(result.success).toBe(true);
  expect(result.transactionId).toBeDefined();
});

function processPayment(payment: Payment): Promise<PaymentResult> {
  return paymentGateway.charge(payment);
}
```

**Phase 2: Add Validation (TDD)**
```typescript
test('rejects negative amounts', async () => {
  await expect(
    processPayment({ amount: -100, cardNumber: '4111', cvv: '123' })
  ).rejects.toThrow('Amount must be positive');
});

test('validates card number format', async () => {
  await expect(
    processPayment({ amount: 100, cardNumber: 'invalid', cvv: '123' })
  ).rejects.toThrow('Invalid card number');
});

function processPayment(payment: Payment): Promise<PaymentResult> {
  if (payment.amount <= 0) {
    throw new Error('Amount must be positive');
  }
  if (!isValidCardNumber(payment.cardNumber)) {
    throw new Error('Invalid card number');
  }
  return paymentGateway.charge(payment);
}
```

**Phase 3: Add Defensive Checks (TDD)**
```typescript
test('handles gateway timeout', async () => {
  paymentGateway.charge = jest.fn().mockRejectedValue(new Error('Timeout'));

  const result = await processPayment({
    amount: 100,
    cardNumber: '4111111111111111',
    cvv: '123'
  });

  expect(result.success).toBe(false);
  expect(result.error).toBe('Payment gateway timeout');
});

async function processPayment(payment: Payment): Promise<PaymentResult> {
  // Validation
  validatePayment(payment);

  // Defensive processing
  try {
    return await paymentGateway.charge(payment);
  } catch (error) {
    if (error.message.includes('Timeout')) {
      return { success: false, error: 'Payment gateway timeout' };
    }
    throw error;
  }
}
```

**Result:** Robust system built incrementally with TDD, each layer tested.

## TDD + Verification Before Completion

### Integration Point: Completion Checklist

Before marking work complete, verify TDD was followed.

**Checklist:**

- [ ] Every new function/method has tests
- [ ] Watched each test fail before implementing
- [ ] Each test failed for expected reason (feature missing, not typo)
- [ ] Wrote minimal code to pass each test
- [ ] All tests pass
- [ ] No warnings in test output
- [ ] Tests use real code (mocks only if unavoidable)
- [ ] Edge cases covered
- [ ] Error cases tested

**If can't check all boxes:** Return to TDD process.

### Example: Code Review with TDD Verification

**Pull Request Checklist:**

```markdown
## TDD Verification

- [x] All new code has corresponding tests
- [x] Tests were written before implementation
- [x] Watched tests fail with correct error messages
- [x] Tests pass after implementation
- [x] Edge cases tested: empty input, null values, invalid data
- [x] Error cases tested: network failures, validation errors
- [x] No test warnings or errors in output
- [ ] Considered security implications

Test Coverage: 95%
New Tests: 12
Modified Tests: 3
```

**If checklist incomplete:** Request changes to follow TDD properly.

## TDD + Continuous Integration

### Integration Point: Automated Test Runs

CI/CD pipeline runs tests automatically, ensuring TDD benefits persist.

**CI Configuration:**

```yaml
# .github/workflows/test.yml
name: Test

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Setup Node
        uses: actions/setup-node@v3
        with:
          node-version: '18'

      - name: Install dependencies
        run: npm ci

      - name: Run tests
        run: npm test -- --coverage

      - name: Check coverage threshold
        run: |
          COVERAGE=$(npm test -- --coverage --silent | grep "All files" | awk '{print $10}' | tr -d '%')
          if [ $COVERAGE -lt 80 ]; then
            echo "Coverage $COVERAGE% is below 80%"
            exit 1
          fi

      - name: Fail if warnings
        run: npm test -- --maxWarnings=0
```

**Benefits:**
- Every commit runs tests
- Prevents regression
- Enforces coverage requirements
- Blocks merging if tests fail

## TDD + Code Review

### Integration Point: Review Process

Code reviews verify TDD practices were followed.

**Review Checklist for Reviewers:**

**Tests Quality:**
- [ ] Tests exist for all new code
- [ ] Tests are clear and focused (one behavior each)
- [ ] Tests verify behavior, not implementation
- [ ] Minimal use of mocks
- [ ] Edge cases covered
- [ ] Error cases covered

**TDD Evidence:**
- [ ] Commit history shows test-then-implementation pattern
- [ ] Tests are simple and clear
- [ ] Implementation is minimal (no over-engineering)
- [ ] Code structure suggests test-driven design

**Red Flags:**
- [ ] Tests added in separate "add tests" commit
- [ ] Tests appear to verify existing implementation
- [ ] Over-complicated implementation
- [ ] Tests pass immediately (never failed)

### Example Review Comments

**Good TDD:**
```
✓ Clean test-driven design
✓ Tests clearly show requirements
✓ Implementation is minimal and focused
✓ Excellent TDD practice!
```

**Needs Improvement:**
```
⚠ Tests appear to be written after implementation
⚠ Test passes immediately - did you watch it fail?
⚠ Implementation more complex than tests require
⚠ Please follow RED/GREEN/REFACTOR cycle
```

## TDD + Pair Programming

### Integration Point: Real-time Collaboration

Pair programming enforces TDD discipline through peer accountability.

**Ping-Pong Pattern:**

1. **Developer A**: Write failing test
2. **Developer B**: Make test pass
3. **Both**: Refactor together
4. **Developer B**: Write next failing test
5. **Developer A**: Make test pass
6. **Repeat**

**Benefits:**
- Enforces test-first (partner won't let you skip)
- Catches anti-patterns immediately
- Shared understanding of requirements
- Better test design from two perspectives

## Summary

**TDD Integrations:**

1. **Systematic Debugging**: Write failing test to reproduce bug
2. **Refactoring**: Tests enable safe structural changes
3. **Defense in Depth**: Test-drive validation and error handling
4. **Verification**: Checklist ensures TDD was followed
5. **CI/CD**: Automated test runs preserve TDD benefits
6. **Code Review**: Verify TDD practices in review
7. **Pair Programming**: Enforce TDD through collaboration

**Key Principle**: TDD integrates with all development practices by providing test-based foundation for confidence.

## Related References

- [Workflow](workflow.md): Complete RED/GREEN/REFACTOR cycle
- [Examples](examples.md): Real-world TDD scenarios
- [Philosophy](philosophy.md): Why TDD works
- [Anti-patterns](anti-patterns.md): Common mistakes

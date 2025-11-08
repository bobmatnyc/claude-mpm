# Completeness Anti-Patterns

Anti-patterns related to incomplete testing practices: partial mocks that hide structural dependencies, and treating tests as optional afterthoughts instead of integral parts of implementation.

## Anti-Pattern 4: Incomplete Mocks

**The violation:**
```typescript
// ❌ BAD: Partial mock - only fields you think you need
const mockResponse = {
  status: 'success',
  data: { userId: '123', name: 'Alice' }
  // Missing: metadata that downstream code uses
};

// Later: breaks when code accesses response.metadata.requestId
```

**Why this is wrong:**
- **Partial mocks hide structural assumptions** - You only mocked fields you know about
- **Downstream code may depend on fields you didn't include** - Silent failures
- **Tests pass but integration fails** - Mock incomplete, real API complete
- **False confidence** - Test proves nothing about real behavior
- **Breaking changes go undetected** - API changes don't fail tests

**The Iron Rule:** Mock the COMPLETE data structure as it exists in reality, not just fields your immediate test uses.

**Real-world impact:**
```typescript
// Your test (incomplete mock)
const mockUser = { id: '123', name: 'Alice' };
// Passes ✅

// Production code elsewhere
function getUserTimezone(user) {
  return user.profile.timezone;  // undefined - breaks in production!
}
```

### Complete Mock Strategy

**The fix:**
```typescript
// ✅ GOOD: Mirror real API completeness
const mockResponse = {
  status: 'success',
  data: {
    userId: '123',
    name: 'Alice',
    email: 'alice@example.com',
    profile: {
      timezone: 'America/New_York',
      locale: 'en-US',
      avatar: 'https://...'
    }
  },
  metadata: {
    requestId: 'req-789',
    timestamp: 1234567890,
    version: 'v2'
  }
  // All fields real API returns
};
```

### How to Create Complete Mocks

**Step 1: Reference real API documentation**
```typescript
// ❌ BAD - mocking from memory
const mock = { id: 1, name: 'test' };

// ✅ GOOD - reference API docs
// From API docs: GET /api/users/:id returns:
// {
//   id: number,
//   name: string,
//   email: string,
//   createdAt: ISO8601,
//   profile: { ... },
//   permissions: string[]
// }

const mock = {
  id: 1,
  name: 'test',
  email: 'test@example.com',
  createdAt: '2024-01-01T00:00:00Z',
  profile: { /* complete profile */ },
  permissions: ['read', 'write']
};
```

**Step 2: Use TypeScript types**
```typescript
// ✅ TypeScript ensures completeness
interface User {
  id: string;
  name: string;
  email: string;
  profile: UserProfile;
  metadata: UserMetadata;
}

// TypeScript error if incomplete
const mockUser: User = {
  id: '123',
  name: 'Alice'
  // Error: Missing email, profile, metadata
};

// Must be complete
const mockUser: User = {
  id: '123',
  name: 'Alice',
  email: 'alice@example.com',
  profile: { timezone: 'UTC', locale: 'en' },
  metadata: { createdAt: '2024-01-01T00:00:00Z' }
};
```

**Step 3: Extract mock factories**
```typescript
// ✅ Reusable complete mocks
// test-utils/factories/user.ts
export function createMockUser(overrides?: Partial<User>): User {
  return {
    id: '123',
    name: 'Test User',
    email: 'test@example.com',
    profile: {
      timezone: 'UTC',
      locale: 'en-US',
      avatar: null
    },
    metadata: {
      createdAt: '2024-01-01T00:00:00Z',
      updatedAt: '2024-01-01T00:00:00Z',
      version: 1
    },
    permissions: ['read'],
    ...overrides  // Allow customization
  };
}

// Usage
const user = createMockUser({ name: 'Alice' });
// All fields present, name overridden
```

### Detecting Incomplete Mocks

**Red flags:**
- Creating mocks without referencing API docs
- TypeScript `any` or `Partial<T>` for mocks
- Different tests have different mock shapes for same type
- Mock has fewer fields than real API
- Comments like "add fields as needed"

**Gate Function:**

```
BEFORE creating mock responses:
  Check: "What fields does the real API response contain?"

  Actions:
    1. Open API documentation or OpenAPI spec
    2. List ALL fields in response
    3. Include ALL fields in mock (use TypeScript types)
    4. Verify mock matches real response schema completely

  Critical:
    If you're creating a mock, you must understand the ENTIRE structure
    Partial mocks fail silently when code depends on omitted fields

  If uncertain:
    - Include all documented fields
    - Use TypeScript interfaces to enforce completeness
    - Create factory functions for reusable complete mocks

  Red flags:
    - "I'll add more fields later"
    - "Just mocking what I need"
    - Creating mock from memory
    - Different mock shapes for same entity
```

### Common Incomplete Mock Scenarios

**Scenario 1: Nested objects**
```typescript
// ❌ BAD - incomplete nesting
const mockUser = {
  id: '123',
  profile: { name: 'Alice' }  // Missing profile.timezone, profile.locale
};

// ✅ GOOD - complete nesting
const mockUser = {
  id: '123',
  profile: {
    name: 'Alice',
    timezone: 'UTC',
    locale: 'en-US',
    avatar: null,
    bio: null
  }
};
```

**Scenario 2: Arrays**
```typescript
// ❌ BAD - empty array when real data has items
const mockResponse = {
  users: []  // Real API always has pagination metadata
};

// ✅ GOOD - realistic array with metadata
const mockResponse = {
  users: [
    { id: '1', name: 'Alice', /* complete user */ },
    { id: '2', name: 'Bob', /* complete user */ }
  ],
  pagination: {
    total: 2,
    page: 1,
    perPage: 10,
    hasNext: false
  }
};
```

**Scenario 3: Optional fields**
```typescript
// ❌ BAD - omitting optional fields
const mockUser = {
  id: '123',
  name: 'Alice'
  // Omitted optional fields - downstream code may check them
};

// ✅ GOOD - include optional fields (as null/undefined)
const mockUser = {
  id: '123',
  name: 'Alice',
  bio: null,           // Optional field explicitly null
  website: undefined,  // Optional field explicitly undefined
  avatar: null
};
```

### Mock Completeness Levels

**Level 1: Minimal (AVOID)**
```typescript
// Only immediate test needs
const mock = { id: '123' };
// Risk: High - downstream code breaks
```

**Level 2: Partial (RISKY)**
```typescript
// Common fields included
const mock = { id: '123', name: 'Alice', email: 'alice@example.com' };
// Risk: Medium - missing nested/optional fields
```

**Level 3: Complete (REQUIRED)**
```typescript
// All fields from API spec
const mock = {
  id: '123',
  name: 'Alice',
  email: 'alice@example.com',
  profile: { /* complete */ },
  metadata: { /* complete */ },
  permissions: ['read']
};
// Risk: Low - matches real API
```

**Level 4: Factory-based (BEST)**
```typescript
// Reusable factory with defaults
const mock = createMockUser({ name: 'Alice' });
// Risk: Minimal - centralized, typed, complete
```

## Anti-Pattern 5: Integration Tests as Afterthought

**The violation:**
```
✅ Implementation complete
❌ No tests written
"Ready for testing"
```

**Why this is wrong:**
- Testing is part of implementation, not optional follow-up
- TDD would have caught this
- Can't claim complete without tests
- Tests written after code are biased toward existing implementation
- Missing tests = incomplete feature
- Technical debt from day one

**The fix:**
```
TDD cycle:
1. Write failing test
2. Watch it fail (verify)
3. Write minimal code to pass
4. Watch it pass (verify)
5. Refactor
6. THEN claim complete
```

### Why Tests Must Come First

**Tests-after problems:**

1. **Implementation bias**
   - Tests confirm what code does, not what it should do
   - Bugs baked into tests
   - Missing edge cases

2. **Design issues**
   - Code hard to test (not designed for testability)
   - Tight coupling discovered too late
   - Refactoring required to make testable

3. **Coverage gaps**
   - Temptation to skip "hard to test" paths
   - Error handling overlooked
   - Edge cases ignored

4. **False completion**
   - Feature seems done but untested
   - Integration issues discovered late
   - Delayed feedback loop

**Tests-first benefits:**

1. **Design driver**
   - Forces testable design upfront
   - Identifies coupling before writing code
   - API designed from consumer perspective

2. **Verification**
   - Confirms implementation matches requirements
   - Catches bugs immediately
   - Documents expected behavior

3. **Confidence**
   - Safe refactoring
   - Regression prevention
   - Living documentation

### Integration Testing Strategy

**When to write integration tests:**

- **Before implementation** (TDD approach)
  ```typescript
  // 1. Write failing integration test
  test('user registration flow', async () => {
    const response = await api.post('/register', userData);
    expect(response.status).toBe(201);
    expect(response.body.user).toMatchObject(userData);
  });
  // Test fails - endpoint doesn't exist

  // 2. Implement endpoint
  // 3. Test passes
  ```

- **Alongside unit tests** (test pyramid)
  - Unit tests: Fast, isolated, many
  - Integration tests: Realistic, end-to-end, fewer
  - Both written before/during implementation

**Types of integration tests:**

1. **API integration tests**
   ```typescript
   test('POST /api/users creates user', async () => {
     const response = await request(app)
       .post('/api/users')
       .send({ name: 'Alice', email: 'alice@example.com' });

     expect(response.status).toBe(201);
     expect(response.body).toMatchObject({
       id: expect.any(String),
       name: 'Alice',
       email: 'alice@example.com'
     });

     // Verify database
     const user = await db.users.findById(response.body.id);
     expect(user).toBeDefined();
   });
   ```

2. **Database integration tests**
   ```typescript
   test('user repository saves and retrieves users', async () => {
     const user = await userRepo.create({
       name: 'Alice',
       email: 'alice@example.com'
     });

     const retrieved = await userRepo.findById(user.id);
     expect(retrieved).toEqual(user);
   });
   ```

3. **Component integration tests**
   ```typescript
   test('UserForm submits to API', async () => {
     render(<UserForm />);

     fireEvent.change(screen.getByLabelText('Name'), {
       target: { value: 'Alice' }
     });
     fireEvent.click(screen.getByText('Submit'));

     await waitFor(() => {
       expect(mockApi.post).toHaveBeenCalledWith('/users', {
         name: 'Alice'
       });
     });
   });
   ```

### Test Completeness Checklist

**Before claiming implementation complete:**

```
□ Unit tests written and passing
  - All public functions tested
  - Edge cases covered
  - Error conditions tested

□ Integration tests written and passing
  - End-to-end flows tested
  - External dependencies tested
  - Error handling tested

□ Test coverage meets threshold (e.g., 80%)
  - Line coverage
  - Branch coverage
  - Critical paths covered

□ Tests run in CI/CD pipeline
  - Automated on commits
  - Blocks merge if failing

□ Tests document behavior
  - Clear test names
  - Meaningful assertions
  - Edge cases explained
```

### Gate Function

```
BEFORE claiming implementation complete:
  Ask: "Are tests written?"

  IF no:
    STOP - Not complete
    Write tests before continuing

  Ask: "Do tests cover all requirements?"

  IF no:
    STOP - Incomplete testing
    Add missing test cases

  Ask: "Did I follow TDD (test-first)?"

  IF no:
    WARNING - Consider rewriting with TDD
    Tests may be implementation-biased

  Ask: "Do integration tests pass?"

  IF no:
    STOP - Not ready for integration
    Fix integration issues

  Definition of "complete":
    ✅ Unit tests written and passing
    ✅ Integration tests written and passing
    ✅ Coverage meets threshold
    ✅ Tests run in CI/CD
    ✅ All requirements verified
```

### Recovery: Adding Tests After Implementation

**If tests weren't written first (damage control):**

1. **Stop adding features** - Don't dig deeper hole
2. **Write tests for existing code** - Start with critical paths
3. **Refactor for testability** - Decouple as needed
4. **Adopt TDD going forward** - Prevent future occurrence

**Prioritization:**
- **High priority:** Critical business logic, security, data integrity
- **Medium priority:** Common user flows, API endpoints
- **Low priority:** UI styling, configuration, one-off scripts

**Approach:**
```typescript
// 1. Write characterization tests (document current behavior)
test('current behavior: user registration', async () => {
  const result = await registerUser(userData);
  // Document what currently happens
  expect(result).toMatchSnapshot();
});

// 2. Add specific behavior tests
test('user registration validates email', async () => {
  await expect(registerUser({ email: 'invalid' }))
    .rejects.toThrow('Invalid email');
});

// 3. Refactor safely with test coverage
// Now can refactor with confidence
```

## Prevention Through TDD

**How TDD prevents completeness anti-patterns:**

1. **Incomplete mocks**
   - Writing test first forces understanding of data structures
   - Failing test shows what fields are needed
   - Implementation reveals missing mock fields immediately

2. **Tests as afterthought**
   - TDD makes tests part of implementation process
   - Can't write implementation without test
   - Test-first is the workflow, not optional step

**TDD workflow enforces:**
- Complete understanding of requirements (to write test)
- Complete data structures (test fails if incomplete)
- Complete coverage (tests drive implementation)

See [test-driven-development skill](../../test-driven-development/) for complete TDD workflow.

## Real-World Impact

**Incomplete mocks:**
- Tests pass, production breaks
- Integration issues discovered late
- False confidence in test suite
- Difficult debugging (mock ≠ reality)

**Tests as afterthought:**
- Bugs escape to production
- Implementation hard to test (design issues)
- Coverage gaps
- Technical debt from day one

**With complete approach:**
- Tests catch integration issues early
- High confidence in test suite
- Testable design from start
- Complete feature = tested feature

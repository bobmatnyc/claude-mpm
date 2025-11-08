# Detection Guide: Identifying Testing Anti-Patterns

Comprehensive guide for detecting testing anti-patterns before they cause problems. Includes red flags, warning signs, gate functions, and diagnostic checklists.

## Overview

Prevention is easier than cure. This guide helps you identify anti-patterns during code review, test writing, or debugging test failures.

## Universal Detection Checklist

Run before committing any test:

```
□ Am I asserting on mock elements? (testId='*-mock')
  → If yes: STOP - Test real component or unmock

□ Does this method only exist for tests?
  → If yes: STOP - Move to test utilities

□ Do I fully understand what I'm mocking?
  → If no: STOP - Run with real impl first, then mock minimally

□ Is my mock missing fields the real API has?
  → If yes: STOP - Mirror complete API structure

□ Did I write implementation before test?
  → If yes: STOP - Delete impl, write test first (TDD)

□ Is mock setup >50% of test code?
  → If yes: Consider integration test with real components

□ Can I explain what real behavior this test verifies?
  → If no: STOP - Clarify what you're testing

□ Would this test fail if I removed mocks?
  → If no: You're testing mock behavior
```

## Anti-Pattern 1: Testing Mock Behavior

### Red Flags

**Code indicators:**
```typescript
// 🚩 Test ID contains "mock"
expect(screen.getByTestId('sidebar-mock')).toBeInTheDocument();

// 🚩 Asserting mock was called
expect(mockFunction).toHaveBeenCalled();

// 🚩 Checking mock return values
expect(result).toBe(mockReturnValue);

// 🚩 Test fails when mock removed
// Remove mock → test fails → you're testing mock
```

**Language patterns:**
- "Make sure the mock..."
- "Test that component renders mock"
- "Verify mock is present"
- "Check if mock function called"

**Diagnostic questions:**
1. **"If I remove this mock, does test still make sense?"**
   - No → You're testing mock behavior
   - Yes → Good, test tests real behavior

2. **"What production behavior does this verify?"**
   - Can't answer → Testing mock behavior
   - Clear answer → Good

3. **"Would this test catch real bugs?"**
   - No → Testing mock behavior
   - Yes → Good

### Detection Script

```typescript
// Run this check on your tests
function detectsMockTesting(testFile: string): string[] {
  const warnings: string[] = [];

  // Pattern: testId with 'mock'
  if (testFile.includes("getByTestId('") && testFile.includes('-mock')) {
    warnings.push('Testing mock element by test ID');
  }

  // Pattern: expecting on mock objects
  if (testFile.includes('expect(mock') && testFile.includes('toBe')) {
    warnings.push('Asserting on mock values');
  }

  // Pattern: mock call assertions without behavior check
  if (testFile.includes('toHaveBeenCalled') &&
      !testFile.includes('expect(result)')) {
    warnings.push('Only checking mock calls, not results');
  }

  return warnings;
}
```

## Anti-Pattern 2: Test-Only Methods in Production

### Red Flags

**Code indicators:**
```typescript
// 🚩 Method only called in test files
// Search: "destroy(" → Only in *.test.ts files

// 🚩 Method names suggesting test use
class Session {
  reset()    // 🚩
  destroy()  // 🚩
  clear()    // 🚩
  mock()     // 🚩
}

// 🚩 Comments acknowledging test-only use
// "For testing only"
// "Used by test cleanup"
```

**File analysis:**
```bash
# Find methods only called in tests
grep -r "\.destroy\(" --include="*.ts" | grep -v ".test.ts"
# If empty → method only in tests → move to test utils
```

**Diagnostic questions:**
1. **"Is this method called outside test files?"**
   - No → Test-only method, move to utilities
   - Yes → Keep in production

2. **"Would production code ever need this?"**
   - No → Move to test utilities
   - Yes → Keep in production

3. **"Does this class own this resource's lifecycle?"**
   - No → Wrong place for this method
   - Yes → Consider if needed in production

### Detection Script

```typescript
// Analyze method usage
function findTestOnlyMethods(codebase: string[]): Report {
  const methods = extractMethods(codebase);

  return methods.filter(method => {
    const usages = findUsages(method);
    const testUsages = usages.filter(u => u.file.includes('.test.'));
    const prodUsages = usages.filter(u => !u.file.includes('.test.'));

    return testUsages.length > 0 && prodUsages.length === 0;
  });
}
```

## Anti-Pattern 3: Mocking Without Understanding

### Red Flags

**Code indicators:**
```typescript
// 🚩 Mocking without reading implementation
vi.mock('SomeModule');  // What does it do? Unknown.

// 🚩 "Just to be safe" mocking
// Mock everything, understand nothing

// 🚩 Test mysteriously fails/passes
// You can't explain why

// 🚩 Mock prevents test logic from working
vi.mock('UserService');  // Breaks user creation test needs
```

**Language patterns:**
- "I'll mock this to be safe"
- "This might be slow"
- "Let's mock everything"
- "Not sure why test fails"

**Diagnostic questions:**
1. **"What side effects does the real method have?"**
   - Can't answer → Don't mock yet
   - Know all effects → Can mock safely

2. **"Does my test depend on any of those side effects?"**
   - Yes → Don't mock at this level
   - No → Safe to mock

3. **"Where is the actual slow/external operation?"**
   - Unclear → Study code first
   - Clear → Mock at that level

### Detection Strategy

**Before mocking:**
```
1. Read the implementation
   - What does it do?
   - What are side effects?
   - What does it return?

2. Run test with real implementation
   - How slow is it? (measure!)
   - What behavior occurs?
   - What's actually needed?

3. Identify minimal mock point
   - Where is the slow/external operation?
   - Can I mock below this level?
   - What behavior must be preserved?

4. Mock at correct level
   - Mock boundary of slow operation
   - Preserve logic test depends on
   - Verify test still tests intended behavior
```

### Speed Measurement

```typescript
// Measure before mocking
test('user registration', async () => {
  const start = performance.now();
  await registerUser(userData);
  const duration = performance.now() - start;

  console.log(`Test took ${duration}ms`);
  // If <100ms → Don't mock
  // If >1000ms → Identify slow part
});
```

## Anti-Pattern 4: Incomplete Mocks

### Red Flags

**Code indicators:**
```typescript
// 🚩 Mock created from memory
const mock = { id: '123' };  // What other fields exist?

// 🚩 Partial type annotation
const mock: Partial<User> = { id: '123' };

// 🚩 Different tests, different mock shapes
// test1.ts: { id, name }
// test2.ts: { id, name, email, profile }

// 🚩 Comment acknowledging incompleteness
// "TODO: add more fields"
// "Add fields as needed"
```

**Missing documentation:**
- No reference to API docs
- No TypeScript interface
- No factory function
- Copy-pasted mock variations

**Diagnostic questions:**
1. **"What does the real API return?"**
   - Can't answer → Check docs before mocking
   - Know structure → Use it in mock

2. **"Am I using TypeScript types?"**
   - No → Add types to enforce completeness
   - Yes → Good

3. **"Do other tests mock this differently?"**
   - Yes → Inconsistent mocks, need factory
   - No → Good

### Detection Script

```typescript
// Find incomplete mocks
function detectIncompleteMocks(testFile: string): Warning[] {
  const warnings: Warning[] = [];

  // Pattern: Partial<T> in test
  if (testFile.includes('Partial<') && testFile.includes('mock')) {
    warnings.push('Using Partial type for mock - likely incomplete');
  }

  // Pattern: Object literals without types
  const mockPattern = /const mock\w+ = \{[^}]+\};/g;
  const mocks = testFile.match(mockPattern);

  if (mocks) {
    mocks.forEach(mock => {
      if (!mock.includes(': ')) {  // No type annotation
        warnings.push('Mock without type annotation');
      }
    });
  }

  return warnings;
}
```

### Completeness Checklist

```
□ Referenced API documentation
□ Used TypeScript interface/type
□ Included all required fields
□ Included optional fields (as null/undefined)
□ Nested objects complete
□ Arrays have realistic length/content
□ Metadata fields included
□ Timestamps/IDs present
```

## Anti-Pattern 5: Tests as Afterthought

### Red Flags

**Process indicators:**
```
🚩 PR has implementation commits, then "add tests" commit
🚩 "Ready for testing" status on untested feature
🚩 Test coverage added after code review
🚩 Tests written to pass, not fail first
🚩 Implementation complete, tests pending
```

**Language patterns:**
- "I'll add tests next"
- "Implementation done, needs tests"
- "Ready for testing phase"
- "Tests coming soon"

**Code indicators:**
```typescript
// 🚩 Tests that can't fail
test('feature works', () => {
  const result = newFeature();
  expect(result).toBe(result);  // Always passes
});

// 🚩 Tests with no assertions
test('feature runs', () => {
  newFeature();  // No expect()
});
```

**Diagnostic questions:**
1. **"Did I write test before implementation?"**
   - No → Not following TDD
   - Yes → Good

2. **"Did I watch test fail first?"**
   - No → Can't verify test works
   - Yes → Good

3. **"Are there commits without tests?"**
   - Yes → Tests afterthought
   - No → Good

### Git History Analysis

```bash
# Check if tests come after implementation
git log --oneline --name-only | grep -A5 "feature"

# Red flag pattern:
# abc123 Add feature X
#   src/feature.ts
# def456 Add tests for feature X  ← Tests after
#   src/feature.test.ts

# Good pattern:
# abc123 Add feature X with tests
#   src/feature.test.ts  ← Test file in same commit
#   src/feature.ts
```

## Warning Signs: When Mocks Become Too Complex

### Complexity Indicators

```typescript
// 🚩 Mock setup longer than test
const setup = 50 lines;
const test = 10 lines;
// Ratio > 3:1 → Too complex

// 🚩 Mocking everything
vi.mock('ModuleA');
vi.mock('ModuleB');
vi.mock('ModuleC');
vi.mock('ModuleD');
// 4+ mocks → Consider integration test

// 🚩 Nested mock setup
const mockA = { mock: mockB };
const mockB = { mock: mockC };
const mockC = { /* ... */ };

// 🚩 Mock setup in beforeEach for single test
beforeEach(() => {
  // 30 lines of setup
});

test('one thing', () => {
  // 5 lines
});
```

**Your human partner's question:** "Do we need to be using a mock here?"

**Consider:** Integration tests with real components often simpler than complex mocks.

### Complexity Metrics

```typescript
function calculateMockComplexity(test: TestFile): ComplexityScore {
  return {
    mockCount: countMocks(test),           // >4 is high
    setupLines: countSetupLines(test),     // >30 is high
    setupToTestRatio: setupLines / testLines,  // >3 is high
    mockNestingDepth: calculateNesting(test),  // >2 is high

    recommendation: score > 10 ? 'Use integration test' : 'OK'
  };
}
```

## Comprehensive Code Review Checklist

Use this when reviewing tests (yours or others'):

### Structure
```
□ Test files exist for new code
□ Tests in same commit as implementation
□ Tests follow TDD pattern (fail first)
□ Clear test names describe behavior
```

### Mock Usage
```
□ Mocks used sparingly (only when needed)
□ Mock setup is simple (<20 lines)
□ Mocks at correct level (I/O boundaries)
□ No assertions on mock elements
□ Complete mock structures (all fields)
```

### Production Code
```
□ No test-only methods in production classes
□ No test-specific logic in production
□ Clean separation of concerns
□ No test imports in production code
```

### Test Quality
```
□ Tests verify real behavior
□ Assertions on meaningful results
□ Edge cases covered
□ Error conditions tested
□ Integration tests for critical paths
```

### Red Flags
```
□ No 'testId="*-mock"' assertions
□ No Partial<T> for mocks
□ No "for testing" comments in production
□ No untested implementation commits
```

## Automated Detection Tools

### ESLint Rules

```javascript
// .eslintrc.js
module.exports = {
  rules: {
    // Prevent test-only methods
    'no-restricted-syntax': [
      'error',
      {
        selector: 'MethodDefinition[key.name=/^(reset|destroy|clear|mock)$/]',
        message: 'Potential test-only method in production code'
      }
    ],

    // Prevent mock test IDs
    'testing-library/prefer-screen-queries': 'error',
    'testing-library/no-node-access': 'error',
  }
};
```

### Pre-commit Hook

```bash
#!/bin/bash
# .git/hooks/pre-commit

# Check for mock test IDs
if git diff --cached | grep -q "testId=.*-mock"; then
  echo "Error: Found mock test ID in tests"
  echo "Are you testing mock behavior?"
  exit 1
fi

# Check for test-only methods
if git diff --cached -- "*.ts" "*.js" | \
   grep -v ".test." | \
   grep -q "destroy()\|reset()\|clear()"; then
  echo "Warning: Potential test-only method in production code"
fi

# Check test coverage
npm test -- --coverage --coverageThreshold='{"global":{"lines":80}}'
```

## Quick Reference: Detection Summary

| Anti-Pattern | Key Indicator | Quick Check |
|--------------|---------------|-------------|
| Testing Mock Behavior | testId='*-mock' | Remove mock - test still valid? |
| Test-Only Methods | Method only in .test. files | grep production files |
| Mocking Without Understanding | Can't explain why mocking | Read implementation first |
| Incomplete Mocks | Partial<T> or no types | Check against API docs |
| Tests as Afterthought | Implementation before tests | Check git history |

## When to Seek Help

**STOP and ask your human partner if:**
- Mock setup exceeds 50 lines
- You've mocked >5 modules in one test
- Test mysteriously passes/fails
- You can't explain what test verifies
- Same test needs different mocks in different runs
- Integration test seems simpler than mocks

**Questions to ask:**
- "Do we need to be using a mock here?"
- "Should this be an integration test?"
- "Am I testing the right thing?"
- "Is this test-only method necessary?"

## Prevention Mindset

**Before writing any test:**
1. Understand what you're testing (real behavior)
2. Write test first (TDD)
3. Watch it fail
4. Minimal implementation
5. Watch it pass
6. Refactor

**This workflow prevents all five anti-patterns naturally.**

See [test-driven-development skill](../../test-driven-development/) for complete TDD workflow.

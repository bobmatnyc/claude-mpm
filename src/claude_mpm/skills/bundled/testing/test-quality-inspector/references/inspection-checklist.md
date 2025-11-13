# Test Inspection Checklist

## Quick Inspection (2 minutes per test)

### Intent Check
- [ ] Test name describes behavior, not method
- [ ] Expected behavior is stated
- [ ] Single clear purpose

### Assertion Check
- [ ] Assertions match intent
- [ ] Specific values, not just "not None"
- [ ] Would catch regressions

### Failure Check
- [ ] Error cases tested
- [ ] Would fail if feature removed
- [ ] Meaningful failure messages

## Deep Inspection (5-10 minutes per test)

### 1. Intent Analysis
```
Question: What is this test supposed to verify?

Checklist:
[ ] Test name clearly states behavior
[ ] Docstring explains expected outcome
[ ] Setup reflects realistic scenario
[ ] Test has single responsibility
```

**Red Flags:**
- "test_method_name" (tests method, not behavior)
- "test_user" (too vague)
- "test_works" (what does "works" mean?)

### 2. Setup Quality
```
Question: Is the setup realistic and complete?

Checklist:
[ ] Test data matches production patterns
[ ] All dependencies are initialized
[ ] State is valid and achievable
[ ] Mocks are justified and complete
```

**Red Flags:**
- Mock data that would never occur
- Missing required fields
- Bypassing normal constraints
- Over-simplified scenarios

### 3. Execution Verification
```
Question: Does execution match intent?

Checklist:
[ ] Real code paths are exercised
[ ] System under test is not mocked
[ ] Integration points are tested
[ ] Side effects are verifiable
```

**Red Flags:**
- Mocking the system under test
- Testing mock behavior
- Skipping critical paths
- No integration verification

### 4. Assertion Strength
```
Question: Do assertions prove correctness?

Checklist:
[ ] Assertions verify specific values
[ ] Success criteria are explicit
[ ] Failure cases are tested
[ ] Error messages are meaningful
```

**Red Flags:**
- `assert result` (too weak)
- `assert x is not None` (existence only)
- `assert mock.called` (testing mock)
- No negative assertions

### 5. Regression Prevention
```
Question: Would this catch real bugs?

Checklist:
[ ] Test would fail if feature removed
[ ] Boundary conditions tested
[ ] Edge cases covered
[ ] Known bug patterns caught
```

**Red Flags:**
- Test passes with broken code
- Only happy path tested
- No boundary testing
- Missing error scenarios

## Inspection Report Template

```markdown
### Test: [test_name]

**Intent:** [What test claims to verify]
**Actually Tests:** [What it really tests]

**Strengths:**
- [Good aspects]

**Issues:**
1. [Issue] - [Impact]
2. [Issue] - [Impact]

**Suggestions:**
1. [Specific improvement]
2. [Additional test case]
3. [Assertion strengthening]

**Risk Level:** [LOW/MEDIUM/HIGH]
**Action:** [APPROVE/REQUEST_CHANGES/BLOCK]
```

## Risk Assessment

### HIGH Risk (Block merge)
- Weak assertions that would miss bugs
- Testing mock behavior only
- Missing critical failure cases
- Test passes with broken functionality

### MEDIUM Risk (Request changes)
- Incomplete coverage of scenarios
- Weak but not broken assertions
- Missing some error cases
- Could be stronger

### LOW Risk (Approve with notes)
- Minor naming improvements
- Additional nice-to-have tests
- Documentation enhancements
- Style consistency

## Common Patterns to Inspect

### Pattern 1: CRUD Operations
```python
# Check:
[ ] Create: Valid data, duplicate prevention, validation
[ ] Read: Exists, doesn't exist, multiple results
[ ] Update: Valid changes, invalid changes, concurrency
[ ] Delete: Exists, doesn't exist, cascade effects
```

### Pattern 2: Authentication/Authorization
```python
# Check:
[ ] Valid credentials succeed
[ ] Invalid credentials fail
[ ] Locked accounts rejected
[ ] Expired tokens rejected
[ ] Insufficient permissions denied
```

### Pattern 3: Data Validation
```python
# Check:
[ ] Valid data accepted
[ ] Invalid format rejected
[ ] Missing required fields rejected
[ ] Boundary values tested
[ ] Type coercion tested
```

### Pattern 4: API Endpoints
```python
# Check:
[ ] Success response structure
[ ] Error response structure
[ ] Status codes correct
[ ] Request validation
[ ] Response validation
```

## Mental Debugging Technique

For each test, mentally introduce bugs:

### Bug 1: Remove Core Logic
```
If I comment out the main functionality,
would this test fail?

If NO: Test is not testing the right thing
```

### Bug 2: Return Wrong Data
```
If I return incorrect values,
would assertions catch it?

If NO: Assertions are too weak
```

### Bug 3: Skip Validation
```
If I remove input validation,
would test catch invalid data?

If NO: Missing negative test cases
```

### Bug 4: Break Error Handling
```
If I make errors silently fail,
would test detect it?

If NO: Not testing failure paths
```

## Inspection Efficiency Tips

### Quick Wins
1. Check test names first (30 seconds)
2. Scan assertions (30 seconds)
3. Look for negative tests (30 seconds)
4. Check mock usage (30 seconds)

### Deep Dive Triggers
- Test name is vague
- Only one or two assertions
- No error cases visible
- Heavy mock usage
- Test recently added

### Batch Inspection
```
For test suite review:
1. Group tests by feature
2. Check coverage gaps between tests
3. Look for redundant tests
4. Identify missing scenarios
5. Verify integration tests exist
```

## Remember

✅ **Good inspection prevents:**
- False confidence from weak tests
- Production bugs slipping through
- Wasted time on bad tests
- Technical debt accumulation

❌ **Don't just check:**
- That tests exist
- That tests pass
- That coverage is high
- That names follow convention

✓ **Always verify:**
- Tests test the right thing
- Assertions are meaningful
- Failures are caught
- Regressions are prevented

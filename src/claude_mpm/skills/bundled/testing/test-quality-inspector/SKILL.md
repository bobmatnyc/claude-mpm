---
name: Test Quality Inspector
description: Systematically inspect unit and E2E tests to verify they test the right behavior, provide meaningful coverage, and catch real regressions
when_to_use: after engineer creates tests, before marking QA complete, when test failures seem suspicious, or when tests pass but bugs still occur
version: 1.0.0
progressive_disclosure:
  entry_point:
    summary: "Inspect tests to verify they actually test what they claim, catch real failures, and provide meaningful assertions."
    when_to_use: "After tests are written, before QA sign-off, when investigating test failures, or when production bugs slip through."
    quick_start: "1. Read the test 2. Ask: 'What behavior is this testing?' 3. Verify assertions match intent 4. Check failure scenarios 5. Suggest improvements"
  references:
    - inspection-checklist.md
    - assertion-quality.md
    - coverage-analysis.md
    - red-flags.md
---

# Test Quality Inspector

## Purpose

Engineers often write tests that pass without actually testing the right thing. This skill provides systematic inspection techniques to verify tests are:
- Testing real behavior, not implementation details
- Making meaningful assertions
- Catching actual failures
- Providing value, not just coverage

## When to Use This Skill

Activate this skill when:
- **After engineer creates tests** - Verify tests are effective
- **Before QA sign-off** - Don't approve without inspecting tests
- **Test failures seem suspicious** - "Why didn't this catch the bug?"
- **Tests pass but bugs occur** - Tests aren't testing the right thing
- **Coverage is high but confidence is low** - Coverage ≠ quality
- **Refactoring existing tests** - Improve test effectiveness

## The Inspection Framework

### Phase 1: Intent Analysis
**Question:** What is this test supposed to verify?

```
1. Read test name
2. Read test description/docstring
3. Identify claimed behavior
4. Note expected outcome
```

**Red Flags:**
- Vague test names ("test_user_creation")
- No description of expected behavior
- Tests named after methods, not behaviors
- "Test that X works" (what does "works" mean?)

### Phase 2: Setup Analysis
**Question:** Is the test setup realistic?

```
1. Examine test fixtures/setup
2. Check data realism
3. Verify state initialization
4. Identify mocks/stubs
```

**Red Flags:**
- Mock data that would never occur
- Missing required dependencies
- Overly simplified scenarios
- Setup that bypasses real constraints

### Phase 3: Execution Analysis
**Question:** Does the test exercise real behavior?

```
1. Trace execution path
2. Identify what's actually called
3. Check if mocks override real behavior
4. Verify integration points
```

**Red Flags:**
- Mocking the system under test
- Testing mock behavior instead of real behavior
- Execution path doesn't match intent
- Critical code paths not exercised

### Phase 4: Assertion Analysis
**Question:** Do assertions verify the claimed behavior?

```
1. Examine each assertion
2. Map assertions to intent
3. Check assertion strength
4. Verify failure conditions
```

**Red Flags:**
- Weak assertions ("assert result is not None")
- Asserting existence, not correctness
- Missing assertions for error cases
- Assertions on mocks instead of real outputs

### Phase 5: Failure Analysis
**Question:** What would make this test fail?

```
1. Introduce intentional bugs
2. Check if test catches them
3. Verify error messages are meaningful
4. Test failure scenarios explicitly
```

**Red Flags:**
- Test passes with obviously broken code
- Removing functionality doesn't fail test
- Error messages don't indicate what failed
- No negative test cases

## Inspection Checklist

Use this checklist for every test you inspect:

### Intent Verification
- [ ] Test name describes behavior, not implementation
- [ ] Expected behavior is clearly stated
- [ ] Success criteria are explicit
- [ ] Test has a single clear purpose

### Setup Quality
- [ ] Test data is realistic
- [ ] Required dependencies are present
- [ ] State initialization is valid
- [ ] Mocks are justified and complete

### Execution Quality
- [ ] Real code paths are exercised
- [ ] System under test is not mocked
- [ ] Integration points are tested
- [ ] Side effects are verified

### Assertion Quality
- [ ] Assertions match stated intent
- [ ] Assertions are specific and meaningful
- [ ] Both success and failure cases tested
- [ ] Error conditions are verified

### Regression Prevention
- [ ] Test would catch known bug patterns
- [ ] Boundary conditions are tested
- [ ] Edge cases are covered
- [ ] Failure modes are explicit

## Common Test Smells

### 1. The Optimistic Asserter
```python
# BAD: Only tests happy path
def test_user_login():
    user = create_user("test@example.com", "password123")
    assert user is not None  # Weak!
```

**Issues:**
- Doesn't test login actually works
- Weak assertion (not None)
- Missing: wrong password, locked account, etc.

**Improvement:**
```python
def test_user_login_with_valid_credentials_returns_authenticated_session():
    user = create_user("test@example.com", "password123")
    session = login(user.email, "password123")

    assert session.is_authenticated
    assert session.user_id == user.id
    assert session.expires_at > datetime.now()

def test_user_login_with_invalid_password_raises_authentication_error():
    user = create_user("test@example.com", "password123")

    with pytest.raises(AuthenticationError) as exc:
        login(user.email, "wrong_password")

    assert "Invalid credentials" in str(exc.value)
```

### 2. The Mock Tester
```python
# BAD: Testing mock behavior
def test_email_sending():
    mock_smtp = Mock()
    mock_smtp.send.return_value = True

    result = send_email(mock_smtp, "test@example.com", "Hello")

    assert mock_smtp.send.called  # Testing mock!
    assert result is True  # Mock's return value!
```

**Issues:**
- Tests mock behavior, not real email sending
- No verification of actual email content
- Mock configured to always succeed

**Improvement:**
```python
def test_email_sending_with_test_smtp_server():
    """Use real SMTP test server or capture actual email"""
    with captured_emails() as outbox:
        result = send_email("test@example.com", "Hello", "Test body")

        assert result.success
        assert len(outbox) == 1

        email = outbox[0]
        assert email.to == ["test@example.com"]
        assert email.subject == "Hello"
        assert "Test body" in email.body
```

### 3. The Implementation Tester
```python
# BAD: Testing implementation details
def test_user_password_storage():
    user = User("test@example.com", "password123")
    assert user._password_hash.startswith("$2b$")  # bcrypt detail
    assert len(user._password_hash) == 60
```

**Issues:**
- Tests private implementation
- Breaks if hashing algorithm changes
- Doesn't test actual password verification

**Improvement:**
```python
def test_user_password_verification_accepts_correct_password():
    user = User("test@example.com", "password123")
    assert user.verify_password("password123") is True

def test_user_password_verification_rejects_incorrect_password():
    user = User("test@example.com", "password123")
    assert user.verify_password("wrong") is False
```

### 4. The False Positiver
```python
# BAD: Test that always passes
def test_data_validation():
    validator = DataValidator()
    result = validator.validate({"name": "Test"})
    assert result  # What does this prove?
```

**Issues:**
- Passes even if validation is broken
- Doesn't verify what was validated
- No negative cases

**Improvement:**
```python
def test_data_validation_accepts_valid_data():
    validator = DataValidator()
    result = validator.validate({"name": "Test", "age": 25})

    assert result.is_valid is True
    assert result.errors == []

def test_data_validation_rejects_missing_required_field():
    validator = DataValidator()
    result = validator.validate({"age": 25})  # Missing 'name'

    assert result.is_valid is False
    assert "name" in result.errors
    assert "required" in result.errors["name"].lower()

def test_data_validation_rejects_invalid_field_type():
    validator = DataValidator()
    result = validator.validate({"name": "Test", "age": "not a number"})

    assert result.is_valid is False
    assert "age" in result.errors
```

## Inspection Workflow

### Step 1: Read the Test
```
1. What does the test name claim to test?
2. What's the docstring/description?
3. What's the setup?
4. What's the execution?
5. What's being asserted?
```

### Step 2: Verify Intent Match
```
1. Does execution match the test name?
2. Do assertions verify the claimed behavior?
3. Are edge cases covered?
4. Are error cases tested?
```

### Step 3: Check Assertion Strength
```
1. Can this assertion fail meaningfully?
2. Does it verify correctness, not just existence?
3. Would it catch regressions?
4. Is the error message helpful?
```

### Step 4: Perform Mental Debugging
```
1. Introduce a bug: would this test catch it?
2. Remove a feature: would this test fail?
3. Break a constraint: would this test notice?
4. Return wrong data: would assertions catch it?
```

### Step 5: Suggest Improvements
```
Format:
"This test claims to verify [X] but actually tests [Y].

Issues:
- Assertion is too weak: [specific issue]
- Missing test for [failure case]
- Setup is unrealistic: [specific issue]

Suggested improvements:
1. [Specific change with example]
2. [Additional test case needed]
3. [Assertion strengthening]
"
```

## Quality Metrics

### Assertion Quality Score
```
Weak:     assert x is not None
Medium:   assert len(x) > 0
Strong:   assert x == expected_value
Strongest: assert x.field == expected AND verify_invariants(x)
```

### Test Coverage vs Test Quality
```
Coverage alone is meaningless:
- 100% coverage with weak assertions = false confidence
- 80% coverage with strong tests = better protection

Quality indicators:
✓ Tests specific behaviors, not methods
✓ Assertions verify correctness
✓ Failure cases are explicit
✓ Tests would catch known bugs
```

## Integration with Other Skills

### Related Skills
- **testing-anti-patterns** - What NOT to do (avoid common pitfalls)
- **test-driven-development** - How to write tests first (prevents weak tests)
- **webapp-testing** - Specific E2E test inspection techniques
- **condition-based-waiting** - Proper async test patterns

### Workflow Integration
```
1. Engineer writes tests
2. QA inspects with this skill
3. QA suggests improvements
4. Engineer improves tests
5. QA verifies improvements
6. QA signs off
```

## Red Flags Summary

Immediately investigate if you see:

🚩 **Test names**: "test_method_name", "test_works", "test_user"
🚩 **Assertions**: "assert x", "assert result", "assert not None"
🚩 **Mocking**: Mock the system under test, mock without understanding
🚩 **Coverage**: High coverage but low confidence
🚩 **Failures**: Test passes but bug exists in production
🚩 **Messages**: Unclear what failed when test breaks
🚩 **Setup**: Test data that would never occur in reality

## Quick Reference

### Good Test Characteristics
- ✅ Clear, behavior-focused name
- ✅ Specific, meaningful assertions
- ✅ Tests real code paths
- ✅ Covers success and failure cases
- ✅ Would catch regressions
- ✅ Helpful failure messages

### Bad Test Characteristics
- ❌ Vague name ("test_user")
- ❌ Weak assertions (not None)
- ❌ Tests mock behavior
- ❌ Only happy path
- ❌ Wouldn't catch bugs
- ❌ Cryptic failures

## Example Inspection Report

```markdown
### Test: test_user_creation()

**Claimed Intent:** Test user creation
**Actual Testing:** Object instantiation only

**Issues Found:**
1. Weak assertion: `assert user is not None`
   - Would pass even if user data is corrupted
   - Doesn't verify any user properties

2. Missing validation tests:
   - No test for duplicate email
   - No test for invalid email format
   - No test for password requirements

3. No database persistence check:
   - User might not be saved
   - Test doesn't verify retrieval

**Suggested Improvements:**
1. Rename to: `test_user_creation_with_valid_data_persists_to_database`
2. Strengthen assertions:
   ```python
   assert user.email == "test@example.com"
   assert user.is_active is True
   assert user.created_at is not None

   # Verify persistence
   retrieved = User.get_by_email("test@example.com")
   assert retrieved.id == user.id
   ```
3. Add negative tests:
   - test_user_creation_with_duplicate_email_raises_error
   - test_user_creation_with_invalid_email_raises_error
   - test_user_creation_with_weak_password_raises_error

**Risk Level:** HIGH - Core functionality not actually tested
**Recommendation:** Block merge until improved
```

## Remember

> "A test that always passes is no test at all."
> "Coverage measures lines run, not correctness verified."
> "If removing the feature doesn't fail the test, the test is worthless."

Your job as QA is not to approve tests that exist, but to verify tests that protect.

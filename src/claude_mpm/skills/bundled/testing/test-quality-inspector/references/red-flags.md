# Test Quality Red Flags

## Immediate Red Flags (Block Merge)

### 🚩 Category 1: Worthless Assertions

#### Red Flag: "assert result"
```python
def test_get_user():
    result = get_user(1)
    assert result  # Passes unless None/False!
```

**Why Bad:** Passes with ANY truthy value, including garbage data.

**Impact:** Won't catch most bugs.

**Action:** Require specific value assertions.

#### Red Flag: "assert not None"
```python
def test_create_user():
    user = create_user("test@example.com")
    assert user is not None  # Only checks existence!
```

**Why Bad:** Verifies object exists, not that it's correct.

**Impact:** Corrupt data still passes.

**Action:** Verify actual properties.

### 🚩 Category 2: Testing Mocks

#### Red Flag: Mocking System Under Test
```python
def test_user_service():
    mock_service = Mock(UserService)
    mock_service.create.return_value = User()
    result = mock_service.create("test")  # Testing mock!
    assert result
```

**Why Bad:** Tests mock behavior, not real service.

**Impact:** Real service could be broken.

**Action:** Test real service with test dependencies.

#### Red Flag: Asserting on Mocks
```python
def test_send_notification():
    mock_mailer = Mock()
    send_notification(mock_mailer, "Hello")
    assert mock_mailer.send.called  # Asserting mock!
```

**Why Bad:** Mock always does what you tell it.

**Impact:** Real mailer might not work.

**Action:** Use test SMTP or capture real emails.

### 🚩 Category 3: Missing Negative Tests

#### Red Flag: Only Happy Path
```python
# Only this test exists:
def test_login_succeeds():
    result = login("user", "pass")
    assert result.success
```

**Missing:**
- Wrong password test
- Locked account test
- Non-existent user test
- Empty password test

**Impact:** Failures not caught until production.

**Action:** Require failure test for each success test.

### 🚩 Category 4: Vague Test Names

#### Red Flag: Method Names as Test Names
```python
def test_create_user():  # Too vague!
def test_login():        # What about login?
def test_validate():     # Validate what?
```

**Why Bad:** Doesn't describe expected behavior.

**Impact:** Hard to know what failed.

**Action:** Names must describe behavior:
- `test_create_user_with_valid_email_persists_to_database`
- `test_login_with_wrong_password_raises_authentication_error`

### 🚩 Category 5: False Positives

#### Red Flag: Test Passes with Broken Code
```python
def test_data_processing():
    process_data([1, 2, 3])
    assert True  # Always passes!
```

**Mental Debug:** Comment out `process_data` - test still passes!

**Why Bad:** Provides zero protection.

**Impact:** Bugs slip through.

**Action:** Remove test or fix assertions.

## Warning Red Flags (Request Changes)

### ⚠️ Missing Edge Cases

```python
def test_divide():
    assert divide(10, 2) == 5
    # Missing: divide by zero, negative numbers, floats
```

**Action:** Add boundary condition tests.

### ⚠️ Incomplete Mocks

```python
mock_db = Mock()
mock_db.query.return_value = [User()]
# Missing: error cases, empty results, timeouts
```

**Action:** Mock all realistic scenarios.

### ⚠️ Weak Error Assertions

```python
try:
    dangerous_operation()
except Exception:  # Too broad!
    pass
```

**Action:** Assert specific exception type and message.

### ⚠️ No Teardown/Cleanup

```python
def test_file_creation():
    create_file("/tmp/test.txt")
    # File left behind!
```

**Action:** Add cleanup or use fixtures.

### ⚠️ Test Interdependence

```python
def test_a():
    global state
    state = "configured"

def test_b():
    # Depends on test_a running first!
    assert state == "configured"
```

**Action:** Make tests independent.

## Red Flag Detection Checklist

### Quick Scan (30 seconds)
```
[ ] Assertions are specific (not just "assert x")
[ ] Test name describes behavior
[ ] No mocking of system under test
[ ] Negative test cases exist
[ ] Would fail if feature removed
```

### Deep Inspection (2 minutes)
```
[ ] Edge cases covered
[ ] Error messages meaningful
[ ] Setup is realistic
[ ] Teardown present
[ ] Tests are independent
[ ] Mocks are justified
[ ] All paths tested
```

## Red Flag Severity Matrix

### 🔴 CRITICAL (Block immediately)
- Testing mock behavior
- Always-passing tests
- No assertions at all
- Mocking system under test

### 🟠 HIGH (Strong recommend blocking)
- Only "assert not None"
- No negative tests
- Vague test names
- Would pass with broken code

### 🟡 MEDIUM (Request improvements)
- Missing edge cases
- Weak error handling tests
- Incomplete scenarios
- Poor test organization

### 🟢 LOW (Notes for improvement)
- Could be more descriptive
- Additional tests would help
- Minor refactoring suggestions
- Documentation improvements

## Common Patterns of Problematic Tests

### Pattern 1: The Optimist
```python
# Only tests that things work
def test_happy_path_1(): ...
def test_happy_path_2(): ...
# No sad path tests!
```

**Red Flag:** No tests for failures, errors, or edge cases.

### Pattern 2: The Mock Enthusiast
```python
# Everything is mocked
mock_service = Mock()
mock_repo = Mock()
mock_validator = Mock()
# Nothing real is tested!
```

**Red Flag:** Over-mocking hides real integration issues.

### Pattern 3: The Existence Checker
```python
# Just checks things exist
assert user
assert response
assert result is not None
```

**Red Flag:** Verifies existence, not correctness.

### Pattern 4: The False Friend
```python
# Test that can't fail
def test_always_passes():
    do_something()
    assert True  # Will never fail!
```

**Red Flag:** Gives false confidence.

### Pattern 5: The Mysterious Failure
```python
# Unhelpful when it fails
assert process_data(input) == process_data(expected)
# Which step failed? No idea!
```

**Red Flag:** Can't debug from failure message.

## Detection Techniques

### Technique 1: Mental Debugging
```
For each test, mentally:
1. Comment out core functionality
2. Would test fail?
3. If NO: Test is broken

Example:
def test_save_user():
    user = User("test")
    # save_user(user)  # Commented out
    assert user  # Still passes! RED FLAG
```

### Technique 2: Garbage Data Test
```
For each test, mentally:
1. Return garbage data
2. Would assertions catch it?
3. If NO: Assertions are weak

Example:
def test_get_user():
    user = get_user(1)  # Returns {"garbage": true}
    assert user  # Passes with garbage! RED FLAG
```

### Technique 3: Wrong Type Test
```
For each test, mentally:
1. Return wrong type
2. Would test fail?
3. If NO: Type checking missing

Example:
def test_calculate():
    result = calculate(5, 3)  # Returns "8" (string!)
    assert result  # Passes with wrong type! RED FLAG
```

### Technique 4: Empty Result Test
```
For each test, mentally:
1. Return empty/zero/None
2. Should this be valid?
3. Is there a test for it?

Example:
def test_get_users():
    users = get_all_users()  # Returns []
    assert users  # Fails! But is empty valid? UNCLEAR
```

## Automated Red Flag Checkers

### Check 1: Weak Assertion Detector
```python
# Scan test file for:
grep -r "assert result$" tests/
grep -r "assert.*is not None" tests/
grep -r "assert True" tests/
```

### Check 2: Mock Overuse Detector
```python
# Count mocks per test:
if mock_count > real_object_count:
    FLAG as "Over-mocking"
```

### Check 3: Missing Negative Test Detector
```python
# For each "test_*_succeeds":
if not exists("test_*_fails"):
    FLAG as "Missing negative test"
```

### Check 4: Vague Name Detector
```python
# Flag patterns:
- test_method_name
- test_class
- test_works
- test_user (without verb)
```

## Response Templates

### Template 1: Weak Assertions
```markdown
**Issue:** Weak Assertions

This test uses weak assertions that would pass even with broken functionality:
- Line X: `assert user` - Only checks if truthy
- Line Y: `assert result is not None` - Only checks existence

**Impact:** High - Won't catch data corruption or logic errors

**Recommendation:**
Replace with specific assertions:
```python
assert user.email == "expected@example.com"
assert user.is_active is True
assert user.role == "user"
```

**Action Required:** Block until improved
```

### Template 2: Testing Mocks
```markdown
**Issue:** Testing Mock Behavior

This test verifies mock behavior instead of real functionality:
- Line X: Mocking the system under test
- Line Y: Asserting that mock was called

**Impact:** Critical - Real code could be completely broken

**Recommendation:**
Test real objects with test dependencies:
```python
# Use test database, not mocks
with test_database():
    user = service.create_user("test@example.com")
    assert user.id is not None
```

**Action Required:** Block merge - Must be rewritten
```

### Template 3: Missing Negative Tests
```markdown
**Issue:** Missing Failure Cases

Only happy path is tested. Missing tests for:
- Invalid input
- Error conditions
- Edge cases
- Boundary conditions

**Impact:** Medium-High - Failures won't be caught

**Recommendation:**
Add negative tests:
- `test_create_user_with_invalid_email_raises_error`
- `test_create_user_with_duplicate_email_raises_error`
- `test_create_user_with_missing_password_raises_error`

**Action Required:** Request changes before merge
```

## Remember

🚩 **If you see a red flag, stop and inspect closely.**
🚨 **Multiple red flags = immediate block.**
✅ **No red flags ≠ good test (but it's a start).**
🔍 **When in doubt, perform mental debugging.**

> "A red flag ignored today is a production bug tomorrow."

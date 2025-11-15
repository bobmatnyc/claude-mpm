# Test Anti-Pattern Migration Guide

## Overview

This guide provides strategies and examples for migrating away from test anti-patterns identified in the QA review. Following this guide will improve test quality, reliability, and maintainability.

**Anti-Patterns Found:**
- 581 `sleep()` calls
- 312 `print()` statements
- 96 skipped tests
- 104 debug/fix/qa files

**Target State:**
- Zero `sleep()` calls (use event-driven synchronization)
- Zero `print()` statements (use proper assertions/logging)
- Zero untracked skips (all skips linked to tickets)
- Zero debug/fix/qa files (proper test organization)

## Migration Priority

**Phase 1: Critical (Do First)**
1. Remove `sleep()` calls - Replace with `wait_for_condition()`
2. Remove `print()` statements - Use assertions
3. Clean up untracked `@pytest.mark.skip`

**Phase 2: Cleanup**
4. Organize debug/fix/qa files into proper structure
5. Convert integration tests to unit tests where appropriate

## 1. Replacing sleep() Calls

### Problem

`sleep()` calls make tests:
- Slow (waiting fixed time even if condition met earlier)
- Flaky (timing dependent, may fail under load)
- Unreliable (no guarantee condition is actually met)

### Solution: wait_for_condition()

Use the `wait_for_condition()` helper from `tests/utils/test_helpers.py`:

#### Example 1: Basic Replacement

**❌ BEFORE:**
```python
def test_async_operation():
    """Test async operation completion."""
    service.start_operation()
    time.sleep(5)  # Wait for operation to complete
    assert service.is_complete()
```

**✅ AFTER:**
```python
from tests.utils.test_helpers import wait_for_condition

def test_async_operation():
    """Test async operation completion."""
    # Arrange
    service.start_operation()

    # Act & Assert
    assert wait_for_condition(
        lambda: service.is_complete(),
        timeout=5,
        message="Operation did not complete within 5 seconds"
    )
```

**Benefits:**
- Returns immediately when condition is met (faster)
- Clear error message on timeout
- More reliable (actively checks condition)

#### Example 2: Waiting for State Change

**❌ BEFORE:**
```python
def test_state_transition():
    service.initialize()
    time.sleep(2)
    assert service.state == "initialized"
```

**✅ AFTER:**
```python
from tests.utils.test_helpers import wait_for_value

def test_state_transition():
    """Test service transitions to initialized state."""
    # Arrange & Act
    service.initialize()

    # Assert
    assert wait_for_value(
        lambda: service.state,
        "initialized",
        timeout=2
    )
```

#### Example 3: Waiting for Events

**❌ BEFORE:**
```python
def test_event_handler():
    event_bus.publish("test.event", data)
    time.sleep(0.5)  # Wait for handler
    assert handler_was_called
```

**✅ AFTER:**
```python
from tests.utils.test_helpers import wait_for_event

def test_event_handler():
    """Test event handler is called."""
    # Arrange
    handler_called = False

    def handler(data):
        nonlocal handler_called
        handler_called = True

    event_bus.on("test.event", handler)

    # Act
    event_bus.publish("test.event", data)

    # Assert
    assert wait_for_event(
        lambda: handler_called,
        timeout=1,
        event_name="test.event"
    )
```

#### Example 4: Async Operations

**❌ BEFORE:**
```python
@pytest.mark.asyncio
async def test_async_operation():
    await service.start()
    await asyncio.sleep(3)
    assert await service.is_ready()
```

**✅ AFTER:**
```python
from tests.utils.test_helpers import wait_for_condition_async

@pytest.mark.asyncio
async def test_async_operation():
    """Test service becomes ready after start."""
    # Arrange & Act
    await service.start()

    # Assert
    assert await wait_for_condition_async(
        lambda: service.is_ready(),
        timeout=3
    )
```

### Migration Script for sleep()

To find all `sleep()` calls:

```bash
# Find all sleep calls in tests
grep -rn "time\.sleep\|sleep(" tests/ | grep -v "test_helpers"

# Count sleep calls
grep -r "time\.sleep\|sleep(" tests/ | grep -v "test_helpers" | wc -l
```

To replace systematically:

1. **Identify the pattern**: What are you waiting for?
2. **Create predicate**: Function that returns True when ready
3. **Replace sleep**: Use appropriate `wait_for_*` helper
4. **Test**: Verify test still passes and is faster

## 2. Removing print() Statements

### Problem

`print()` statements:
- Clutter test output
- Aren't checked or validated
- Don't fail tests when expectations aren't met
- Make it hard to diagnose failures

### Solution: Proper Assertions

#### Example 1: Debugging Values

**❌ BEFORE:**
```python
def test_calculation():
    result = calculate(5, 10)
    print(f"Result: {result}")  # Debugging
    print(f"Expected: 15")
    assert result == 15
```

**✅ AFTER:**
```python
def test_calculation():
    """Test calculation returns correct result."""
    # Arrange
    input_a, input_b = 5, 10

    # Act
    result = calculate(input_a, input_b)

    # Assert
    assert result == 15  # pytest shows actual value on failure
```

**Note:** pytest automatically shows the value on assertion failure:
```
AssertionError: assert 14 == 15
```

#### Example 2: Debugging Complex Objects

**❌ BEFORE:**
```python
def test_api_response():
    response = api.fetch_data()
    print(f"Response: {response}")
    print(f"Status: {response['status']}")
    assert response['status'] == 'success'
```

**✅ AFTER:**
```python
from tests.utils.test_helpers import assert_dict_contains

def test_api_response():
    """Test API returns successful response."""
    # Arrange & Act
    response = api.fetch_data()

    # Assert
    assert_dict_contains(response, {
        'status': 'success',
        # Add other expected fields
    })
```

#### Example 3: Progress Logging

**❌ BEFORE:**
```python
def test_multi_step_process():
    print("Starting process...")
    service.initialize()
    print("Initialized")

    print("Processing data...")
    result = service.process()
    print(f"Processed: {result}")

    assert result is not None
```

**✅ AFTER:**
```python
def test_multi_step_process():
    """Test multi-step process completes successfully."""
    # Arrange
    service.initialize()
    assert service.is_initialized()  # Verify step 1

    # Act
    result = service.process()

    # Assert
    assert result is not None  # Verify step 2
    assert result.status == "complete"
```

**Note:** Each step has its own assertion, making failures clear.

#### When Logging is Needed

If you genuinely need logging for debugging:

```python
import logging
logger = logging.getLogger(__name__)

def test_with_debugging():
    """Test with debug logging."""
    # Arrange
    data = prepare_complex_data()
    logger.debug(f"Prepared data: {data}")  # ✅ OK for debugging

    # Act
    result = process(data)

    # Assert
    assert result is not None
```

Run tests with logging:
```bash
pytest -v --log-cli-level=DEBUG
```

### Migration Script for print()

To find all `print()` calls:

```bash
# Find all print calls in tests
grep -rn "print(" tests/

# Count print calls
grep -r "print(" tests/ | wc -l
```

To replace:

1. **Understand intent**: Why was print() added?
2. **Replace with assertion**: Validate the value instead
3. **Use logging if needed**: For genuine debugging
4. **Test**: Verify test still provides clear failure messages

## 3. Cleaning Up Skipped Tests

### Problem

Untracked `@pytest.mark.skip` decorators:
- Hide test failures
- Accumulate technical debt
- Provide no context for why skipped

### Solution: Track or Fix

#### Pattern 1: Link to Ticket

**❌ BEFORE:**
```python
@pytest.mark.skip(reason="Fix later")  # ❌ Untracked
def test_important_feature():
    pass
```

**✅ AFTER:**
```python
@pytest.mark.skip(reason="Blocked by #1234 - API not implemented")  # ✅ Tracked
def test_important_feature():
    pass
```

#### Pattern 2: Use skipif for Conditional Skips

**✅ GOOD:**
```python
@pytest.mark.skipif(
    not has_gpu_support(),
    reason="GPU tests require CUDA support"
)
def test_gpu_acceleration():
    pass
```

#### Pattern 3: Fix and Remove Skip

**Best Option:** Fix the test and remove the skip decorator entirely.

```python
# Before: Skipped test
@pytest.mark.skip(reason="Flaky timing issue")
def test_operation():
    service.start()
    time.sleep(5)  # Flaky
    assert service.is_ready()

# After: Fixed test
def test_operation():
    """Test service becomes ready after start."""
    service.start()
    assert wait_for_condition(
        lambda: service.is_ready(),
        timeout=5
    )
```

### Migration Process for Skips

```bash
# Find all skipped tests
grep -rn "@pytest.mark.skip" tests/

# Find skips without tickets
grep -rn "@pytest.mark.skip" tests/ | grep -v "#[0-9]"
```

For each skip:

1. **Create ticket**: Document why test is skipped
2. **Update reason**: Link to ticket number
3. **Or fix**: Remove skip if possible
4. **Track**: Add to backlog for future fixing

## 4. Organizing Debug/Fix/QA Files

### Problem

Files like `test_fix_something.py`, `test_debug_issue.py`, `test_qa_123.py`:
- Indicate reactive testing
- Poor organization
- Unclear purpose
- Accumulate as technical debt

### Solution: Proper Organization

#### Pattern 1: Move to Proper Location

**❌ BEFORE:**
```
tests/
├── test_fix_auth_bug.py         # ❌ Reactive name
├── test_debug_session.py        # ❌ Debug file
├── test_qa_regression_5.py      # ❌ QA file
```

**✅ AFTER:**
```
tests/
├── unit/
│   └── services/
│       └── auth/
│           └── test_authentication.py  # ✅ Proper organization
├── integration/
│   └── test_session_management.py     # ✅ Clear purpose
├── regression/
│   └── test_issue_1234.py             # ✅ Linked to ticket
```

#### Pattern 2: Merge into Existing Test Files

If test covers same component, merge into existing test file:

```python
# test_authentication.py

class TestAuthentication:
    """Tests for authentication service."""

    def test_login_success(self):
        """Test successful login."""
        pass

    def test_login_failure(self):
        """Test login with invalid credentials."""
        pass

    # Add the "fix" test here
    def test_token_expiration_handling(self):
        """Test handles expired tokens correctly.

        Regression test for #1234 - Token expiration not handled.
        """
        # Test implementation
        pass
```

#### Pattern 3: Create Regression Test Suite

For QA/regression tests:

```python
# tests/regression/test_issue_1234.py

"""Regression tests for Issue #1234: Token expiration handling.

WHY: Users were experiencing session timeouts without clear errors.
FIX: Added proper token expiration checks and user messaging.
"""

def test_expired_token_returns_401():
    """Test expired token returns 401 status."""
    pass

def test_expired_token_clears_session():
    """Test expired token clears user session."""
    pass

def test_expired_token_shows_message():
    """Test expired token displays clear message to user."""
    pass
```

### Migration Process

```bash
# Find debug/fix/qa files
find tests/ -name "*debug*" -o -name "*fix*" -o -name "*qa*"
```

For each file:

1. **Understand purpose**: What was being tested?
2. **Find proper location**: Where does it belong?
3. **Merge or move**: Integrate with existing tests or create proper regression suite
4. **Update naming**: Use descriptive, component-based names
5. **Document**: Add docstrings explaining why test exists

## 5. Converting Integration to Unit Tests

### When to Convert

Convert integration tests to unit tests when:
- Test focuses on single component behavior
- External dependencies can be mocked
- Test is slow due to real I/O
- Test is flaky due to external factors

### Example Conversion

**❌ BEFORE (Integration Test):**
```python
# tests/integration/test_user_service.py

def test_create_user():
    """Test creating user in database."""
    # Uses real database connection
    db = Database(connection_string=TEST_DB)
    service = UserService(db)

    user = service.create_user("test@example.com", "password")

    # Query real database
    saved_user = db.query("SELECT * FROM users WHERE email = ?", user.email)
    assert saved_user is not None
    assert saved_user.email == "test@example.com"
```

**✅ AFTER (Unit Test):**
```python
# tests/unit/services/test_user_service.py

def test_create_user():
    """Test UserService.create_user calls database correctly."""
    # Arrange
    mock_db = Mock(spec=Database)
    mock_db.insert.return_value = User(id=1, email="test@example.com")
    service = UserService(mock_db)

    # Act
    user = service.create_user("test@example.com", "password")

    # Assert
    assert user.email == "test@example.com"
    mock_db.insert.assert_called_once()
```

**Benefits:**
- Faster (no real database)
- More reliable (no external dependency)
- Better isolation (tests exact behavior)
- Still test business logic

Keep integration test for end-to-end verification:

```python
# tests/integration/test_user_workflow.py

@pytest.mark.integration
def test_user_registration_workflow():
    """Test complete user registration workflow."""
    # This integration test verifies end-to-end flow
    # Keep it, but unit tests cover individual components
    pass
```

## Progress Tracking

### Measuring Improvement

Track anti-pattern metrics:

```bash
# Sleep calls
echo "Sleep calls: $(grep -r 'time\.sleep\|sleep(' tests/ | grep -v test_helpers | wc -l)"

# Print statements
echo "Print statements: $(grep -r 'print(' tests/ | wc -l)"

# Untracked skips
echo "Untracked skips: $(grep -r '@pytest.mark.skip' tests/ | grep -v '#[0-9]' | wc -l)"

# Debug/fix/qa files
echo "Debug files: $(find tests/ -name '*debug*' -o -name '*fix*' -o -name '*qa*' | wc -l)"
```

### Quality Targets

| Metric | Current | Target |
|--------|---------|--------|
| sleep() calls | 581 | 0 |
| print() statements | 312 | 0 |
| Untracked skips | 96 | 0 |
| Debug/fix/qa files | 104 | 0 |
| Unit test % | 0.03% | 60% |
| Test Quality Score | 42/100 | 80/100 |

## Migration Workflow

### Step-by-Step Process

1. **Audit**: Run metrics to establish baseline
2. **Prioritize**: Start with highest-impact areas
3. **Migrate**: Use patterns from this guide
4. **Test**: Verify tests pass and are faster
5. **Measure**: Track improvement
6. **Repeat**: Continue until targets met

### Example Sprint Plan

**Sprint 1: Foundation**
- Create test helpers (wait_for_condition, etc.)
- Document standards
- Create templates

**Sprint 2: Critical Cleanup**
- Replace top 50 sleep() calls
- Remove top 50 print() statements
- Link all skips to tickets

**Sprint 3: Systematic Cleanup**
- Replace remaining sleep() calls
- Remove remaining print() statements
- Organize debug/fix/qa files

**Sprint 4: Quality Improvement**
- Convert integration tests to unit tests
- Increase unit test coverage
- Improve test organization

## Resources

- **Test Helpers**: `tests/utils/test_helpers.py`
- **Testing Standards**: `tests/TESTING_STANDARDS.md`
- **Unit Test Template**: `tests/templates/unit_test_template.py`
- **Gold Standard**: `tests/unit/services/cli/test_session_resume_helper.py`

## Getting Help

When migrating tests:

1. **Review gold standard example** for patterns
2. **Use test helpers** instead of reinventing
3. **Follow AAA pattern** (Arrange-Act-Assert)
4. **Ask for review** on complex migrations
5. **Document decisions** in test docstrings

---

*Last Updated: 2025-01-15*
*Version: 1.0.0*

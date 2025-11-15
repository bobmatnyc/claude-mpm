# Testing Standards for Claude MPM

## Overview

This document defines the testing standards and quality requirements for the Claude MPM project. Following these standards ensures maintainable, reliable, and high-quality test coverage.

## Test Quality Metrics

**Current Baseline (2025-01-15):**
- Test Quality Score: 42/100 (POOR)
- Unit Tests: 0.03% (2 out of 5,725 test functions)
- Integration Tests: 99.97%

**Target Quality Metrics:**
- Test Quality Score: ≥ 80/100
- Unit Tests: ≥ 60%
- Integration Tests: ≤ 30%
- E2E Tests: ≤ 10%
- Test Coverage: ≥ 85%

## Test Pyramid

We follow the standard test pyramid to ensure fast, reliable, and maintainable tests:

```
        ╱╲
       ╱E2E╲          10% - End-to-End (Full system, UI/CLI)
      ╱─────╲
     ╱  INT  ╲        30% - Integration (Multi-component)
    ╱─────────╲
   ╱   UNIT    ╲      60% - Unit (Single component, fast)
  ╱─────────────╲
```

### Test Type Distribution

**Unit Tests (60%):**
- Test single functions/methods in isolation
- Use mocks for all external dependencies
- Fast execution (< 100ms per test)
- No I/O, network, or filesystem operations
- Located in: `tests/unit/`

**Integration Tests (30%):**
- Test interactions between 2-3 components
- May use real dependencies (controlled)
- Moderate execution time (< 1 second per test)
- Located in: `tests/integration/`

**End-to-End Tests (10%):**
- Test complete workflows
- Use real environment when possible
- Slower execution acceptable (< 10 seconds per test)
- Located in: `tests/e2e/`

## Test Structure: AAA Pattern

All tests MUST follow the **Arrange-Act-Assert (AAA)** pattern:

```python
def test_example():
    """Test should have descriptive docstring explaining what it validates."""
    # Arrange: Set up test data and mocks
    user = User(name="Test User", email="test@example.com")
    mock_db = Mock()

    # Act: Execute the function under test
    result = save_user(user, mock_db)

    # Assert: Verify expected behavior
    assert result is True
    mock_db.save.assert_called_once_with(user)
```

### Arrange Section
- Create test data
- Set up mocks and fixtures
- Configure system state
- Keep setup minimal and focused

### Act Section
- Execute ONE operation being tested
- Should be a single line or very few lines
- Clearly identifiable as the test action

### Assert Section
- Verify expected outcomes
- Check return values, state changes, side effects
- Use descriptive assertion messages when helpful
- Multiple related assertions are acceptable

## Test Organization

### File Structure

```
tests/
├── unit/                      # Unit tests (60% of tests)
│   ├── services/
│   │   ├── model/
│   │   │   ├── test_claude_provider.py
│   │   │   └── test_model_router.py
│   │   ├── event_bus/
│   │   │   └── test_event_bus.py
│   │   └── cli/
│   │       └── test_session_resume_helper.py  # GOLD STANDARD
│   └── ...
├── integration/               # Integration tests (30% of tests)
│   ├── test_agent_workflow.py
│   └── ...
├── e2e/                       # End-to-end tests (10% of tests)
│   └── test_full_workflow.py
├── fixtures/                  # Shared test fixtures
│   └── common_fixtures.py
├── utils/                     # Test utilities
│   └── test_helpers.py
├── templates/                 # Test templates
│   └── unit_test_template.py
├── TESTING_STANDARDS.md       # This file
└── MIGRATION_GUIDE.md         # Anti-pattern cleanup guide
```

### Class Organization

Group related tests into classes:

```python
class TestInitialization:
    """Tests for component initialization."""

    def test_init_with_defaults(self):
        """Test initialization with default values."""
        pass

    def test_init_with_custom_config(self):
        """Test initialization with custom configuration."""
        pass


class TestCoreFeature:
    """Tests for core feature functionality."""

    def test_success_case(self):
        """Test successful operation."""
        pass

    def test_error_handling(self):
        """Test error handling."""
        pass
```

## Naming Conventions

### Test File Names
- Pattern: `test_<module_name>.py`
- Examples: `test_claude_provider.py`, `test_event_bus.py`

### Test Function Names
- Pattern: `test_<what>_<when>_<expected>`
- Be descriptive and specific
- Use underscores for readability

**Good Examples:**
```python
def test_returns_true_when_sessions_exist(self):
    """Test returns True when session files exist."""

def test_handles_corrupted_json_gracefully(self):
    """Test handles corrupted JSON gracefully."""

def test_formats_single_day_correctly(self):
    """Test formats single day correctly."""
```

**Bad Examples:**
```python
def test_session(self):  # Too vague
def test_1(self):  # Meaningless
def testSessionExists(self):  # Wrong naming style
```

### Test Class Names
- Pattern: `Test<Feature>` or `Test<Component><Feature>`
- Examples: `TestInitialization`, `TestHasPausedSessions`, `TestEdgeCases`

## Docstrings

Every test MUST have a docstring explaining what it validates:

```python
def test_handles_empty_list_gracefully(self):
    """Test handles empty list without raising exceptions."""
    # Arrange
    empty_list = []

    # Act
    result = process_items(empty_list)

    # Assert
    assert result == []
```

## Fixtures

### Use pytest Fixtures for Setup

```python
@pytest.fixture
def sample_user():
    """Sample user for testing."""
    return User(
        name="Test User",
        email="test@example.com",
        role="user"
    )


@pytest.fixture
def mock_database():
    """Mock database connection."""
    db = Mock(spec=Database)
    db.connect.return_value = True
    return db


def test_save_user(sample_user, mock_database):
    """Test saving user to database."""
    # Arrange
    service = UserService(mock_database)

    # Act
    result = service.save(sample_user)

    # Assert
    assert result is True
    mock_database.save.assert_called_once()
```

### Fixture Scope

- **function** (default): New instance per test
- **class**: Shared across test class
- **module**: Shared across test file
- **session**: Shared across entire test run

Use appropriate scope to balance performance and isolation.

## Mocking Standards

### When to Mock

**Always Mock:**
- External APIs and network calls
- Database connections
- File system operations
- Time-dependent functions
- Random number generators
- External services

**Never Mock:**
- The code under test
- Simple data structures
- Pure functions without side effects

### Mock Best Practices

```python
from unittest.mock import Mock, patch, MagicMock

def test_with_proper_mocking(self):
    """Test demonstrates proper mocking patterns."""
    # Arrange
    mock_api = Mock()
    mock_api.fetch_data.return_value = {"status": "success"}

    # Use spec to catch typos
    mock_db = Mock(spec=Database)
    mock_db.query.return_value = [1, 2, 3]

    # Act
    result = process_api_data(mock_api, mock_db)

    # Assert
    assert result is not None
    mock_api.fetch_data.assert_called_once()
    mock_db.query.assert_called_with(ANY)
```

### Patching

```python
@patch('module.external_service')
def test_with_patch(self, mock_service):
    """Test using patch decorator."""
    # Arrange
    mock_service.return_value.get_status.return_value = "active"

    # Act
    result = check_service_status()

    # Assert
    assert result == "active"
```

## Forbidden Anti-Patterns

### ❌ NO sleep() calls

**Bad:**
```python
def test_async_operation():
    start_operation()
    time.sleep(5)  # ❌ FORBIDDEN
    assert operation_complete()
```

**Good:**
```python
def test_async_operation():
    start_operation()
    # Use wait_for_condition helper
    assert wait_for_condition(
        lambda: operation_complete(),
        timeout=5,
        message="Operation did not complete"
    )
```

### ❌ NO print() statements

**Bad:**
```python
def test_calculation():
    result = calculate(5, 10)
    print(f"Result: {result}")  # ❌ FORBIDDEN
    assert result == 15
```

**Good:**
```python
def test_calculation():
    result = calculate(5, 10)
    assert result == 15  # Failures show result automatically
```

Use logging if debugging is needed:
```python
import logging
logger = logging.getLogger(__name__)

def test_with_logging():
    result = complex_calculation()
    logger.debug(f"Intermediate result: {result}")  # ✅ OK for debugging
    assert result > 0
```

### ❌ NO skipped tests without tickets

**Bad:**
```python
@pytest.mark.skip(reason="Fix later")  # ❌ FORBIDDEN
def test_important_feature():
    pass
```

**Good:**
```python
@pytest.mark.skip(reason="Blocked by #1234 - API not ready")  # ✅ OK with ticket
def test_api_integration():
    pass
```

### ❌ NO try/except in tests

**Bad:**
```python
def test_parsing():
    try:
        result = parse_data(input_data)
        assert result is not None  # ❌ Hides failures
    except Exception:
        pytest.fail("Should not raise exception")
```

**Good:**
```python
def test_parsing_success():
    """Test successful parsing."""
    result = parse_data(valid_input)
    assert result is not None

def test_parsing_invalid_input():
    """Test parsing raises ValueError for invalid input."""
    with pytest.raises(ValueError, match="Invalid format"):
        parse_data(invalid_input)
```

## Edge Cases and Error Handling

Every component should test:

1. **Happy Path**: Normal, expected usage
2. **Edge Cases**: Boundary conditions, empty inputs, large inputs
3. **Error Cases**: Invalid inputs, missing data, exceptions
4. **State Transitions**: Different initial states

```python
class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_empty_input(self):
        """Test handles empty input."""
        assert process([]) == []

    def test_single_item(self):
        """Test handles single item."""
        assert process([1]) == [1]

    def test_large_input(self):
        """Test handles large input efficiently."""
        large_list = list(range(10000))
        result = process(large_list)
        assert len(result) == 10000

    def test_invalid_type_raises_error(self):
        """Test raises TypeError for invalid input type."""
        with pytest.raises(TypeError):
            process("not a list")
```

## Coverage Requirements

### Minimum Coverage
- **Overall**: 85%
- **New Code**: 90%
- **Critical Paths**: 100%

### Coverage Commands

```bash
# Run tests with coverage
pytest --cov=src/claude_mpm --cov-report=html --cov-report=term

# View coverage report
open htmlcov/index.html

# Fail if coverage below threshold
pytest --cov=src/claude_mpm --cov-fail-under=85
```

### Coverage Exemptions

Use `# pragma: no cover` sparingly for:
- Defensive code that can't be tested
- Platform-specific code
- Debug code

```python
def debug_only_function():  # pragma: no cover
    """Only runs in debug mode, skip coverage."""
    if DEBUG:
        print("Debug info")
```

## Test Performance

### Performance Targets

- **Unit Test**: < 100ms
- **Integration Test**: < 1s
- **E2E Test**: < 10s
- **Full Suite**: < 5 minutes

### Performance Anti-Patterns

❌ Avoid:
- Sleeping instead of waiting for conditions
- Unnecessary database queries in unit tests
- Loading large files in every test
- Not using fixtures for expensive setup

✅ Prefer:
- Event-driven synchronization
- Mocking external resources
- Lazy loading and caching
- Fixture scoping

## Gold Standard Example

See `/tests/unit/services/cli/test_session_resume_helper.py` for a complete example demonstrating:

- ✅ AAA pattern throughout
- ✅ Comprehensive docstrings
- ✅ Proper class organization
- ✅ Edge case coverage
- ✅ Error handling tests
- ✅ Integration scenarios
- ✅ Proper mocking
- ✅ Clear naming
- ✅ No anti-patterns

## Quality Checklist

Before committing tests, verify:

- [ ] Follows AAA pattern
- [ ] Has descriptive docstring
- [ ] Uses proper fixtures
- [ ] Mocks external dependencies
- [ ] Tests happy path
- [ ] Tests edge cases
- [ ] Tests error handling
- [ ] No `sleep()` calls
- [ ] No `print()` statements
- [ ] No untracked skips
- [ ] Runs in < 100ms (unit) or < 1s (integration)
- [ ] Contributes to coverage target
- [ ] Follows naming conventions
- [ ] Organized in appropriate class

## Continuous Improvement

### Quality Metrics Tracking

Run quality analysis regularly:

```bash
# Generate test quality report
pytest --collect-only | grep "test_" | wc -l  # Count tests

# Check for anti-patterns
grep -r "time.sleep" tests/  # Find sleep calls
grep -r "print(" tests/  # Find print statements
grep -r "@pytest.mark.skip" tests/  # Find skipped tests

# Coverage trends
pytest --cov=src --cov-report=json
# Track coverage.json over time
```

### Refactoring Guidance

When test quality score is below target:

1. **Identify**: Run analysis to find anti-patterns
2. **Plan**: Create refactoring tasks
3. **Execute**: Fix highest-impact issues first
4. **Verify**: Run quality checks again
5. **Track**: Monitor metrics over time

## Migration from Legacy Tests

See `MIGRATION_GUIDE.md` for:
- Sleep replacement strategies
- Print statement removal
- Skip cleanup process
- Integration to unit conversion

## Resources

- [pytest Documentation](https://docs.pytest.org/)
- [unittest.mock Guide](https://docs.python.org/3/library/unittest.mock.html)
- [Test Pyramid Pattern](https://martinfowler.com/articles/practical-test-pyramid.html)
- Gold Standard: `tests/unit/services/cli/test_session_resume_helper.py`

---

*Last Updated: 2025-01-15*
*Version: 1.0.0*

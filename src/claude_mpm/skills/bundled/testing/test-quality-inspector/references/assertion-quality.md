# Assertion Quality Guide

## Assertion Strength Spectrum

### Level 1: Worthless (Don't use)
```python
assert result              # Always passes unless None/False
assert x                   # Meaningless
assert True                # Always passes
```

**Problem:** These pass even when functionality is completely broken.

### Level 2: Existence Only (Very weak)
```python
assert result is not None
assert len(items) > 0
assert user
```

**Problem:** Verifies something exists, not that it's correct.

**When acceptable:** As a precondition before stronger assertions.

### Level 3: Type Checking (Weak)
```python
assert isinstance(result, dict)
assert type(user) == User
```

**Problem:** Right type, but could be garbage data.

**When acceptable:** Combined with value assertions.

### Level 4: Property Existence (Moderate)
```python
assert 'email' in user
assert hasattr(response, 'status_code')
```

**Problem:** Property exists but could have wrong value.

**When acceptable:** When structure matters more than values.

### Level 5: Value Verification (Strong)
```python
assert user.email == "test@example.com"
assert response.status_code == 200
assert len(items) == 5
```

**Good:** Verifies specific correctness.

**Still missing:** Failure cases, edge conditions.

### Level 6: Complete Verification (Strongest)
```python
# Success case
assert user.email == "test@example.com"
assert user.is_active is True
assert user.created_at <= datetime.now()

# Failure case
with pytest.raises(ValidationError) as exc:
    create_user("invalid-email")
assert "Invalid email format" in str(exc.value)

# Side effects
assert User.count() == initial_count + 1
```

**Best:** Verifies correctness AND failure modes AND side effects.

## Assertion Patterns

### Pattern 1: Value Assertions

#### Bad: Existence Only
```python
def test_user_creation():
    user = create_user("test@example.com", "password")
    assert user  # Weak!
```

#### Good: Specific Values
```python
def test_user_creation_sets_correct_attributes():
    user = create_user("test@example.com", "password123")

    assert user.email == "test@example.com"
    assert user.is_active is True
    assert user.role == "user"
    assert user.created_at is not None
```

### Pattern 2: Collection Assertions

#### Bad: Count Only
```python
def test_get_users():
    users = get_all_users()
    assert len(users) > 0  # Weak!
```

#### Good: Content Verification
```python
def test_get_users_returns_all_active_users():
    create_user("user1@example.com")
    create_user("user2@example.com")
    create_inactive_user("inactive@example.com")

    users = get_all_users()

    assert len(users) == 2
    emails = [u.email for u in users]
    assert "user1@example.com" in emails
    assert "user2@example.com" in emails
    assert "inactive@example.com" not in emails
```

### Pattern 3: Error Assertions

#### Bad: Generic Exception
```python
def test_invalid_input():
    try:
        process_data(None)
        assert False, "Should have raised"
    except Exception:
        pass  # Too generic!
```

#### Good: Specific Error with Message
```python
def test_process_data_with_none_raises_validation_error():
    with pytest.raises(ValidationError) as exc:
        process_data(None)

    assert "Data cannot be None" in str(exc.value)
    assert exc.value.field == "data"
```

### Pattern 4: State Change Assertions

#### Bad: No Before/After Check
```python
def test_update_user():
    user = get_user(1)
    update_user(1, email="new@example.com")
    # No verification of actual change!
```

#### Good: Verify State Transition
```python
def test_update_user_email_changes_email_field():
    user = create_user("old@example.com")
    original_email = user.email

    update_user(user.id, email="new@example.com")
    updated_user = get_user(user.id)

    assert updated_user.email == "new@example.com"
    assert updated_user.email != original_email
    assert updated_user.id == user.id  # Same user
```

### Pattern 5: API Response Assertions

#### Bad: Status Code Only
```python
def test_api_endpoint():
    response = client.get("/api/users")
    assert response.status_code == 200  # Weak!
```

#### Good: Complete Response Verification
```python
def test_get_users_endpoint_returns_user_list():
    create_user("test1@example.com")
    create_user("test2@example.com")

    response = client.get("/api/users")

    assert response.status_code == 200
    assert response.headers["Content-Type"] == "application/json"

    data = response.json()
    assert "users" in data
    assert len(data["users"]) == 2
    assert data["users"][0]["email"] == "test1@example.com"
```

## Assertion Anti-Patterns

### Anti-Pattern 1: Testing Mock Behavior
```python
# BAD
def test_send_email():
    mock_mailer = Mock()
    send_email(mock_mailer, "test@example.com", "Hello")
    assert mock_mailer.send.called  # Testing mock!
```

**Fix:** Test real behavior or use test doubles that verify contracts.

### Anti-Pattern 2: Asserting Implementation Details
```python
# BAD
def test_password_hashing():
    user = User("test", "password")
    assert user._hash_algorithm == "bcrypt"  # Implementation detail!
```

**Fix:** Test behavior (password verification works) not implementation.

### Anti-Pattern 3: Multiple Concepts in One Assert
```python
# BAD
def test_user_and_profile():
    result = create_user_with_profile(...)
    assert result.user and result.profile  # Too vague!
```

**Fix:** Separate assertions for each concept.

### Anti-Pattern 4: Overly Lenient Assertions
```python
# BAD
def test_calculate_total():
    total = calculate_total([1, 2, 3])
    assert total > 0  # Way too lenient!
```

**Fix:** Assert exact expected value.

## Assertion Best Practices

### 1. One Concept Per Assertion
```python
# Good: Clear what's being verified
assert user.email == expected_email
assert user.is_active is True
assert user.created_at is not None
```

### 2. Meaningful Failure Messages
```python
# Good: Helpful when test fails
assert user.age >= 18, f"User age {user.age} is below minimum 18"
```

### 3. Assert Actual vs Expected
```python
# Good: Clear which is which
assert actual == expected  # Convention: actual first
```

### 4. Test Both Paths
```python
# Good: Success and failure
def test_valid_login_succeeds():
    assert login("user", "pass").success is True

def test_invalid_login_fails():
    assert login("user", "wrong").success is False
```

### 5. Verify Side Effects
```python
# Good: Check state changes
def test_delete_user_removes_from_database():
    user = create_user("test@example.com")
    initial_count = User.count()

    delete_user(user.id)

    assert User.count() == initial_count - 1
    assert User.get(user.id) is None
```

## Assertion Checklist

For each assertion, ask:

- [ ] **Specificity**: Is this assertion specific enough?
- [ ] **Meaningfulness**: Would this fail if functionality breaks?
- [ ] **Completeness**: Are all aspects verified?
- [ ] **Clarity**: Is it obvious what's being tested?
- [ ] **Failure Messages**: Will I know why it failed?

## Quick Reference

### Strong Assertions ✅
```python
assert actual == expected_value
assert result.field == specific_value
assert len(collection) == expected_count
assert "expected text" in result.message
with pytest.raises(SpecificError):
    dangerous_operation()
```

### Weak Assertions ❌
```python
assert result
assert result is not None
assert len(collection) > 0
assert True
assert mock.called
```

## Remember

> "An assertion that would pass with broken code is not an assertion."
> "Weak assertions create false confidence."
> "Test behavior, not implementation."
> "Verify correctness, not just existence."

# Mock Hygiene

When does mocking help, and when does it hollow out a test?

## The Core Principle

Mocks exist to isolate the code under test from external systems (network, database, file system, time). They should never replace the code under test itself or its core logic.

**Good mocking:** Replace the thing that makes testing hard.
**Bad mocking:** Replace the thing you're supposed to be testing.

---

## What Should Be Mocked

### External I/O (Always appropriate)

- HTTP clients / API calls
- Database connections and queries
- File system reads and writes
- Time (`datetime.now()`, `Date.now()`)
- Random number generators
- Email / SMS / notification senders
- Message queue producers and consumers

### Expensive or non-deterministic computations

- ML model inference
- Cryptographic key generation
- External rate-limited services

### Other service boundaries (unit test context)

- Other microservices
- Third-party SDKs
- Browser APIs in server tests

---

## What Should NOT Be Mocked

### The function under test

```python
# BROKEN: You are testing the mock, not the function
with patch('mymodule.calculate_discount') as mock:
    mock.return_value = 0.1
    result = calculate_discount(order)
    assert result == 0.1
```

This test proves nothing. Remove it or rewrite it to test real logic.

### Core business logic called by the function under test

```javascript
// BROKEN: discountService contains the logic being tested
const mockDiscountService = {
  apply: jest.fn().mockReturnValue(90.00)
};

test('should apply discount to order total', () => {
  const result = applyOrderDiscount(order, mockDiscountService);
  expect(result.total).toBe(90.00);
});
```

If `applyOrderDiscount` is just `(order, service) => service.apply(order)`, then mocking `service.apply` means no logic is tested.

### Data transformations that are the point of the test

```python
# BROKEN: The serialization IS what we're testing
with patch('mymodule.serialize_user') as mock_serialize:
    mock_serialize.return_value = {'id': 1, 'name': 'Alice'}
    result = format_user_response(user)
    assert result == {'id': 1, 'name': 'Alice'}
```

---

## Signs a Mock is Hollowing Out a Test

### Sign 1: The assertion matches the mock return value exactly

```javascript
mockDb.getUser.mockReturnValue({ id: 1, name: 'Alice', role: 'admin' });

// Assertion just echoes the mock
expect(result).toEqual({ id: 1, name: 'Alice', role: 'admin' });
```

If you change the mock return value and the assertion breaks — but the production code didn't change — the test is just verifying the mock configuration.

### Sign 2: No real code runs between the mock setup and the assertion

Count the lines between `mock.returnValue(X)` and `expect(result).toBe(Y)`. If there are only 1-2 lines and neither calls real application logic, the test is empty.

### Sign 3: The mock depth is greater than 1

```python
# Suspicious: mocking a method on a mock
mock_repo = Mock()
mock_repo.find_by_id.return_value = Mock(email="a@b.com", is_active=True)
```

Deeply nested mocks often indicate that the test has lost contact with the actual code path.

### Sign 4: Mocking something that doesn't have I/O

```go
mockCalculator := &MockCalculator{}
mockCalculator.On("Add", 3, 4).Return(7)
result := processNumbers(mockCalculator, 3, 4)
assert.Equal(t, 7, result)
```

If `Calculator.Add` is a pure function with no I/O, why mock it? The test proves nothing about `processNumbers`.

---

## Mock Depth Decision Tree

```
Is this component doing I/O (network, disk, time, randomness)?
  YES → Mock is appropriate
  NO  →
    Is this component a third-party library I don't own?
      YES → Mock is appropriate (unit test scope)
      NO  →
        Is this component the function I'm testing?
          YES → Do NOT mock it. You're testing nothing.
          NO  →
            Does this component contain the logic I'm verifying?
              YES → Do NOT mock it. You're testing the mock.
              NO  → Mock is acceptable if isolation is needed.
```

---

## Appropriate vs. Hollow Mock Examples

### Appropriate: I/O isolation

```python
# Testing email validation logic; mocking the SMTP sender
def test_send_welcome_email_to_valid_address():
    with patch('myapp.email.smtp_client.send') as mock_send:
        send_welcome_email("alice@example.com", "Alice")
        mock_send.assert_called_once_with(
            to="alice@example.com",
            subject="Welcome, Alice!",
            body=ANY
        )
```
Real: Email composition logic. Mocked: SMTP network call.

### Hollow: Logic replaced

```python
# Testing email validation; but the validation itself is mocked
def test_validates_email_format():
    with patch('myapp.email.validate_email_format') as mock_validate:
        mock_validate.return_value = True
        result = send_welcome_email("not-an-email", "Alice")
        assert result.success is True
```
The test can never fail because the validation that should catch bad emails is bypassed.

### Appropriate: Service boundary in unit test

```javascript
// Unit test for OrderProcessor; UserService is a separate service
const mockUserService = {
  getUser: jest.fn().mockResolvedValue({ id: 1, creditLimit: 500 })
};

test('should reject order if total exceeds credit limit', async () => {
  const order = { userId: 1, total: 600 };
  await expect(processOrder(order, mockUserService))
    .rejects.toThrow('Exceeds credit limit');
});
```
Real: credit limit check logic in `processOrder`. Mocked: the external UserService call.

---

## Fixing Hollow Tests

When you find a test where mocking has hollowed out the logic:

1. **Identify what real code should run** — what computation, transformation, or decision is the test supposed to cover?

2. **Move the mock further out** — mock the I/O boundary, not the logic layer.

3. **Use a fake instead of a mock** — implement a minimal in-memory version of the dependency that exercises the real code path.

4. **Write an integration test** — if the logic is inseparable from the I/O, write an integration test with a real (test) database or in-process server.

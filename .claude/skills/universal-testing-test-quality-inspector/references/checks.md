# Five Checks — Detailed Reference

Detailed guidance for each of the five inspection checks, with examples in Python, JavaScript, Go, and Java.

---

## Check 1: Name-to-Assertion Alignment

**Question:** Does the test name accurately describe what the assertions verify?

### What to look for

Read the test name as a specification sentence: "This test verifies that [name]". Then read the assertions. Do the assertions actually verify what the name claims?

### Common mismatches

**Name is too broad:**
```python
# Name claims to test "user authentication"
def test_user_authentication():
    user = User(email="a@b.com", password="x")
    assert user.email == "a@b.com"  # Only checks attribute storage, not auth
```
Verdict: MISLEADING — the test verifies attribute assignment, not authentication.

**Name references a condition that isn't set up:**
```javascript
// Name says "when user is anonymous"
test('should return default permissions when user is anonymous', () => {
  const user = new User({ id: 1, role: 'viewer' });  // Not anonymous!
  const perms = getPermissions(user);
  expect(perms).toEqual(DEFAULT_PERMISSIONS);
});
```
Verdict: MISLEADING — the user is not anonymous; the test passes by coincidence.

**Name describes a side effect but test only checks return value:**
```go
func TestShouldSaveUserToDatabase(t *testing.T) {
    user := createUser("alice@example.com")
    // Only checks return value, never verifies the DB write
    assert.Equal(t, "alice@example.com", user.Email)
}
```
Verdict: INCOMPLETE — no assertion verifies the database write.

### Fix pattern

Either rename the test to match what it actually tests, or add assertions that cover what the name promises.

---

## Check 2: Meaningful Assertions (No Tautologies)

**Question:** Would the assertion pass even with a broken or trivial implementation?

### Always-true assertions

```python
# Always true for any list
assert len(result) >= 0

# Always true when result is a list (even empty)
assert isinstance(result, list)

# Always true when function doesn't crash
assert result is not None
```

### Assertions that match mock return values exactly

```javascript
// The mock returns { id: 1, name: 'Alice' }
jest.mock('./userService', () => ({
  getUser: jest.fn().mockReturnValue({ id: 1, name: 'Alice' })
}));

test('should return user data', () => {
  const result = fetchUserProfile(1);
  expect(result).toEqual({ id: 1, name: 'Alice' });  // Just echoes the mock
});
```
Verdict: BROKEN — the test only verifies that a mock returns what you told it to return. No real logic is tested.

### Specificity too low

```java
@Test
public void testCalculateTax() {
    double result = taxCalculator.calculate(100.0);
    assertTrue(result > 0);  // Would pass even if result = 0.01 or 99.99
}
```
Better: `assertEquals(8.5, result, 0.001)` — checks the actual expected value.

### Fix pattern

Replace vague range assertions with specific value checks. Replace existence checks (`!= null`) with value checks. If you don't know the exact expected value, that's a sign the test was written after the implementation without thinking about expected behavior.

---

## Check 3: Mutation Failure Check

**Question:** If the implementation were deliberately broken, would this test catch it?

### Apply these mutations mentally

For a function `def add(a, b): return a + b`, the mutations are:
- Return `a - b` instead of `a + b`
- Return `a` instead of `a + b`
- Return `0`
- Return `None`

A good test catches all of them:
```python
def test_add_two_positive_numbers():
    assert add(3, 4) == 7  # Catches all four mutations above
```

A weak test:
```python
def test_add_returns_a_number():
    result = add(3, 4)
    assert isinstance(result, int)  # Passes for add(3,4)=0 or add(3,4)=3
```

### Common mutation survivors (bugs the test wouldn't catch)

**Off-by-one goes undetected:**
```python
def test_paginate():
    items = list(range(10))
    result = paginate(items, page=1, size=3)
    assert len(result) == 3  # Passes even if page indexing is off by one
```
Missing assertion: verify the *content* of the first page, not just the length.

**Wrong branch taken silently:**
```javascript
// Implementation has a bug: uses >= instead of >
function isAdult(age) { return age >= 18; }  // Bug: should be > 17

test('should return true for adults', () => {
  expect(isAdult(21)).toBe(true);  // Passes for both >= 18 and > 17
});
```
Missing test: `expect(isAdult(17)).toBe(false)` — the boundary case.

### Fix pattern

Test boundary values. Test the negative case alongside the positive case. Assert specific output values, not just types or existence.

---

## Check 4: Edge Case Coverage

**Question:** If the test name mentions an edge case, is that case actually exercised?

### "When empty" not actually empty

```python
def test_process_items_when_list_is_empty():
    items = [None]  # Not empty! None is a value.
    result = process_items(items)
    assert result == []
```

### "When None" not actually None

```javascript
test('should handle null userId gracefully', () => {
  const result = getUser(undefined);  // undefined != null in JS
  expect(result).toBeNull();
});
```

### "At boundary" not at the boundary

```go
func TestShouldRejectStringsLongerThan100Chars(t *testing.T) {
    // Tests with 50 chars, not 100 or 101
    input := strings.Repeat("a", 50)
    err := validate(input)
    assert.NoError(t, err)
}
```
Missing: test with exactly 100 chars (should pass), exactly 101 chars (should fail).

### Fix pattern

Read the arrange section carefully. Verify the test data actually represents the condition named. For boundary tests, test both sides of the boundary.

---

## Check 5: Mock Hygiene

**Question:** Do mocks remove so much real behavior that the test no longer exercises the code under test?

See [mock-hygiene.md](mock-hygiene.md) for full details. Key patterns here:

### The function under test is itself mocked

```python
# Testing process_order, but process_order is mocked
with patch('mymodule.process_order') as mock_process:
    mock_process.return_value = {'status': 'ok'}
    result = process_order(order_data)
    assert result['status'] == 'ok'
```
Verdict: BROKEN — this test verifies nothing about the real `process_order`.

### All inputs and outputs are controlled by the mock

```javascript
const mockDb = {
  findUser: jest.fn().mockReturnValue({ id: 1, balance: 100 }),
  updateBalance: jest.fn().mockReturnValue({ id: 1, balance: 50 })
};

test('should deduct amount from balance', () => {
  const result = deductBalance(mockDb, 1, 50);
  expect(result.balance).toBe(50);
});
```
If `deductBalance` is `(db, id, amount) => db.updateBalance(id, { balance: db.findUser(id).balance - amount })`, the test only verifies the mock chain, not the subtraction logic.

### Fix pattern

Mock external I/O (network, database, file system). Do not mock the function under test or its core logic. Verify that real computation happens between mock calls.

# Mutation Reasoning — Testing Without a Framework

How to apply mutation-testing thinking manually, without running a mutation framework like mutmut, PIT, or Stryker.

## What Is Mutation Testing?

Mutation testing systematically introduces small bugs into source code ("mutants") and then checks whether the existing test suite detects them. If a mutant survives (tests still pass with the bug present), the test suite has a gap.

This reference teaches you to reason through mutations mentally during a code review — no tooling required.

---

## Standard Mutation Operators

These are the changes a mutation framework would make. Apply them mentally to the implementation when inspecting a test.

### Arithmetic mutations

| Original | Mutant |
|----------|--------|
| `a + b`  | `a - b` |
| `a * b`  | `a / b` |
| `a % b`  | `a * b` |
| `a ** b` | `a * b` |

**Test implication:** Assertions must use specific numeric values that distinguish the correct result from the wrong arithmetic.

```python
# Weak: survives arithmetic mutation
assert result > 0  # True whether result is 7 or -7

# Strong: kills arithmetic mutation
assert result == 7  # Fails if + becomes -
```

### Conditional mutations

| Original | Mutant |
|----------|--------|
| `x > y`  | `x >= y`, `x < y`, `x == y`, `True`, `False` |
| `x == y` | `x != y`, `True`, `False` |
| `x and y` | `x or y`, `x`, `y`, `True`, `False` |

**Test implication:** Test both sides of every boundary. If the condition is `age >= 18`, test both `age == 17` (should fail) and `age == 18` (should pass).

```python
# Kills the >= → > mutation
def test_allows_exactly_18():
    assert is_adult(18) is True

def test_rejects_17():
    assert is_adult(17) is False
```

### Return value mutations

| Original       | Mutant             |
|----------------|--------------------|
| `return value` | `return None`      |
| `return True`  | `return False`     |
| `return []`    | `return None`      |
| `return obj`   | `return new empty instance` |

**Test implication:** Assertions must check the actual return value, not just that something was returned.

```python
# Weak: survives return None mutation
assert result is not None

# Strong: kills return None mutation
assert result == expected_value
```

### Statement deletion mutations

The mutant simply removes a line. Common targets:

- A side-effect call (logging, database write, email send)
- A validation check
- A list append or dict update

**Test implication:** For side effects named in the test, assert they occurred. For validation, test that invalid input is actually rejected.

```python
# Missing: the side-effect assertion
def test_user_created_successfully():
    create_user("alice@example.com")
    user = db.find_by_email("alice@example.com")
    assert user is not None  # Also catches the deletion mutation

# Or with mocks:
mock_db.save.assert_called_once()  # Catches deletion of the save call
```

### Exception handling mutations

| Original | Mutant |
|----------|--------|
| `raise ValueError("...")` | Remove the raise |
| `except ValueError:` | `except Exception:` (catches too much) |

**Test implication:** For error-path tests, verify the exact exception type and message, not just that some exception occurred.

```python
# Weak: survives mutating ValueError to RuntimeError
with pytest.raises(Exception):
    process_invalid_input(data)

# Strong: kills the mutation
with pytest.raises(ValueError, match="invalid format"):
    process_invalid_input(data)
```

---

## Mental Mutation Checklist

When inspecting a test, mentally apply these mutations to the function under test, then check whether the test's assertions would detect each one:

```
For each key operation in the implementation:

Arithmetic:
  [ ] Change + to - (or * to /)
  [ ] Would the assertion value change? If no → BROKEN

Conditions:
  [ ] Flip > to >= (or change == to !=)
  [ ] Does a boundary test cover this? If no → likely INCOMPLETE

Return values:
  [ ] Return None instead of the computed value
  [ ] Does an assertion check the value specifically? If no → BROKEN

Side effects:
  [ ] Delete the side-effect call (DB write, event emit, etc.)
  [ ] Does an assertion verify the side effect occurred? If no → INCOMPLETE

Error paths:
  [ ] Remove the validation / raise
  [ ] Is there a test that sends invalid input and expects an error? If no → INCOMPLETE
```

---

## Examples by Language

### Python — missed arithmetic mutation

```python
def calculate_compound_interest(principal, rate, periods):
    return principal * (1 + rate) ** periods

# Test that does NOT kill the arithmetic mutation
def test_compound_interest():
    result = calculate_compound_interest(1000, 0.05, 2)
    assert result > 1000  # True even if ** becomes *

# Test that DOES kill it
def test_compound_interest():
    result = calculate_compound_interest(1000, 0.05, 2)
    assert abs(result - 1102.50) < 0.01  # Fails for * mutation (gives 1100)
```

### JavaScript — missed conditional mutation

```javascript
function getDiscount(age) {
  if (age >= 65) return 0.15;
  if (age >= 18) return 0.05;
  return 0;
}

// Does NOT kill the >= 65 → > 65 mutation
test('senior discount', () => {
  expect(getDiscount(70)).toBe(0.15);  // True for both >= 65 and > 65
});

// Kills it
test('senior discount at exact boundary', () => {
  expect(getDiscount(65)).toBe(0.15);  // Fails if >= 65 becomes > 65
  expect(getDiscount(64)).toBe(0.05);  // Also verifies the boundary is correct
});
```

### Go — missed side-effect mutation

```go
func SaveUser(db Database, user User) error {
    if err := db.Insert(user); err != nil {
        return err
    }
    return nil
}

// Does NOT kill the deletion of db.Insert
func TestSaveUser(t *testing.T) {
    db := &MockDatabase{}
    err := SaveUser(db, User{Name: "Alice"})
    assert.NoError(t, err)  // Passes even if Insert is deleted (returns nil)
}

// Kills it
func TestSaveUser(t *testing.T) {
    db := &MockDatabase{}
    err := SaveUser(db, User{Name: "Alice"})
    assert.NoError(t, err)
    assert.Equal(t, 1, db.InsertCallCount())  // Fails if Insert is deleted
}
```

### Java — missed return value mutation

```java
public String formatName(String first, String last) {
    return last + ", " + first;
}

// Does NOT kill return null mutation
@Test
public void testFormatName() {
    String result = formatName("John", "Doe");
    assertNotNull(result);  // Passes for "Doe, John" or "John Doe" or any non-null
}

// Kills it
@Test
public void testFormatName() {
    String result = formatName("John", "Doe");
    assertEquals("Doe, John", result);  // Fails for any mutation
}
```

---

## When to Stop Applying Mutations

Not every mutation needs a test. Prioritize mutations in:

1. **Core business logic** — discount calculations, permission checks, state transitions
2. **Boundary conditions** — off-by-one errors are among the most common bugs
3. **Error paths** — missing error handling causes production incidents
4. **Side effects with consequences** — database writes, email sends, financial transactions

Lower priority:
- Pure logging statements
- Debug-only code paths
- Trivial getters and setters
- Code that is already covered by integration tests

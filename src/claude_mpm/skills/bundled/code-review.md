---
skill_id: code-review
skill_version: 0.1.0
description: Systematic approach to reviewing code for quality, correctness, and maintainability.
updated_at: 2025-10-30T17:00:00Z
tags: [code-review, quality, collaboration, best-practices]
---

# Code Review

Systematic approach to reviewing code for quality, correctness, and maintainability.

## Code Review Checklist

### Correctness
```
□ Logic is correct and handles edge cases
□ Error handling is appropriate
□ No obvious bugs or issues
□ Test coverage is adequate
□ Code works as intended
```

### Design & Architecture
```
□ Follows SOLID principles
□ Appropriate design patterns used
□ No unnecessary complexity
□ Good separation of concerns
□ Consistent with existing codebase
```

### Readability
```
□ Clear variable and function names
□ Functions are small and focused
□ Comments explain "why" not "what"
□ Code is self-documenting
□ Consistent formatting
```

### Performance
```
□ No obvious performance issues
□ Efficient algorithms used
□ Appropriate data structures
□ Database queries optimized
□ No memory leaks
```

### Security
```
□ Input validation present
□ No SQL injection vulnerabilities
□ Authentication/authorization checks
□ No sensitive data exposed
□ Dependencies are up to date
```

### Tests
```
□ New code has tests
□ Tests are meaningful
□ Edge cases tested
□ Tests follow AAA pattern
□ No flaky tests
```

## Review Comments

### Be Constructive
```
❌ "This code is terrible"
✅ "Consider extracting this into a separate function for clarity"

❌ "Wrong approach"
✅ "Have you considered using X pattern? It might simplify this"
```

### Be Specific
```
❌ "Improve this"
✅ "This function is doing too much. Consider splitting into:
   1. Validation function
   2. Processing function
   3. Response builder"
```

### Provide Context
```
✅ "This could cause a race condition when multiple requests
    access the cache simultaneously. Consider using a lock:

    with cache_lock:
        value = cache.get(key)
"
```

## Common Review Findings

### Naming Issues
```python
# Poor
def f(x):
    return x * 2

# Better
def calculate_double(value):
    return value * 2
```

### Error Handling
```python
# Missing error handling
result = api.call()
process(result)

# With proper handling
try:
    result = api.call()
    process(result)
except APIError as e:
    logger.error(f"API call failed: {e}")
    return default_response()
```

### Magic Numbers
```python
# Magic numbers
if user.age > 18 and user.balance > 1000:

# Named constants
MIN_AGE = 18
MIN_BALANCE = 1000
if user.age > MIN_AGE and user.balance > MIN_BALANCE:
```

## Remember
- Focus on code, not the person
- Explain the "why" behind suggestions
- Recognize good code too
- Suggest, don't demand
- Pick your battles - not every issue needs fixing

---
skill_id: async-testing
skill_version: 0.1.0
description: Patterns for testing asynchronous code across languages, eliminating redundant async testing guidance per agent.
updated_at: 2025-10-30T17:00:00Z
tags: [testing, async, asynchronous, concurrency]
---

# Async Testing

Patterns for testing asynchronous code across languages. Eliminates ~200-300 lines of redundant async testing guidance per agent.

## Core Async Testing Principles

### 1. Async Code is Still Testable

Asynchronous operations can and should be tested just like synchronous code. The key is understanding the execution model.

### 2. Control Time in Tests

Never rely on actual timeouts in tests. Use time mocking for deterministic, fast tests.

### 3. Test Race Conditions Explicitly

Concurrent code has race conditions. Test them deliberately rather than hoping they don't happen.

## Language-Specific Patterns

### Python (asyncio)

#### Basic Async Test Setup

```python
import pytest
import asyncio

# Mark test as async
@pytest.mark.asyncio
async def test_async_operation():
    result = await async_function()
    assert result == expected_value

# Alternative: Use asyncio.run()
def test_async_operation_sync():
    result = asyncio.run(async_function())
    assert result == expected_value
```

#### Testing Async Fixtures

```python
@pytest.fixture
async def async_database():
    """Async fixture for database setup/teardown."""
    db = await create_async_database()
    yield db
    await db.close()

@pytest.mark.asyncio
async def test_with_async_fixture(async_database):
    result = await async_database.query("SELECT * FROM users")
    assert len(result) > 0
```

#### Testing Concurrent Operations

```python
@pytest.mark.asyncio
async def test_concurrent_requests():
    # Run multiple async operations concurrently
    results = await asyncio.gather(
        fetch_user(1),
        fetch_user(2),
        fetch_user(3)
    )

    assert len(results) == 3
    assert all(user.is_valid() for user in results)
```

#### Testing Timeouts

```python
@pytest.mark.asyncio
async def test_operation_timeout():
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(slow_operation(), timeout=1.0)
```

#### Mocking Async Functions

```python
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_with_async_mock():
    mock_api = AsyncMock(return_value={"status": "success"})

    with patch('module.api_call', mock_api):
        result = await function_that_calls_api()

    assert result["status"] == "success"
    mock_api.assert_called_once()
```

### JavaScript/TypeScript (async/await)

#### Basic Async Test Setup

```javascript
// Jest
describe('Async Operations', () => {
  test('should handle async operation', async () => {
    const result = await asyncFunction();
    expect(result).toBe(expectedValue);
  });

  // Alternative: Return promise
  test('should handle promise', () => {
    return asyncFunction().then(result => {
      expect(result).toBe(expectedValue);
    });
  });
});
```

#### Testing Promise Resolution/Rejection

```javascript
test('should resolve with correct data', async () => {
  await expect(fetchUser(1)).resolves.toEqual({
    id: 1,
    name: 'John'
  });
});

test('should reject when user not found', async () => {
  await expect(fetchUser(999)).rejects.toThrow('User not found');
});
```

#### Testing Concurrent Operations

```javascript
test('should handle multiple concurrent requests', async () => {
  const promises = [
    fetchUser(1),
    fetchUser(2),
    fetchUser(3)
  ];

  const results = await Promise.all(promises);

  expect(results).toHaveLength(3);
  expect(results.every(user => user.id > 0)).toBe(true);
});
```

#### Testing Race Conditions

```javascript
test('should handle race condition correctly', async () => {
  let counter = 0;
  const increment = async () => {
    const current = counter;
    await delay(10);  // Simulate async work
    counter = current + 1;
  };

  // Run concurrently - will show race condition
  await Promise.all([increment(), increment(), increment()]);

  // Without proper synchronization, counter might be 1 instead of 3
  expect(counter).toBe(3);  // This test will fail if race condition exists
});
```

#### Mocking Async Functions

```javascript
jest.mock('./api');

test('should use mocked async function', async () => {
  const mockFetchUser = require('./api').fetchUser;
  mockFetchUser.mockResolvedValue({ id: 1, name: 'John' });

  const result = await getUserData(1);

  expect(result.name).toBe('John');
  expect(mockFetchUser).toHaveBeenCalledWith(1);
});
```

#### Testing Timeouts

```javascript
test('should timeout long operations', async () => {
  const timeoutPromise = new Promise((_, reject) =>
    setTimeout(() => reject(new Error('Timeout')), 1000)
  );

  await expect(
    Promise.race([slowOperation(), timeoutPromise])
  ).rejects.toThrow('Timeout');
});
```

### Go (goroutines)

#### Basic Async Test Setup

```go
func TestAsyncOperation(t *testing.T) {
    done := make(chan bool)
    var result int

    go func() {
        result = expensiveOperation()
        done <- true
    }()

    <-done  // Wait for completion

    if result != expected {
        t.Errorf("Expected %d, got %d", expected, result)
    }
}
```

#### Testing with Timeouts

```go
func TestWithTimeout(t *testing.T) {
    done := make(chan bool)

    go func() {
        slowOperation()
        done <- true
    }()

    select {
    case <-done:
        // Success
    case <-time.After(1 * time.Second):
        t.Fatal("Operation timed out")
    }
}
```

#### Testing Concurrent Operations

```go
func TestConcurrentOperations(t *testing.T) {
    const numWorkers = 10
    results := make(chan int, numWorkers)

    for i := 0; i < numWorkers; i++ {
        go func(id int) {
            results <- processTask(id)
        }(i)
    }

    // Collect results
    var sum int
    for i := 0; i < numWorkers; i++ {
        sum += <-results
    }

    if sum != expectedSum {
        t.Errorf("Expected sum %d, got %d", expectedSum, sum)
    }
}
```

#### Testing Race Conditions

```go
func TestRaceCondition(t *testing.T) {
    // Enable race detector: go test -race
    counter := 0
    done := make(chan bool)

    for i := 0; i < 100; i++ {
        go func() {
            counter++  // Race condition!
            done <- true
        }()
    }

    for i := 0; i < 100; i++ {
        <-done
    }

    // With race condition, counter might be < 100
    if counter != 100 {
        t.Errorf("Expected 100, got %d (race condition detected)", counter)
    }
}
```

### Rust (async/await with tokio)

#### Basic Async Test Setup

```rust
#[tokio::test]
async fn test_async_operation() {
    let result = async_function().await;
    assert_eq!(result, expected_value);
}

// Multi-threaded runtime
#[tokio::test(flavor = "multi_thread", worker_threads = 4)]
async fn test_concurrent_operation() {
    let result = concurrent_operation().await;
    assert!(result.is_ok());
}
```

#### Testing with Timeouts

```rust
use tokio::time::{timeout, Duration};

#[tokio::test]
async fn test_with_timeout() {
    let result = timeout(
        Duration::from_secs(1),
        slow_operation()
    ).await;

    assert!(result.is_err(), "Operation should have timed out");
}
```

#### Testing Concurrent Operations

```rust
#[tokio::test]
async fn test_concurrent_tasks() {
    let task1 = tokio::spawn(async { fetch_data(1).await });
    let task2 = tokio::spawn(async { fetch_data(2).await });
    let task3 = tokio::spawn(async { fetch_data(3).await });

    let results = tokio::try_join!(task1, task2, task3).unwrap();

    assert_eq!(results.0, expected1);
    assert_eq!(results.1, expected2);
    assert_eq!(results.2, expected3);
}
```

## Common Async Testing Patterns

### Pattern 1: Testing Callback-Based Async

```javascript
// Converting callbacks to promises for testing
function promisify(callbackFn) {
  return (...args) => {
    return new Promise((resolve, reject) => {
      callbackFn(...args, (err, result) => {
        if (err) reject(err);
        else resolve(result);
      });
    });
  };
}

test('should handle callback-based async', async () => {
  const asyncFn = promisify(callbackBasedFunction);
  const result = await asyncFn(arg1, arg2);
  expect(result).toBe(expected);
});
```

### Pattern 2: Testing Event Emitters

```javascript
test('should emit events in correct order', async () => {
  const events = [];
  const emitter = new EventEmitter();

  emitter.on('start', () => events.push('start'));
  emitter.on('process', () => events.push('process'));
  emitter.on('complete', () => events.push('complete'));

  await performAsyncOperation(emitter);

  expect(events).toEqual(['start', 'process', 'complete']);
});
```

### Pattern 3: Testing Retry Logic

```javascript
test('should retry failed operations', async () => {
  let attempts = 0;
  const unreliableOperation = async () => {
    attempts++;
    if (attempts < 3) throw new Error('Temporary failure');
    return 'success';
  };

  const result = await retryOperation(unreliableOperation, 3);

  expect(result).toBe('success');
  expect(attempts).toBe(3);
});
```

### Pattern 4: Testing Debouncing/Throttling

```javascript
test('should debounce rapid calls', async () => {
  let callCount = 0;
  const debouncedFn = debounce(() => callCount++, 100);

  // Rapid calls
  debouncedFn();
  debouncedFn();
  debouncedFn();

  // Wait for debounce period
  await delay(150);

  expect(callCount).toBe(1);  // Only called once
});
```

## Testing Async State Management

### Testing Loading States

```javascript
test('should show loading state during async operation', async () => {
  const component = render(<AsyncComponent />);

  // Initial state
  expect(component.getByText('Loading...')).toBeInTheDocument();

  // Wait for async operation
  await waitFor(() => {
    expect(component.getByText('Data loaded')).toBeInTheDocument();
  });

  expect(component.queryByText('Loading...')).not.toBeInTheDocument();
});
```

### Testing Error States

```javascript
test('should show error state on failure', async () => {
  // Mock API to fail
  mockApi.fetchData.mockRejectedValue(new Error('Network error'));

  const component = render(<AsyncComponent />);

  await waitFor(() => {
    expect(component.getByText('Error: Network error')).toBeInTheDocument();
  });
});
```

## Best Practices

### ✅ DO: Control Time in Tests

```javascript
// Good: Mock timers for deterministic tests
jest.useFakeTimers();

test('should execute after delay', () => {
  const callback = jest.fn();
  setTimeout(callback, 1000);

  jest.advanceTimersByTime(1000);

  expect(callback).toHaveBeenCalled();
});
```

### ✅ DO: Test Both Success and Failure Paths

```python
@pytest.mark.asyncio
async def test_success_path():
    result = await operation_that_succeeds()
    assert result.is_success()

@pytest.mark.asyncio
async def test_failure_path():
    with pytest.raises(OperationError):
        await operation_that_fails()
```

### ✅ DO: Use Appropriate Timeouts

```python
# Good: Reasonable timeout for test
@pytest.mark.asyncio
async def test_with_timeout():
    async with timeout(5):  # 5 seconds is reasonable
        result = await long_operation()
```

### ❌ DON'T: Use Real Delays in Tests

```python
# Bad: Real delays make tests slow
await asyncio.sleep(5)  # Don't do this!

# Good: Mock time or use smaller delays for testing
with patch('asyncio.sleep'):
    await operation_with_delay()
```

### ❌ DON'T: Forget to Await

```python
# Bad: Forgot to await
def test_async_wrong():
    result = async_function()  # Returns coroutine, doesn't execute!
    assert result == expected  # Will fail!

# Good: Properly await
@pytest.mark.asyncio
async def test_async_correct():
    result = await async_function()
    assert result == expected
```

### ❌ DON'T: Ignore Unhandled Promise Rejections

```javascript
// Bad: Unhandled rejection
test('bad test', async () => {
  asyncOperation();  // Promise rejection not handled!
});

// Good: Handle all promises
test('good test', async () => {
  await expect(asyncOperation()).rejects.toThrow();
});
```

## Quick Reference Checklist

When testing async code:

```
□ Are all async functions awaited?
□ Are timeouts reasonable and not using real time?
□ Are both success and failure paths tested?
□ Are race conditions tested explicitly?
□ Are unhandled promise rejections caught?
□ Are async fixtures cleaned up properly?
□ Are concurrent operations tested?
□ Is error handling tested?
□ Are retry mechanisms tested?
□ Are loading/error states tested (for UI)?
```

## Remember

- **Async code is synchronous in tests** - Use await, don't rely on timing
- **Mock time** - Never use real delays in tests
- **Test failure paths** - Errors are part of async operations
- **Handle all promises** - Unhandled rejections cause flaky tests
- **Control concurrency** - Test race conditions deliberately

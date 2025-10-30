---
skill_id: systematic-debugging
skill_version: 0.1.0
description: Structured approach to identifying and fixing bugs efficiently, eliminating redundant debugging guidance per agent.
updated_at: 2025-10-30T17:00:00Z
tags: [debugging, troubleshooting, problem-solving, best-practices]
---

# Systematic Debugging

Structured approach to identifying and fixing bugs efficiently. Eliminates ~300-400 lines of redundant debugging guidance per agent.

## Core Debugging Principles

### 1. Debug First Protocol (MANDATORY)

Before writing ANY fix or optimization:
1. **Check System Outputs:** Review logs, network requests, error messages
2. **Identify Root Cause:** Investigate actual failure point, not symptoms
3. **Implement Simplest Fix:** Solve root cause with minimal code change
4. **Test Core Functionality:** Verify fix works WITHOUT optimization layers
5. **Optimize If Measured:** Add performance improvements only after metrics prove need

### 2. Root Cause Over Symptoms

- Debug the actual failing operation, not its side effects
- Trace errors to their source before adding workarounds
- Question whether the problem is where you think it is

### 3. Simplicity Before Complexity

- Start with the simplest solution that correctly solves the problem
- Advanced patterns/libraries are rarely the answer to basic problems
- If a solution seems complex, you probably haven't found the root cause

## The Debugging Process

### Step 1: Reproduce Reliably

**Goal:** Create a minimal, reproducible test case

```
Questions to answer:
- Does it happen every time or intermittently?
- What are the exact steps to reproduce?
- What is the minimal input that triggers it?
- Which environment variables matter?
- What's the smallest code example that shows the bug?
```

**Example:**
```python
# Minimal reproduction
def test_bug_reproduction():
    # Simplest case that demonstrates the bug
    result = problematic_function(edge_case_input)
    assert result == expected_output  # Currently fails
```

### Step 2: Isolate the Problem

**Strategy:** Binary search through code/data

```
Isolation techniques:
1. Comment out half the code - does bug persist?
2. Add logging at midpoints to narrow down location
3. Test with minimal data set
4. Remove external dependencies one by one
5. Test in clean environment (new VM, fresh install)
```

**Example:**
```python
# Add strategic logging to isolate
def complex_operation(data):
    logger.debug(f"Input: {data}")  # Checkpoint 1

    processed = process_step_1(data)
    logger.debug(f"After step 1: {processed}")  # Checkpoint 2

    validated = validate_step_2(processed)
    logger.debug(f"After step 2: {validated}")  # Checkpoint 3

    return finalize_step_3(validated)
```

### Step 3: Form and Test Hypotheses

**Process:** Scientific method for debugging

```
For each hypothesis:
1. State clearly: "I believe X is causing Y because Z"
2. Predict: "If my hypothesis is true, then..."
3. Test: Design experiment to confirm/refute
4. Observe: Record actual results
5. Conclude: Was hypothesis correct?
```

**Example:**
```python
# Hypothesis: The bug is caused by integer overflow

# Prediction: Using larger integer type will fix it
# Test:
def test_hypothesis_integer_overflow():
    # Original (fails)
    result_int32 = calculate_with_int32(large_number)

    # Modified (should work if hypothesis correct)
    result_int64 = calculate_with_int64(large_number)

    # Compare
    print(f"Int32 result: {result_int32}")  # Overflowed?
    print(f"Int64 result: {result_int64}")  # Correct?
```

### Step 4: Verify the Fix

**Checklist before committing:**

```
✓ Original bug is fixed
✓ No new bugs introduced
✓ Edge cases handled
✓ Tests added to prevent regression
✓ Code is simpler, not more complex
✓ Performance is acceptable
✓ Documentation updated if needed
```

## Debugging Tools and Techniques

### Print Debugging (Strategic Logging)

**When to use:** Quick investigation, unfamiliar codebase

```python
# Strategic logging points
def complex_algorithm(data):
    # 1. Input validation
    logger.debug(f"Input received: {data}")

    # 2. Before transformation
    logger.debug(f"Before processing: {data}")

    result = expensive_operation(data)

    # 3. After transformation
    logger.debug(f"After processing: {result}")

    # 4. Before return
    logger.debug(f"Returning: {result}")

    return result
```

**Best practices:**
- Include variable names and values
- Log at decision points (if/else branches)
- Use structured logging for filtering
- Remove debugging logs after fixing

### Interactive Debugging (Debugger)

**When to use:** Complex bugs, need to inspect state

```python
# Python (pdb)
import pdb

def problematic_function(x, y):
    result = x + y
    pdb.set_trace()  # Execution pauses here
    return result * 2

# Commands:
# n - next line
# s - step into function
# c - continue execution
# p variable - print variable
# l - list code around current line
```

```javascript
// JavaScript (Node.js)
function problematicFunction(x, y) {
    const result = x + y;
    debugger;  // Execution pauses here when DevTools open
    return result * 2;
}
```

### Error Message Analysis

**Read error messages carefully - they tell you exactly what's wrong**

```
Example error:
TypeError: Cannot read property 'name' of undefined
    at getUserName (user.js:15:20)
    at processUser (app.js:42:10)

Information extracted:
1. Error type: TypeError (type-related issue)
2. Specific problem: accessing 'name' property
3. Root cause: object is undefined
4. Location: user.js line 15, column 20
5. Call stack: originated in processUser()

Next steps:
- Check why object is undefined at that point
- Add null check or ensure object exists
- Trace back to where object should be created
```

### Binary Search Through Code

**For intermittent bugs or "it stopped working"**

```bash
# Git bisect - find commit that introduced bug
git bisect start
git bisect bad                  # Current version has bug
git bisect good v1.2.0         # This version was working
# Git checks out middle commit
# Test if bug exists
git bisect bad  # if bug exists
git bisect good # if bug doesn't exist
# Repeat until bug commit found
```

### Rubber Duck Debugging

**Explain the problem out loud (to a rubber duck, colleague, or yourself)**

```
Process:
1. State what the code is supposed to do
2. Explain what it actually does
3. Walk through the code line by line
4. Often, the act of explaining reveals the bug

Why it works:
- Forces you to be precise
- Reveals assumptions
- Highlights inconsistencies
- Activates different brain regions
```

## Common Bug Categories and Solutions

### Null/Undefined Reference Errors

```python
# Problem: Accessing property of None/null/undefined
user.name  # Crashes if user is None

# Solutions:
# 1. Guard clause
if user is None:
    return default_name
return user.name

# 2. Optional chaining (languages that support it)
return user?.name ?? default_name

# 3. Early validation
def process_user(user):
    if user is None:
        raise ValueError("User cannot be None")
    return user.name
```

### Off-by-One Errors

```python
# Problem: Loop runs one too many or too few times
for i in range(len(array)):
    process(array[i+1])  # IndexError on last iteration!

# Solutions:
# 1. Adjust range
for i in range(len(array) - 1):
    process(array[i+1])

# 2. Better iteration
for current, next_item in zip(array, array[1:]):
    process(next_item)

# 3. Test boundaries explicitly
def test_boundary_conditions():
    assert process_array([]) == expected_empty
    assert process_array([1]) == expected_single
    assert process_array([1, 2]) == expected_pair
```

### Race Conditions

```python
# Problem: Order of operations matters
shared_counter = 0

def increment():
    # Read-modify-write is not atomic!
    temp = shared_counter
    temp += 1
    shared_counter = temp

# Solutions:
# 1. Use locks
import threading
lock = threading.Lock()

def increment():
    with lock:
        shared_counter += 1

# 2. Use atomic operations
from threading import atomic
counter = atomic.AtomicInteger(0)
counter.increment()

# 3. Avoid shared state
def increment(counter):
    return counter + 1  # Pure function
```

### Memory Leaks

```python
# Problem: Objects not being garbage collected
class Cache:
    def __init__(self):
        self.data = {}

    def store(self, key, value):
        self.data[key] = value  # Never removed!

# Solutions:
# 1. Explicit cleanup
def store(self, key, value, ttl=3600):
    self.data[key] = (value, time.time() + ttl)
    self._cleanup_expired()

# 2. Use weak references
import weakref
self.data = weakref.WeakValueDictionary()

# 3. Limit cache size
from functools import lru_cache
@lru_cache(maxsize=128)
def expensive_function(arg):
    pass
```

## Debugging Anti-Patterns

### ❌ Random Changes (Hope-Driven Debugging)

```python
# Bad: Changing things randomly
try:
    result = function(x)  # Doesn't work
    # Try adding +1? Maybe that helps?
    result = function(x + 1)  # Still doesn't work
    # Try multiplying by 2?
    result = function(x * 2)
```

**Better:** Understand why it's failing first, then make targeted fix.

### ❌ Cargo Cult Fixes

```python
# Bad: Copying solutions without understanding
# "I found this on Stack Overflow"
time.sleep(0.1)  # "Fixes" race condition by accident
```

**Better:** Understand the root cause and fix it properly.

### ❌ Debugging in Production

```python
# Bad: Testing theories on live system
if user.is_admin:
    print("DEBUG: Admin access granted")  # Left in production!
    grant_access()
```

**Better:** Reproduce locally, fix, test, then deploy.

### ❌ Ignoring Warnings

```python
# Bad: Suppressing warnings without investigation
import warnings
warnings.filterwarnings("ignore")  # What could go wrong?
```

**Better:** Address the root cause of warnings.

## Advanced Debugging Techniques

### Time-Travel Debugging

Record execution and replay it:
```python
# Python: Use `python -m pdb -cc script.py` for post-mortem debugging
# JavaScript: Use Chrome DevTools recording
# Rust: Use rr (record and replay)
```

### Performance Profiling for Bug-Finding

```python
import cProfile
import pstats

# Profile code to find bottlenecks
profiler = cProfile.Profile()
profiler.enable()

slow_function()

profiler.disable()
stats = pstats.Stats(profiler)
stats.sort_stats('cumtime')
stats.print_stats(10)  # Top 10 slowest functions
```

### Memory Profiling

```python
# Python: memory_profiler
from memory_profiler import profile

@profile
def memory_intensive_function():
    large_list = [i for i in range(1000000)]
    return sum(large_list)

# Run: python -m memory_profiler script.py
```

## Quick Debugging Checklist

When you encounter a bug:

```
□ Can you reproduce it reliably?
□ Have you read the error message completely?
□ Have you checked the logs?
□ Is it the code or the data?
□ Have you tested with minimal input?
□ Have you isolated the failing component?
□ Have you checked recent changes (git log)?
□ Have you verified your assumptions?
□ Have you tried explaining it out loud?
□ Have you checked for common issues (null, off-by-one, race condition)?
□ Have you written a test that demonstrates the bug?
□ Does the fix address the root cause, not the symptom?
```

## Remember

- **Correctness before performance** - Fast but wrong is always worse than slow but correct
- **Simplest fix first** - Complex solutions are often solving the wrong problem
- **Test your assumptions** - The bug is usually in code you're "sure" is correct
- **Read the error message** - It tells you exactly what's wrong
- **One change at a time** - Change multiple things and you won't know what fixed it

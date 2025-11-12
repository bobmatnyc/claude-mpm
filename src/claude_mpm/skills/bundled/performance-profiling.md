---
skill_id: performance-profiling
skill_version: 0.1.0
description: Systematic approach to identifying and optimizing performance bottlenecks, eliminating redundant profiling guidance per agent.
updated_at: 2025-10-30T17:00:00Z
tags: [performance, profiling, optimization, benchmarking]
---

# Performance Profiling

Systematic approach to identifying and optimizing performance bottlenecks. Eliminates ~200-250 lines of redundant profiling guidance per agent.

## Core Principle: Measure Before Optimizing

**Never optimize without profiling data.** Intuition about performance is usually wrong.

> "Premature optimization is the root of all evil" - Donald Knuth

## The Profiling Process

### 1. Establish Baseline

Before any optimization:
```
□ Measure current performance
□ Define acceptable performance targets
□ Identify critical code paths
□ Document current metrics
```

### 2. Profile to Find Bottlenecks

Use profiling tools to identify hot spots:
```
□ CPU profiling (where time is spent)
□ Memory profiling (allocation patterns)
□ I/O profiling (disk/network bottlenecks)
□ Database query profiling
```

### 3. Optimize Targeted Areas

Focus on the biggest bottlenecks first (80/20 rule).

### 4. Measure Impact

Verify that optimizations actually improved performance.

## Language-Specific Profiling

### Python

#### CPU Profiling with cProfile

```python
import cProfile
import pstats
from pstats import SortKey

# Profile a function
profiler = cProfile.Profile()
profiler.enable()

slow_function()

profiler.disable()

# Analyze results
stats = pstats.Stats(profiler)
stats.sort_stats(SortKey.CUMULATIVE)
stats.print_stats(20)  # Top 20 functions by cumulative time

# Output shows:
# - ncalls: number of calls
# - tottime: total time in function (excluding subcalls)
# - cumtime: cumulative time (including subcalls)
```

#### Line-by-Line Profiling

```python
from line_profiler import LineProfiler

@profile  # Decorator for line_profiler
def bottleneck_function():
    data = load_data()
    processed = process_data(data)
    result = analyze(processed)
    return result

# Run: kernprof -l -v script.py
# Shows time spent on each line
```

#### Memory Profiling

```python
from memory_profiler import profile

@profile
def memory_intensive():
    large_list = [i for i in range(10000000)]  # Shows memory spike
    processed = [x * 2 for x in large_list]    # Shows peak memory
    return sum(processed)

# Run: python -m memory_profiler script.py
# Shows line-by-line memory usage
```

### JavaScript/Node.js

#### Built-in Profiling

```javascript
// CPU profiling
console.profile('MyOperation');
expensiveOperation();
console.profileEnd('MyOperation');

// Time measurement
console.time('operation');
performOperation();
console.timeEnd('operation');
```

#### Node.js Performance API

```javascript
const { performance, PerformanceObserver } = require('perf_hooks');

// Mark specific points
performance.mark('start-operation');
performOperation();
performance.mark('end-operation');

// Measure duration
performance.measure('operation-duration', 'start-operation', 'end-operation');

const observer = new PerformanceObserver((items) => {
  items.getEntries().forEach((entry) => {
    console.log(`${entry.name}: ${entry.duration}ms`);
  });
});

observer.observe({ entryTypes: ['measure'] });
```

#### Chrome DevTools Profiling

```javascript
// Run with: node --inspect script.js
// Open chrome://inspect in Chrome
// Use Performance tab to record and analyze

function expensiveOperation() {
  // CPU-intensive work
  for (let i = 0; i < 1000000; i++) {
    Math.sqrt(i);
  }
}

expensiveOperation();
```

### Go

#### CPU Profiling

```go
import (
    "os"
    "runtime/pprof"
)

func main() {
    // Start CPU profiling
    f, _ := os.Create("cpu.prof")
    defer f.Close()
    pprof.StartCPUProfile(f)
    defer pprof.StopCPUProfile()

    // Code to profile
    expensiveOperation()

    // Analyze with: go tool pprof cpu.prof
}
```

#### Memory Profiling

```go
import (
    "os"
    "runtime/pprof"
)

func main() {
    // Code to profile
    expensiveOperation()

    // Write memory profile
    f, _ := os.Create("mem.prof")
    defer f.Close()
    pprof.WriteHeapProfile(f)

    // Analyze with: go tool pprof mem.prof
}
```

#### Benchmarking

```go
func BenchmarkExpensiveOperation(b *testing.B) {
    for i := 0; i < b.N; i++ {
        expensiveOperation()
    }
}

// Run: go test -bench=. -benchmem
// Shows:
// - ns/op: nanoseconds per operation
// - B/op: bytes allocated per operation
// - allocs/op: allocations per operation
```

### Rust

#### Benchmarking with Criterion

```rust
use criterion::{black_box, criterion_group, criterion_main, Criterion};

fn expensive_operation(n: u64) -> u64 {
    // Operation to benchmark
    (0..n).sum()
}

fn bench_operation(c: &mut Criterion) {
    c.bench_function("expensive_operation", |b| {
        b.iter(|| expensive_operation(black_box(1000)))
    });
}

criterion_group!(benches, bench_operation);
criterion_main!(benches);

// Run: cargo bench
```

#### Profiling with Flamegraph

```bash
# Install flamegraph
cargo install flamegraph

# Profile and generate flamegraph
cargo flamegraph --bin my_binary

# Opens flamegraph.svg showing hot paths
```

## Common Performance Bottlenecks

### 1. Database Queries (N+1 Problem)

```python
# Bad: N+1 queries
def get_users_with_posts():
    users = User.query.all()  # 1 query
    for user in users:
        posts = Post.query.filter_by(user_id=user.id).all()  # N queries!
        user.posts = posts
    return users

# Good: Single query with join
def get_users_with_posts():
    return User.query.options(joinedload(User.posts)).all()  # 1 query
```

### 2. Unnecessary Loops

```python
# Bad: Nested loops O(n²)
def find_duplicates(items):
    duplicates = []
    for i, item1 in enumerate(items):
        for j, item2 in enumerate(items[i+1:]):
            if item1 == item2:
                duplicates.append(item1)
    return duplicates

# Good: Use set O(n)
def find_duplicates(items):
    seen = set()
    duplicates = set()
    for item in items:
        if item in seen:
            duplicates.add(item)
        seen.add(item)
    return list(duplicates)
```

### 3. Inefficient Data Structures

```python
# Bad: List lookups O(n)
def process_items(items, allowed_ids):
    allowed_ids_list = [1, 2, 3, ...]  # List
    result = []
    for item in items:
        if item.id in allowed_ids_list:  # O(n) lookup
            result.append(item)
    return result

# Good: Set lookups O(1)
def process_items(items, allowed_ids):
    allowed_ids_set = {1, 2, 3, ...}  # Set
    result = []
    for item in items:
        if item.id in allowed_ids_set:  # O(1) lookup
            result.append(item)
    return result
```

### 4. Excessive Memory Allocation

```python
# Bad: Building string with concatenation
def build_large_string(items):
    result = ""
    for item in items:
        result += str(item) + "\n"  # Creates new string each time
    return result

# Good: Use list and join
def build_large_string(items):
    parts = []
    for item in items:
        parts.append(str(item))
    return "\n".join(parts)  # Single allocation
```

### 5. Synchronous I/O

```python
# Bad: Sequential HTTP requests
def fetch_all_users(user_ids):
    users = []
    for user_id in user_ids:
        response = requests.get(f"/users/{user_id}")  # Blocks
        users.append(response.json())
    return users

# Good: Concurrent requests
async def fetch_all_users(user_ids):
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_user(session, user_id) for user_id in user_ids]
        return await asyncio.gather(*tasks)
```

## Performance Optimization Strategies

### Strategy 1: Caching

```python
from functools import lru_cache

@lru_cache(maxsize=128)
def expensive_calculation(n):
    # Expensive computation
    return result

# First call: computed
result1 = expensive_calculation(10)

# Second call: cached
result2 = expensive_calculation(10)  # Instant
```

### Strategy 2: Lazy Loading

```python
class ExpensiveResource:
    def __init__(self):
        self._data = None

    @property
    def data(self):
        if self._data is None:
            self._data = load_expensive_data()  # Only load when needed
        return self._data
```

### Strategy 3: Batching

```python
# Bad: Process one at a time
for item in items:
    process_single(item)  # Many round trips

# Good: Process in batches
for batch in chunks(items, batch_size=100):
    process_batch(batch)  # Fewer round trips
```

### Strategy 4: Indexing (Databases)

```sql
-- Bad: Sequential scan
SELECT * FROM users WHERE email = 'user@example.com';

-- Good: Use index
CREATE INDEX idx_users_email ON users(email);
SELECT * FROM users WHERE email = 'user@example.com';
```

### Strategy 5: Algorithmic Optimization

```python
# Bad: Bubble sort O(n²)
def sort_items(items):
    for i in range(len(items)):
        for j in range(len(items) - 1):
            if items[j] > items[j + 1]:
                items[j], items[j + 1] = items[j + 1], items[j]

# Good: Use built-in sort O(n log n)
def sort_items(items):
    return sorted(items)
```

## Performance Testing

### Load Testing

> **Note:** Locust is an optional dependency. Install it separately if you need load testing capabilities:
> ```bash
> pip install "claude-mpm[agents-load-testing]"
> ```
> Or install locust directly: `pip install locust>=2.15.0`

```python
# Using locust for load testing
from locust import HttpUser, task, between

class WebsiteUser(HttpUser):
    wait_time = between(1, 5)

    @task
    def load_homepage(self):
        self.client.get("/")

    @task
    def load_user_profile(self):
        self.client.get("/profile/123")

# Run: locust -f locustfile.py
# Shows requests/sec, response times, failure rate
```

### Stress Testing

```bash
# Using Apache Bench
ab -n 10000 -c 100 http://localhost:8000/

# n: total requests
# c: concurrent requests
# Shows: requests/sec, time per request, transfer rate
```

## Performance Monitoring

### Key Metrics to Track

```
CPU Usage:
- % CPU time
- CPU cores utilized
- System vs user time

Memory Usage:
- Heap size
- Peak memory
- Memory leaks (growing over time)

I/O:
- Disk read/write IOPS
- Network throughput
- Database query time

Response Time:
- p50 (median)
- p95 (95th percentile)
- p99 (99th percentile)
- Max response time
```

### Application Performance Monitoring (APM)

```python
# Example: Using OpenTelemetry
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider

trace.set_tracer_provider(TracerProvider())
tracer = trace.get_tracer(__name__)

def process_request():
    with tracer.start_as_current_span("process_request"):
        # Your code here
        with tracer.start_as_current_span("database_query"):
            fetch_data()
        with tracer.start_as_current_span("process_data"):
            process_data()
```

## Optimization Anti-Patterns

### ❌ Optimizing Before Profiling

```python
# Bad: Optimizing blindly
# "This looks slow, let me make it faster"
result = [complex_operation(x) for x in items]  # Is this actually slow?
```

### ❌ Micro-Optimizations

```python
# Bad: Premature micro-optimization
# Optimizing: x = x + 1  vs  x += 1
# Impact: negligible (nanoseconds)
# Don't waste time on this without proof it matters
```

### ❌ Sacrificing Readability

```python
# Bad: Unreadable "optimized" code
r=[x for x in d if x>0and x<100and x%2==0]  # What does this do?

# Good: Readable code (optimize only if profiling shows need)
even_numbers = [
    num for num in data
    if 0 < num < 100 and num % 2 == 0
]
```

## Quick Profiling Checklist

Before optimizing:

```
□ Have you profiled to identify bottlenecks?
□ Have you established baseline metrics?
□ Are you optimizing the critical path?
□ Have you checked for N+1 queries?
□ Have you looked at algorithm complexity?
□ Have you considered caching?
□ Have you tested with realistic data volumes?
□ Have you measured the impact of changes?
□ Does the optimization maintain correctness?
□ Is the code still readable?
```

## Remember

- **Profile first** - Don't guess where the bottleneck is
- **80/20 rule** - 20% of code accounts for 80% of execution time
- **Real data** - Profile with production-like data volumes
- **Diminishing returns** - Getting 2x faster is easy, 10x is hard
- **Correctness > Speed** - Fast but wrong is useless

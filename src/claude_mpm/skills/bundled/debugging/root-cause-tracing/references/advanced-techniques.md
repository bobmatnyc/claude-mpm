# Advanced Tracing Techniques

Advanced methods for tracing bugs when manual inspection isn't sufficient: instrumentation, stack traces, test pollution detection, and async tracing.

## When Manual Tracing Isn't Enough

Manual code inspection works well when:
- Code path is clear
- Stack traces are available
- Single-threaded execution
- You can identify all callers

**Use advanced techniques when:**
- Can't identify which code path triggers the issue
- Multiple async operations interleave
- Race conditions or timing issues
- Need to find which test causes pollution
- External code (libraries) involved
- Production issues you can't reproduce locally

## Stack Trace Instrumentation

### Purpose

Capture complete call stack at strategic points to understand execution flow.

### Basic Stack Trace Capture

```typescript
function suspiciousOperation(param: string) {
  // Capture stack trace BEFORE the operation
  const stack = new Error().stack;
  console.error('DEBUG suspiciousOperation:', {
    param,
    cwd: process.cwd(),
    timestamp: Date.now(),
    stack
  });

  // Now do the operation
  performOperation(param);
}
```

**Key points:**
- Use `console.error()` in tests (regular logger may be suppressed)
- Log BEFORE the operation, not after it fails
- Include context: parameters, environment, state
- Capture stack with `new Error().stack`

### Analyzing Stack Traces

**Run and capture output:**
```bash
npm test 2>&1 | grep 'DEBUG suspiciousOperation'
```

**Look for:**
- Test file names in stack traces
- Line numbers that trigger the call
- Patterns: same test? same parameters?
- Call frequency: how many times called?

**Example output:**
```
DEBUG suspiciousOperation: {
  param: '',
  cwd: '/Users/jesse/project/packages/core',
  stack: 'Error
    at suspiciousOperation (file.ts:10)
    at WorktreeManager.create (worktree.ts:45)
    at Session.initialize (session.ts:78)
    at Project.create (project.ts:23)
    at Test.<anonymous> (project.test.ts:12)
    at Test.run (node:internal/test)'
}
```

**Analysis:** The call originates from `project.test.ts:12` with empty parameter.

### Conditional Instrumentation

Only log when conditions are suspicious:

```typescript
function gitInit(directory: string) {
  // Only log if directory is empty or equals cwd
  if (!directory || directory === process.cwd()) {
    console.error('SUSPICIOUS git init:', {
      directory,
      cwd: process.cwd(),
      nodeEnv: process.env.NODE_ENV,
      stack: new Error().stack
    });
  }

  execFileAsync('git', ['init'], { cwd: directory });
}
```

This reduces noise while capturing problematic cases.

### Stack Trace in Production

**Warning:** Stack traces have performance cost. Use carefully in production.

```typescript
class ErrorTracker {
  private static captureInterval = 100; // Only capture 1% of calls
  private static counter = 0;

  static maybeCapture(operation: string, data: any) {
    this.counter++;
    if (this.counter % this.captureInterval === 0) {
      // Sample 1% of operations
      logger.warn('Sampled operation', {
        operation,
        data,
        stack: new Error().stack
      });
    }
  }
}
```

## Finding Test Pollution

### What is Test Pollution?

Tests that create files, directories, or state that persists after the test completes.

**Common polluters:**
- Creating files/directories outside temp dir
- Not cleaning up in afterEach
- Modifying global state
- Creating git repositories
- Writing to current directory

### Detection Strategy

**Symptoms:**
- Files appear in source code directory
- Tests fail when run together but pass individually
- Side effects from one test affect another
- Cleanup code not running

### Manual Detection

**Check for artifacts after test run:**
```bash
# Before tests
ls -la src/

# Run tests
npm test

# After tests - did anything appear?
ls -la src/
```

**Common artifacts:**
- `.git` directories
- `node_modules/` subdirectories
- Temp files not cleaned up
- Config files created
- Log files

### Automated Detection with Bisection

Use the `find-polluter.sh` script to automatically find which test creates pollution:

```bash
#!/bin/bash
# find-polluter.sh
# Usage: ./find-polluter.sh <artifact> <test-pattern>
# Example: ./find-polluter.sh '.git' 'src/**/*.test.ts'

ARTIFACT=$1
TEST_PATTERN=$2

if [ -z "$ARTIFACT" ] || [ -z "$TEST_PATTERN" ]; then
  echo "Usage: $0 <artifact> <test-pattern>"
  echo "Example: $0 '.git' 'src/**/*.test.ts'"
  exit 1
fi

# Get list of test files
TEST_FILES=($(ls $TEST_PATTERN))

echo "Testing ${#TEST_FILES[@]} files for artifact: $ARTIFACT"

for test_file in "${TEST_FILES[@]}"; do
  echo "Testing: $test_file"

  # Remove artifact if exists
  rm -rf "$ARTIFACT" 2>/dev/null

  # Run single test file
  npm test -- "$test_file"

  # Check if artifact was created
  if [ -e "$ARTIFACT" ]; then
    echo "FOUND POLLUTER: $test_file"
    exit 0
  fi
done

echo "No polluter found"
exit 1
```

**Usage:**
```bash
# Find which test creates .git directory
./find-polluter.sh '.git' 'src/**/*.test.ts'

# Find which test creates node_modules
./find-polluter.sh 'node_modules' 'src/**/*.test.ts'
```

**Advanced version with binary search:**
```bash
#!/bin/bash
# find-polluter-fast.sh - Uses binary search for faster detection

ARTIFACT=$1
TEST_PATTERN=$2
TEST_FILES=($(ls $TEST_PATTERN))

function test_files() {
  local files=("$@")
  rm -rf "$ARTIFACT" 2>/dev/null
  npm test -- "${files[@]}"
  [ -e "$ARTIFACT" ]
}

function binary_search() {
  local files=("$@")
  local count=${#files[@]}

  if [ $count -eq 0 ]; then
    echo "No polluter found"
    return 1
  fi

  if [ $count -eq 1 ]; then
    if test_files "${files[@]}"; then
      echo "FOUND POLLUTER: ${files[0]}"
      return 0
    fi
    return 1
  fi

  # Split in half
  local mid=$((count / 2))
  local left=("${files[@]:0:mid}")
  local right=("${files[@]:mid}")

  # Test left half
  if test_files "${left[@]}"; then
    binary_search "${left[@]}"
  else
    binary_search "${right[@]}"
  fi
}

binary_search "${TEST_FILES[@]}"
```

### Preventing Test Pollution

**Best practices:**
1. **Always use temp directories:**
   ```typescript
   let tempDir: string;

   beforeEach(() => {
     tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'test-'));
   });

   afterEach(() => {
     fs.rmSync(tempDir, { recursive: true });
   });
   ```

2. **Validate test isolation:**
   ```typescript
   // Guard against operations outside temp dir
   if (process.env.NODE_ENV === 'test') {
     if (!directory.includes(os.tmpdir())) {
       throw new Error(`Test safety: operation outside tmpdir: ${directory}`);
     }
   }
   ```

3. **Use cleanup verification:**
   ```typescript
   afterEach(() => {
     // Clean up
     fs.rmSync(tempDir, { recursive: true });

     // Verify no artifacts in source
     const gitInSource = fs.existsSync(path.join(__dirname, '.git'));
     if (gitInSource) {
       throw new Error('Test pollution: .git created in source directory');
     }
   });
   ```

## Async Operation Tracing

### The Challenge

Async operations obscure call chains:
```typescript
async function a() {
  await b();
}

async function b() {
  await c();
}

async function c() {
  throw new Error('Something failed');
}
```

Stack trace might only show:
```
Error: Something failed
  at c (file.ts:10)
```

Missing the full chain: `a → b → c`

### Node.js Async Stack Traces

**Enable async stack traces:**
```bash
node --async-stack-traces test.js
```

Or in code:
```typescript
// At application entry point
Error.stackTraceLimit = 50; // Capture deeper stacks
```

**In package.json:**
```json
{
  "scripts": {
    "test": "node --async-stack-traces ./node_modules/.bin/jest"
  }
}
```

### Trace IDs for Async Operations

When multiple async operations interleave, use trace IDs:

```typescript
import { randomUUID } from 'crypto';
import { AsyncLocalStorage } from 'async_hooks';

const asyncLocalStorage = new AsyncLocalStorage();

function withTraceId<T>(fn: () => T): T {
  const traceId = randomUUID();
  return asyncLocalStorage.run({ traceId }, fn);
}

function getTraceId(): string {
  const store = asyncLocalStorage.getStore() as { traceId: string };
  return store?.traceId || 'no-trace-id';
}

// Usage
async function operationA() {
  console.log(`[${getTraceId()}] Starting operation A`);
  await operationB();
}

async function operationB() {
  console.log(`[${getTraceId()}] Starting operation B`);
  await operationC();
}

// Run with trace ID
await withTraceId(async () => {
  await operationA();
});
```

**Output:**
```
[abc-123] Starting operation A
[abc-123] Starting operation B
[abc-123] Starting operation C
```

All operations from same call chain have same trace ID.

### Debugging Race Conditions

**Problem:** Operations complete in wrong order, causing bugs.

**Solution: Add timing instrumentation:**

```typescript
class TimingTracer {
  private events: Array<{ time: number; event: string; data: any }> = [];

  record(event: string, data: any = {}) {
    this.events.push({
      time: Date.now(),
      event,
      data
    });
  }

  dump() {
    const sorted = this.events.sort((a, b) => a.time - b.time);
    console.error('=== Timing Trace ===');
    let start = sorted[0]?.time || 0;
    sorted.forEach(({ time, event, data }) => {
      console.error(`+${time - start}ms: ${event}`, data);
      start = time;
    });
  }
}

// Usage
const tracer = new TimingTracer();

async function operation() {
  tracer.record('start');

  const promise1 = async1().then(() => tracer.record('async1 done'));
  const promise2 = async2().then(() => tracer.record('async2 done'));

  await Promise.all([promise1, promise2]);

  tracer.record('both done');
  tracer.dump();
}
```

**Output shows operation order:**
```
=== Timing Trace ===
+0ms: start {}
+45ms: async2 done {}
+67ms: async1 done {}
+67ms: both done {}
```

Shows async2 completed before async1.

## Debugging Third-Party Libraries

### When Library Behavior is Unexpected

**Strategy:**
1. Verify you're using the API correctly
2. Check library version and changelog
3. Read library source code
4. Add instrumentation around library calls

### Wrapping Library Calls

```typescript
// Wrap library function to add tracing
import { originalFunction } from 'third-party-lib';

const tracedFunction = (...args: any[]) => {
  console.error('Calling library function:', {
    args,
    stack: new Error().stack
  });

  const result = originalFunction(...args);

  console.error('Library function result:', result);

  return result;
};

// Use traced version
export { tracedFunction as originalFunction };
```

### Checking Library Source

**When to read library source:**
- Documentation is unclear
- Behavior differs from documentation
- Need to understand edge cases
- Debugging library bug

**How to read library source:**
```bash
# Find library location
npm ls third-party-lib

# View source
code node_modules/third-party-lib/src/

# Or on GitHub
open https://github.com/author/third-party-lib
```

## Environment-Specific Issues

### Capturing Environment Context

```typescript
function captureEnvironment() {
  return {
    nodeVersion: process.version,
    platform: process.platform,
    arch: process.arch,
    cwd: process.cwd(),
    env: {
      NODE_ENV: process.env.NODE_ENV,
      CI: process.env.CI,
      // Add relevant env vars
    },
    memory: process.memoryUsage(),
    uptime: process.uptime()
  };
}

// Log with every error
try {
  riskyOperation();
} catch (error) {
  console.error('Operation failed:', {
    error,
    environment: captureEnvironment(),
    stack: error.stack
  });
  throw error;
}
```

### Reproducing Production Issues Locally

**Techniques:**
1. **Match environment:**
   ```bash
   nvm use <production-node-version>
   export NODE_ENV=production
   ```

2. **Use production data (sanitized):**
   ```bash
   # Dump production DB to local
   pg_dump production_db | psql local_db
   ```

3. **Enable production logging locally:**
   ```typescript
   if (process.env.DEBUG_PROD) {
     logger.level = 'debug';
   }
   ```

4. **Replay production requests:**
   ```typescript
   // Log requests in production
   app.use((req, res, next) => {
     logger.info('Request', {
       method: req.method,
       url: req.url,
       headers: req.headers,
       body: req.body
     });
     next();
   });

   // Replay locally
   const productionRequest = loadFromLogs();
   await fetch('http://localhost:3000' + productionRequest.url, {
     method: productionRequest.method,
     headers: productionRequest.headers,
     body: productionRequest.body
   });
   ```

## Performance Profiling for Root Cause

Sometimes "bug" is performance issue. Trace to find bottleneck.

### Node.js Built-in Profiler

```bash
# Generate CPU profile
node --cpu-prof app.js

# Analyze with Chrome DevTools
open chrome://inspect
```

### Custom Performance Tracing

```typescript
class PerformanceTracer {
  private timers = new Map<string, number>();

  start(label: string) {
    this.timers.set(label, Date.now());
  }

  end(label: string): number {
    const start = this.timers.get(label);
    if (!start) throw new Error(`No timer: ${label}`);

    const duration = Date.now() - start;
    console.log(`${label}: ${duration}ms`);
    this.timers.delete(label);
    return duration;
  }

  async measure<T>(label: string, fn: () => T): Promise<T> {
    this.start(label);
    try {
      return await fn();
    } finally {
      this.end(label);
    }
  }
}

// Usage
const tracer = new PerformanceTracer();

await tracer.measure('database query', async () => {
  return await db.query('SELECT ...');
});

await tracer.measure('API call', async () => {
  return await fetch('https://api.example.com');
});
```

**Output:**
```
database query: 1243ms  ← BOTTLENECK FOUND
API call: 89ms
```

## Summary

**Stack traces:** Capture call chains with `new Error().stack`
**Test pollution:** Use bisection to find polluting tests
**Async tracing:** Use trace IDs and async stack traces
**Library issues:** Wrap calls, read source, verify API usage
**Environment issues:** Match production environment, replay requests
**Performance:** Profile to find bottlenecks

**When to use:**
- Manual tracing hits dead end
- Multiple async operations involved
- Test pollution occurring
- Race conditions or timing issues
- Need production-level debugging

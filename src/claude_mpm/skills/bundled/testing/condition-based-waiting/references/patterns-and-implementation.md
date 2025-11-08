# Detailed Patterns and Implementation Guide

This reference provides detailed implementation patterns, common mistakes, and edge cases for condition-based waiting.

## Common Mistakes

### ❌ Polling too fast
```typescript
// BAD: Wastes CPU
await new Promise(r => setTimeout(r, 1));
```

**✅ Fix:** Poll every 10ms
```typescript
await new Promise(r => setTimeout(r, 10)); // Balanced interval
```

### ❌ No timeout
```typescript
// BAD: Loop forever if condition never met
while (true) {
  const result = condition();
  if (result) return result;
  await new Promise(r => setTimeout(r, 10));
}
```

**✅ Fix:** Always include timeout with clear error
```typescript
const startTime = Date.now();
while (true) {
  const result = condition();
  if (result) return result;

  if (Date.now() - startTime > timeoutMs) {
    throw new Error(`Timeout waiting for ${description} after ${timeoutMs}ms`);
  }

  await new Promise(r => setTimeout(r, 10));
}
```

### ❌ Stale data
```typescript
// BAD: Cache state before loop
const state = machine.getState();
await waitFor(() => state === 'ready'); // state never updates!
```

**✅ Fix:** Call getter inside loop for fresh data
```typescript
await waitFor(() => machine.getState() === 'ready'); // Fresh on each poll
```

## When Arbitrary Timeout IS Correct

There are legitimate cases where a fixed timeout is the right approach:

```typescript
// Tool ticks every 100ms - need 2 ticks to verify partial output
await waitForEvent(manager, 'TOOL_STARTED'); // First: wait for condition
await new Promise(r => setTimeout(r, 200));   // Then: wait for timed behavior
// 200ms = 2 ticks at 100ms intervals - documented and justified
```

**Requirements for justified arbitrary timeouts:**
1. First wait for triggering condition (condition-based wait comes first)
2. Based on known timing (not guessing - actual system tick rate)
3. Comment explaining WHY timeout is necessary

## Advanced Patterns

### Waiting with transformation
```typescript
// Wait for event and return transformed data
const userId = await waitFor(
  () => events.find(e => e.type === 'USER_CREATED')?.data.id,
  'user creation event'
);
```

### Waiting with complex conditions
```typescript
// Multiple conditions must be met
await waitFor(
  () => {
    const user = getUser();
    return user?.verified && user?.credits > 0 ? user : undefined;
  },
  'verified user with credits'
);
```

### Waiting with side effects
```typescript
// Log attempts while waiting
let attempts = 0;
await waitFor(
  () => {
    attempts++;
    if (attempts % 10 === 0) {
      console.log(`Still waiting after ${attempts} attempts...`);
    }
    return isReady() || undefined;
  },
  'system ready'
);
```

### Waiting with custom timeouts per condition
```typescript
// Different timeouts for different scenarios
async function waitForDeploy(environment: string) {
  const timeout = environment === 'prod' ? 30000 : 5000;
  return waitFor(
    () => checkDeployStatus(environment),
    `${environment} deployment`,
    timeout
  );
}
```

## Domain-Specific Helpers

When you have common waiting scenarios, create domain-specific helpers:

```typescript
// Event-based waiting
async function waitForEvent(
  manager: EventManager,
  eventType: string,
  timeoutMs = 5000
) {
  return waitFor(
    () => manager.getEvents().find(e => e.type === eventType),
    `event ${eventType}`,
    timeoutMs
  );
}

// Count-based waiting
async function waitForEventCount(
  manager: EventManager,
  minCount: number,
  timeoutMs = 5000
) {
  return waitFor(
    () => {
      const events = manager.getEvents();
      return events.length >= minCount ? events : undefined;
    },
    `at least ${minCount} events`,
    timeoutMs
  );
}

// Pattern matching waiting
async function waitForEventMatch(
  manager: EventManager,
  matcher: (event: Event) => boolean,
  timeoutMs = 5000
) {
  return waitFor(
    () => manager.getEvents().find(matcher),
    'event matching predicate',
    timeoutMs
  );
}
```

See @example.ts for complete working implementations from real debugging session.

## Debugging Tips

### Add descriptive error messages
```typescript
// GOOD: Clear what failed
await waitFor(
  () => orders.find(o => o.status === 'SHIPPED'),
  'order to be shipped',
  5000
);
// Error: "Timeout waiting for order to be shipped after 5000ms"

// BETTER: Include context
await waitFor(
  () => orders.find(o => o.id === orderId && o.status === 'SHIPPED'),
  `order ${orderId} to be shipped`,
  5000
);
// Error: "Timeout waiting for order abc-123 to be shipped after 5000ms"
```

### Log current state on timeout
```typescript
async function waitForWithDebug<T>(
  condition: () => T | undefined | null | false,
  description: string,
  getCurrentState: () => any,
  timeoutMs = 5000
): Promise<T> {
  const startTime = Date.now();

  while (true) {
    const result = condition();
    if (result) return result;

    if (Date.now() - startTime > timeoutMs) {
      const state = getCurrentState();
      throw new Error(
        `Timeout waiting for ${description} after ${timeoutMs}ms. ` +
        `Current state: ${JSON.stringify(state)}`
      );
    }

    await new Promise(r => setTimeout(r, 10));
  }
}
```

## Performance Considerations

### Poll interval trade-offs
- **1ms**: Too fast, wastes CPU (10,000 checks/second)
- **10ms**: Good default, responsive (100 checks/second)
- **50ms**: Acceptable for slow operations (20 checks/second)
- **100ms+**: Only for very slow operations or known timing

### Choose appropriate timeout values
```typescript
// Fast operations - short timeout
await waitFor(() => cache.get(key), 'cache hit', 1000);

// Network operations - medium timeout
await waitFor(() => fetchStatus(), 'API response', 5000);

// External systems - long timeout
await waitFor(() => checkDeployment(), 'deployment complete', 30000);
```

### Avoid expensive condition checks
```typescript
// BAD: Expensive regex on every poll
await waitFor(() => /complex.*regex.*pattern/.test(getLargeString()), ...);

// GOOD: Cache expensive computations
let parsed;
await waitFor(() => {
  const str = getString();
  parsed = parsed || expensiveParse(str);
  return parsed.isReady;
}, ...);
```

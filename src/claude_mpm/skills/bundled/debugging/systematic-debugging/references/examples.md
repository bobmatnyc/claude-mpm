# Real-World Debugging Examples

> **Part of**: [Systematic Debugging](../SKILL.md)
> **Category**: debugging
> **Reading Level**: Intermediate

## Purpose

Real-world scenarios demonstrating systematic debugging in action, with step-by-step walkthroughs showing how to apply the four-phase process.

## Example 1: API Integration Failure

### Symptom

```
Error: API request failed with status 401
Tests pass locally but fail in CI
```

### Phase 1: Root Cause Investigation

**Read Error:**
```
HTTP 401 Unauthorized
Response: {"error": "Invalid API key"}
```

**Reproduce:**
- ✓ Runs successfully locally
- ✗ Fails in CI every time
- Difference: Local has `.env` file, CI uses environment variables

**Check Changes:**
```bash
git log --oneline --since="3 days ago"
# Found: "Add API key authentication" 2 days ago
```

**Gather Evidence:**
```bash
# In CI config
echo "API_KEY present: ${API_KEY:+YES}${API_KEY:-NO}"
# Output: API_KEY present: NO

# In local env
echo $API_KEY
# Output: sk-abc123...
```

**Root cause identified**: API_KEY environment variable not set in CI

### Phase 2: Pattern Analysis

**Find working examples:**
```yaml
# Other workflows using secrets
env:
  DATABASE_URL: ${{ secrets.DATABASE_URL }}  # Works
  API_KEY: ${{ secrets.API_KEY }}            # Missing!
```

**Identify difference**: DATABASE_URL configured in GitHub secrets, API_KEY is not

### Phase 3: Hypothesis and Testing

**Hypothesis**: "API_KEY secret not configured in GitHub repository settings"

**Test**: Check repository settings → Secrets → API_KEY not found

**Confirmed**: Secret needs to be added

### Phase 4: Implementation

**Test case** (manual verification):
```bash
# After adding secret, check in CI
echo "API_KEY set: ${API_KEY:+YES}"
# Expected: YES
```

**Fix**: Add API_KEY to GitHub repository secrets

**Verify**: CI build passes, API calls succeed

**Time**: 15 minutes with systematic approach vs 2+ hours guessing

## Example 2: Intermittent Test Failure

### Symptom

```
Test 'processes user data' fails randomly
Passes 80% of the time, fails 20%
No clear pattern to failures
```

### Phase 1: Root Cause Investigation

**Read Error:**
```
Expected: { id: 1, name: 'Alice', role: 'admin' }
Received: { id: 1, name: 'Alice', role: 'user' }
```

**Reproduce:**
- Run test 10 times → fails 2-3 times
- Failure seems random
- Not time-dependent

**Check Recent Changes:**
```bash
git diff HEAD~1 -- tests/user.test.ts
# No changes to test
# But role assignment logic changed
```

**Gather Evidence:**
```typescript
// Add logging
test('processes user data', async () => {
  console.log('Test start:', new Date().toISOString());
  const user = await createUser({ name: 'Alice', role: 'admin' });
  console.log('User created:', user);
  console.log('Role at creation:', user.role);
  // ...
});
```

**Pattern found**: Role correct at creation, changes later

**Trace Data Flow:**
```typescript
// Step through code
createUser() → saveToDatabase() → applyDefaults() → role changes!

// applyDefaults has bug:
function applyDefaults(user) {
  return {
    ...user,
    role: user.role || 'user'  // BUG: 'user' overwrites existing role
  };
}
```

### Phase 2: Pattern Analysis

**Find working examples:**
```typescript
// Correct default handling
function applyDefaults(user) {
  return {
    role: 'user',  // Default first
    ...user,       // Then overrides
  };
}
```

**Identify difference**: Order of spread operator matters

### Phase 3: Hypothesis and Testing

**Hypothesis**: "Spread operator order causes role to be overwritten with default"

**Test**:
```typescript
// Minimal test
const result = { ...{ name: 'Alice', role: 'admin' }, role: 'user' };
console.log(result.role);  // 'user' - overwrites!

const correct = { role: 'user', ...{ name: 'Alice', role: 'admin' } };
console.log(correct.role);  // 'admin' - correct!
```

**Confirmed**: Spread order is the issue

### Phase 4: Implementation

**Test case**:
```typescript
test('preserves existing role when applying defaults', () => {
  const user = { name: 'Alice', role: 'admin' };
  const result = applyDefaults(user);
  expect(result.role).toBe('admin');
});
```

**Fix**:
```typescript
function applyDefaults(user) {
  return {
    role: 'user',  // Default first
    status: 'active',
    ...user,       // User values override
  };
}
```

**Verify**: Test passes 100 consecutive times, no more intermittent failures

## Example 3: Performance Degradation

### Symptom

```
Dashboard loads in 5+ seconds (was <1 second)
Users complaining about slowness
No recent deploys
```

### Phase 1: Root Cause Investigation

**Read Error**: No explicit error, just slow performance

**Reproduce**:
```bash
# Measure consistently
time curl http://localhost:3000/dashboard
# ~5.2 seconds consistently
```

**Check Recent Changes**:
```bash
git log --oneline --since="1 week ago" -- src/dashboard/
# No code changes to dashboard

git log --oneline --since="1 week ago" -- database/
# Found: "Add index to improve user queries" 3 days ago
```

**Gather Evidence**:
```sql
-- Enable query logging
SET log_min_duration_statement = 100;

-- Analyze slow queries
EXPLAIN ANALYZE SELECT * FROM user_activity
WHERE user_id = 123
ORDER BY created_at DESC;

-- Output shows: Seq Scan on user_activity (cost=0.00..45678.23 rows=500000)
```

**Pattern found**: Query doing sequential scan despite new index

### Phase 2: Pattern Analysis

**Check index**:
```sql
\d user_activity
-- Indexes:
--   "user_activity_user_created_idx" btree (user_id, created_at)

-- But query doesn't use it!
```

**Find working examples**:
```sql
-- This query uses index
SELECT * FROM user_sessions WHERE user_id = 123;

-- Our query doesn't - why?
SELECT * FROM user_activity WHERE user_id = 123 ORDER BY created_at DESC;
```

**Identify difference**: ORDER BY direction (DESC) doesn't match index (ASC)

### Phase 3: Hypothesis and Testing

**Hypothesis**: "Index not used because ORDER BY DESC doesn't match index order ASC"

**Test**:
```sql
-- Drop and recreate with DESC
DROP INDEX user_activity_user_created_idx;
CREATE INDEX user_activity_user_created_idx
  ON user_activity (user_id, created_at DESC);

-- Test query performance
EXPLAIN ANALYZE SELECT * FROM user_activity
WHERE user_id = 123
ORDER BY created_at DESC;

-- Output: Index Scan using user_activity_user_created_idx (cost=0.43..123.45)
```

**Confirmed**: Index now used, performance improved

### Phase 4: Implementation

**Test case**:
```typescript
test('dashboard loads in under 1 second', async () => {
  const start = Date.now();
  await fetch('/dashboard');
  const duration = Date.now() - start;
  expect(duration).toBeLessThan(1000);
});
```

**Fix**: Update index definition to match query pattern

**Verify**:
- Dashboard loads in 0.4 seconds
- All other queries still work
- No performance regressions

## Example 4: Multi-Component System Failure

### Symptom

```
iOS app code signing fails in CI
Error: "No identity found"
Works on developer machines
```

### Phase 1: Root Cause Investigation

**Read Error**:
```
error: No signing certificate "iOS Distribution" found
codesign failed with exit code 1
```

**Reproduce**:
- ✓ Works locally with Xcode
- ✗ Fails in CI every time
- Multi-layer system: CI → build → keychain → signing

**Gather Evidence at Each Layer**:
```bash
# Layer 1: CI environment
echo "=== Secrets available ==="
echo "CERT_P12: ${CERT_P12:+SET}${CERT_P12:-UNSET}"
echo "CERT_PASSWORD: ${CERT_PASSWORD:+SET}${CERT_PASSWORD:-UNSET}"
# Output: Both SET

# Layer 2: Keychain setup
echo "=== Keychain state ==="
security list-keychains
security find-identity -v -p codesigning
# Output: No identities found

# Layer 3: Certificate import
security import cert.p12 -k ~/Library/Keychains/build.keychain -P "$CERT_PASSWORD" -T /usr/bin/codesign
echo "Import exit code: $?"
# Output: Exit code 0 (success)

# But still no identity!
security find-identity -v -p codesigning
# Output: Still no identities
```

**Pattern found**: Import succeeds but identity not available

### Phase 2: Pattern Analysis

**Find working examples**:
```bash
# Local machine
security find-identity -v
# Shows many identities in login keychain

# CI (after import)
security find-identity -v
# Shows nothing
```

**Compare keychain paths**:
```bash
# Local
security list-keychains
# "~/Library/Keychains/login.keychain-db"

# CI
security list-keychains
# Custom build.keychain not in search list!
```

**Identify difference**: Keychain created but not added to search list

### Phase 3: Hypothesis and Testing

**Hypothesis**: "Identity imported but keychain not in search list, so codesign can't find it"

**Test**:
```bash
# Add keychain to search list
security list-keychains -s ~/Library/Keychains/build.keychain-db

# Check if identity now visible
security find-identity -v -p codesigning
# Output: Shows imported identity!
```

**Confirmed**: Keychain search list was the issue

### Phase 4: Implementation

**Test case** (integration test in CI):
```bash
# After fix, verify identity available
security find-identity -v -p codesigning | grep "iOS Distribution" || exit 1
```

**Fix**:
```bash
# Complete keychain setup
security create-keychain -p "$KEYCHAIN_PASSWORD" build.keychain
security list-keychains -s ~/Library/Keychains/build.keychain-db  # Add to search
security unlock-keychain -p "$KEYCHAIN_PASSWORD" build.keychain
security import cert.p12 -k build.keychain -P "$CERT_PASSWORD" -T /usr/bin/codesign
security set-key-partition-list -S apple-tool:,apple: -s -k "$KEYCHAIN_PASSWORD" build.keychain
```

**Verify**: Code signing succeeds in CI

**Time**: 45 minutes systematic vs 4+ hours of random attempts

## Key Patterns Across Examples

### Common Root Causes
1. **Configuration differences** (Example 1): Local vs CI environment
2. **Timing/order issues** (Example 2): Race conditions, initialization order
3. **Hidden assumptions** (Example 3): Index order matching query
4. **Multi-layer problems** (Example 4): Issue at component boundaries

### Systematic Approach Benefits
- **Faster resolution**: 15-45 minutes vs 2-4 hours
- **First-time fix**: 95%+ success rate
- **No new bugs**: Targeted fixes don't break other things
- **Knowledge gained**: Understanding root cause prevents recurrence

### Red Flags That Would Have Failed
- "Just try adding the secret" (skips investigation)
- "Add try-catch around failing code" (masks problem)
- "Increase timeout" (hides real issue)
- "Maybe clear cache?" (random guess)

## Summary

Systematic debugging:
1. Saves time (15-45 min vs 2-4 hours)
2. Fixes correctly first time (95% vs 40%)
3. Prevents new bugs (targeted vs random changes)
4. Builds understanding (root cause vs symptom)

## Related References

- [Workflow](workflow.md): Complete four-phase process
- [Troubleshooting](troubleshooting.md): When debugging gets stuck
- [Anti-patterns](anti-patterns.md): Common mistakes to avoid

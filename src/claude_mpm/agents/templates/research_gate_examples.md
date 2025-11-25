# Research Gate Protocol Examples

## Example 1: Research Gate Triggered

```
User: "Add caching to improve performance"

PM Analysis:
- Ambiguous: which component? what metric? what cache?
- Multiple approaches: Redis, Memcached, in-memory
- Research needed: YES

PM Action:
Step 1: ✅ Determined research needed
Step 2: Delegate to Research:
  "Research caching requirements and approach for performance improvement"
Step 3: Research returns:
  - Target: API response time <200ms (currently 800ms)
  - Recommended: Redis for session caching
  - Files: src/api/middleware/cache.js
  - Dependencies: redis, ioredis
Step 4: Delegate to Engineer with research context
  "Implement Redis caching per Research findings..."

Result: ✅ Implementation based on validated requirements
```

## Example 2: Research Gate Skipped (Appropriate)

```
User: "Update package version to 1.2.3 in package.json"

PM Analysis:
- Clear: specific file, specific action, specific value
- Simple: no ambiguity, no multiple approaches
- Research needed: NO

PM Action:
Skip Research Gate → Delegate directly to Engineer
"Update version in package.json to 1.2.3"

Result: ✅ Appropriate skip, task is trivial
```

## Example 3: Research Gate Violated (PM Error)

```
User: "Add authentication"

PM Analysis:
- Ambiguous: which auth method?
- Multiple approaches: OAuth, JWT, sessions
- Research needed: YES

❌ PM VIOLATION: Skips Research, delegates directly:
"Implement authentication using JWT"

Problems:
- PM made assumption (JWT) without validation
- User might want OAuth
- Security requirements not researched
- Implementation may need rework

Correct Action:
Step 1: Recognize ambiguity
Step 2: Delegate to Research first
Step 3: Validate findings (which auth method user wants)
Step 4: Then delegate implementation with validated approach
```

## Decision Matrix Reference

| Scenario | Research Needed? | Reason |
|----------|------------------|--------|
| "Fix login bug" | ✅ YES | Ambiguous: which bug? which component? |
| "Fix bug where /api/auth/login returns 500 on invalid email" | ❌ NO | Clear: specific endpoint, symptom, trigger |
| "Add authentication" | ✅ YES | Multiple approaches: OAuth, JWT, session-based |
| "Add JWT authentication using jsonwebtoken library" | ❌ NO | Clear: specific approach specified |
| "Optimize database" | ✅ YES | Unclear: which queries? what metric? target? |
| "Optimize /api/users query: target <100ms from current 500ms" | ❌ NO | Clear: specific query, metric, baseline, target |
| "Implement feature X" | ✅ YES | Needs requirements, acceptance criteria |
| "Build dashboard" | ✅ YES | Needs design, metrics, data sources |

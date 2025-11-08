# Coordination Patterns

Complete guide to identifying independent domains, dispatching agents, and integrating their work.

## Domain Identification Patterns

### The Independence Test

Before dispatching parallel agents, verify true independence:

```
✓ Independent domains:
  - Different test files with unrelated functionality
  - Different subsystems (auth, payments, notifications)
  - Different bug reports from different users
  - Different data processing pipelines

✗ Not independent:
  - Tests failing due to shared database state
  - Cascading failures (one root cause, many symptoms)
  - Features that share core business logic
  - Components with tight coupling
```

### Domain Grouping Strategy

**By Test File:**
```
File A: tool-approval-flow.test.ts
File B: batch-completion.test.ts
File C: abort-handling.test.ts
→ 3 domains, each gets one agent
```

**By Subsystem:**
```
Subsystem A: Authentication module
Subsystem B: Payment processing
Subsystem C: Email notifications
→ 3 domains, clear boundaries
```

**By Feature:**
```
Feature A: User registration flow
Feature B: Product search
Feature C: Shopping cart
→ 3 domains, minimal overlap
```

### Anti-Pattern: False Independence

```
❌ BAD: Treat as independent when they're not
Problem 1: Login tests failing
Problem 2: Dashboard tests failing (needs login)
Problem 3: User profile tests failing (needs login)

→ NOT independent! Root cause is login.
→ Solution: Single agent investigates login first
```

## Dispatch Strategies

### Strategy 1: Parallel Task Creation

**Best for:** Clear, well-defined problems with no discovery needed

```typescript
// All tasks created at once
Task("Fix authentication flow - login.test.ts 3 failures")
Task("Fix payment processing - checkout.test.ts 2 failures")
Task("Fix email service - notifications.test.ts 4 failures")

// Agents work simultaneously
// You review results when all complete
```

**Advantages:**
- Maximum parallelization
- Fastest total time
- Clear workload distribution

**Disadvantages:**
- Requires upfront domain analysis
- Risk of conflicts if domains overlap
- Hard to adjust if one agent finds systemic issue

### Strategy 2: Sequential with Parallel Bursts

**Best for:** Mixed certainty - some problems clear, others need investigation

```typescript
// Phase 1: Investigate unclear areas
Task("Investigate root cause of database connection errors")

// Wait for result...

// Phase 2: Based on findings, dispatch parallel fixes
Task("Fix connection pool exhaustion in auth service")
Task("Fix timeout handling in payment service")
Task("Fix retry logic in notification service")
```

**Advantages:**
- Reduces risk of false independence
- Adapts to discoveries
- Maintains parallelization where safe

**Disadvantages:**
- Slower than pure parallel
- Requires decision point between phases

### Strategy 3: Hierarchical Dispatch

**Best for:** Large-scale problems with clear subsystem boundaries

```typescript
// Level 1: Subsystem leads
Task("Auth subsystem: Investigate and delegate 5 test failures")
Task("Payments subsystem: Investigate and delegate 4 test failures")

// Level 2: Each subsystem agent dispatches focused tasks
// Auth agent creates:
  Task("Fix OAuth token refresh logic")
  Task("Fix session timeout handling")

// Payments agent creates:
  Task("Fix Stripe webhook handling")
  Task("Fix refund processing")
```

**Advantages:**
- Scales to large problem sets
- Domain experts coordinate sub-tasks
- Natural verification points

**Disadvantages:**
- Higher coordination overhead
- More complex integration
- Requires clear subsystem boundaries

## Integration Workflows

### Integration Pattern 1: Summary Review

**When agents return:**

1. **Read all summaries first**
   - Don't look at code yet
   - Understand what each agent did
   - Identify potential conflicts

2. **Check for overlaps**
   - Did multiple agents edit same files?
   - Did one agent's fix depend on another's?
   - Are there conflicting approaches?

3. **Verify independently**
   - Run each agent's tests in isolation
   - Confirm each fix works alone
   - Check no new failures introduced

4. **Integrate progressively**
   - Merge one agent's work at a time
   - Run full suite after each merge
   - Isolate which merge causes conflicts

### Integration Pattern 2: Conflict Resolution

**When conflicts arise:**

```
Agent A changed: auth.service.ts (lines 50-60)
Agent B changed: auth.service.ts (lines 55-65)
→ Overlap detected!

Resolution steps:
1. Understand both changes - why did each agent change this?
2. Check if both changes needed - or is one redundant?
3. Determine merge strategy:
   a) One change supersedes other
   b) Both changes needed, manual merge
   c) Neither optimal, new solution needed
4. Verify merged version passes both agents' tests
```

### Integration Pattern 3: Full Suite Verification

**After integration:**

```bash
# Run complete test suite
npm test

# Check for unexpected failures
# - Tests that weren't part of any agent's scope
# - Integration points between fixed domains
# - System-level behavior

# If new failures:
# 1. Identify which agent's changes caused it
# 2. Understand why (missing integration consideration?)
# 3. Fix with minimal change
# 4. Re-verify
```

## Scope Management

### Clear Scope Definition

**Good scope definition:**
```markdown
Agent scope: Fix all failures in src/auth/login.test.ts

Allowed to change:
- src/auth/login.service.ts
- src/auth/login.controller.ts
- Test file itself (if testing wrong behavior)

NOT allowed to change:
- Other auth modules
- Shared utilities (without consultation)
- Database schema
- API contracts (breaking changes)

Expected output:
- Summary of root cause
- List of files changed
- Explanation of fix approach
- Confirmation all 3 tests now pass
```

**Bad scope definition:**
```markdown
❌ "Fix the auth issues"
   → Too vague, agent doesn't know where to focus

❌ "Make all tests pass"
   → Too broad, agent will change anything

❌ "Fix login.test.ts but use your judgment"
   → Unclear constraints, unpredictable changes
```

### Scope Boundaries

**Enforce clear boundaries:**

```
Agent A domain: Authentication flow
├── login.service.ts
├── logout.service.ts
├── session.manager.ts
└── auth.test.ts

Agent B domain: User profile
├── profile.service.ts
├── profile.controller.ts
└── profile.test.ts

Shared boundary (coordination needed):
└── user.model.ts (both agents might need to modify)
    → Solution: Neither agent changes it without asking
    → Or: Designate one agent as owner
```

## Communication Patterns

### Agent-to-Coordinator Communication

**What agents should report:**

```markdown
# Agent Return Template

## Domain
Which test file / subsystem I worked on

## Root Cause
What was actually broken (not symptoms)

## Changes Made
- File A: Modified lines 50-60 to fix X
- File B: Added validation for Y
- Test file: Adjusted expectations for Z

## Verification
All 3 tests in my scope now pass:
✓ Test 1: login with valid credentials
✓ Test 2: login with invalid credentials
✓ Test 3: login with expired session

## Dependencies Discovered
None - my changes are isolated

## Risks
Watch for: Session timeout edge cases in other tests
```

### Coordinator-to-Agent Communication

**Clear task assignment:**

```markdown
# Task for Agent

## Your Scope
Fix 3 failures in src/auth/login.test.ts:
1. "should handle expired sessions" - throws TypeError
2. "should refresh tokens" - token undefined
3. "should logout on invalid token" - logout not called

## Context
These started failing after we upgraded auth library v2→v3
Library changed: TokenService API now async

## Constraints
- Fix the implementation or tests (your judgment)
- Don't change other auth files unless necessary
- Don't modify TokenService (external library)

## Expected Output
- Root cause explanation
- List of changes
- Confirmation tests pass
```

## Performance Optimization

### Minimizing Coordination Overhead

**Trade-off analysis:**

```
1 problem:  Sequential (no parallelization benefit)
2 problems: Marginal benefit (coordination overhead ≈ parallelization gain)
3 problems: Clear benefit (coordination < parallelization gain)
5+ problems: High benefit (scales well)

Exception: Very quick fixes (<5 min each)
→ Sequential might be faster due to low task-switching cost
```

### Optimal Agent Count

```
Problems: 3-5   → Agents: 3-5 (1:1 mapping)
Problems: 6-10  → Agents: 4-6 (group related problems)
Problems: 10+   → Agents: 5-8 (hierarchical dispatch)

Maximum: ~8 agents (human coordination limit)
→ Beyond 8: Use hierarchical pattern
```

## Advanced Patterns

### Pattern: Dependency-Aware Dispatch

**When problems have loose dependencies:**

```
Problem A: Must fix first (others depend on it)
Problems B, C, D: Independent once A is fixed

Dispatch strategy:
1. Agent 1 fixes A
2. After A complete, dispatch B, C, D in parallel
3. Integrate all together
```

### Pattern: Speculative Parallel

**When independence is likely but uncertain:**

```
Dispatch all agents in parallel BUT:
- Each agent starts with investigation phase
- Agents report if they find shared dependencies
- Coordinator halts others if one finds systemic issue

Example:
3 agents start investigating 3 test files
Agent 1 discovers: "All failures due to config loading bug"
→ Coordinator halts Agent 2 & 3
→ Agent 1 fixes config bug
→ All tests pass
```

### Pattern: Progressive Integration

**For large-scale parallel work:**

```
8 agents working on different subsystems

Integration phases:
1. Integrate auth agents (A1, A2) → Verify auth suite
2. Integrate payment agents (P1, P2) → Verify payment suite
3. Integrate all auth + payments → Verify integration
4. Continue with notifications, etc.

Benefit: Catch conflicts early, smaller integration surface
```

## Common Mistakes

### Mistake 1: Premature Parallelization

```
❌ 5 test failures, immediately dispatch 5 agents
✓ Read all 5 failures, identify if root cause is shared
  → Shared: 1 agent fixes root cause
  → Independent: Dispatch in parallel
```

### Mistake 2: Ignoring Soft Dependencies

```
❌ "Files are separate, must be independent"
✓ Check runtime dependencies:
  - Shared database state
  - Service initialization order
  - Global configuration
  - Shared caches/singletons
```

### Mistake 3: No Integration Plan

```
❌ Dispatch agents, merge all changes at once, run tests
✓ Plan integration:
  - Which order to merge?
  - How to verify each step?
  - What to do if conflicts arise?
```

### Mistake 4: Vague Boundaries

```
❌ "Fix auth stuff" + "Fix user stuff"
   → Overlap potential: What is "auth" vs "user"?

✓ "Fix login.test.ts" + "Fix profile.test.ts"
   → Clear file-based boundary
```

## Verification Checklist

Before dispatching:
- [ ] Verified problems are truly independent
- [ ] Defined clear scope for each agent
- [ ] Identified shared boundaries / risks
- [ ] Planned integration approach
- [ ] Estimated if parallelization worth overhead

During execution:
- [ ] Monitoring for agents reporting dependencies
- [ ] Ready to halt if systemic issue found
- [ ] Tracking which agent is working on what

After completion:
- [ ] Read all summaries before integrating
- [ ] Checked for file/scope overlaps
- [ ] Verified each fix in isolation
- [ ] Progressive integration with verification
- [ ] Full suite pass with all changes

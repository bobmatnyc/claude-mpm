# Prompting Guide for Claude MPM

**Version**: 1.0.0
**Last Updated**: January 2026
**Audience**: All MPM users

---

## Table of Contents

1. [Overview](#overview)
2. [How MPM Differs from Regular Claude](#how-mpm-differs-from-regular-claude)
3. [General Prompting Principles](#general-prompting-principles)
4. [TxDD: Test-Driven Development via Documentation](#txdd-test-driven-development-via-documentation)
5. [Common Prompt Patterns](#common-prompt-patterns)
6. [Anti-Patterns to Avoid](#anti-patterns-to-avoid)
7. [Before/After Examples](#beforeafter-examples)
8. [See Also](#see-also)

---

## Overview

This guide teaches you how to write effective prompts for Claude MPM to get the best results. MPM uses a **multi-agent orchestration model** where a PM (Project Manager) agent coordinates with specialized agents to accomplish your goals.

**Key Insight**: The better your prompt, the better MPM can delegate to the right agents and deliver quality results.

---

## How MPM Differs from Regular Claude

### Regular Claude Usage
- **Single Agent**: One Claude instance handles everything
- **Direct Execution**: You ask, Claude does it immediately
- **No Specialization**: Same capabilities for all tasks

### Claude MPM Usage
- **Multi-Agent System**: PM coordinates with 47+ specialized agents
- **Intelligent Delegation**: PM analyzes your request and routes to appropriate specialists
- **Domain Expertise**: Each agent (Engineer, QA, Security, Ops, etc.) has specialized knowledge and skills
- **Workflow Orchestration**: Complex tasks flow through multiple agents automatically

### What This Means for Prompting

**With MPM, you communicate with the PM agent**, who:
- Analyzes your request
- Determines which specialist agents are needed
- Delegates work appropriately
- Verifies results meet requirements
- Coordinates multi-step workflows

**Your prompts should**:
- State the goal clearly (what you want to achieve)
- Specify acceptance criteria (how you'll know it's done)
- Indicate preferences (tests, no commits, specific approaches)
- Let PM decide *how* to accomplish it (agent delegation, workflow)

---

## General Prompting Principles

### 1. Be Clear About Your Goal

**Good**: State what you want to accomplish
```
"Implement user authentication with email/password"
```

**Better**: Include success criteria
```
"Implement user authentication with email/password.
Users should be able to register, login, and logout.
Passwords must be hashed before storage."
```

**Best**: Add testing requirements
```
"Implement user authentication with email/password.
Requirements:
- Users can register with email/password
- Passwords must be 8+ characters with at least 1 number
- Passwords are hashed before storage (bcrypt)
- Users can login and logout
- Write tests first, then implementation"
```

### 2. Specify When You Want Tests

MPM supports **TxDD (Test-Driven Development via Documentation)** - tell PM when you want tests:

**For new features**:
```
"Add pagination to the user list API. Write tests first."
```

**For bug fixes**:
```
"Fix the bug where users can't login with special characters in password.
Write a regression test that fails first, then fix the bug."
```

**When you DON'T want tests** (be explicit):
```
"Add a console.log statement for debugging. No tests needed."
```

### 3. Control Commit Behavior

**During debugging** (don't commit):
```
"Debug why the payment webhook is failing.
Don't commit anything - just investigate and report findings."
```

**When you want commits**:
```
"Refactor the authentication module to use dependency injection.
Ensure all tests pass, then commit the changes."
```

**Default behavior**: PM will commit when implementation is complete and tests pass.

### 4. Leverage Agent Specialization

You usually don't need to specify agents - PM will delegate appropriately. But you can guide the workflow:

**Implicit delegation** (recommended):
```
"Add rate limiting to the API endpoints"
```
→ PM delegates to Engineer agent

**Explicit workflow**:
```
"Add rate limiting to the API endpoints, then have QA verify it works correctly"
```
→ PM delegates to Engineer, then QA agent

**Security-critical**:
```
"Implement OAuth2 authentication. Make sure Security reviews the implementation."
```
→ PM delegates to Engineer, then Security agent

### 5. Provide Context When Needed

**For bug fixes**:
```
"Fix the bug where the shopping cart total is wrong when applying discounts.
The issue started after the recent refactoring in commit abc123.
Write a failing test that reproduces the bug, then fix it."
```

**For feature additions**:
```
"Add export functionality to the reports page.
Users should be able to export reports as CSV or PDF.
Follow the same pattern used in the invoices export feature."
```

**For refactoring**:
```
"Refactor the user validation logic to use a shared validator.
The same validation is duplicated in 3 places: registration, profile update, and admin creation.
Extract to a single validator, ensure all tests pass."
```

---

## TxDD: Test-Driven Development via Documentation

### What is TxDD?

**TxDD (Test-Driven Development via Documentation)** is MPM's approach to building quality software:

1. **Specification**: Clearly document what you want (in your prompt)
2. **Tests**: Write failing tests that verify the specification
3. **Implementation**: Write minimal code to make tests pass
4. **Verification**: Confirm tests pass and requirements are met

**Core Principle**: If you didn't watch the test fail first, you don't know if it tests the right thing.

### Why TxDD Matters

**Benefits**:
- **Catches bugs early**: Tests fail before code exists, proving they work
- **Documents behavior**: Tests show exactly what code should do
- **Prevents regressions**: Future changes can't break existing functionality
- **Enables refactoring**: Change code confidently with test safety net
- **Improves design**: Writing tests first leads to better API design

**Real-world impact**:
- Test-first: 95%+ first-time correctness
- Test-after: 40% first-time correctness
- TxDD time: 25-45 minutes per feature (including tests)
- Non-TDD time: 15 minutes coding + 60-120 minutes debugging

### The TxDD Workflow

#### 1. Write Specification in Prompt

**Example**:
```
"Implement email validation function.
Requirements:
- Must contain @ symbol
- Must have text before and after @
- Should trim whitespace
- Should reject multiple @ symbols"
```

#### 2. Request Tests First

**Add to prompt**:
```
"Write tests first following TDD approach."
```

or more explicitly:

```
"Follow the RED/GREEN/REFACTOR cycle:
1. Write failing tests
2. Verify they fail for the right reason
3. Implement minimal code to pass
4. Verify all tests pass
5. Refactor if needed"
```

#### 3. PM Delegates to Engineer

Engineer agent will:
1. **RED**: Write failing test showing desired behavior
2. **VERIFY RED**: Run test, confirm it fails correctly
3. **GREEN**: Write minimal code to pass test
4. **VERIFY GREEN**: Run test, confirm it passes
5. **REFACTOR**: Clean up code while keeping tests green
6. **REPEAT**: Next test for next requirement

### TxDD Prompt Examples

#### Example 1: New Feature
```
"Implement retry logic for failed API calls.
Requirements:
- Retry up to 3 times
- Use exponential backoff (1s, 2s, 4s)
- Throw error if all retries fail
- Log each retry attempt

Write tests first using TDD approach, then implement."
```

**What happens**:
1. Engineer writes test: "retries failed operation 3 times"
2. Test fails (function doesn't exist)
3. Engineer implements basic retry
4. Test passes
5. Engineer writes test: "uses exponential backoff"
6. Test fails (no backoff logic)
7. Engineer adds backoff
8. Test passes
9. Continue for remaining requirements

#### Example 2: Bug Fix
```
"Fix bug where users can't save profiles with apostrophes in their name.
Steps:
1. Write a failing test that reproduces the bug (e.g., O'Brien)
2. Verify the test fails
3. Fix the SQL escaping issue
4. Verify the test passes
5. Run all tests to ensure no regressions"
```

#### Example 3: Refactoring
```
"Refactor the payment processing module to separate concerns.
Current code mixes validation, processing, and logging in one function.
Steps:
1. Ensure all current tests pass (baseline)
2. Extract validation to separate function
3. Verify tests still pass
4. Extract logging to separate function
5. Verify tests still pass
6. Extract processing to separate function
7. Verify all tests pass
8. Refactor for clarity while keeping tests green"
```

### Acceptance Criteria Format

Use clear acceptance criteria to define "done":

```
"Add user search functionality.

Acceptance Criteria:
✓ Users can search by name (partial match, case-insensitive)
✓ Users can search by email (exact match)
✓ Search returns results sorted by relevance
✓ Empty search returns all users
✓ Invalid search parameters return 400 error

Tests should verify each criterion before implementation."
```

### When to Skip TDD

Sometimes TDD isn't appropriate - be explicit:

```
"Add a TODO comment above the authentication function.
No tests needed - just documentation."
```

```
"Create a proof-of-concept for WebRTC video chat.
This is exploratory code - skip tests for now."
```

**Rule of thumb**: If it's going to production, use TDD. If it's temporary/exploratory, you can skip it.

---

## Common Prompt Patterns

### Pattern 1: Feature Implementation

**Template**:
```
"Implement [feature name] that [description].
Requirements:
- [requirement 1]
- [requirement 2]
- [requirement 3]
Write tests first, then implementation."
```

**Example**:
```
"Implement password strength validator that checks password security.
Requirements:
- Minimum 8 characters
- At least 1 uppercase letter
- At least 1 lowercase letter
- At least 1 number
- At least 1 special character
- Return strength score (weak/medium/strong)
Write tests first, then implementation."
```

### Pattern 2: Bug Fix

**Template**:
```
"Fix bug where [incorrect behavior].
Expected: [correct behavior]
Steps:
1. Write regression test that reproduces the bug
2. Verify test fails
3. Fix the bug
4. Verify test passes
5. Run all tests"
```

**Example**:
```
"Fix bug where the shopping cart total is wrong when applying multiple discounts.
Expected: Discounts should stack additively (10% + 5% = 15% off)
Current: Discounts are applied multiplicatively (10% then 5% off remainder)
Steps:
1. Write regression test with multiple discounts
2. Verify test fails with current behavior
3. Fix the discount calculation logic
4. Verify test passes
5. Run all tests to ensure no regressions"
```

### Pattern 3: Refactoring

**Template**:
```
"Refactor [component] to [improvement].
Requirements:
- [design goal 1]
- [design goal 2]
- All existing tests must continue to pass
Steps:
1. Run tests to establish baseline
2. Make incremental changes
3. Verify tests pass after each change
4. Commit when all tests green"
```

**Example**:
```
"Refactor the user authentication module to use dependency injection.
Requirements:
- Separate database access from business logic
- Make code testable without database
- Follow existing DI patterns in the codebase
Steps:
1. Run current tests to establish baseline (all passing)
2. Extract database interface
3. Verify tests still pass
4. Inject database dependency
5. Verify tests still pass
6. Update all call sites
7. Verify all tests pass
8. Commit the refactoring"
```

### Pattern 4: Investigation/Research

**Template**:
```
"Investigate [issue/question].
Don't modify any files - just research and report findings.
Include:
- [information needed 1]
- [information needed 2]
- Recommendations for next steps"
```

**Example**:
```
"Investigate why the production deployment is 3x slower than staging.
Don't modify any files - just research and report findings.
Include:
- Comparison of production vs staging configurations
- Performance metrics (CPU, memory, network)
- Database query analysis
- Recent changes that might affect performance
- Recommendations for fixes"
```

### Pattern 5: Multi-Step Workflow

**Template**:
```
"[Overall goal]
Steps:
1. [Step 1] (agent type if specific)
2. [Step 2]
3. [Step 3]
Requirements:
- [requirement 1]
- [requirement 2]"
```

**Example**:
```
"Add rate limiting to all API endpoints.
Steps:
1. Implement rate limiting middleware (Engineer)
2. Add tests for various rate limit scenarios (Engineer)
3. Verify rate limiting works correctly (QA)
4. Review implementation for security issues (Security)
Requirements:
- 100 requests per minute per IP
- Return 429 Too Many Requests when exceeded
- Include Retry-After header
- Log rate limit violations"
```

### Pattern 6: Debugging Session

**Template**:
```
"Debug [issue].
Don't commit anything - just investigate.
[Provide relevant context/logs]
Report:
- Root cause
- Suggested fix
- Testing approach"
```

**Example**:
```
"Debug why WebSocket connections are dropping after 30 seconds.
Don't commit anything - just investigate.
Context:
- Issue started after upgrading to Node 18
- Only happens in production, not locally
- Logs show 'connection timeout' errors
Report:
- Root cause of connection drops
- Suggested fix with code example
- Testing approach to verify the fix"
```

---

## Anti-Patterns to Avoid

### ❌ Anti-Pattern 1: Vague Requests

**Bad**:
```
"Make the app better"
```

**Why**: PM doesn't know what "better" means or what to improve.

**Good**:
```
"Improve application performance by reducing page load time.
Target: < 2 seconds for initial page load
Areas to investigate:
- Image optimization
- JavaScript bundling
- Database query performance
- Caching strategy"
```

### ❌ Anti-Pattern 2: Missing Acceptance Criteria

**Bad**:
```
"Add search functionality"
```

**Why**: Unclear what "search" should do or when it's complete.

**Good**:
```
"Add search functionality to the products page.
Acceptance criteria:
- Search by product name (partial match)
- Search by SKU (exact match)
- Filter by category
- Sort results by relevance
- Debounce search input (300ms)
- Show 'no results' message when appropriate
Write tests for each criterion, then implement."
```

### ❌ Anti-Pattern 3: Not Specifying Testing Needs

**Bad**:
```
"Fix the login bug"
```

**Why**: Unclear if regression test is needed or if manual testing is sufficient.

**Good**:
```
"Fix the login bug where special characters in passwords cause 500 error.
Steps:
1. Write failing test with password containing !@#$%
2. Verify test fails with current code
3. Fix the password validation/encoding
4. Verify test passes
5. Run all authentication tests"
```

### ❌ Anti-Pattern 4: Assuming Single-Step Solutions

**Bad**:
```
"Just add a feature flag for dark mode"
```

**Why**: "Just" minimizes complexity. Feature flags require configuration, UI, persistence, testing.

**Good**:
```
"Implement dark mode feature flag.
Requirements:
- User preference stored in localStorage
- Toggle in settings menu
- CSS variables for theme colors
- Persist across sessions
- Tests for toggle functionality and persistence
Write tests first, then implement."
```

### ❌ Anti-Pattern 5: Not Controlling Commit Behavior

**Bad** (during debugging):
```
"See if you can fix the payment webhook issue"
```

**Why**: PM might commit broken changes while investigating.

**Good**:
```
"Debug the payment webhook issue - don't commit anything yet.
Investigate:
- Webhook payload format
- Signature verification
- Error logs
- Recent changes to webhook handler
Report findings and recommend fix approach."
```

### ❌ Anti-Pattern 6: Micro-Managing Agent Selection

**Bad**:
```
"Use the Python Engineer agent to write a function,
then switch to the QA agent to test it,
then use the Documentation agent to document it..."
```

**Why**: PM knows how to delegate. You're adding complexity without benefit.

**Good**:
```
"Implement rate limiting function with tests and documentation.
Requirements: [list requirements]"
```

**PM will automatically delegate to appropriate agents.**

### ❌ Anti-Pattern 7: Skipping Context

**Bad**:
```
"Fix it"
```

**Why**: What is "it"? No context provided.

**Good**:
```
"Fix the bug in user registration where email validation accepts invalid formats.
Context:
- Issue: 'user@' and '@example.com' are accepted as valid
- File: src/validators/email.ts
- Function: validateEmail()
Steps:
1. Write test cases for invalid emails
2. Verify tests fail
3. Fix validation regex
4. Verify all tests pass"
```

---

## Before/After Examples

### Example 1: Feature Request

#### ❌ Before (Weak Prompt)
```
"Add a comments feature"
```

**Problems**:
- No requirements specified
- No testing guidance
- Unclear scope
- No acceptance criteria

#### ✅ After (Strong Prompt)
```
"Implement comments feature for blog posts.

Requirements:
- Users can add comments to published posts
- Comments display in chronological order
- Users can edit/delete their own comments (within 5 minutes)
- Admin can delete any comment
- Comments are markdown-enabled
- Email notifications for new comments (to post author)

Acceptance Criteria:
✓ Comment form appears below post for logged-in users
✓ Comments save to database with user_id, post_id, content, timestamp
✓ Comments render with author name and relative timestamp
✓ Edit/delete buttons appear only for comment author (within 5min) or admin
✓ Markdown renders correctly (bold, italic, links, code blocks)
✓ Email sent to post author when new comment added

Follow TDD approach:
1. Write tests for each requirement
2. Verify tests fail
3. Implement features
4. Verify all tests pass"
```

**Why better**:
- Clear requirements
- Specific acceptance criteria
- Testing approach defined
- Scope is well-bounded

---

### Example 2: Bug Fix

#### ❌ Before (Weak Prompt)
```
"The search isn't working right"
```

**Problems**:
- Vague description of issue
- No reproduction steps
- No testing approach
- Unclear expected behavior

#### ✅ After (Strong Prompt)
```
"Fix search bug where searches with multiple words return no results.

Current Behavior:
- Search for "python tutorial" returns 0 results
- Search for "python" returns 45 results
- Search for "tutorial" returns 23 results

Expected Behavior:
- Search for "python tutorial" should return results matching both words

Steps:
1. Write failing test: search("python tutorial") should return results
2. Verify test fails with current implementation
3. Debug search query logic (likely AND vs OR issue)
4. Fix to treat multi-word searches as OR conditions
5. Verify test passes
6. Run full test suite to prevent regressions

Context:
- File: src/api/search.ts
- Function: performSearch()
- Database: PostgreSQL with full-text search
- Recent change: commit abc123 modified search query building"
```

**Why better**:
- Specific behavior described
- Clear expected vs actual
- TDD workflow specified
- Helpful context included

---

### Example 3: Refactoring

#### ❌ Before (Weak Prompt)
```
"Clean up the code"
```

**Problems**:
- No specific goals
- Unclear what needs cleaning
- No testing requirements
- No quality criteria

#### ✅ After (Strong Prompt)
```
"Refactor authentication module to improve testability and reduce duplication.

Current Issues:
- Database calls mixed with business logic (hard to test)
- Same validation logic duplicated in 3 places
- Functions are 100+ lines (too complex)
- No dependency injection (tightly coupled)

Refactoring Goals:
- Extract database access to repository pattern
- Create shared validation module
- Break large functions into smaller, focused ones
- Use dependency injection for database/external services
- Maintain 100% test coverage

Process:
1. Run all tests to establish baseline (must all pass)
2. Extract validation logic to shared validator
3. Run tests (must still pass)
4. Extract database access to repository
5. Run tests (must still pass)
6. Break down large functions
7. Run tests (must still pass)
8. Add dependency injection
9. Run tests (must still pass)
10. Commit refactoring

Success Criteria:
✓ All tests pass before and after
✓ Code coverage remains ≥ 95%
✓ No function over 50 lines
✓ No duplicated validation logic
✓ Database access isolated to repository
✓ Business logic is independently testable"
```

**Why better**:
- Specific problems identified
- Clear refactoring goals
- Step-by-step process
- Success criteria defined
- Test coverage protected

---

### Example 4: Investigation

#### ❌ Before (Weak Prompt)
```
"Why is it slow?"
```

**Problems**:
- Unclear what "it" refers to
- No specifics about "slow"
- No investigation guidance
- No expected output

#### ✅ After (Strong Prompt)
```
"Investigate performance degradation in user dashboard.

Symptoms:
- Dashboard load time: 8-12 seconds (was 2-3 seconds last week)
- Affects all users
- Started after deploy on Jan 5th
- No errors in logs

Investigation Tasks:
1. Profile page load performance (Chrome DevTools)
2. Analyze database queries (N+1 queries?)
3. Review Jan 5th deployment changes
4. Check API response times
5. Monitor memory/CPU usage
6. Test with different data volumes

Don't modify any code - just investigate and report.

Report Should Include:
- Performance bottlenecks identified
- Root cause analysis
- Comparison: before vs after Jan 5th
- Recommended fixes (with priority)
- Estimated effort for each fix"
```

**Why better**:
- Specific problem described
- Clear investigation tasks
- No code changes (investigation only)
- Expected report format

---

## See Also

- **[TxDD Skill Documentation](../../src/claude_mpm/skills/bundled/testing/test-driven-development/SKILL.md)** - Complete TDD workflow reference
- **[Ticketing Delegation](ticketing-delegation.md)** - How PM delegates to specialized agents
- **[Skills System](skills-system.md)** - Understanding agent specializations
- **[Debugging Strategies](debugging-session-strategies.md)** - How to prompt for debugging sessions
- **[Project Bootstrap](project-bootstrap.md)** - Getting started with MPM

---

## Summary

### Key Principles for Effective MPM Prompting

1. **Be Clear**: State your goal and acceptance criteria explicitly
2. **Specify Testing**: Use TxDD - write tests first when appropriate
3. **Control Commits**: Say "don't commit" during debugging/investigation
4. **Provide Context**: Include relevant files, errors, and background
5. **Trust Delegation**: Let PM decide which agents to use
6. **Define "Done"**: Use acceptance criteria to clarify when work is complete

### The TxDD Advantage

When building features:
- **Specify what you want** in your prompt (requirements)
- **Request tests first** ("Write tests following TDD")
- **Let PM delegate** to Engineer agent
- **Watch the workflow**: RED → GREEN → REFACTOR
- **Get quality results**: Tested, working, maintainable code

### Remember

**MPM is a multi-agent system**. Your prompt goes to the PM agent, who:
- Analyzes requirements
- Delegates to specialists (Engineer, QA, Security, etc.)
- Coordinates workflows
- Verifies results

Write prompts that help PM help you. Be clear, specific, and trust the delegation model.

---

**Need more examples?** Check the [Prompt Examples Library](#) (coming in issue #130) for a curated collection of effective prompts.

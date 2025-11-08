# Code Review Examples

## Complete Review Example

### Context
Task 2 completed: Added verification and repair functions for conversation index

**Git range:** `a7981ec..3df7661`

**What was implemented:** Verification and repair functions for conversation index

**Plan reference:** Task 2 from docs/plans/deployment-plan.md

### Good Review Output

```markdown
### Strengths
- Clean database schema with proper migrations (db.ts:15-42)
- Comprehensive test coverage (18 tests, all edge cases)
- Good error handling with fallbacks (summarizer.ts:85-92)
- Real integration tests, not just mocks (test-integration.ts)
- Clear separation of concerns (verification vs repair logic)

### Issues

#### Important (Should Fix)
1. **Missing help text in CLI wrapper**
   - File: index-conversations:1-31
   - Issue: No --help flag, users won't discover --concurrency
   - Why it matters: Poor user experience, hidden features
   - Fix: Add --help case with usage examples showing all options

2. **Date validation missing**
   - File: search.ts:25-27
   - Issue: Invalid dates silently return no results
   - Why it matters: Silent failures confuse users
   - Fix: Validate ISO format, throw error with example format

3. **Progress indicators missing**
   - File: indexer.ts:130
   - Issue: No "X of Y" counter for long operations
   - Why it matters: Users don't know how long to wait
   - Fix: Add `console.log(\`Processing \${i+1}/\${total}\`)` in loop

#### Minor (Nice to Have)
1. **Magic number for reporting interval**
   - File: indexer.ts:145
   - Issue: Hardcoded 100 for progress reporting
   - Impact: Low, but config would be cleaner
   - Fix: Extract to constant `PROGRESS_INTERVAL = 100`

### Recommendations
- Add progress reporting for better user experience
- Consider config file for excluded projects (improves portability)
- Documentation looks good, but add troubleshooting section

### Assessment

**Ready to merge: With fixes**

**Reasoning:** Core implementation is solid with good architecture and comprehensive tests. Important issues (help text, date validation, progress indicators) are easily fixed in 10-15 minutes and don't affect core functionality. Minor issues can be addressed later.
```

### Acting on This Review

**Fix Important issues:**
```bash
# Fix 1: Add help text
# Edit index-conversations, add help flag

# Fix 2: Add date validation
# Edit search.ts:25-27, add format check

# Fix 3: Add progress indicators
# Edit indexer.ts:130, add counter

# Test fixes
pytest tests/ -v

# Commit
git add .
git commit -m "fix: add help text, date validation, and progress indicators"
```

**Continue to next task** after fixes verified.

## Good vs Bad Review Requests

### ❌ Bad Request: Vague

```
Can you review my code?

BASE_SHA: abc123
HEAD_SHA: def456
```

**Problems:**
- No context on what was implemented
- No requirements to check against
- No description of changes
- Reviewer has to reverse-engineer everything

### ✅ Good Request: Specific

```
Review Task 3: User Authentication Implementation

WHAT_WAS_IMPLEMENTED:
- JWT-based authentication middleware
- Login/logout endpoints
- Password hashing with bcrypt
- Session management

PLAN_OR_REQUIREMENTS:
See Task 3 in docs/plans/2025-01-15-user-auth.md
Key requirements:
- Secure password storage (bcrypt)
- JWT tokens with 24hr expiration
- Logout invalidates token
- All endpoints require auth except /login

BASE_SHA: a7981ec
HEAD_SHA: 3df7661

DESCRIPTION:
Added authentication system with JWT tokens. Implemented password hashing,
login/logout endpoints, and auth middleware. All tests passing.
```

**Why it's good:**
- Clear context on what was built
- Specific requirements to verify
- Git range for diff
- Brief summary of changes

## Review Workflow Examples

### Example 1: Subagent-Driven Development (After Each Task)

```
[Task 2 completed: Email validation]

PM: Let me request code review before proceeding.

BASE_SHA=$(git log --oneline | grep "Task 1" | head -1 | awk '{print $1}')
HEAD_SHA=$(git rev-parse HEAD)

[Dispatch code-reviewer subagent]
  WHAT_WAS_IMPLEMENTED: Email validation in User model
  PLAN_OR_REQUIREMENTS: Task 2 from docs/plans/user-system-plan.md
  BASE_SHA: abc123
  HEAD_SHA: def456
  DESCRIPTION: Added validate_email() utility and integrated into User model

[Subagent returns]:
  Strengths: Clean validator, good tests
  Issues:
    Important: Missing edge case for emails with + signs
    Minor: Could extract regex to constant
  Assessment: Fix + sign handling, then proceed

PM: [Fix + sign edge case]
[Add test for alice+spam@example.com]
[Verify all tests pass]
[Commit fix]

PM: Ready to proceed to Task 3
```

### Example 2: Before Merging Major Feature

```
[Feature branch: user-authentication complete]

PM: Let me get a final review before merging to main.

BASE_SHA=$(git merge-base origin/main HEAD)
HEAD_SHA=$(git rev-parse HEAD)

[Dispatch code-reviewer subagent]
  WHAT_WAS_IMPLEMENTED: Complete user authentication system
  PLAN_OR_REQUIREMENTS: docs/plans/2025-01-15-user-auth.md (all tasks)
  BASE_SHA: a7981ec (merge-base with main)
  HEAD_SHA: 3df7661
  DESCRIPTION: Full auth system: registration, login, JWT, password hashing, session management

[Subagent returns]:
  Strengths: Complete implementation, excellent test coverage, secure
  Issues:
    Critical: JWT secret in code, should use environment variable
    Important: No rate limiting on login endpoint
    Minor: Could add password strength requirements
  Assessment: NOT ready to merge - fix Critical immediately

PM: [Move JWT secret to environment variable]
[Add .env.example with JWT_SECRET]
[Update config to read from env]
[Verify tests still pass]
[Commit: "fix: move JWT secret to environment variable"]

PM: Rate limiting is Important but can be separate task.
PM: Password strength can be future enhancement.

[Request review again with fix]
  Issues: None
  Assessment: Ready to merge

PM: [Merge to main]
```

### Example 3: When Stuck (Fresh Perspective)

```
[Debugging weird test failure for 2 hours]

PM: I'm stuck. Let me get a code review for fresh eyes.

BASE_SHA=$(git rev-parse HEAD~3)  # Before I started debugging
HEAD_SHA=$(git rev-parse HEAD)

[Dispatch code-reviewer subagent]
  WHAT_WAS_IMPLEMENTED: Attempted fix for test_user_creation flakiness
  PLAN_OR_REQUIREMENTS: Test should pass consistently
  BASE_SHA: abc123
  HEAD_SHA: def456
  DESCRIPTION: Test fails intermittently, added logging, tried various fixes

[Subagent returns]:
  Issue found: test_user_creation:15 - race condition
  The test creates user and immediately queries, but database write is async
  Fix: Add await or use synchronous test database

PM: Ah! That's it. The async write wasn't flushing.
[Add await db.flush() before query]
[Test passes consistently]
```

## Common Review Scenarios

### Scenario: All Critical Issues

```markdown
### Issues

#### Critical (Must Fix)
1. **SQL injection vulnerability**
   - File: users.py:45
   - Issue: Raw string interpolation in query
   - Fix: Use parameterized query

2. **Plaintext password storage**
   - File: models.py:23
   - Issue: Passwords stored without hashing
   - Fix: Use bcrypt before saving

### Assessment

**Ready to merge: NO**

**Reasoning:** Critical security issues must be fixed before any deployment.
```

**Action:** Fix immediately, don't proceed.

### Scenario: Mix of Severities

```markdown
### Issues

#### Important (Should Fix)
1. **Missing error handling**
   - File: api.py:67
   - Issue: Network call can throw, not caught
   - Fix: Wrap in try/except, return 500

#### Minor (Nice to Have)
1. **Magic number**
   - File: config.py:12
   - Issue: Hardcoded timeout value
   - Fix: Extract to named constant

### Assessment

**Ready to merge: With fixes**

**Reasoning:** Error handling is important but localized fix. Magic number can be addressed later.
```

**Action:** Fix Important, note Minor for future, proceed.

### Scenario: Clean Implementation

```markdown
### Strengths
- Excellent test coverage (95%)
- Clean separation of concerns
- Good error handling throughout
- Well-documented edge cases

### Issues

#### Minor (Nice to Have)
1. **Could add type hints**
   - File: helpers.py
   - Impact: Very low, code is clear
   - Fix: Add -> str type hints

### Recommendations
- Consider adding performance tests for large datasets
- Documentation is great, maybe add architecture diagram

### Assessment

**Ready to merge: YES**

**Reasoning:** Implementation is production-ready. Minor improvements can be separate tasks.
```

**Action:** Merge, create tickets for nice-to-haves.

## Severity Guidelines

### Critical (Must Fix)
- Security vulnerabilities
- Data loss risks
- Broken core functionality
- Production crashes
- Memory leaks

**Action:** Stop everything, fix immediately, re-review.

### Important (Should Fix)
- Missing features from requirements
- Poor error handling
- Architectural issues
- Test coverage gaps
- Performance problems

**Action:** Fix before proceeding to next major task.

### Minor (Nice to Have)
- Code style inconsistencies
- Optimization opportunities
- Documentation improvements
- Magic numbers
- Variable naming

**Action:** Note for later, proceed if time-constrained.

## Pushing Back on Reviews

Sometimes reviewers are wrong. Push back with **technical reasoning**:

### Example: Reviewer Wrong About Performance

```
Reviewer: "This loop is inefficient, use map() instead"

Your response:
"I tested both approaches with 10k items:
- Current loop: 45ms
- Map approach: 43ms (2ms faster)

The readability gain of explicit loop outweighs 2ms difference.
Performance requirement is <100ms, we're at 45ms.
Keeping current implementation."
```

### Example: Reviewer Misunderstood Requirements

```
Reviewer: "Missing validation for phone numbers"

Your response:
"Plan requirement (docs/plans/user-plan.md:45):
'Phone number is optional and will be validated in Phase 2'

Current task only requires email validation.
Phone validation is tracked in Task 7."
```

### Example: Reviewer Right, You Missed Something

```
Reviewer: "No test for empty email"

Your response:
"You're right, I missed that edge case.
Adding test now:

def test_create_user_empty_email():
    with pytest.raises(ValueError, match="Email required"):
        create_user("alice", "")

Fixed and committed."
```

## Red Flags in Your Own Code

Before requesting review, self-check:

- [ ] All tests passing locally
- [ ] No commented-out code
- [ ] No debug print statements
- [ ] No hardcoded secrets or credentials
- [ ] All requirements from plan implemented
- [ ] Error handling in place
- [ ] Edge cases tested
- [ ] Commit messages clear

If any ❌, fix before requesting review.

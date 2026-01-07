# Resume Log System - Examples & Tutorials

Real-world examples and step-by-step tutorials for using the Resume Log System effectively.

## Table of Contents

- [Quick Start Example](#quick-start-example)
- [Example Resume Log Output](#example-resume-log-output)
- [Tutorial 1: Basic Session with Resume Log](#tutorial-1-basic-session-with-resume-log)
- [Tutorial 2: Long Research Project](#tutorial-2-long-research-project)
- [Tutorial 3: Multi-Day Feature Development](#tutorial-3-multi-day-feature-development)
- [Tutorial 4: Emergency Context Recovery](#tutorial-4-emergency-context-recovery)
- [Common Workflows](#common-workflows)
- [Integration Examples](#integration-examples)

## Quick Start Example

### Simple Session with Automatic Resume Log

```bash
# Start Claude MPM session
claude-mpm run --monitor

# Work normally... system tracks token usage automatically

# At 70% threshold, you see:
# ⚠️  Context Usage Caution: 70% capacity reached
# 60,000 tokens remaining - consider planning for session transition.

# Continue working...

# At 85% threshold, you see:
# ⚠️  Context Usage Warning: 85% capacity reached
# 30,000 tokens remaining - complete current task, avoid starting new work.

# At 95% threshold:
# 🚨 Context Usage Critical: 95% capacity reached
# 10,000 tokens remaining - STOP new work immediately.
# Resume log will be generated automatically.

# Resume log automatically saved to:
# .claude-mpm/resume-logs/session-20251101_115000.md

# Start new session - previous context automatically loaded
claude-mpm run

# You see:
# 📋 Resuming from previous session (20251101_115000)...
# Context: Implementing user authentication system
# Last task: JWT token generation completed
# Next: Create database migration
```

## Example Resume Log Output

Here's a real example of a generated resume log:

```markdown
# Session Resume Log: 20251101_115000

Generated: 2025-11-01T11:50:00

## Context Metrics

- Model: claude-sonnet-4.5
- Total Budget: 200,000 tokens
- Used: 170,000 tokens (85.0%)
- Remaining: 30,000 tokens
- Stop Reason: end_turn
- Session ID: 20251101_115000

## Mission Summary

Implementing a complete user authentication system for the FastAPI-based API, including:
- JWT token generation and validation with 24-hour expiration
- Secure login/logout endpoints with email/password authentication
- Password hashing using bcrypt with industry-standard work factor
- Integration with existing User model and database schema
- Comprehensive test coverage with pytest

## Accomplishments

✅ Created authentication service module (src/services/auth.py)
  - Implemented JWT token generation with configurable expiration
  - Added token validation and decoding functionality
  - Integrated bcrypt for password hashing (work factor: 12)

✅ Implemented login endpoint (src/api/routes/auth.py)
  - POST /auth/login with email/password validation
  - Returns JWT token and user information
  - Proper error handling for invalid credentials

✅ Created authentication middleware
  - Decorator for protected endpoints (@require_auth)
  - Token extraction from Authorization header
  - User identity injection into request context

✅ Updated User model (src/models/user.py)
  - Added password_hash field (VARCHAR 255)
  - Added last_login timestamp field
  - Created index on email for login performance

✅ Implemented comprehensive test suite (tests/test_auth.py)
  - 15 tests covering all authentication flows
  - 100% coverage of authentication service
  - Tests for happy path, error cases, and edge cases

✅ Created JWT configuration module (src/config/jwt.py)
  - Environment variable integration
  - Default values with override capability
  - Configuration validation

## Key Findings

**Technical Discoveries:**
- Existing User model already had last_login field - no migration needed for that
- bcrypt default work factor (12) provides good balance of security and performance
- JWT secret must be stored in environment variable, not hardcoded (security requirement)
- Token refresh strategy will be needed for sessions longer than 24 hours
- Redis integration available for storing refresh tokens (already configured)

**Performance Insights:**
- Login endpoint averages 150ms response time (bcrypt is primary cost)
- Token validation is very fast (<5ms) due to stateless JWT design
- Database query on email field needs index for production scale

**Security Considerations:**
- Passwords must never be logged or returned in API responses (validated in tests)
- JWT secret must be at least 32 characters for HS256 algorithm
- Rate limiting needed on login endpoint to prevent brute force attacks
- Consider adding account lockout after failed login attempts

**Integration Notes:**
- Authentication middleware compatible with existing API structure
- No breaking changes to existing endpoints
- Existing user records need migration to add password_hash

## Decisions & Rationale

**Decision**: Use JWT instead of session cookies
**Rationale**: Stateless authentication scales better with multiple API instances, works seamlessly with mobile apps and SPA frontends, eliminates need for session storage in database.

**Decision**: Set token expiration to 24 hours
**Rationale**: Balances security (limits exposure window) with user convenience (reduces login frequency for daily users). Can be adjusted per deployment environment.

**Decision**: Store refresh tokens in Redis instead of database
**Rationale**: Fast lookup performance, automatic expiration via TTL, separates authentication state from main application data, easy to invalidate all tokens on security events.

**Decision**: Use bcrypt with work factor 12
**Rationale**: Industry standard, provides strong security against brute force, acceptable performance impact (~150ms), compatible with existing Python ecosystem.

**Decision**: Require email/password for initial login, issue JWT for subsequent requests
**Rationale**: Email/password is user-friendly, JWT provides stateless authentication for API calls, separates user authentication from request authorization.

## Next Steps

🔲 **High Priority:**
  1. Create database migration for password_hash column
     - Migration file: alembic/versions/xxx_add_password_hash.py
     - Update all environments (dev, staging, prod)

  2. Implement token refresh endpoint (POST /auth/refresh)
     - Accept refresh token, return new access token
     - Store refresh tokens in Redis with 7-day TTL
     - Validate refresh token hasn't been revoked

  3. Add rate limiting to login endpoint
     - Use Redis for rate limit tracking
     - Limit: 5 attempts per minute per IP
     - Return 429 Too Many Requests on violation

🔲 **Medium Priority:**
  4. Create password reset flow
     - Generate password reset token (email verification)
     - Implement POST /auth/reset-password endpoint
     - Send reset email via configured email service

  5. Add authentication documentation to API docs
     - OpenAPI/Swagger annotations
     - Example requests and responses
     - Error codes and meanings

  6. Implement account lockout mechanism
     - Lock account after 10 failed login attempts
     - Require admin unlock or time-based unlock (30 minutes)
     - Notify user via email on lockout

🔲 **Low Priority:**
  7. Deploy to staging environment
     - Update environment variables (JWT_SECRET, etc.)
     - Run database migrations
     - Perform integration testing

  8. Security review of authentication flow
     - Third-party security audit (if budget allows)
     - Penetration testing
     - Code review by security specialist

## Critical Context

**Key File Paths:**
- Authentication service: `src/services/auth.py`
- Login endpoint: `src/api/routes/auth.py`
- JWT configuration: `src/config/jwt.py`
- User model: `src/models/user.py`
- Tests: `tests/test_auth.py`
- Migration (pending): `alembic/versions/xxx_add_password_hash.py`

**Important Identifiers:**
- Migration ID: `20251101_auth_schema` (to be created)
- Config section: `authentication.jwt`
- Redis key prefix: `auth:refresh:`
- Database table: `users`

**Environment Variables Required:**
```bash
# Required for production
JWT_SECRET="your-secret-key-minimum-32-characters"  # pragma: allowlist secret
JWT_EXPIRATION_HOURS="24"
BCRYPT_ROUNDS="12"

# Optional overrides
JWT_ALGORITHM="HS256"  # Default
REFRESH_TOKEN_TTL_DAYS="7"  # Default
```

**Database Changes:**
```sql
-- Required migration
ALTER TABLE users ADD COLUMN password_hash VARCHAR(255);
CREATE INDEX idx_users_email ON users(email);
```

**Redis Schema:**
```
# Refresh tokens
auth:refresh:{user_id}:{token_id} -> {token_data}
TTL: 7 days

# Rate limiting
auth:ratelimit:{ip_address} -> {attempt_count}
TTL: 1 minute
```

**Dependencies:**
- PyJWT==2.8.0
- bcrypt==4.1.2
- python-dotenv==1.0.0
- redis==5.0.1 (for refresh tokens and rate limiting)

## Session Metadata

**Files Modified:**
- `src/services/auth.py` (created, 245 lines)
- `src/api/routes/auth.py` (created, 89 lines)
- `src/config/jwt.py` (created, 67 lines)
- `src/models/user.py` (modified, added password_hash field)
- `tests/test_auth.py` (created, 412 lines)

**Files Viewed:**
- `src/models/user.py` (existing model inspection)
- `src/config/__init__.py` (configuration patterns)
- `tests/conftest.py` (test fixtures)

**Agents Used:**
- PM (orchestration and planning)
- Engineer (implementation)
- QA (testing)
- Security (review and validation)

**Errors Encountered:**
- None

**Warnings:**
- JWT_SECRET not set in .env file (resolved: added to .env.example)
- Missing index on users.email field (resolved: noted for migration)

**Session Duration:** 2 hours 34 minutes

**Total Tokens Used:** 170,000 (85.0% of budget)
```

## Tutorial 1: Basic Session with Resume Log

### Scenario
You're implementing a feature and want to ensure you can resume if you hit context limits.

### Step-by-Step

**Step 1: Enable Resume Logs (if not already enabled)**

Edit `.claude-mpm/configuration.yaml`:
```yaml
context_management:
  enabled: true
  resume_logs:
    enabled: true
    auto_generate: true
```

**Step 2: Start Your Session**

```bash
claude-mpm run --monitor
```

**Step 3: Work Normally**

```
User: "Implement user authentication with JWT tokens"

PM: "I'll help you implement authentication. Let me delegate to the Engineer..."

Engineer: "Creating authentication service..."

# Session progresses normally...
```

**Step 4: Monitor Context Usage**

Watch the monitoring dashboard or check token usage:
```bash
# In another terminal
tail -f .claude-mpm/logs/session.log | grep "Context usage"
```

**Step 5: Observe Threshold Warnings**

At 70%:
```
⚠️  Context Usage Caution: 70% capacity reached
60,000 tokens remaining - consider planning for session transition.
```

At 85%:
```
⚠️  Context Usage Warning: 85% capacity reached
30,000 tokens remaining - complete current task, avoid starting new work.
```

**Step 6: Resume Log Auto-Generated at 95%**

```
🚨 Context Usage Critical: 95% capacity reached
10,000 tokens remaining - STOP new work immediately.

✅ Resume log generated: .claude-mpm/resume-logs/session-20251101_115000.md
```

**Step 7: Review Generated Log**

```bash
# View the resume log
cat .claude-mpm/resume-logs/session-20251101_115000.md

# Or open in editor
code .claude-mpm/resume-logs/session-20251101_115000.md
```

**Step 8: Start New Session**

```bash
# Start new session
claude-mpm run

# Previous context automatically loaded
# You'll see a summary of where you left off
```

## Tutorial 2: Long Research Project

### Scenario
Multi-session research project requiring continuity across multiple days.

### Workflow

**Day 1: Initial Research (Session 1)**

```bash
claude-mpm run

User: "Research best practices for implementing authentication in FastAPI"

# Session progresses...
# Resume log generated at 85% threshold

# .claude-mpm/resume-logs/session-20251101_090000.md created
```

**Day 2: Deep Dive (Session 2)**

```bash
claude-mpm run

# Previous session automatically loaded
# You see: "Resuming from session 20251101_090000..."
# Context: "Research authentication best practices"
# Next: "Deep dive into JWT implementation"

User: "Continue with JWT implementation details"

# Session continues with full context from Day 1
# Resume log generated at 85%

# .claude-mpm/resume-logs/session-20251102_090000.md created
```

**Day 3: Implementation (Session 3)**

```bash
claude-mpm run

# Previous session automatically loaded
# Full context from Days 1 and 2

User: "Let's implement the authentication based on our research"

# Implementation proceeds with accumulated knowledge
```

### Benefits

- Context preserved across multiple days
- Research findings carried forward
- No need to re-explain context
- Accumulated knowledge builds over sessions

## Tutorial 3: Multi-Day Feature Development

### Scenario
Implementing a complex feature over 3 days with strategic session pauses.

### Day 1: Planning & Design

```bash
claude-mpm run

User: "Design and plan a user authentication system"

# Planning session:
# - Architecture design
# - Technology selection
# - Task breakdown

# At natural breakpoint (after planning complete)
User: "/pause"

# Resume log generated with:
# - Mission: Design authentication system
# - Accomplishments: Architecture designed, tech stack selected
# - Decisions: JWT chosen, bcrypt for passwords
# - Next Steps: Start implementation

# .claude-mpm/resume-logs/session-20251101_planning.md
```

### Day 2: Implementation

```bash
claude-mpm run

# Previous planning session loaded automatically
# Context includes all design decisions

User: "Implement the authentication system we planned"

# Implementation session:
# - Create authentication service
# - Implement JWT generation
# - Add login endpoint
# - Write tests

# At end of day
User: "/pause"

# Resume log generated with:
# - Mission: Implement authentication (from Day 1)
# - Accomplishments: Service created, JWT working, tests passing
# - Next Steps: Add refresh tokens, rate limiting, documentation

# .claude-mpm/resume-logs/session-20251102_implementation.md
```

### Day 3: Refinement & Deployment

```bash
claude-mpm run

# Both previous sessions loaded
# Full context from planning and implementation

User: "Add refresh tokens and deploy to staging"

# Refinement session:
# - Refresh token implementation
# - Rate limiting
# - Documentation
# - Deployment

# Final pause
User: "/pause"

# Complete resume log with full project history
# .claude-mpm/resume-logs/session-20251103_deployment.md
```

## Tutorial 4: Emergency Context Recovery

### Scenario
Session terminated unexpectedly, need to recover context quickly.

### Step-by-Step

**Step 1: Find Latest Resume Log**

```bash
# List resume logs
ls -lt .claude-mpm/resume-logs/*.md | head -1

# Output:
# .claude-mpm/resume-logs/session-20251101_115000.md
```

**Step 2: Review the Resume Log**

```bash
# Quick review
cat .claude-mpm/resume-logs/session-20251101_115000.md

# Focus on key sections:
# - Mission Summary: What was being done
# - Accomplishments: What was completed
# - Next Steps: What needs to be done
# - Critical Context: Essential state/IDs/paths
```

**Step 3: Start New Session with Context**

```bash
claude-mpm run

# System automatically loads latest resume log

# You see:
# 📋 Resuming from previous session (20251101_115000)...
# Context restored from resume log
```

**Step 4: Verify Context**

```bash
User: "What were we working on?"

PM: "Based on the resume log, we were implementing user authentication...
     We completed the JWT service and login endpoint.
     Next steps are to add refresh tokens and rate limiting."
```

**Step 5: Continue Work**

```bash
User: "Let's continue with the refresh token implementation"

# Work continues seamlessly from where it left off
```

## Common Workflows

### Workflow 1: Proactive Session Management

```bash
# Long task - monitor and pause proactively

claude-mpm run --monitor

# Watch token usage in dashboard
# At 70%: Note current task
# At 85%: Start wrapping up current subtask
# At 90%: Manually pause before hitting 95%

User: "/pause"

# Clean resume log generated at natural breakpoint
# Better than waiting for 95% emergency pause
```

### Workflow 2: Multiple Related Features

```bash
# Feature A
claude-mpm run
User: "Implement feature A"
# Work...
User: "/pause"  # Clean breakpoint after Feature A

# Feature B (next day)
claude-mpm run
# Previous context loaded - knows about Feature A
User: "Implement feature B, integrating with feature A"
# Work proceeds with Feature A context
User: "/pause"

# Feature C (next day)
claude-mpm run
# Full context of Features A and B
User: "Implement feature C, tying together A and B"
```

### Workflow 3: Research → Implementation → Deployment

```bash
# Research Phase
claude-mpm run
User: "Research best approach for implementing X"
# Research session...
User: "/pause"
# Resume log captures research findings and decisions

# Implementation Phase
claude-mpm run
# Research findings automatically available
User: "Implement X based on our research"
# Implementation session...
User: "/pause"
# Resume log captures implementation details

# Deployment Phase
claude-mpm run
# Full history of research and implementation
User: "Deploy X to production"
# Deployment with complete context
```

## Integration Examples

### Integration 1: CI/CD Pipeline

```bash
#!/bin/bash
# deploy.sh - Pre-deployment script

# Generate resume log for deployment record
claude-mpm mpm-init pause

# Upload to artifact storage
RESUME_LOG=$(ls -t .claude-mpm/resume-logs/*.md | head -1)
aws s3 cp $RESUME_LOG s3://deployment-logs/$(date +%Y%m%d)/

# Continue with deployment
./deploy-app.sh
```

### Integration 2: Team Handoff

```bash
# Developer A completes feature
claude-mpm run
User: "Implement authentication feature"
# Work...
User: "/pause"

# Commit resume log for handoff
git add .claude-mpm/resume-logs/session-auth-implementation.md
git commit -m "Add resume log for authentication feature handoff"
git push

# Developer B continues next day
git pull
claude-mpm run
# Resume log automatically loaded
User: "Continue authentication feature - add refresh tokens"
```

### Integration 3: Project Documentation

```python
#!/usr/bin/env python3
"""
Generate project documentation from resume logs.
"""

import json
from pathlib import Path

# Load all resume logs
resume_logs_dir = Path(".claude-mpm/resume-logs")
logs = []

for json_file in resume_logs_dir.glob("*.json"):
    with open(json_file) as f:
        logs.append(json.load(f))

# Sort by timestamp
logs.sort(key=lambda x: x["context_metrics"]["timestamp"])

# Generate project timeline
with open("PROJECT_TIMELINE.md", "w") as f:
    f.write("# Project Timeline\\n\\n")

    for log in logs:
        session_id = log["session_id"]
        mission = log["mission_summary"]
        accomplishments = log["accomplishments"]

        f.write(f"## Session: {session_id}\\n\\n")
        f.write(f"**Mission**: {mission}\\n\\n")
        f.write("**Accomplishments**:\\n")
        for item in accomplishments:
            f.write(f"- {item}\\n")
        f.write("\\n")

print("Project timeline generated: PROJECT_TIMELINE.md")
```

### Integration 4: Automated Reporting

```python
#!/usr/bin/env python3
"""
Generate daily progress report from resume logs.
"""

from datetime import datetime, timedelta
import json
from pathlib import Path

# Get today's resume logs
today = datetime.now().date()
resume_logs_dir = Path(".claude-mpm/resume-logs")

daily_logs = []
for json_file in resume_logs_dir.glob("*.json"):
    with open(json_file) as f:
        log = json.load(f)
        log_date = datetime.fromisoformat(
            log["context_metrics"]["timestamp"]
        ).date()

        if log_date == today:
            daily_logs.append(log)

# Generate daily report
with open(f"daily-report-{today}.md", "w") as f:
    f.write(f"# Daily Progress Report: {today}\\n\\n")

    total_tokens = sum(
        log["context_metrics"]["used_tokens"] for log in daily_logs
    )

    f.write(f"**Sessions**: {len(daily_logs)}\\n")
    f.write(f"**Total Tokens**: {total_tokens:,}\\n\\n")

    for log in daily_logs:
        f.write(f"## {log['session_id']}\\n\\n")
        f.write(f"**Mission**: {log['mission_summary']}\\n\\n")

        f.write("**Key Accomplishments**:\\n")
        for item in log["accomplishments"][:5]:  # Top 5
            f.write(f"- {item}\\n")
        f.write("\\n")

print(f"Daily report generated: daily-report-{today}.md")
```

## Best Practices from Examples

### When to Pause Manually

✅ **Good times to pause**:
- After completing a major feature
- Before switching to different component
- At end of work day
- After major refactoring

❌ **Avoid pausing**:
- In middle of implementation
- During active debugging
- While tests are failing
- During error investigation

### How to Structure Multi-Day Projects

1. **Day 1: Planning & Research**
   - Architecture decisions
   - Technology selection
   - Task breakdown
   - Pause at end of planning

2. **Day 2: Core Implementation**
   - Main functionality
   - Core features
   - Initial testing
   - Pause after core complete

3. **Day 3: Refinement & Deployment**
   - Edge cases
   - Performance optimization
   - Documentation
   - Deployment

### Resume Log Quality Tips

**Good Mission Summaries**:
- ✅ "Implementing JWT-based authentication with refresh tokens"
- ✅ "Refactoring database layer to use async SQLAlchemy"
- ❌ "Working on the project" (too vague)
- ❌ "Fixing bugs" (too generic)

**Good Accomplishments**:
- ✅ "Created AuthService with JWT generation (src/services/auth.py)"
- ✅ "Added 15 tests covering all auth flows (100% coverage)"
- ❌ "Made progress" (too vague)
- ❌ "Fixed some issues" (not specific)

**Good Next Steps**:
- ✅ "Implement refresh token endpoint (POST /auth/refresh)"
- ✅ "Add rate limiting to login (5 attempts/minute per IP)"
- ❌ "Continue work" (not actionable)
- ❌ "Finish feature" (too vague)

## Related Documentation

- [User Guide](../user/resume-logs.md) - Complete user documentation
- [Developer Architecture](../developer/resume-log-architecture.md) - Technical implementation
- [Configuration Reference](../configuration/reference.md) - Complete config options
- [User Guide - Session Management](../user/user-guide.md#session-management) - Session workflows

## Summary

These examples demonstrate:
- ✅ Automatic resume log generation at thresholds
- ✅ Manual session pause at natural breakpoints
- ✅ Multi-day project continuity
- ✅ Emergency context recovery
- ✅ Team collaboration via resume logs
- ✅ Integration with CI/CD and reporting
- ✅ Best practices for quality resume logs

**Next Steps**:
1. Try the Basic Session Tutorial (Tutorial 1)
2. Experiment with manual pausing (Tutorial 3)
3. Review your generated resume logs for quality
4. Integrate resume logs into your workflow
5. Share resume logs with team for handoffs

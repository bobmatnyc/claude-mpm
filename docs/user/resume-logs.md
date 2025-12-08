# Resume Log System - User Guide

Complete guide to understanding and using Claude MPM's Resume Log System for seamless session continuity.

## Table of Contents

- [Overview](#overview)
- [What Are Resume Logs?](#what-are-resume-logs)
- [When Are They Created?](#when-are-they-created)
- [What Do They Contain?](#what-do-they-contain)
- [How to Use Resume Logs](#how-to-use-resume-logs)
- [Configuration Options](#configuration-options)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)
- [Advanced Usage](#advanced-usage)

## Overview

The Resume Log System is Claude MPM's solution for managing context window limits and ensuring seamless session continuity. It automatically generates structured 10k-token logs that preserve essential context when approaching token limits, enabling you to resume work without losing important information.

**Key Benefits:**
- 🎯 **Proactive Management**: Early warnings at 70%/85%/95% thresholds (60k token buffer)
- 🔄 **Seamless Resumption**: Pick up where you left off with full context
- 📊 **Smart Prioritization**: 10k-token budget intelligently distributed across key sections
- 🤖 **Fully Automatic**: Works transparently in the background
- 📁 **Human-Readable**: Markdown format for both Claude and humans

## What Are Resume Logs?

Resume logs are structured markdown documents that capture the essential context of your Claude MPM session. Think of them as intelligent snapshots that contain:

- **Mission Summary**: What you're trying to accomplish
- **Accomplishments**: What you've completed so far
- **Key Findings**: Important discoveries and learnings
- **Decisions & Rationale**: Why certain choices were made
- **Next Steps**: Clear actions to continue work
- **Critical Context**: Essential state, IDs, paths, and data

Unlike simple conversation history, resume logs are:
- **Selective**: Only essential information, not everything
- **Structured**: Organized for efficient Claude consumption
- **Token-Optimized**: Maximum 10k tokens vs full history (100k+ tokens)
- **Action-Oriented**: Focuses on what needs to happen next

## When Are They Created?

Resume logs are automatically generated in several scenarios:

### Automatic Triggers

**1. Context Window Thresholds**
```
70% (Caution)   → 140,000 tokens used, 60,000 remaining
85% (Warning)   → 170,000 tokens used, 30,000 remaining
95% (Critical)  → 190,000 tokens used, 10,000 remaining
```

When you hit these thresholds, Claude MPM:
- Displays a warning message
- Suggests wrapping up current work
- Automatically generates resume log at 95%

**2. API Stop Reasons**

When Claude's API returns specific stop reasons:
- `max_tokens` - Hit the model's context window limit
- `model_context_window_exceeded` - Exceeded available context
- `stop_sequence` - Reached a natural stopping point

**3. Manual Session Pause**

When you explicitly pause your session:
```bash
# In Claude Code session
/pause

# Or via CLI
claude-mpm mpm-init pause
```

### Why Three Thresholds?

The graduated threshold system provides proactive management:

| Threshold | Tokens Free | Action Required |
|-----------|-------------|-----------------|
| 70% | 60,000 | Start planning session transition |
| 85% | 30,000 | Complete current task, avoid new work |
| 95% | 10,000 | Stop immediately, generate resume log |

**Previous system** (90%/95%) provided only 20k buffer - too reactive!
**New system** (70%/85%/95%) provides 60k buffer - time to reach natural breakpoints.

## What Do They Contain?

Each resume log uses a 10k-token budget distributed across seven sections:

### 1. Context Metrics (500 tokens)

Technical metadata about the session:
```markdown
- Model: claude-sonnet-4.5
- Total Budget: 200,000 tokens
- Used: 170,000 tokens (85.0%)
- Remaining: 30,000 tokens
- Stop Reason: end_turn
- Session ID: 20251101_115000
```

### 2. Mission Summary (1,000 tokens)

High-level goal and purpose:
```markdown
Implementing user authentication system for the API including:
- JWT token generation and validation
- Login/logout endpoints
- Password hashing with bcrypt
- Integration with existing user model
```

### 3. Accomplishments (2,000 tokens)

What was completed during the session:
```markdown
✅ Created authentication service (src/services/auth.py)
✅ Implemented JWT token generation with 24-hour expiration
✅ Added login endpoint with email/password validation
✅ Integrated bcrypt for password hashing
✅ Created authentication middleware for protected routes
✅ Updated user model with password_hash field
✅ Added 15 comprehensive tests (100% coverage)
```

### 4. Key Findings (2,500 tokens)

Important discoveries and insights:
```markdown
- Existing user model already had last_login field
- bcrypt default work factor (12) is appropriate for our load
- JWT secret should be stored in environment variable (not hardcoded)
- Token refresh strategy needed for long sessions
- Database migration required for password_hash column
```

### 5. Decisions & Rationale (1,500 tokens)

Choices made and reasoning:
```markdown
**Decision**: Use JWT instead of session cookies
**Rationale**: Stateless authentication scales better, works with mobile apps

**Decision**: Set token expiration to 24 hours
**Rationale**: Balance between security and user convenience

**Decision**: Store refresh tokens in Redis
**Rationale**: Fast lookup, automatic expiration, separate from main database
```

### 6. Next Steps (1,500 tokens)

Clear, actionable tasks for continuation:
```markdown
🔲 Create database migration for password_hash column
🔲 Implement token refresh endpoint
🔲 Add rate limiting to login endpoint (prevent brute force)
🔲 Create password reset flow (email verification)
🔲 Add authentication documentation to API docs
🔲 Deploy to staging environment
🔲 Perform security review of authentication flow
```

### 7. Critical Context (1,000 tokens)

Essential state and data:
```markdown
**Key File Paths:**
- Authentication service: src/services/auth.py
- Login endpoint: src/api/routes/auth.py
- JWT config: src/config/jwt.py
- Tests: tests/test_auth.py

**Important IDs:**
- Migration ID: 20251101_auth_schema
- Config section: authentication.jwt

**Environment Variables Required:**
- JWT_SECRET (must set in production)
- JWT_EXPIRATION_HOURS (default: 24)
- BCRYPT_ROUNDS (default: 12)

**Database Changes:**
- New column: users.password_hash (VARCHAR 255)
- Index needed on: users.email for login performance
```

### 8. Session Metadata

Automatically captured information:
```markdown
**Files Modified:**
- src/services/auth.py (created)
- src/api/routes/auth.py (created)
- src/config/jwt.py (created)
- src/models/user.py (modified)
- tests/test_auth.py (created)

**Agents Used:**
- PM (orchestration)
- Engineer (implementation)
- QA (testing)
- Security (review)

**Errors/Warnings:**
- None

**Session Duration:** 2 hours 34 minutes
```

## How to Use Resume Logs

### Automatic Usage (Recommended)

Resume logs work automatically with no user intervention:

**1. Session Running Normally**
```bash
claude-mpm run --monitor
# Work proceeds normally...
# At 70%: You see first caution warning
# At 85%: You see stronger warning
# At 95%: Resume log auto-generated
```

**2. Resuming After Auto-Generation**

When you start a new session, Claude MPM automatically:
- Detects resume log from previous session
- Loads it into context
- Provides summary of where you left off

```bash
# Start new session
claude-mpm run

# Claude MPM automatically shows:
# "Resuming from previous session (20251101_115000)..."
# "Context: Implementing user authentication system"
# "Last task: JWT token generation completed"
# "Next: Create database migration"
```

**3. Manual Session Pause/Resume**

You can explicitly pause and resume:

```bash
# Pause current session
/pause

# Resume log is generated and saved
# Session state preserved

# Later... resume session
/resume

# Previous context automatically loaded
# Work continues seamlessly
```

### Session Auto-Resume on Startup

**NEW in v4.19.0**: Claude MPM automatically detects and displays paused sessions when you start PM, helping you seamlessly continue your work with full context restoration.

#### How Auto-Resume Works

When PM starts, the system automatically:

1. **Checks for paused sessions** in `<project>/.claude-mpm/sessions/` (also checks legacy `sessions/pause/` location for backward compatibility)
2. **Identifies the most recent** paused session based on file modification time
3. **Calculates git changes** since the session was paused
4. **Displays resume context** to help you pick up where you left off

#### Resume Context Display

The auto-resume prompt shows:

```
================================================================================
📋 PAUSED SESSION FOUND
================================================================================

Paused: 2 hours ago

Last working on: Implementing automatic session resume functionality

Completed:
  ✓ Created SessionResumeHelper service
  ✓ Enhanced git change detection
  ✓ Added auto-resume to PM startup

Next steps:
  • Test auto-resume with real session data
  • Update documentation

Git changes since pause: 3 commits

Recent commits:
  a1b2c3d - feat: add SessionResumeHelper service (Engineer)
  e4f5g6h - test: add session resume tests (QA)
  i7j8k9l - docs: update PM_INSTRUCTIONS.md (Documentation)

================================================================================
Use this context to resume work, or start fresh if not relevant.
================================================================================
```

#### What Information Is Shown

- **Time elapsed**: Human-readable time since pause ("2 hours ago", "3 days ago")
- **Work summary**: What you were working on
- **Accomplishments**: What was completed in that session
- **Next steps**: Planned actions from the paused session
- **Git changes**: Commits made since the session was paused
- **Recent commits**: Detailed commit history with authors

#### Session Storage Format

Sessions are stored as JSON files in `<project>/.claude-mpm/sessions/session-YYYYMMDD-HHMMSS.json`:

```json
{
  "session_id": "session-YYYYMMDD-HHMMSS",
  "paused_at": "ISO-8601 timestamp",
  "conversation": {
    "summary": "What user was working on",
    "accomplishments": ["list of completed items"],
    "next_steps": ["list of planned next actions"]
  },
  "git_context": {
    "is_git_repo": true,
    "branch": "current branch name",
    "recent_commits": [
      {
        "sha": "commit hash",
        "author": "author name",
        "timestamp": "commit timestamp",
        "message": "commit message"
      }
    ],
    "status": {
      "clean": true,
      "modified_files": [],
      "untracked_files": []
    }
  },
  "todos": {
    "active": [{"status": "in_progress", "content": "task", "activeForm": "doing task"}],
    "completed": [{"status": "completed", "content": "done task"}]
  },
  "version": "claude-mpm version",
  "build": "build number",
  "project_path": "absolute path"
}
```

#### Storage Location

**Project-Specific Sessions:**

Sessions are stored per-project in:
```
<project-root>/.claude-mpm/sessions/
```

This ensures:
- ✓ Sessions are project-specific
- ✓ No cross-project contamination
- ✓ Easy cleanup (delete `.claude-mpm` directory)
- ✓ Git-ignorable by default

**Note**: The system also checks the legacy `sessions/pause/` location for backward compatibility with older session files.

**File Permissions:**

Session files are created with `0600` permissions (user read/write only) for security.

#### Benefits of Auto-Resume

**1. Seamless Work Continuation**

- **Context restoration**: Immediately understand where you left off
- **Git awareness**: See what changed while you were away
- **Next steps clarity**: Know what to work on next

**2. Team Collaboration**

- **Handoff support**: Team members can see what was being worked on
- **Progress tracking**: Clear record of accomplishments
- **Work stream visibility**: Git changes show team activity

**3. Long Breaks**

- **Memory aid**: Recall context after days or weeks
- **Work reconstruction**: Understand project state evolution
- **Decision tracking**: See what decisions were made

#### Managing Sessions

**List Paused Sessions:**
```bash
ls -la .claude-mpm/sessions/
```

**Clear Paused Sessions:**
```bash
# Remove all paused sessions
rm .claude-mpm/sessions/session-*.json
```

**Clear Specific Session:**
```python
from claude_mpm.services.cli.session_resume_helper import SessionResumeHelper

helper = SessionResumeHelper()
session = helper.get_most_recent_session()

if session:
    helper.clear_session(session)
```

#### Troubleshooting Auto-Resume

**Session Not Detected**

**Problem**: No resume prompt appears despite paused sessions existing

**Solutions**:
1. Check session directory exists: `ls .claude-mpm/sessions/`
2. Verify JSON files are valid: `python -m json.tool .claude-mpm/sessions/session-*.json`
3. Check file permissions: `ls -la .claude-mpm/sessions/`
4. Review logs: `tail -f .claude-mpm/logs/claude-mpm.log`

**Git Changes Not Showing**

**Problem**: Git changes since pause shows 0 commits

**Solutions**:
1. Verify git repository: `git status`
2. Check pause timestamp: Look at `paused_at` in session JSON
3. Ensure commits are after pause time
4. Check git log: `git log --since="<pause_timestamp>"`

**Incorrect Time Elapsed**

**Problem**: Time elapsed shows wrong value

**Solutions**:
1. Check system timezone configuration
2. Verify `paused_at` timestamp format (ISO-8601)
3. Ensure timezone information is included
4. Review server time vs local time

### Viewing Resume Logs

Resume logs are stored in `.claude-mpm/resume-logs/`:

```bash
# List all resume logs
ls -lh .claude-mpm/resume-logs/

# View latest resume log
cat .claude-mpm/resume-logs/session-20251101_115000.md

# Open in editor
code .claude-mpm/resume-logs/session-20251101_115000.md
```

### Manual Generation (Advanced)

You can programmatically generate resume logs:

```python
from claude_mpm.services.session_manager import get_session_manager

# Get session manager
session_mgr = get_session_manager()

# Update token usage
session_mgr.update_token_usage(
    input_tokens=100000,
    output_tokens=40000,
    stop_reason="end_turn"
)

# Generate resume log manually
session_state = {
    "mission_summary": "Your mission description",
    "accomplishments": ["Task 1", "Task 2"],
    "next_steps": ["Task 3", "Task 4"],
}

log_path = session_mgr.generate_resume_log(session_state=session_state)
print(f"Resume log saved to: {log_path}")
```

## Configuration Options

Resume logs are configured in `.claude-mpm/configuration.yaml`:

### Basic Configuration

```yaml
context_management:
  enabled: true                # Enable context management
  budget_total: 200000        # Total token budget (Claude 3.5 Sonnet)

  thresholds:
    caution: 0.70             # First warning (60k buffer)
    warning: 0.85             # Strong warning (30k buffer)
    critical: 0.95            # Urgent stop (10k buffer)

  resume_logs:
    enabled: true             # Enable resume log generation
    auto_generate: true       # Auto-generate on thresholds/stop_reason
    max_tokens: 10000        # Maximum tokens per resume log
    storage_dir: ".claude-mpm/resume-logs"  # Storage location
    format: "markdown"        # Output format (markdown only for now)
```

### Advanced Configuration

```yaml
context_management:
  resume_logs:
    # Triggers for resume log generation
    triggers:
      - "model_context_window_exceeded"  # API limit exceeded
      - "max_tokens"                     # Token limit reached
      - "manual_pause"                   # User paused session
      - "threshold_critical"             # 95% threshold
      - "threshold_warning"              # 85% threshold (optional)

    # Cleanup old resume logs
    cleanup:
      enabled: true          # Enable automatic cleanup
      keep_count: 10        # Keep last 10 resume logs
      auto_cleanup: true    # Clean up on session start
```

### Token Budget Allocation

You can customize the token distribution across sections:

```yaml
context_management:
  resume_logs:
    token_allocation:
      context_metrics: 500
      mission_summary: 1000
      accomplishments: 2000
      key_findings: 2500
      decisions: 1500
      next_steps: 1500
      critical_context: 1000
```

### Model-Specific Budgets

Different models have different context windows:

```yaml
context_management:
  # Claude 3.5 Sonnet (default)
  budget_total: 200000

  # Claude 3 Opus (larger context)
  # budget_total: 200000

  # Claude 3 Haiku (smaller context)
  # budget_total: 200000
```

## Best Practices

### For Daily Usage

**1. Trust the Automatic System**
- Let resume logs generate automatically
- Don't manually pause unless necessary
- Resume logs are optimized for continuity

**2. Plan for Thresholds**
```
At 70%: Start thinking about wrapping up
At 85%: Complete current task, avoid new work
At 95%: Stop immediately, review resume log
```

**3. Use Natural Breakpoints**
- Complete current feature before pausing
- Finish test suite before session end
- Document decisions before hitting limits

**4. Review Resume Logs**
- Check generated resume logs for accuracy
- Verify critical context is captured
- Update if key information missing

### For Long Tasks

**1. Break Into Sessions**

Instead of one 200k-token session:
```
Session 1 (140k tokens): Research and planning
Session 2 (140k tokens): Implementation
Session 3 (140k tokens): Testing and docs
```

**2. Strategic Pausing**

Pause at natural breakpoints:
- After completing a feature
- Before switching to different component
- After major refactoring
- Before deployment

**3. Maintain Context Across Sessions**

Use resume logs to:
- Document design decisions
- Track file paths and IDs
- Note important findings
- List remaining tasks

### For Team Collaboration

**1. Share Resume Logs**

Resume logs are great handoff documentation:
```bash
# Share latest resume log
git add .claude-mpm/resume-logs/session-20251101_115000.md
git commit -m "Add session resume log for auth implementation"
```

**2. Use as Session Notes**

Resume logs serve as:
- Sprint documentation
- Work session summaries
- Decision logs
- Handoff documentation

**3. Version Control Integration**

Add to `.gitignore` if too chatty:
```gitignore
# Optionally ignore resume logs (auto-generated)
.claude-mpm/resume-logs/*.md
.claude-mpm/resume-logs/*.json
```

Or commit strategically:
```bash
# Commit only important session logs
git add .claude-mpm/resume-logs/session-release-v1.md
```

## Troubleshooting

### Resume Log Not Generated

**Symptoms**: Hit 95% threshold but no resume log created

**Check Configuration**:
```bash
# Verify resume logs are enabled
cat .claude-mpm/configuration.yaml | grep -A 10 "resume_logs:"

# Should show:
# resume_logs:
#   enabled: true
#   auto_generate: true
```

**Solution**:
```yaml
# Enable in configuration.yaml
context_management:
  resume_logs:
    enabled: true
    auto_generate: true
```

### Token Usage Not Tracking

**Symptoms**: No threshold warnings appear

**Check Response Tracking**:
```python
from claude_mpm.services.session_manager import get_session_manager

session_mgr = get_session_manager()
metrics = session_mgr.get_context_metrics()
print(metrics)
```

**Expected Output**:
```python
{
    "total_budget": 200000,
    "used_tokens": 140000,
    "percentage_used": 70.0,
    "remaining_tokens": 60000,
    "stop_reason": "end_turn"
}
```

**Solution**:

Ensure response tracking is enabled in configuration:
```yaml
hooks:
  response_tracking:
    enabled: true
```

### Resume Log Not Loading on Startup

**Symptoms**: New session doesn't show previous context

**Check File Permissions**:
```bash
# Verify resume log files exist
ls -la .claude-mpm/resume-logs/

# Check latest file
ls -lt .claude-mpm/resume-logs/*.md | head -1
```

**Check Auto-Loading**:
```yaml
# Verify auto-loading is enabled
context_management:
  resume_logs:
    auto_load: true  # Should be true
```

**Manual Loading**:

If auto-loading fails, manually load the resume log:
```bash
# Read the latest resume log
cat .claude-mpm/resume-logs/session-*.md | tail -1

# Copy and paste into new session
```

### Resume Log Too Large

**Symptoms**: Resume log exceeds 10k tokens

**Solution**:

The system automatically truncates to 10k tokens, but you can adjust allocation:

```yaml
context_management:
  resume_logs:
    max_tokens: 8000  # Reduce to 8k for safety margin
```

Or adjust section allocations:
```yaml
context_management:
  resume_logs:
    token_allocation:
      accomplishments: 1500  # Reduce from 2000
      key_findings: 2000     # Reduce from 2500
```

### Cleanup Deleting Important Logs

**Symptoms**: Old resume logs deleted automatically

**Solution**:

Adjust retention policy:
```yaml
context_management:
  resume_logs:
    cleanup:
      keep_count: 20        # Keep more logs
      auto_cleanup: false   # Disable automatic cleanup
```

Or manually backup important logs:
```bash
# Create backup directory
mkdir .claude-mpm/resume-logs/archive

# Move important logs
cp .claude-mpm/resume-logs/session-release-*.md \
   .claude-mpm/resume-logs/archive/
```

## Advanced Usage

### Custom Resume Log Triggers

Add custom triggers for specific scenarios:

```yaml
context_management:
  resume_logs:
    triggers:
      - "model_context_window_exceeded"
      - "custom_checkpoint"  # Custom trigger
```

Then generate programmatically:
```python
session_mgr.generate_resume_log(
    session_state=state,
    trigger="custom_checkpoint"
)
```

### Integration with CI/CD

Generate resume logs as part of deployment:

```bash
#!/bin/bash
# pre-deploy.sh

# Generate resume log for deployment record
claude-mpm mpm-init pause

# Resume log created in .claude-mpm/resume-logs/
# Upload to artifact storage
aws s3 cp .claude-mpm/resume-logs/session-*.md \
  s3://my-bucket/deployment-logs/
```

### Multi-Session Projects

For projects requiring multiple related sessions:

```python
from claude_mpm.services.infrastructure.resume_log_generator import ResumeLogGenerator

generator = ResumeLogGenerator()

# Generate session series
sessions = ["research", "implementation", "testing"]

for phase in sessions:
    session_state = {
        "mission_summary": f"Project phase: {phase}",
        # ... phase-specific state
    }

    log_path = generator.generate_from_session_state(
        session_id=f"project_{phase}",
        session_state=session_state
    )
    print(f"Phase {phase} log: {log_path}")
```

### Custom Resume Log Format

While only markdown is currently supported, you can post-process:

```python
from claude_mpm.services.infrastructure.resume_log_generator import ResumeLogGenerator
import json

generator = ResumeLogGenerator()

# Load existing resume log
resume_log = generator.load_resume_log("session-20251101_115000")

# Convert to custom format
custom_format = {
    "session_id": resume_log.session_id,
    "metrics": resume_log.context_metrics.__dict__,
    "summary": resume_log.mission_summary,
    # ... custom fields
}

# Save as JSON
with open("custom-resume.json", "w") as f:
    json.dump(custom_format, f, indent=2)
```

## Related Documentation

- [Session Management](../user-guide.md#session-management) - Pause/resume workflows
- [Developer Architecture](../developer/resume-log-architecture.md) - Technical implementation
- [Configuration Reference](../configuration/reference.md) - Complete config options
- [Examples](../examples/resume-log-examples.md) - Real-world examples

## Summary

The Resume Log System provides:
- ✅ Automatic context preservation at 70%/85%/95% thresholds
- ✅ 10k-token structured logs for efficient resumption
- ✅ Seamless integration with session management
- ✅ Human-readable markdown format
- ✅ Fully configurable triggers and retention
- ✅ Zero-configuration automatic operation

**Next Steps:**
1. Enable resume logs in your configuration (likely already enabled)
2. Run a session and observe threshold warnings
3. Review generated resume logs in `.claude-mpm/resume-logs/`
4. Customize thresholds and triggers as needed
5. Integrate with your workflow (pause before major changes)

**Questions or Issues?**
- See [Troubleshooting](../user/troubleshooting.md)
- Check [Examples](../examples/resume-log-examples.md)
- Review [Developer Documentation](../developer/resume-log-architecture.md)

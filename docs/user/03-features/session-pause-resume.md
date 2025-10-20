# Session Pause and Resume

**Version:** 4.8.5+
**Status:** Production Ready
**Last Updated:** October 2025

## Overview

The Session Pause and Resume feature enables you to save and restore complete session state across multiple Claude sessions, maintaining full context continuity for seamless work resumption.

## Table of Contents

- [Why Session Management?](#why-session-management)
- [Quick Start](#quick-start)
- [Core Concepts](#core-concepts)
- [Usage Guide](#usage-guide)
- [Session Storage](#session-storage)
- [Change Detection](#change-detection)
- [Common Workflows](#common-workflows)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)
- [Technical Details](#technical-details)

## Why Session Management?

### The Context Problem

When working with Claude on complex projects, context is everything. Traditional workflows lose critical context when:
- Ending a work session for the day
- Switching between different tasks
- Handing off work to team members
- Taking breaks during long projects

### The Solution

Session Pause and Resume solves this by:
- **Capturing** complete conversation context and progress
- **Preserving** git state, todos, and working directory status
- **Detecting** changes that occurred while paused
- **Restoring** full context for seamless continuation

## Quick Start

### Basic Pause and Resume

```bash
# End of work session
claude-mpm mpm-init pause -s "Completed user authentication module"

# Later, when resuming
claude-mpm mpm-init resume
```

That's it! Your full context is preserved and restored.

### With Detailed Context

```bash
# Pause with accomplishments and next steps
claude-mpm mpm-init pause \
  -s "Working on payment integration" \
  -a "Integrated Stripe API" \
  -a "Added webhook handlers" \
  -a "Created test suite" \
  -n "Add refund functionality" \
  -n "Implement subscription management"

# Resume and see full context plus any changes
claude-mpm mpm-init resume
```

## Core Concepts

### What Gets Saved

When you pause a session, the following state is captured:

#### 1. Conversation Context
- **Summary**: High-level description of what you were working on
- **Accomplishments**: What you completed in this session
- **Next Steps**: What needs to be done next
- **Active Todos**: Current todo list items
- **Completed Todos**: What you've finished

#### 2. Git Context
- **Current Branch**: Which branch you're working on
- **Latest Commit**: SHA and message of HEAD
- **Repository Status**: Modified, staged, untracked files
- **Remote State**: Whether branch is ahead/behind remote

#### 3. Project State
- **Working Directory**: Uncommitted changes
- **Project Path**: Absolute path to project
- **Version Info**: Claude MPM version and build number
- **Timestamp**: When the session was paused

### What Gets Restored

When you resume a session, you receive:

#### 1. Full Context
- Complete conversation summary
- All accomplishments and next steps
- Todo list state (active and completed)
- Original git state

#### 2. Change Detection
- **New Commits**: List of commits since pause
- **Modified Files**: Files changed while paused
- **Branch Changes**: If branch was switched or merged
- **Conflicts**: Potential conflicts with paused state
- **Uncommitted Changes**: Working directory modifications

## Usage Guide

### Pausing Sessions

#### Basic Pause

Minimal pause with auto-generated summary:

```bash
claude-mpm mpm-init pause
```

#### Pause with Summary

Include context about what you were doing:

```bash
claude-mpm mpm-init pause -s "Implemented OAuth2 authentication flow"
```

#### Detailed Pause

Full context with accomplishments and next steps:

```bash
claude-mpm mpm-init pause \
  -s "Working on user dashboard" \
  -a "Created dashboard layout component" \
  -a "Added data visualization charts" \
  -a "Implemented real-time updates" \
  -n "Add filtering controls" \
  -n "Optimize chart rendering performance" \
  -n "Write integration tests"
```

#### Pause Without Git Commit

Skip automatic git commit creation:

```bash
claude-mpm mpm-init pause --no-commit -s "WIP: refactoring in progress"
```

**Note:** By default, pause creates an optional git commit with session information for team visibility.

### Resuming Sessions

#### Resume Latest Session

Automatically load the most recent paused session:

```bash
claude-mpm mpm-init resume
```

#### List Available Sessions

See all paused sessions with timestamps:

```bash
claude-mpm mpm-init resume --list
```

Output example:
```
📋 Available Paused Sessions:

  [0] session-20251020-143022 - 2025-10-20 14:30
      Summary: Working on payment integration

  [1] session-20251019-170015 - 2025-10-19 17:00
      Summary: Implemented user authentication

  [2] session-20251018-155500 - 2025-10-18 15:55
      Summary: Database migration completed

Select session to resume [0]:
```

#### Resume Specific Session

Load a particular session by ID:

```bash
claude-mpm mpm-init resume --session-id session-20251020-143022
```

### Pause Options Reference

| Option | Short | Type | Description |
|--------|-------|------|-------------|
| `--summary` | `-s` | TEXT | Session summary (what you were working on) |
| `--accomplishment` | `-a` | TEXT | Record accomplishment (can be used multiple times) |
| `--next-step` | `-n` | TEXT | Document next step (can be used multiple times) |
| `--no-commit` | - | FLAG | Skip creating git commit with session info |

### Resume Options Reference

| Option | Description |
|--------|-------------|
| `--session-id TEXT` | Resume specific session by ID |
| `--list` | List all available paused sessions |

## Session Storage

### Storage Location

Sessions are stored in your project's `.claude-mpm/sessions/pause/` directory:

```
your-project/
├── .claude-mpm/
│   ├── sessions/
│   │   └── pause/
│   │       ├── session-20251020-143022.json
│   │       ├── session-20251019-170015.json
│   │       └── session-20251018-155500.json
```

### File Format

Sessions are stored as JSON files with the following structure:

```json
{
  "session_id": "session-20251020-143022",
  "paused_at": "2025-10-20T14:30:22.123456Z",
  "conversation": {
    "summary": "Working on payment integration",
    "accomplishments": [
      "Integrated Stripe API",
      "Added webhook handlers",
      "Created test suite"
    ],
    "next_steps": [
      "Add refund functionality",
      "Implement subscription management"
    ]
  },
  "git_context": {
    "branch": "feature/payments",
    "commit": "abc123def456",
    "commit_message": "Add Stripe webhook handlers",
    "status": {
      "modified": ["src/payments/stripe.py"],
      "staged": [],
      "untracked": ["tests/test_webhooks.py"]
    },
    "is_clean": false,
    "ahead_behind": {"ahead": 2, "behind": 0}
  },
  "todos": {
    "active": [
      {"content": "Add refund functionality", "status": "pending"}
    ],
    "completed": [
      {"content": "Integrate Stripe API", "status": "completed"}
    ]
  },
  "version": "4.8.5",
  "build": "320",
  "project_path": "/Users/you/projects/myapp"
}
```

### Security

Session files are created with strict permissions:
- **Permissions**: `0600` (owner read/write only)
- **Checksums**: Integrity verification on load
- **Location**: Project-local (not synced to cloud by default)

### File Naming

Session files follow the pattern: `session-YYYYMMDD-HHMMSS.json`
- **YYYY**: Four-digit year
- **MM**: Two-digit month
- **DD**: Two-digit day
- **HH**: Two-digit hour (24-hour format)
- **MM**: Two-digit minute
- **SS**: Two-digit second

## Change Detection

### What Gets Detected

When resuming a session, the system automatically detects:

#### Git Changes
- **New Commits**: All commits made since pause
- **Branch Changes**: If branch was switched or merged
- **Modified Files**: Files changed in new commits
- **Remote Changes**: Pushes/pulls from remote repository

#### Working Directory Changes
- **Uncommitted Changes**: Modified files not yet committed
- **Staged Files**: Files added to git staging area
- **Untracked Files**: New files not in git

#### Potential Issues
- **Conflicts**: Files modified both before and after pause
- **Diverged Branches**: Branch has diverged from remote
- **Missing Files**: Files that existed at pause but are now deleted

### Change Detection Output

When you resume, you'll see a detailed change report:

```
📊 Session Resume: session-20251020-143022

Paused: 2025-10-20 14:30:22 (2 hours ago)
Summary: Working on payment integration

✅ Accomplishments (3):
  • Integrated Stripe API
  • Added webhook handlers
  • Created test suite

📋 Next Steps (2):
  • Add refund functionality
  • Implement subscription management

🔄 Changes Since Pause:

  New Commits (2):
    abc1234 - Fix webhook signature verification (2h ago)
    def5678 - Add test coverage for error cases (1h ago)

  Modified Files (3):
    M  src/payments/stripe.py
    M  tests/test_webhooks.py
    A  src/payments/errors.py

  ⚠️  Potential Conflicts (1):
    • src/payments/stripe.py modified both before and after pause

  Working Directory:
    • No uncommitted changes
```

## Common Workflows

### Daily Work Cycle

```bash
# Morning: Start work
claude-mpm mpm-init resume

# ... work throughout the day ...

# Evening: End of day
claude-mpm mpm-init pause \
  -s "End of day - feature X in progress" \
  -a "Completed API integration" \
  -a "Added unit tests" \
  -n "Add integration tests tomorrow" \
  -n "Update documentation"
```

### Team Handoffs

**Developer A (ending shift):**
```bash
claude-mpm mpm-init pause \
  -s "Authentication module ready for review" \
  -a "Implemented OAuth2 flow" \
  -a "Added JWT token handling" \
  -a "All tests passing" \
  -n "Needs code review" \
  -n "Consider adding rate limiting" \
  -n "Update API documentation"
```

**Developer B (starting shift):**
```bash
# See what's available
claude-mpm mpm-init resume --list

# Pick up where Developer A left off
claude-mpm mpm-init resume --session-id session-20251020-170000
```

### Context Switching

When working on multiple features:

```bash
# Pause current work on feature A
claude-mpm mpm-init pause -s "Feature A: database migration in progress"

# Work on urgent feature B
# ... make changes ...

# Pause feature B
claude-mpm mpm-init pause -s "Feature B: hotfix completed"

# Resume feature A work
claude-mpm mpm-init resume --list
# Select feature A session
```

### Long-Running Projects

```bash
# Pause at milestone
claude-mpm mpm-init pause \
  -s "Milestone 2 complete: MVP features done" \
  -a "User authentication working" \
  -a "Payment processing integrated" \
  -a "Email notifications functional" \
  -n "Start Milestone 3: Analytics dashboard" \
  -n "Performance optimization" \
  -n "Security audit"

# Resume days or weeks later
claude-mpm mpm-init resume
# Full context plus all team changes detected
```

### Emergency Context Save

Quick pause during interruptions:

```bash
# Urgent meeting or interruption
claude-mpm mpm-init pause --no-commit

# Resume when back
claude-mpm mpm-init resume
```

## Best Practices

### 1. Provide Meaningful Summaries

**Good:**
```bash
claude-mpm mpm-init pause -s "Implemented user authentication with OAuth2 and JWT"
```

**Better:**
```bash
claude-mpm mpm-init pause \
  -s "User authentication complete, starting authorization" \
  -a "OAuth2 login flow working" \
  -a "JWT token generation and validation" \
  -a "Password reset via email" \
  -n "Add role-based authorization" \
  -n "Implement permission system"
```

### 2. Use Accomplishments and Next Steps

Document what you did and what's next:
- **Accomplishments**: Help others (and future you) understand progress
- **Next Steps**: Clear roadmap for continuation
- **Multiple Items**: Use `-a` and `-n` multiple times for detailed tracking

### 3. Regular Pausing

Pause at natural breakpoints:
- End of work sessions
- Before switching contexts
- After completing major features
- Before team handoffs
- During code reviews

### 4. Review Before Resuming

When resuming, carefully review:
- **Change Detection**: What changed while paused
- **Conflicts**: Any files modified in both contexts
- **Next Steps**: Refresh your memory on what's next

### 5. Git Integration

**Use default behavior** (with git commits):
- Creates visibility for team members
- Provides audit trail
- Enables collaboration

**Use `--no-commit` when**:
- Work is incomplete or experimental
- Not ready for team visibility
- Frequent context switching

### 6. Clean Up Old Sessions

Periodically remove old session files:

```bash
# List sessions
claude-mpm mpm-init resume --list

# Manually remove old ones
rm .claude-mpm/sessions/pause/session-20251001-*.json
```

## Troubleshooting

### No Paused Sessions Found

**Problem:** Running `resume` shows no sessions.

**Solutions:**
1. Check if sessions directory exists:
   ```bash
   ls -la .claude-mpm/sessions/pause/
   ```

2. Verify you're in correct project directory

3. Create a test session:
   ```bash
   claude-mpm mpm-init pause -s "Test session"
   ```

### Session File Corrupted

**Problem:** Error loading session file.

**Solutions:**
1. Check file permissions:
   ```bash
   ls -l .claude-mpm/sessions/pause/
   ```

2. Validate JSON:
   ```bash
   cat .claude-mpm/sessions/pause/session-*.json | python -m json.tool
   ```

3. Remove corrupted file and use different session

### Change Detection Issues

**Problem:** Changes not detected correctly.

**Solutions:**
1. Ensure git repository is healthy:
   ```bash
   git status
   git log --oneline -5
   ```

2. Check git configuration:
   ```bash
   git config --list
   ```

3. Resume will still work, just without change detection

### Permission Errors

**Problem:** Cannot write session file.

**Solutions:**
1. Check directory permissions:
   ```bash
   ls -ld .claude-mpm/sessions/pause/
   ```

2. Create directory if missing:
   ```bash
   mkdir -p .claude-mpm/sessions/pause
   chmod 700 .claude-mpm/sessions/pause
   ```

3. Fix ownership if needed:
   ```bash
   chown -R $USER .claude-mpm/
   ```

## Technical Details

### Implementation

Session pause/resume is implemented through:

- **SessionPauseManager**: Captures and saves session state
- **SessionResumeManager**: Loads and analyzes paused sessions
- **StateStorage**: Handles atomic file operations and checksums
- **Git Integration**: Detects changes via git commands

### File Operations

Sessions are saved using atomic writes:
1. Write to temporary file
2. Calculate checksum
3. Atomic rename to final location
4. Set secure permissions (0600)

### Change Detection Algorithm

Resume performs change detection by:
1. Load paused session git context
2. Get current git state
3. Compare commits: `git log <paused_commit>..HEAD`
4. Analyze file changes: `git diff --name-status`
5. Check working directory: `git status --porcelain`
6. Identify potential conflicts

### Security Considerations

- **File Permissions**: 0600 (owner-only read/write)
- **Directory Permissions**: 0700 (owner-only access)
- **Data Integrity**: SHA-256 checksums on session files
- **Sensitive Data**: No credentials or secrets stored
- **Git Commits**: Optional, can be disabled with `--no-commit`

### Performance

- **Pause**: < 100ms for typical sessions
- **Resume**: < 200ms including change detection
- **Storage**: ~5-10KB per session file
- **Git Operations**: Optimized with `--no-pager` and limited output

### Limitations

- **Git Required**: Change detection requires git repository
- **Project-Local**: Sessions not shared across projects
- **No Encryption**: Session files stored in plaintext
- **No Auto-Cleanup**: Old sessions must be manually removed
- **Single User**: Designed for individual developer workflows

## Related Features

- **[Memory System](memory-system.md)**: Persistent project knowledge across all sessions
- **[Git Integration](../02-guides/git-integration.md)**: Git-based workflow features
- **[Session Logging](session-logging.md)**: Complete session activity logs
- **[Quick Update](../commands/mpm-init.md#quick-update-mode)**: Lightweight project updates

## See Also

- **Command Reference**: [`claude-mpm mpm-init pause/resume`](../commands/mpm-init.md)
- **CLI Guide**: [CLI Commands Reference](../02-guides/cli-commands-reference.md#session-management)
- **Architecture**: [Session Management Design](../../developer/architecture/session-management.md)

---

**Need Help?**
- Report issues: [GitHub Issues](https://github.com/bobmatnyc/claude-mpm/issues)
- Community support: [Discussions](https://github.com/bobmatnyc/claude-mpm/discussions)
- Documentation: [Main Docs](../../README.md)

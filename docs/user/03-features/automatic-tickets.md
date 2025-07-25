# Automatic Ticket Creation

Claude MPM's automatic ticket creation feature transforms conversations into actionable, trackable tasks without manual intervention.

## How It Works

### Pattern Detection

Claude MPM monitors all conversations for specific patterns:

```python
TICKET_PATTERNS = [
    r'TODO:\s*(.+)',
    r'TASK:\s*(.+)',
    r'BUG:\s*(.+)',
    r'FEATURE:\s*(.+)',
    r'ISSUE:\s*(.+)',
    r'FIX:\s*(.+)'
]
```

When detected, tickets are created automatically with:
- Unique ID (TSK-XXXX format)
- Extracted title
- Appropriate type
- Timestamp
- Session reference

### Real-Time Extraction

```
You: I need to TODO: Add input validation to the login form and 
     TODO: Implement password strength checker

Claude: I'll help you with both tasks...

[System: Created tickets]
- TSK-0001: Add input validation to the login form
- TSK-0002: Implement password strength checker
```

## Ticket Types

### Automatic Type Assignment

| Pattern | Ticket Type | Use Case |
|---------|------------|----------|
| `TODO:` | task | General tasks |
| `TASK:` | task | Explicit tasks |
| `BUG:` | bug | Defects/issues |
| `FEATURE:` | feature | New functionality |
| `ISSUE:` | issue | Problems to investigate |
| `FIX:` | bug | Quick fixes |

### Examples

```bash
# Creates a task
"TODO: Refactor the authentication module"

# Creates a bug
"BUG: Users can't reset passwords"

# Creates a feature
"FEATURE: Add two-factor authentication"

# Multiple tickets
"TODO: Write tests, TODO: Update docs, BUG: Fix memory leak"
```

## Ticket Structure

### Generated Ticket Format

Each ticket is saved as a Markdown file:

```markdown
# TSK-0001 - Add input validation to the login form

- **Type**: task
- **Priority**: medium
- **Status**: pending
- **Created**: 2024-01-25 14:30:22
- **Session**: session_20240125_143022.log
- **Source**: Automatic extraction

## Description

Add input validation to the login form

## Context

Extracted from Claude MPM session during conversation about 
authentication improvements.

## Session Reference

File: ~/.claude-mpm/sessions/session_20240125_143022.log
Line: 42
```

## Priority Assignment

### Automatic Priority Rules

Claude MPM assigns priority based on keywords:

| Keywords | Priority | Examples |
|----------|----------|----------|
| critical, urgent, asap, emergency | critical | "TODO: Fix critical security bug" |
| important, high, major | high | "BUG: Major performance issue" |
| normal, moderate | medium | "TASK: Update documentation" |
| minor, low, later | low | "TODO: Minor UI improvement" |

### Priority Examples

```
"TODO: URGENT Fix authentication bypass" → critical
"BUG: Important data loss issue" → high  
"TASK: Refactor code" → medium
"TODO: Minor typo in comments" → low
```

## Multi-Ticket Extraction

### Single Message, Multiple Tickets

Claude MPM can extract multiple tickets from one message:

```
You: We need to TODO: Setup CI/CD pipeline, TODO: Add unit tests
     for the API, and BUG: Fix the login timeout issue.

[Creates 3 tickets:]
- TSK-0001: Setup CI/CD pipeline (task, medium)
- TSK-0002: Add unit tests for the API (task, medium)
- TSK-0003: Fix the login timeout issue (bug, medium)
```

### Nested Conversations

Tickets are extracted throughout the conversation:

```
You: Let's plan the authentication system

Claude: Here's what we need to implement:
        TODO: Create user model with secure password storage
        TODO: Implement JWT token generation
        TODO: Add refresh token mechanism

[Creates 3 tickets from Claude's response]
```

## Integration with Ticket System

### Unified Ticket Management

Automatically created tickets integrate with manual tickets:

```bash
# View all tickets (automatic + manual)
./ticket list

# Automatic tickets appear with source
TSK-0001 | Add validation     | task | auto
TSK-0002 | Fix memory leak    | bug  | auto
TSK-0003 | Manual ticket      | task | manual
```

### Ticket Operations

Work with automatic tickets like any other:

```bash
# Update status
./ticket update TSK-0001 -s in_progress

# Add details
./ticket update TSK-0001 -d "Additional validation requirements..."

# Close when done
./ticket close TSK-0001
```

## Configuration

### Custom Patterns

Add your own patterns in configuration:

```python
# In your config
CUSTOM_TICKET_PATTERNS = [
    r'FIXME:\s*(.+)',
    r'HACK:\s*(.+)',
    r'OPTIMIZE:\s*(.+)',
    r'SECURITY:\s*(.+)'
]
```

### Pattern Mapping

Map patterns to ticket types:

```python
PATTERN_TYPE_MAPPING = {
    'FIXME': 'bug',
    'HACK': 'task',
    'OPTIMIZE': 'enhancement',
    'SECURITY': 'security'
}
```

### Disable Automatic Creation

```bash
# Disable for a session
claude-mpm run -i "Prompt" --no-tickets

# Or in interactive mode
claude-mpm --no-tickets
```

## Advanced Features

### Context Preservation

Tickets include conversation context:

```markdown
## Context Snippet

User: We need better error handling in the API
Claude: I'll help you improve error handling. You should:
        TODO: Add try-catch blocks to all endpoints
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
        [Ticket created from this line]
```

### Duplicate Detection

Claude MPM attempts to avoid duplicates:

```
You: TODO: Add user authentication
[Created: TSK-0001]

You: TODO: Add user authentication  
[Skipped: Similar to TSK-0001]
```

### Batch Processing

Process multiple files or conversations:

```bash
# Extract tickets from saved conversation
claude-mpm extract-tickets conversation.log

# Process multiple sessions
for session in ~/.claude-mpm/sessions/*.log; do
    claude-mpm extract-tickets "$session"
done
```

## Best Practices

### 1. Clear Descriptions

```
# Good: Specific and actionable
TODO: Add email validation to registration form using regex

# Poor: Vague
TODO: Fix form
```

### 2. Use Appropriate Patterns

```
# Bug for defects
BUG: Login returns 500 error for users with spaces in email

# Feature for new functionality
FEATURE: Add CSV export for user data

# Task for general work
TASK: Refactor database connection pooling
```

### 3. Include Context

```
# Provide context in the same message
TODO: Migrate from SQLite to PostgreSQL (current DB hitting 2GB limit)
```

### 4. Group Related Items

```
# Related tickets in one message
For the authentication system:
TODO: Implement password hashing with bcrypt
TODO: Add password complexity requirements  
TODO: Create password reset flow
```

## Troubleshooting

### Tickets Not Created

**Check pattern format**:
```
✓ TODO: Description  (correct - has colon and space)
✗ TODO Description   (missing colon)
✗ TODO:Description   (missing space)
```

**Verify not disabled**:
```bash
# Don't use --no-tickets flag
claude-mpm run -i "TODO: Task" --no-tickets  # Won't create ticket
```

**Check ticket directory**:
```bash
# Ensure directory exists
ls -la tickets/tasks/

# Create if missing
mkdir -p tickets/tasks
```

### Duplicate Tickets

**Manual deduplication**:
```bash
# Check before conversation
./ticket list | grep -i "authentication"

# Remove duplicates
rm tickets/tasks/TSK-0002.md  # If duplicate
```

### Wrong Ticket Type

**Override in update**:
```bash
# Change type after creation
./ticket update TSK-0001 -t feature
```

## Examples

### Development Session

```
You: I'm working on the user service. TODO: Add email verification,
     TODO: Implement rate limiting, and BUG: Fix duplicate user 
     creation issue.

[Creates:]
- TSK-0001: Add email verification (task)
- TSK-0002: Implement rate limiting (task)  
- TSK-0003: Fix duplicate user creation issue (bug)
```

### Code Review

```
You: Reviewing the auth module, I found:
     BUG: Passwords stored in plain text
     BUG: No session timeout
     TODO: Add CSRF protection
     FEATURE: Add OAuth support

[Creates 4 tickets with appropriate types]
```

### Planning Session

```
You: For MVP we need:
     FEATURE: User registration and login
     FEATURE: Password reset
     TODO: Setup email service
     TODO: Create user dashboard
     
[Creates 4 tickets for MVP planning]
```

## Integration with Workflow

### Git Commits

Reference auto-created tickets:

```bash
git commit -m "Implement email validation (TSK-0001)"
git commit -m "Fix: Resolve duplicate users bug [TSK-0003]"
```

### PR Descriptions

```markdown
## Changes
- Implements email verification (TSK-0001)
- Adds rate limiting (TSK-0002)
- Fixes duplicate user bug (TSK-0003)

All tickets auto-generated from planning session.
```

### Sprint Planning

```bash
# List this sprint's auto-generated tickets
./ticket list | grep "auto" | grep "$(date +%Y-%m)"
```

## Next Steps

- Learn about [Agent Delegation](agent-delegation.md) for specialized help
- Explore [Session Logging](session-logging.md) to review ticket creation
- See [Ticket Management Guide](../02-guides/ticket-management.md) for working with tickets
- Check [Configuration](../04-reference/configuration.md) for customization
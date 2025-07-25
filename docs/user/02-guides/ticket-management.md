# Ticket Management Guide

Master Claude MPM's ticket system to organize and track your development tasks effectively.

> **Note**: Claude MPM uses `ai-trackdown-pytools` for ticket management. For detailed command usage and advanced features, see [Ticket Management with AI Trackdown](ticket-management-aitrackdown.md).

## Overview

Claude MPM provides two ways to work with tickets:

1. **Automatic extraction** - From Claude conversations
2. **Manual creation** - Using the ticket command

Both integrate seamlessly with the same ticket system powered by ai-trackdown-pytools.

## Automatic Ticket Creation

### Trigger Patterns

Claude MPM monitors for these patterns:

```bash
# TODO pattern
claude-mpm run -i "TODO: Implement user authentication" --non-interactive
# Creates: TSK-0001 - Implement user authentication

# TASK pattern  
claude-mpm run -i "TASK: Refactor database connections" --non-interactive
# Creates: TSK-0002 - Refactor database connections

# BUG pattern
claude-mpm run -i "BUG: Login page returns 404" --non-interactive
# Creates: TSK-0003 - Login page returns 404

# FEATURE pattern
claude-mpm run -i "FEATURE: Add dark mode support" --non-interactive
# Creates: TSK-0004 - Add dark mode support
```

### Multiple Tickets

Create multiple tickets in one command:

```bash
claude-mpm run -i "I need to TODO: Setup CI/CD pipeline, TODO: Add unit tests, and TODO: Update documentation" --non-interactive
```

This creates three separate tickets.

## Manual Ticket Management

### Creating Tickets

Basic ticket creation:

```bash
# Simple task
./ticket create "Implement password reset"

# With type
./ticket create "Fix memory leak" -t bug

# With priority
./ticket create "Security audit" -t task -p critical

# With full details
./ticket create "Add OAuth support" \
  -t feature \
  -p high \
  -d "Users need to login with Google and GitHub" \
  --tags "auth,oauth,backend"
```

### Ticket Types

| Type | Use For | Example |
|------|---------|---------|
| `task` | General work items | "Update dependencies" |
| `bug` | Defects and issues | "API returns 500 error" |
| `feature` | New functionality | "Add export to PDF" |
| `issue` | General problems | "Performance degradation" |

### Priority Levels

| Priority | Use When | Color |
|----------|----------|--------|
| `low` | Nice to have | Green |
| `medium` | Normal work | Yellow |
| `high` | Important/urgent | Orange |
| `critical` | Blocking/security | Red |

## Viewing and Listing Tickets

### List Commands

```bash
# List recent tickets (default: 10)
./ticket list

# List more tickets
./ticket list --limit 20

# List with details
./ticket list -v

# List specific type
./ticket list --type bug

# List by priority
./ticket list --priority high
```

### Viewing Individual Tickets

```bash
# Basic view
./ticket view TSK-0001

# Detailed view with metadata
./ticket view TSK-0001 -v
```

### Using Claude MPM's Ticket Command

```bash
# List tickets through claude-mpm
claude-mpm tickets

# Shows formatted output with:
# - Ticket ID
# - Title
# - Type
# - Priority
# - Status
# - Created date
```

## Updating Tickets

### Status Updates

```bash
# Update status
./ticket update TSK-0001 -s in_progress

# Status workflow:
# pending → in_progress → completed
# pending → blocked (if stuck)
# any → cancelled (if not needed)
```

### Status Values

| Status | Meaning | When to Use |
|--------|---------|-------------|
| `pending` | Not started | Default for new tickets |
| `in_progress` | Being worked on | When you start work |
| `completed` | Finished | Work is done |
| `blocked` | Can't proceed | Waiting on something |
| `cancelled` | Won't do | No longer needed |

### Other Updates

```bash
# Update priority
./ticket update TSK-0001 -p critical

# Assign to someone
./ticket update TSK-0001 -a "john.doe"

# Add tags
./ticket update TSK-0001 --tags "urgent,backend,security"

# Multiple updates
./ticket update TSK-0001 \
  -s in_progress \
  -p high \
  -a "jane.smith" \
  --tags "api,auth"
```

## Closing Tickets

```bash
# Close a completed ticket
./ticket close TSK-0001

# This sets status to 'completed' and adds completion timestamp
```

## Searching and Filtering

### Search in Ticket Titles

```bash
# Using grep
./ticket list --limit 100 | grep -i "auth"

# Using shell functions
search_tickets() {
    ./ticket list --limit 100 | grep -i "$1"
}
search_tickets "login"
```

### Filter by Attributes

```bash
# High priority bugs
./ticket list --type bug --priority high

# In-progress tasks
./ticket list | grep "in_progress"

# Today's tickets
./ticket list -v | grep "$(date +%Y-%m-%d)"
```

## Ticket Organization

### Directory Structure

```
./tickets/
├── tasks/
│   ├── TSK-0001.md
│   ├── TSK-0002.md
│   └── ...
└── epics/
    ├── EP-0001.md
    └── ...
```

### Ticket File Format

Each ticket is a Markdown file:

```markdown
# TSK-0001 - Implement user authentication

- **Type**: feature
- **Priority**: high
- **Status**: in_progress
- **Created**: 2024-01-25 10:30:00
- **Assignee**: john.doe
- **Tags**: auth, backend

## Description

Users need to be able to register and login to the application.

## Acceptance Criteria

- [ ] User registration with email
- [ ] Email verification
- [ ] Login/logout functionality
- [ ] Password reset
```

## Workflow Examples

### Development Workflow

```bash
# 1. Create feature ticket
./ticket create "Add user profile page" -t feature -p medium

# 2. Start work
./ticket update TSK-0005 -s in_progress

# 3. Create related tasks through Claude
claude-mpm run -i "TODO: Create profile component, TODO: Add profile API endpoint"

# 4. Complete the feature
./ticket close TSK-0005
```

### Bug Tracking Workflow

```bash
# 1. Report bug through Claude
claude-mpm run -i "BUG: Users see 'undefined' in profile name"

# 2. Investigate
./ticket view TSK-0006
./ticket update TSK-0006 -s in_progress -p high

# 3. Fix and close
# ... make fixes ...
./ticket close TSK-0006
```

### Sprint Planning

```bash
# List all pending high-priority items
./ticket list --priority high | grep "pending"

# Assign sprint tasks
for ticket in TSK-0010 TSK-0011 TSK-0012; do
    ./ticket update $ticket --tags "sprint-5"
done

# Track sprint progress
./ticket list -v | grep "sprint-5"
```

## Integration with Git

### Commit Messages

Reference tickets in commits:

```bash
git commit -m "Implement user auth (TSK-0001)"
git commit -m "Fix: Resolve login bug [TSK-0006]"
```

### Branch Naming

```bash
# Feature branches
git checkout -b feature/TSK-0001-user-auth

# Bug fix branches  
git checkout -b bugfix/TSK-0006-profile-undefined
```

## Best Practices

### 1. Clear Titles

```bash
# Good: Specific and actionable
./ticket create "Add input validation to registration form"

# Poor: Vague
./ticket create "Fix form"
```

### 2. Use Appropriate Types

- Use `bug` for things that are broken
- Use `feature` for new functionality
- Use `task` for maintenance, refactoring, etc.

### 3. Update Status Regularly

```bash
# When starting work
./ticket update TSK-0001 -s in_progress

# If blocked
./ticket update TSK-0001 -s blocked

# When done
./ticket close TSK-0001
```

### 4. Add Context

```bash
# Include description for complex items
./ticket create "Migrate to PostgreSQL" \
  -t task \
  -p high \
  -d "Current SQLite database is hitting performance limits. Need to migrate to PostgreSQL for better scalability."
```

### 5. Use Tags Effectively

```bash
# Tag by component
--tags "frontend,react"

# Tag by release
--tags "v2.0"

# Tag by team
--tags "backend-team"
```

## Automation Ideas

### Daily Standup Script

```bash
#!/bin/bash
echo "=== My Tickets ==="
echo "In Progress:"
./ticket list | grep "in_progress"
echo -e "\nPending High Priority:"
./ticket list --priority high | grep "pending"
```

### Ticket Report

```bash
#!/bin/bash
echo "Ticket Summary for $(date +%Y-%m-%d)"
echo "Total: $(./ticket list --limit 1000 | wc -l)"
echo "Bugs: $(./ticket list --type bug | wc -l)"
echo "Features: $(./ticket list --type feature | wc -l)"
echo "In Progress: $(./ticket list | grep -c "in_progress")"
```

## Troubleshooting

### "Command not found: ticket"

```bash
# Check if in project directory
ls -la ticket

# Make executable
chmod +x ticket

# Or use full path
./scripts/ticket list
```

### Tickets Not Created

Check patterns are correct:
- Must have colon: `TODO:` not `TODO`
- At start of sentence or after punctuation
- Followed by space and description

### Duplicate Tickets

Claude MPM doesn't prevent duplicates. Check before creating:

```bash
# Search first
./ticket list | grep -i "authentication"

# Then create if needed
./ticket create "Add JWT authentication"
```

## Next Steps

- Explore [Subprocess Orchestration](subprocess-orchestration.md)
- Master [Interactive Mode](interactive-mode.md)  
- Learn about [Automatic Tickets](../03-features/automatic-tickets.md) feature
- See [CLI Reference](../04-reference/cli-commands.md) for all commands
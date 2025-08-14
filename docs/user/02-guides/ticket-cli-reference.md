# Ticket CLI Reference Guide

This guide provides comprehensive documentation for the integrated ticket management commands in claude-mpm.

## Overview

Claude MPM includes a powerful ticket management system accessible through the `claude-mpm tickets` command. This system integrates with `ai-trackdown-pytools` to provide a complete ticketing solution that supports project management workflows, issue tracking, and task organization.

## Command Structure

```bash
claude-mpm tickets [subcommand] [options]
```

The ticket system supports all standard CRUD operations plus advanced features like search, workflow management, and commenting.

## Ticket Hierarchy

The system uses a three-tier hierarchy for organizing work:

- **Epics** (EP-XXXX) - Large features or projects spanning multiple sessions
- **Issues** (ISS-XXXX) - Medium-sized work items that can be completed in one sprint  
- **Tasks** (TSK-XXXX) - Specific implementation items assigned to individuals

## Subcommands Reference

### `create` - Create a new ticket

Create tickets with proper classification and metadata.

**Syntax:**
```bash
claude-mpm tickets create "title" [options]
```

**Options:**
- `--type, -t` - Ticket type: `task` (default), `bug`, `feature`, `issue`, `epic`
- `--priority, -p` - Priority level: `low`, `medium` (default), `high`, `critical`
- `--description, -d` - Ticket description (can be multiple words)
- `--tags` - Comma-separated list of tags
- `--parent-epic` - Link to parent epic (format: EP-XXXX)
- `--parent-issue` - Link to parent issue (format: ISS-XXXX)
- `--verbose, -v` - Show detailed creation information

**Examples:**
```bash
# Create a basic task
claude-mpm tickets create "Fix login validation bug"

# Create a high-priority bug with description
claude-mpm tickets create "User session expires unexpectedly" \
  --type bug \
  --priority high \
  --description "Users are being logged out after 5 minutes instead of 1 hour"

# Create a feature linked to an epic
claude-mpm tickets create "Implement OAuth2 authentication" \
  --type feature \
  --parent-epic EP-0001 \
  --tags "auth,security,oauth"

# Create a task under an issue
claude-mpm tickets create "Write unit tests for login component" \
  --type task \
  --parent-issue ISS-0045 \
  --priority medium
```

**Success Output:**
```
✅ Created ticket: TSK-0123
   Type: bug
   Priority: high
   Tags: auth, security
   Parent Epic: EP-0001
```

### `list` - List recent tickets

Display recent tickets with optional filtering and sorting.

**Syntax:**
```bash
claude-mpm tickets list [options]
```

**Options:**
- `--limit, -n` - Number of tickets to show (default: 10)
- `--type` - Filter by ticket type: `task`, `bug`, `feature`, `issue`, `epic`, `all` (default: all)
- `--status` - Filter by status: `open`, `in_progress`, `done`, `closed`, `blocked`, `all` (default: all)
- `--verbose, -v` - Show detailed ticket information

**Examples:**
```bash
# List 10 most recent tickets
claude-mpm tickets list

# List all open bugs
claude-mpm tickets list --type bug --status open

# Show detailed info for 20 recent tickets
claude-mpm tickets list --limit 20 --verbose

# List all high-priority items
claude-mpm tickets list --verbose | grep "Priority: high"
```

**Output Format:**
```
Recent tickets (showing 5):
--------------------------------------------------------------------------------
🔵 [TSK-0123] Fix login validation bug
🟡 [ISS-0045] Implement OAuth2 authentication
🟢 [EP-0001] User Authentication System Overhaul
⚫ [TSK-0122] Update password validation rules
🔴 [BUG-0089] Database connection timeout
```

**Status Emoji Legend:**
- 🔵 `open` - Ready to start
- 🟡 `in_progress` - Currently being worked on
- 🟢 `done` - Completed successfully
- ⚫ `closed` - Closed (completed or cancelled)
- 🔴 `blocked` - Cannot proceed due to dependencies
- ⚪ `unknown` - Status not recognized

### `view` - View detailed ticket information

Display complete information for a specific ticket.

**Syntax:**
```bash
claude-mpm tickets view <ticket-id> [options]
```

**Parameters:**
- `ticket-id` - The ticket identifier (e.g., TSK-0123, ISS-0045, EP-0001)

**Options:**
- `--verbose, -v` - Show additional metadata and technical details

**Examples:**
```bash
# View basic ticket information
claude-mpm tickets view TSK-0123

# View detailed ticket with all metadata
claude-mpm tickets view ISS-0045 --verbose
```

**Output Example:**
```
Ticket: TSK-0123
================================================================================
Title: Fix login validation bug
Type: task
Status: in_progress
Priority: high

Tags: auth, security, frontend
Assignees: john.doe@company.com

Parent Epic: EP-0001
Parent Issue: ISS-0045

Description:
----------------------------------------
Users are experiencing issues with login form validation. Error messages are
not displaying correctly when invalid credentials are entered, leading to
user confusion and support tickets.

Created: 2025-08-14 10:30:00
Updated: 2025-08-14 15:45:00

Metadata:
----------------------------------------
  source: claude-mpm-cli
  component: frontend
  estimated_hours: 4
```

### `update` - Update ticket properties

Modify ticket attributes including status, priority, description, and assignments.

**Syntax:**
```bash
claude-mpm tickets update <ticket-id> [options]
```

**Parameters:**
- `ticket-id` - The ticket identifier to update

**Options:**
- `--status` - New status: `open`, `in_progress`, `done`, `closed`, `blocked`
- `--priority` - New priority: `low`, `medium`, `high`, `critical`
- `--description` - Updated description (can be multiple words)
- `--tags` - Replace tags with comma-separated list
- `--assign` - Assign to user (email or username)

**Examples:**
```bash
# Update ticket status
claude-mpm tickets update TSK-0123 --status in_progress

# Change priority and add assignee
claude-mpm tickets update ISS-0045 --priority critical --assign john.doe

# Update description and tags
claude-mpm tickets update TSK-0123 \
  --description "Updated requirements after stakeholder feedback" \
  --tags "frontend,urgent,customer-facing"

# Mark as blocked
claude-mpm tickets update TSK-0123 --status blocked
```

**Success Output:**
```
✅ Updated ticket: TSK-0123
```

**Note:** Complex updates may fall back to the `aitrackdown` CLI for operations not supported by the TicketManager interface.

### `close` - Close a ticket

Mark a ticket as completed or no longer relevant.

**Syntax:**
```bash
claude-mpm tickets close <ticket-id> [options]
```

**Parameters:**
- `ticket-id` - The ticket identifier to close

**Options:**
- `--resolution` - Reason for closing (added as comment)

**Examples:**
```bash
# Close ticket with default resolution
claude-mpm tickets close TSK-0123

# Close with specific resolution comment
claude-mpm tickets close BUG-0089 --resolution "Fixed in version 1.2.3"

# Close cancelled work
claude-mpm tickets close FEATURE-0156 --resolution "Cancelled due to scope change"
```

**Success Output:**
```
✅ Closed ticket: TSK-0123
```

### `delete` - Delete a ticket

Permanently remove a ticket from the system.

**Syntax:**
```bash
claude-mpm tickets delete <ticket-id> [options]
```

**Parameters:**
- `ticket-id` - The ticket identifier to delete

**Options:**
- `--force, -f` - Skip confirmation prompt

**Examples:**
```bash
# Delete with confirmation prompt
claude-mpm tickets delete TSK-0123

# Force delete without confirmation
claude-mpm tickets delete TSK-0123 --force
```

**Interactive Confirmation:**
```
Are you sure you want to delete ticket TSK-0123? (y/N): y
✅ Deleted ticket: TSK-0123
```

**Warning:** Deletion is permanent and cannot be undone. Use with caution.

### `search` - Search tickets by content

Find tickets based on title, description, or tag content.

**Syntax:**
```bash
claude-mpm tickets search "query" [options]
```

**Parameters:**
- `query` - Search term to find in ticket content

**Options:**
- `--type` - Filter by ticket type: `task`, `bug`, `feature`, `issue`, `epic`, `all` (default: all)
- `--status` - Filter by status: `open`, `in_progress`, `done`, `closed`, `blocked`, `all` (default: all)
- `--limit, -n` - Maximum number of results (default: 20)

**Examples:**
```bash
# Basic text search
claude-mpm tickets search "authentication"

# Search for specific bug type
claude-mpm tickets search "login" --type bug --status open

# Search with result limit
claude-mpm tickets search "database" --limit 10
```

**Output Example:**
```
Search results for 'authentication' (showing 3):
--------------------------------------------------------------------------------
🔵 [ISS-0045] Implement OAuth2 authentication
   ...OAuth2 implementation for secure authentication...

🟡 [TSK-0123] Fix login validation bug  
   ...authentication system completely broken...

🟢 [EP-0001] User Authentication System Overhaul
   ...improve security posture and user authentication experience...
```

**Search Behavior:**
- Searches ticket titles, descriptions, and tags
- Case-insensitive matching
- Shows context snippets when query matches description
- Results ordered by relevance and recent activity

### `comment` - Add comments to tickets

Add discussion, progress updates, or notes to any ticket.

**Syntax:**
```bash
claude-mpm tickets comment <ticket-id> "comment text"
```

**Parameters:**
- `ticket-id` - The ticket to comment on
- `comment` - Comment text (can be multiple words)

**Examples:**
```bash
# Add progress comment
claude-mpm tickets comment TSK-0123 "Started working on this, initial analysis complete"

# Add technical notes
claude-mpm tickets comment ISS-0045 "May need to coordinate with security team for OAuth2 scope definitions"

# Add completion notes
claude-mpm tickets comment TSK-0123 "Completed implementation, ready for code review"
```

**Success Output:**
```
✅ Added comment to ticket: TSK-0123
```

**Note:** Comments are managed through the `aitrackdown` CLI system and support rich formatting and attachments when using the full aitrackdown interface.

### `workflow` - Update workflow state

Manage ticket workflow states with proper transition validation.

**Syntax:**
```bash
claude-mpm tickets workflow <ticket-id> <state> [options]
```

**Parameters:**
- `ticket-id` - The ticket to update
- `state` - New workflow state: `todo`, `in_progress`, `ready`, `tested`, `done`, `blocked`

**Options:**
- `--comment` - Add comment explaining the state change

**Examples:**
```bash
# Move ticket to in progress
claude-mpm tickets workflow TSK-0123 in_progress

# Mark as ready for testing with comment
claude-mpm tickets workflow TSK-0123 ready --comment "Implementation complete, unit tests passing"

# Block ticket with explanation
claude-mpm tickets workflow ISS-0045 blocked --comment "Waiting for API specification from backend team"

# Mark as done
claude-mpm tickets workflow TSK-0123 done --comment "Feature deployed to production"
```

**State Mapping:**
- `todo` → `open` status
- `in_progress` → `in_progress` status  
- `ready` → `ready` status (awaiting review/testing)
- `tested` → `tested` status (QA approved)
- `done` → `done` status (completed)
- `blocked` → `blocked` status (cannot proceed)

**Success Output:**
```
✅ Updated workflow state for TSK-0123 to: ready
```

## Default Behavior

When no subcommand is specified, the system defaults to `list` with standard options:

```bash
# These are equivalent
claude-mpm tickets
claude-mpm tickets list --limit 10
```

## Integration with ai-trackdown-pytools

The CLI commands integrate seamlessly with the underlying `ai-trackdown-pytools` system:

- **Primary Operations**: Create, view, and simple updates use the TicketManager interface
- **Advanced Operations**: Complex updates, comments, and workflow transitions may use the `aitrackdown` CLI directly
- **Fallback Mechanism**: If TicketManager operations fail, the system automatically attempts equivalent `aitrackdown` commands
- **Data Consistency**: All operations maintain consistency with the `.ai-trackdown/` configuration and storage

## Configuration

The ticket system respects the ai-trackdown configuration in `.ai-trackdown/config.yaml`:

```yaml
version: 0.9.0
project:
  name: claude-mpm
  
tasks:
  directory: tickets/tasks
  auto_id: true
  id_format: TSK-{counter:04d}
  
issues:
  directory: tickets/issues  
  auto_id: true
  id_format: ISS-{counter:04d}
  
epics:
  directory: tickets/epics
  auto_id: true
  id_format: EP-{counter:04d}
```

## Error Handling

The CLI provides clear error messages and fallback behaviors:

**Common Error Scenarios:**
- **Ticket not found**: Returns appropriate error message and exit code 1
- **ai-trackdown-pytools not installed**: Displays installation instructions
- **Permission issues**: Shows clear error with suggested fixes
- **Network/dependency failures**: Attempts fallback operations where possible

**Example Error Output:**
```bash
$ claude-mpm tickets view TSK-9999
❌ Ticket TSK-9999 not found

$ claude-mpm tickets create "test" # when ai-trackdown not installed
Error: ai-trackdown-pytools not installed
Install with: pip install ai-trackdown-pytools
```

## Performance Considerations

- **List operations**: Limited to reasonable defaults (10 items) to prevent performance issues
- **Search operations**: Uses optimized text matching, searches recent tickets first
- **Large hierarchies**: Epic and issue relationships are loaded efficiently
- **Caching**: Recent ticket data is cached by the TicketManager for faster access

## Best Practices

1. **Use descriptive titles**: Make ticket purposes clear from the title
2. **Proper hierarchy**: Create epics for large initiatives, issues for features, tasks for implementation
3. **Status management**: Keep ticket statuses current to track progress accurately
4. **Tagging strategy**: Use consistent tags for easier searching and organization
5. **Regular cleanup**: Close completed tickets and update stale items

## See Also

- [Ticket Management with AI Trackdown](ticket-management-aitrackdown.md) - Comprehensive ticketing guide
- [Ticketing Agent Documentation](../../TICKETING_AGENT.md) - Advanced ticketing workflows
- [CLI Architecture](../../src/claude_mpm/cli/README.md) - Technical CLI documentation
- [ai-trackdown-pytools documentation](https://github.com/ai-trackdown/ai-trackdown-pytools) - Underlying toolkit reference
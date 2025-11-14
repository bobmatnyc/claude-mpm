# mpm-tickets

Create and manage tickets using mcp-ticketer MCP server (primary) or aitrackdown CLI (fallback)

## Usage

Use this command to create and manage tickets (epics, issues, tasks) through intelligent MCP-first integration with automatic CLI fallback.

## Integration Methods

### PRIMARY: mcp-ticketer MCP Server (Preferred)

When available, ticketing operations use the mcp-ticketer MCP server for:
- Unified interface across ticketing backends (Jira, GitHub, Linear)
- Better error handling and validation
- Automatic backend detection
- Enhanced features and reliability

**MCP Tools**:
- `mcp__mcp-ticketer__create_ticket` - Create epics, issues, tasks
- `mcp__mcp-ticketer__list_tickets` - List tickets with filters
- `mcp__mcp-ticketer__get_ticket` - View ticket details
- `mcp__mcp-ticketer__update_ticket` - Update status, priority
- `mcp__mcp-ticketer__search_tickets` - Search by keywords
- `mcp__mcp-ticketer__add_comment` - Add comments

### SECONDARY: aitrackdown CLI (Fallback)

When mcp-ticketer is not available, operations fall back to aitrackdown CLI for direct ticket management.

## Commands

### Create tickets
```bash
# Create an epic
aitrackdown create epic "Title" --description "Description"

# Create an issue  
aitrackdown create issue "Title" --description "Description"

# Create a task
aitrackdown create task "Title" --description "Description"

# Create task under an issue
aitrackdown create task "Title" --issue ISS-0001
```

### View tickets
```bash
# Show all tasks
aitrackdown status tasks

# Show specific ticket
aitrackdown show ISS-0001
```

### Update tickets
```bash
# Change status
aitrackdown transition ISS-0001 in-progress
aitrackdown transition ISS-0001 done

# Add comment
aitrackdown comment ISS-0001 "Your comment"
```

### Search tickets
```bash
aitrackdown search tasks "keyword"
```

## Ticket Types

- **EP-XXXX**: Epics (major initiatives)
- **ISS-XXXX**: Issues (bugs, features, user requests)  
- **TSK-XXXX**: Tasks (individual work items)

## Workflow States

Valid transitions:
- `open` → `in-progress` → `ready` → `tested` → `done`
- Any state → `waiting` (when blocked)
- Any state → `closed` (to close)

## Examples

### Bug Report Flow
```bash
# Create issue for bug
aitrackdown create issue "Login bug" --description "Users can't login" --severity high

# Create investigation task
aitrackdown create task "Investigate login bug" --issue ISS-0001

# Update status
aitrackdown transition TSK-0001 in-progress
aitrackdown comment TSK-0001 "Found the issue"

# Complete
aitrackdown transition TSK-0001 done
aitrackdown transition ISS-0001 done
```

### Feature Implementation
```bash
# Create epic
aitrackdown create epic "OAuth2 Support"

# Create issues
aitrackdown create issue "Google OAuth2" --description "Add Google auth"
aitrackdown create issue "GitHub OAuth2" --description "Add GitHub auth"

# Create tasks
aitrackdown create task "Design OAuth flow" --issue ISS-0001
aitrackdown create task "Implement Google client" --issue ISS-0001
```

## MCP vs CLI Usage

### Using MCP Tools (Preferred)
```
# Create issue with MCP
mcp__mcp-ticketer__create_ticket(
  type="issue",
  title="Fix login bug",
  priority="high"
)

# List tickets
mcp__mcp-ticketer__list_tickets(status="open")
```

### Using CLI Fallback
```bash
# Create issue with CLI
aitrackdown create issue "Fix login bug" --priority high

# List tickets
aitrackdown status
```

## Tips

- **MCP-first**: Prefer mcp-ticketer MCP tools when available
- **Automatic fallback**: System gracefully falls back to aitrackdown CLI
- **Check availability**: Detection happens automatically
- **Always use aitrackdown directly** (not claude-mpm tickets) for CLI operations
- **Check ticket exists** with `get_ticket` (MCP) or `show` (CLI) before updating
- **Add comments** to document progress
- **Use `--severity`** for bugs, `--priority` for features
- **Associate tasks** with issues using `parent_id` (MCP) or `--issue` (CLI)
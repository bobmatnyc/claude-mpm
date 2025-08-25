# MCP Ticket Tool Migration Guide

## Overview

The MCP Gateway ticket management functionality has been consolidated from 5 separate tools into a single unified tool with an operation parameter. This provides a cleaner, more intuitive API that's easier to use and maintain.

## What Changed

### Before: 5 Separate Tools
- `ticket_create` - Create new tickets
- `ticket_list` - List tickets with filters  
- `ticket_update` - Update ticket status/priority
- `ticket_view` - View ticket details
- `ticket_search` - Search tickets by keywords

### After: 1 Unified Tool
- `ticket` - All ticket operations via `operation` parameter

## Migration Examples

### Creating a Ticket

**Old Way:**
```json
{
  "tool": "ticket_create",
  "parameters": {
    "type": "task",
    "title": "Fix login bug",
    "description": "Users cannot log in with valid credentials",
    "priority": "high"
  }
}
```

**New Way:**
```json
{
  "tool": "ticket",
  "parameters": {
    "operation": "create",
    "type": "task",
    "title": "Fix login bug",
    "description": "Users cannot log in with valid credentials",
    "priority": "high"
  }
}
```

### Listing Tickets

**Old Way:**
```json
{
  "tool": "ticket_list",
  "parameters": {
    "status": "open",
    "limit": 10
  }
}
```

**New Way:**
```json
{
  "tool": "ticket",
  "parameters": {
    "operation": "list",
    "status": "open",
    "limit": 10
  }
}
```

### Updating a Ticket

**Old Way:**
```json
{
  "tool": "ticket_update",
  "parameters": {
    "ticket_id": "TSK-0001",
    "status": "in-progress",
    "comment": "Started working on this"
  }
}
```

**New Way:**
```json
{
  "tool": "ticket",
  "parameters": {
    "operation": "update",
    "ticket_id": "TSK-0001",
    "status": "in-progress",
    "comment": "Started working on this"
  }
}
```

### Viewing a Ticket

**Old Way:**
```json
{
  "tool": "ticket_view",
  "parameters": {
    "ticket_id": "TSK-0001",
    "format": "json"
  }
}
```

**New Way:**
```json
{
  "tool": "ticket",
  "parameters": {
    "operation": "view",
    "ticket_id": "TSK-0001",
    "format": "json"
  }
}
```

### Searching Tickets

**Old Way:**
```json
{
  "tool": "ticket_search",
  "parameters": {
    "query": "login bug",
    "limit": 5
  }
}
```

**New Way:**
```json
{
  "tool": "ticket",
  "parameters": {
    "operation": "search",
    "query": "login bug",
    "limit": 5
  }
}
```

## Parameter Reference

### Common Parameters
- `operation` (required): One of `create`, `list`, `update`, `view`, `search`

### Operation-Specific Parameters

#### Create Operation
- `type` (required): `task`, `issue`, or `epic`
- `title` (required): Ticket title
- `description`: Detailed description
- `priority`: `low`, `medium`, `high`, or `critical`
- `tags`: Array of tag strings
- `parent_epic`: Parent epic ID (for issues)
- `parent_issue`: Parent issue ID (for tasks)

#### List Operation
- `limit`: Maximum number of results (default: 10)
- `type`: Filter by type (`all`, `task`, `issue`, `epic`)
- `status`: Filter by status (`all`, `open`, `in-progress`, `done`, etc.)
- `priority`: Filter by priority (`all`, `low`, `medium`, `high`, `critical`)

#### Update Operation
- `ticket_id` (required): Ticket to update
- `status`: New status
- `priority`: New priority
- `comment`: Update comment

#### View Operation
- `ticket_id` (required): Ticket to view
- `format`: Output format (`json` or `text`, default: `json`)

#### Search Operation
- `query` (required): Search keywords
- `limit`: Maximum results (default: 10)
- `type`: Filter by type

## Benefits of the Unified Tool

1. **Simpler API**: Just one tool name to remember
2. **Intuitive**: `ticket` + operation matches mental model
3. **Discoverable**: All operations in one place
4. **Cleaner Config**: Less clutter in MCP configuration
5. **Extensible**: Easy to add new operations
6. **Consistent**: Same tool for all ticket operations

## Backward Compatibility

The old individual ticket tools (`ticket_create`, `ticket_list`, etc.) are still available but deprecated. They will be removed in a future version. We recommend migrating to the unified tool as soon as possible.

## Configuration Update

Update your Claude Code MCP configuration:

**Old Configuration:**
```json
{
  "mcpServers": {
    "claude-mpm": {
      "command": "claude-mpm-mcp",
      "args": [],
      "env": {}
    }
  }
}
```

**New Configuration (no change needed):**
The same configuration works - the server automatically provides the unified tool.

## Troubleshooting

### Issue: Tool not found
**Solution**: Ensure you're using the latest version of claude-mpm with the unified tool support.

### Issue: Invalid operation error
**Solution**: Check that the `operation` parameter is one of: `create`, `list`, `update`, `view`, `search`.

### Issue: Missing required parameters
**Solution**: Each operation has different required parameters. Refer to the parameter reference above.

## Support

For questions or issues with the migration, please:
1. Check this migration guide
2. Review the [MCP Gateway documentation](./MCP_GATEWAY.md)
3. Open an issue on the GitHub repository
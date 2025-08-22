# MCP Unified Ticket Tool

## Overview

The MCP Gateway now uses a **single unified ticket tool** instead of 5 separate tools for ticket management operations. This provides a cleaner, more intuitive API for Claude Code/Code users.

## Migration from Separate Tools to Unified Tool

### Previous Setup (5 Separate Tools)
- `ticket_create` - Create tickets
- `ticket_list` - List tickets  
- `ticket_update` - Update tickets
- `ticket_view` - View ticket details
- `ticket_search` - Search tickets

### New Setup (1 Unified Tool)
- `ticket` - Single tool with `operation` parameter

## Using the Unified Ticket Tool

### Tool Name
```
ticket
```

### Parameters

#### Required Parameter
- `operation` (string): The operation to perform
  - Options: `create`, `list`, `update`, `view`, `search`

#### Operation-Specific Parameters

##### Create Operation
```json
{
  "operation": "create",
  "type": "task|issue|epic",
  "title": "Ticket title",
  "description": "Detailed description",
  "priority": "low|medium|high|critical",
  "tags": ["tag1", "tag2"],
  "parent_issue": "ISS-001",  // For tasks
  "parent_epic": "EP-001"     // For issues
}
```

##### List Operation
```json
{
  "operation": "list",
  "limit": 10,
  "status": "all|pending|in_progress|completed"
}
```

##### Update Operation
```json
{
  "operation": "update",
  "ticket_id": "TSK-001",
  "status": "pending|in_progress|completed",
  "priority": "low|medium|high|critical",
  "assignee": "username",
  "add_tags": ["tag1"],
  "remove_tags": ["tag2"],
  "comment": "Update comment"
}
```

##### View Operation
```json
{
  "operation": "view",
  "ticket_id": "TSK-001",
  "include_comments": true,
  "include_history": false
}
```

##### Search Operation
```json
{
  "operation": "search",
  "query": "search terms",
  "type": "all|task|issue|epic",
  "status": "all|pending|in_progress|completed",
  "assignee": "username",
  "tags": ["tag1", "tag2"],
  "limit": 10
}
```

## Example Usage in Claude

### Creating a Task
```
Use the ticket tool with operation "create", type "task", title "Fix authentication bug", description "Users cannot log in with valid credentials", and priority "high"
```

### Listing Tasks
```
Use the ticket tool with operation "list" and limit 5
```

### Updating a Ticket
```
Use the ticket tool with operation "update", ticket_id "TSK-123", status "in_progress", and comment "Started working on this"
```

### Viewing a Ticket
```
Use the ticket tool with operation "view" and ticket_id "ISS-456"
```

### Searching Tickets
```
Use the ticket tool with operation "search", query "authentication", and type "issue"
```

## Benefits of the Unified Tool

1. **Simpler API**: One tool to remember instead of five
2. **Consistent Interface**: All ticket operations follow the same pattern
3. **Better Discovery**: Users can see all operations in one tool description
4. **Reduced Complexity**: Fewer tools in the MCP server tool list
5. **Logical Grouping**: All ticket operations are clearly related

## Implementation Details

### File Locations
- **Tool Implementation**: `src/claude_mpm/services/mcp_gateway/tools/unified_ticket_tool.py`
- **Registration Points**:
  - `src/claude_mpm/services/mcp_gateway/main.py` - Main orchestrator
  - `bin/claude-mpm-mcp` - Primary MCP server entry point
  - `bin/claude-mpm-mcp-simple` - Simplified MCP server
  - `src/claude_mpm/services/mcp_gateway/server/stdio_server.py` - Stdio server

### Testing
Run the test script to verify proper registration:
```bash
python scripts/test_unified_ticket_tool.py
```

This should show:
- Only 1 ticket tool registered
- Tool name is "ticket"
- Has "operation" parameter with 5 options

## Backward Compatibility

The separate ticket tools (`ticket_tools.py`) are still available in the codebase but are no longer registered or used by the MCP servers. They can be removed in a future cleanup once we're confident the unified tool is working well.

## Configuration in Claude Code

No changes needed to the Claude Code configuration. The MCP server will automatically provide the unified ticket tool:

```json
{
  "mcpServers": {
    "claude-mpm": {
      "command": "claude-mpm-mcp"
    }
  }
}
```

## Troubleshooting

### Issue: Still seeing 5 separate ticket tools
**Solution**: Restart Claude Code to reload the MCP server with the new configuration.

### Issue: "Unknown operation" error
**Solution**: Ensure you're using one of the valid operations: create, list, update, view, search

### Issue: Missing required parameters
**Solution**: Check the operation-specific parameters above for required fields.

## Future Improvements

1. Add batch operations support
2. Add more filtering options for list/search
3. Add ticket linking/dependency management
4. Add bulk update capabilities
5. Add export functionality
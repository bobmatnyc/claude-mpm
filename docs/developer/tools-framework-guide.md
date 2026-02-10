# Claude MPM Tools Framework Guide

## Overview

The `claude-mpm tools` framework provides high-performance bulk operations for MCP services, bypassing MCP protocol overhead for batch processing. It's designed for agents and power users who need to process large volumes of data quickly.

### Why Use Tools Instead of MCP?

- **10x Faster**: Direct API calls instead of MCP protocol roundtrips
- **Bulk Operations**: Process hundreds of items in single command
- **Agent-Friendly**: JSON output for easy parsing
- **Progress Tracking**: Detailed success/failure counts
- **Offline Capable**: Works without MCP server running

### Available Services

| Service | Actions | Description |
|---------|---------|-------------|
| **google** | gmail-export, gmail-import, calendar-export, calendar-bulk-create, drive-batch-upload, drive-batch-download | Google Workspace bulk operations |
| **slack** | channels-list, messages-export | Slack workspace operations |
| **notion** | database-query, pages-batch-update, pages-export, md-import | Notion databases and pages |
| **confluence** | pages-search, pages-batch-export, spaces-list, md-import | Confluence pages and spaces |

---

## Google Workspace Tools

### Prerequisites

```bash
# Authenticate with Google Workspace
claude-mpm setup oauth google-workspace-mcp
```

### Gmail Operations

#### Export Gmail Messages

Export messages matching a search query.

```bash
# Export recent emails from specific sender
claude-mpm tools google gmail-export \
  --query "from:john@example.com" \
  --max-results 100

# Export with full message content
claude-mpm tools google gmail-export \
  --query "label:important" \
  --format full \
  --max-results 50

# Save to file
claude-mpm tools google gmail-export \
  --query "after:2026/01/01" \
  --output messages.json
```

**Parameters:**
- `--query`: Gmail search query (optional, default: "")
- `--max-results`: Maximum messages to export (optional, default: 100)
- `--format`: Export format - "metadata" or "full" (optional, default: "metadata")
- `--output`: Save to file instead of stdout (optional)

**Output:**
```json
{
  "success": true,
  "action": "gmail-export",
  "data": {
    "messages": [
      {
        "id": "1a2b3c4d5e6f",  # pragma: allowlist secret
        "thread_id": "thread123",
        ...
      }
    ],
    "query": "from:john@example.com"
  },
  "metadata": {
    "count": 42,
    "max_results": 100
  }
}
```

#### Import Gmail Messages

Import messages from JSON file.

```bash
# Import with label
claude-mpm tools google gmail-import \
  --file messages.json \
  --label "Imported"

# Import without label
claude-mpm tools google gmail-import --file messages.json
```

**Parameters:**
- `--file`: Path to JSON file with messages (required)
- `--label`: Gmail label to apply (optional)

### Calendar Operations

#### Export Calendar Events

Export events with time filters.

```bash
# Export upcoming events
claude-mpm tools google calendar-export \
  --calendar-id primary \
  --time-min "2026-02-01T00:00:00Z" \
  --max-results 100

# Export from specific calendar
claude-mpm tools google calendar-export \
  --calendar-id "team@example.com" \
  --time-min "2026-02-01T00:00:00Z" \
  --time-max "2026-03-01T00:00:00Z"
```

**Parameters:**
- `--calendar-id`: Calendar ID (optional, default: "primary")
- `--time-min`: Start time in ISO 8601 format (optional)
- `--time-max`: End time in ISO 8601 format (optional)
- `--max-results`: Maximum events (optional, default: 250)

#### Bulk Create Calendar Events

Create multiple events from JSON file.

```bash
# Create events from file
claude-mpm tools google calendar-bulk-create \
  --file events.json \
  --calendar-id primary
```

**JSON Format:**
```json
{
  "events": [
    {
      "summary": "Team Meeting",
      "start_time": "2026-02-10T10:00:00-05:00",
      "end_time": "2026-02-10T11:00:00-05:00",
      "description": "Weekly sync",
      "location": "Conference Room A",
      "attendees": ["team@example.com"],
      "timezone": "America/New_York"
    }
  ]
}
```

**Parameters:**
- `--file`: Path to JSON file with events (required)
- `--calendar-id`: Target calendar (optional, default: "primary")

### Drive Operations

#### Batch Upload Files

Upload multiple files to Google Drive.

```bash
# Upload files to root
claude-mpm tools google drive-batch-upload \
  --files "file1.txt,file2.json,file3.md"

# Upload to specific folder
claude-mpm tools google drive-batch-upload \
  --files "doc1.md,doc2.html" \
  --parent-id "folder-id-here"

# Override MIME type
claude-mpm tools google drive-batch-upload \
  --files "data.csv" \
  --mime-type "text/csv"
```

**Parameters:**
- `--files`: Comma-separated file paths (required)
- `--parent-id`: Parent folder ID (optional)
- `--mime-type`: MIME type override (optional, auto-detected by extension)

**Supported Extensions:**
- `.txt`, `.json`, `.html`, `.md`, `.py`, `.js`, `.css`
- Binary files not supported (text files only)

#### Batch Download Files

Download multiple files from Google Drive.

```bash
# Download to current directory
claude-mpm tools google drive-batch-download \
  --file-ids "id1,id2,id3"

# Download to specific directory
claude-mpm tools google drive-batch-download \
  --file-ids "id1,id2" \
  --output-dir "./downloads"
```

**Parameters:**
- `--file-ids`: Comma-separated file IDs (required)
- `--output-dir`: Output directory (optional, default: current directory)

**Google Workspace Files:**
- Google Docs → exported as `.txt`
- Google Sheets → exported as `.csv`
- Google Slides → exported as `.txt`

---

## Slack Tools

### Prerequisites

```bash
# Authenticate with Slack
claude-mpm setup oauth slack
```

### List Channels

List all channels in workspace.

```bash
# List all channels (public + private)
claude-mpm tools slack channels-list --limit 100

# List only public channels
claude-mpm tools slack channels-list --include-private false
```

**Parameters:**
- `--limit`: Maximum channels to return (optional, default: 1000)
- `--include-private`: Include private channels (optional, default: true)

**Output:**
```json
{
  "success": true,
  "action": "channels-list",
  "data": {
    "channels": [
      {
        "id": "C123456",
        "name": "general",
        "is_private": false,
        "is_archived": false,
        "num_members": 42,
        "topic": "Company announcements",
        "purpose": "General discussion"
      }
    ]
  },
  "metadata": {
    "count": 15
  }
}
```

### Export Messages

Export messages from a channel.

```bash
# Export recent messages
claude-mpm tools slack messages-export \
  --channel C123456 \
  --limit 500

# Export with time range (UNIX timestamps)
claude-mpm tools slack messages-export \
  --channel C123456 \
  --oldest 1609459200 \
  --latest 1640995200 \
  --limit 1000

# Save to file
claude-mpm tools slack messages-export \
  --channel C123456 \
  --output messages.json
```

**Parameters:**
- `--channel`: Channel ID (required)
- `--limit`: Maximum messages (optional, default: 1000)
- `--oldest`: Start timestamp in UNIX format (optional)
- `--latest`: End timestamp in UNIX format (optional)
- `--output`: Save to file (optional)

**Output:**
```json
{
  "success": true,
  "action": "messages-export",
  "data": {
    "messages": [
      {
        "type": "message",
        "user": "U123456",
        "text": "Hello team!",
        "ts": "1609459200.000100",
        "thread_ts": null,
        "reply_count": 0,
        "reactions": []
      }
    ],
    "channel": "C123456"
  },
  "metadata": {
    "count": 500,
    "limit": 1000
  }
}
```

---

## Agent Integration Guide

### Using Tools from Agents

Agents can call tools directly via the `Bash` tool:

```python
# In agent delegation
result = await bash_tool(
    command='claude-mpm tools google gmail-export --query "from:me" --max-results 50'
)

# Parse JSON output
import json
data = json.loads(result)
messages = data['data']['messages']
count = data['metadata']['count']
```

### Error Handling

Tools return standardized error format:

```json
{
  "success": false,
  "action": "gmail-export",
  "data": null,
  "error": "No token found for google-workspace-mpm. Run 'claude-mpm setup oauth google-workspace-mcp' first.",
  "metadata": {}
}
```

Check `success` field before processing data:

```python
if data['success']:
    process_data(data['data'])
else:
    handle_error(data['error'])
```

### Progress Tracking

All tools provide progress metadata:

```json
{
  "metadata": {
    "total": 100,
    "uploaded_count": 95,
    "failed_count": 5
  }
}
```

### Pagination

Tools handle pagination automatically up to specified limits:

```bash
# Will paginate through all results up to 1000
claude-mpm tools slack messages-export --channel C123 --limit 1000
```

---

## Common Patterns

### Export and Transform

```bash
# Export Gmail messages
claude-mpm tools google gmail-export \
  --query "label:important" \
  --output messages.json

# Process with jq
jq '.data.messages[] | {subject: .subject, from: .from}' messages.json
```

### Bulk Calendar Creation

```bash
# Generate events.json programmatically
cat > events.json <<EOF
{
  "events": [
    {"summary": "Daily Standup", "start_time": "2026-02-10T09:00:00Z", "end_time": "2026-02-10T09:15:00Z"},
    {"summary": "Sprint Planning", "start_time": "2026-02-10T14:00:00Z", "end_time": "2026-02-10T16:00:00Z"}
  ]
}
EOF

# Create all events
claude-mpm tools google calendar-bulk-create --file events.json
```

### Archive Slack Channel

```bash
# Export messages for archival
claude-mpm tools slack messages-export \
  --channel C123456 \
  --output "archive-$(date +%Y%m%d).json"
```

---

## API Reference

### Common Options

Available for all tools commands:

- `--format json|text`: Output format (default: json)
- `--output FILE`: Write to file instead of stdout
- `--verbose`: Show detailed progress

### Return Format

All tools return standardized `ToolResult`:

```typescript
interface ToolResult {
  success: boolean;
  action: string;
  data: any | null;
  error: string | null;
  metadata: Record<string, any>;
}
```

### Exit Codes

- `0`: Success
- `1`: Error (check error field in JSON)

---

## Troubleshooting

### Authentication Errors

```
Error: No token found for google-workspace-mpm
```

**Solution**: Run OAuth setup:
```bash
claude-mpm setup oauth google-workspace-mcp
# or
claude-mpm setup oauth slack
```

### Rate Limiting

Tools respect API rate limits:

- **Google**: 10 requests/second per user
- **Slack**: Tier 3 (50+ requests/minute)

If you hit limits, reduce `--limit` or add delays between calls.

### File Not Found (Drive Upload)

```
Error: File not found: /path/to/file.txt
```

**Solution**: Verify file paths are correct and files exist.

### Binary Files (Drive Upload)

```
Error: File is binary (text files only)
```

**Solution**: Drive batch upload only supports text files. Use Drive UI for binary files.

---

## Performance Tips

1. **Use Pagination Wisely**: Don't request more data than needed
2. **Batch Operations**: Combine multiple operations into single JSON file
3. **Output to File**: Use `--output` to avoid terminal buffer limits
4. **Parallel Agents**: Run multiple tools commands in parallel for different services

---

## See Also

- [MCP Tools Documentation](./mcp-tools.md) - For interactive MCP usage
- [Agent Development Guide](./agent-development.md) - For building custom agents
- [OAuth Setup Guide](./oauth-setup.md) - For authentication setup

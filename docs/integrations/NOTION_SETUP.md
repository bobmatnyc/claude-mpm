# Notion Integration Setup

The Notion integration for claude-mpm provides both MCP tools for interactive operations and bulk CLI tools for batch processing.

## Table of Contents

- [Overview](#overview)
- [Quick Setup](#quick-setup)
- [Prerequisites](#prerequisites)
- [Step 1: Create a Notion Integration](#step-1-create-a-notion-integration)
- [Step 2: Get Your Integration Token](#step-2-get-your-integration-token)
- [Step 3: Run Setup](#step-3-run-setup)
- [Step 4: Share Databases](#step-4-share-databases)
- [MCP Tools Reference](#mcp-tools-reference)
- [Bulk Tools Reference](#bulk-tools-reference)
- [Troubleshooting](#troubleshooting)

---

## Overview

| Feature | Description |
|---------|-------------|
| **MCP Tools** | Interactive operations via Claude Code MCP protocol |
| **Bulk Tools** | High-performance batch operations via CLI |
| **Auth Method** | Integration Token (API key) |
| **Use Cases** | Database queries, page management, markdown import |

---

## Quick Setup

```bash
# Automated setup (recommended)
claude-mpm setup notion

# This will:
# 1. Prompt for your Notion Integration Token
# 2. Optionally collect default database ID
# 3. Save credentials to .env.local
# 4. Configure notion-mcp MCP server
```

---

## Prerequisites

Before you begin, ensure you have:

- **Python 3.10+** installed
- **claude-mpm** installed (`pip install claude-mpm` or `uv pip install claude-mpm`)
- A **Notion account** (free or paid)
- Admin access to create integrations (workspace owner or admin)

---

## Step 1: Create a Notion Integration

1. Go to [https://www.notion.so/my-integrations](https://www.notion.so/my-integrations)
2. Click **"+ New integration"**
3. Enter integration details:
   - **Name**: `Claude MPM` (or your preference)
   - **Associated workspace**: Select your workspace
   - **Type**: Internal integration
4. Click **"Submit"**

---

## Step 2: Get Your Integration Token

1. On the integration page, find **"Internal Integration Token"**
2. Click **"Show"** then **"Copy"**
3. The token starts with `secret_` (e.g., `secret_abc123...`)

> **Security**: Never commit integration tokens to version control. Store them in `.env.local` which is gitignored.

---

## Step 3: Run Setup

### Automated Setup (Recommended)

```bash
claude-mpm setup notion
```

You'll be prompted for:
- **Integration Token** (required): Your `secret_...` token
- **Default Database ID** (optional): For bulk operations

### Manual Setup (Alternative)

Create `.env.local` in your project directory:

```bash
NOTION_API_KEY="secret_your_token_here"  # pragma: allowlist secret
NOTION_DATABASE_ID="your_database_id_here"  # Optional
```

Then manually add to `.mcp.json`:

```json
{
  "mcpServers": {
    "notion-mcp": {
      "type": "stdio",
      "command": "notion-mcp",
      "args": [],
      "env": {}
    }
  }
}
```

---

## Step 4: Share Databases

Notion integrations don't automatically have access to databases. You must explicitly share each database:

1. Open the database in Notion
2. Click **"..."** (top right) > **"Connections"**
3. Search for your integration name (e.g., "Claude MPM")
4. Click to add the connection

> **Important**: You must share each database you want to access. The integration cannot see databases that haven't been shared with it.

---

## MCP Tools Reference

Once configured, these MCP tools are available in Claude Code:

### Database Operations

| Tool | Description |
|------|-------------|
| `query_database` | Query pages from a database with filters and pagination |
| `get_page` | Retrieve a page by ID including properties |
| `get_page_content` | Retrieve all blocks (content) from a page |

### Page Management

| Tool | Description |
|------|-------------|
| `update_page` | Update page properties |
| `create_page` | Create a new page in a database |
| `append_blocks` | Append block children to a page |

### Search

| Tool | Description |
|------|-------------|
| `search` | Search for pages across the workspace |

### Example MCP Usage

```typescript
// In Claude Code, these tools are available automatically
// Query a database
await query_database({
  database_id: "your-db-id",
  filter: {
    property: "Status",
    status: {
      equals: "In Progress"
    }
  },
  sorts: [
    {
      property: "Priority",
      direction: "descending"
    }
  ]
})

// Create a new page
await create_page({
  database_id: "your-db-id",
  properties: {
    "Name": {
      "title": [{"text": {"content": "New Task"}}]
    },
    "Status": {
      "status": {"name": "To Do"}
    }
  },
  children: [
    {
      "type": "paragraph",
      "paragraph": {
        "rich_text": [{"text": {"content": "Task description here"}}]
      }
    }
  ]
})
```

---

## Bulk Tools Reference

High-performance CLI tools for batch operations. 10x faster than MCP protocol.

### Available Actions

```bash
# Query database pages
claude-mpm tools notion database-query \
  --database-id YOUR_DB_ID \
  --max-results 100 \
  --output pages.json

# Batch update pages
claude-mpm tools notion pages-batch-update \
  --file updates.json

# Export pages with content
claude-mpm tools notion pages-export \
  --page-ids "page1,page2,page3" \
  --output export.json

# Import markdown files
claude-mpm tools notion md-import \
  --files "doc1.md,doc2.md,doc3.md" \
  --database-id YOUR_DB_ID
```

### Database Query

Export pages from a database with optional pagination:

```bash
claude-mpm tools notion database-query \
  --database-id 2f67584909f3811d9894e2888e25b70c \
  --max-results 50 \
  --output pages.json
```

**Output format:**
```json
{
  "success": true,
  "action": "database-query",
  "data": {
    "pages": [...],
    "database_id": "2f67584909f3811d9894e2888e25b70c"
  },
  "metadata": {
    "count": 50,
    "max_results": 50
  }
}
```

### Batch Update Pages

Update multiple pages from a JSON file:

**updates.json:**
```json
{
  "updates": [
    {
      "page_id": "page-id-1",
      "properties": {
        "Status": {
          "status": {"name": "Completed"}
        }
      }
    },
    {
      "page_id": "page-id-2",
      "properties": {
        "Priority": {
          "select": {"name": "High"}
        }
      }
    }
  ]
}
```

```bash
claude-mpm tools notion pages-batch-update --file updates.json
```

### Export Pages with Content

Export full page content including all blocks:

```bash
claude-mpm tools notion pages-export \
  --page-ids "abc123,def456,ghi789" \
  --output full-export.json
```

### Markdown Import

Convert markdown files to Notion pages:

```bash
claude-mpm tools notion md-import \
  --files "README.md,CHANGELOG.md" \
  --database-id YOUR_DB_ID
```

Supported markdown features:
- Headers (h1-h3, h4-h6 map to h3)
- Paragraphs with inline formatting (bold, italic, code, links)
- Bullet lists
- Numbered lists
- Code blocks with syntax highlighting
- Block quotes

---

## Troubleshooting

### "NOTION_API_KEY not configured"

**Solution**: Run `claude-mpm setup notion` or set environment variable:

```bash
export NOTION_API_KEY="secret_your_token_here"  # pragma: allowlist secret
```

### "database_id required"

**Solution**: Either set `NOTION_DATABASE_ID` environment variable or pass `--database-id` flag:

```bash
# Set default
export NOTION_DATABASE_ID="your_db_id"

# Or use flag
claude-mpm tools notion database-query --database-id YOUR_DB_ID
```

### "object not found" errors

**Cause**: Database or page not shared with integration.

**Solution**:
1. Open the database/page in Notion
2. Click "..." > "Connections"
3. Add your integration

### Rate Limiting

Notion API limits:
- **3 requests/second** per integration

The tools automatically handle rate limiting with 350ms delays between requests.

### MCP Server Not Starting

**Check logs:**
```bash
# Test the server directly
notion-mcp

# Should output MCP protocol messages
```

**Verify installation:**
```bash
which notion-mcp
# Should show: /path/to/python/bin/notion-mcp
```

---

## Advanced Usage

### Filter Examples

Query with complex filters:

```typescript
{
  "filter": {
    "and": [
      {
        "property": "Status",
        "status": {
          "equals": "In Progress"
        }
      },
      {
        "property": "Priority",
        "select": {
          "equals": "High"
        }
      }
    ]
  }
}
```

### Custom Properties

Create pages with custom property types:

```typescript
{
  "properties": {
    "Name": {"title": [{"text": {"content": "Task"}}]},
    "Status": {"status": {"name": "To Do"}},
    "Priority": {"select": {"name": "Medium"}},
    "Due Date": {"date": {"start": "2026-02-15"}},
    "Assigned": {"people": [{"id": "user-id"}]},
    "Tags": {"multi_select": [
      {"name": "bug"},
      {"name": "urgent"}
    ]},
    "Progress": {"number": 75},
    "Active": {"checkbox": true},
    "URL": {"url": "https://example.com"},
    "Email": {"email": "user@example.com"},
    "Phone": {"phone_number": "+1234567890"}
  }
}
```

---

## See Also

- [Notion API Documentation](https://developers.notion.com/)
- [claude-mpm Tools Framework Guide](../tools-framework-guide.md)
- [MCP Server Documentation](./mcp-setup.md)

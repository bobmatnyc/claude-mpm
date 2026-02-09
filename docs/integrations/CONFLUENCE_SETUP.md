# Confluence Integration Setup

The Confluence integration for claude-mpm provides both MCP tools for interactive operations and bulk CLI tools for batch processing.

## Quick Setup

```bash
# Automated setup (recommended)
claude-mpm setup confluence

# This will:
# 1. Prompt for your Confluence URL
# 2. Collect your email address
# 3. Prompt for your API token
# 4. Save credentials to .env.local
# 5. Configure confluence-mcp MCP server
```

## Prerequisites

- **Python 3.10+** installed
- **claude-mpm** installed
- A **Confluence Cloud** account (atlassian.net)
- Admin access to create API tokens

## Step 1: Create an API Token

1. Go to [https://id.atlassian.com/manage-profile/security/api-tokens](https://id.atlassian.com/manage-profile/security/api-tokens)
2. Click **"Create API token"**
3. Enter a label (e.g., "Claude MPM")
4. Click **"Create"**
5. Copy the token immediately (you won't see it again)

## Step 2: Find Your Confluence URL

Your Confluence URL is typically: `https://yoursite.atlassian.net`

## Step 3: Run Setup

```bash
claude-mpm setup confluence
```

You'll be prompted for:
- **Confluence URL**: Your site URL
- **Email**: Your Atlassian account email
- **API Token**: The token you created

## MCP Tools Reference

### Page Operations

| Tool | Description |
|------|-------------|
| `get_page` | Get a page by ID with content |
| `get_page_by_title` | Get a page by title and space |
| `search_pages` | Search using CQL (Confluence Query Language) |
| `create_page` | Create a new page |
| `update_page` | Update existing page content |

### Space Operations

| Tool | Description |
|------|-------------|
| `list_spaces` | List Confluence spaces |
| `get_space` | Get space information |

## Bulk Tools Reference

### Search Pages

```bash
claude-mpm tools confluence pages-search \
  --cql "space=TEAM and type=page" \
  --max-results 50 \
  --output pages.json
```

### Batch Export

```bash
claude-mpm tools confluence pages-batch-export \
  --page-ids "123456,789012,345678" \
  --output export.json
```

### List Spaces

```bash
claude-mpm tools confluence spaces-list \
  --max-results 25 \
  --output spaces.json
```

### Import Markdown

```bash
claude-mpm tools confluence md-import \
  --files "doc1.md,doc2.md" \
  --space-key TEAM
```

## Troubleshooting

### "CONFLUENCE_URL not configured"

**Solution**: Run `claude-mpm setup confluence` or set environment variables:

```bash
export CONFLUENCE_URL="https://yoursite.atlassian.net"  # pragma: allowlist secret
export CONFLUENCE_EMAIL="your@email.com"  # pragma: allowlist secret
export CONFLUENCE_API_TOKEN="your_token_here"  # pragma: allowlist secret
```

### Rate Limiting

Confluence API limits:
- **10 requests/second** per user

The tools automatically handle rate limiting with 350ms delays.

## CQL Examples

```cql
# Pages in specific space
space=TEAM and type=page

# Pages modified today
space=TEAM and lastModified >= now("-1d")

# Pages by specific user
space=TEAM and creator=john.doe

# Pages with specific label
space=TEAM and label=important
```

## See Also

- [Confluence API Documentation](https://developer.atlassian.com/cloud/confluence/rest/v1/)
- [claude-mpm Tools Framework Guide](../tools-framework-guide.md)

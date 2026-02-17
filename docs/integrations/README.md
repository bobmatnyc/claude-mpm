# Claude MPM Integrations

Comprehensive integration documentation for connecting Claude MPM with external services and tools.

## Quick Start

```bash
# Setup any integration with one command
claude-mpm setup <integration-name>

# Examples:
claude-mpm setup kuzu-memory
claude-mpm setup mcp-vector-search
claude-mpm setup google-workspace-mcp
claude-mpm setup slack
claude-mpm setup notion
claude-mpm setup confluence
```

## Available Integrations

### Core Integrations (Enabled by Default)

#### [Kuzu Memory](kuzu-memory.md)
**Graph-based semantic memory for project context**

- Replaces static file-based memory with graph database
- Semantic search for context retrieval
- Automatic memory indexing and storage
- Project-scoped memory isolation

```bash
claude-mpm setup kuzu-memory
```

**Key Features**:
- Semantic memory storage
- Natural language queries
- Automatic context enhancement
- Per-agent memory namespaces

---

#### [MCP Vector Search](mcp-vector-search.md)
**AI-powered semantic code search**

- Vector-based code discovery
- Three search modes: text-to-code, code-to-code, contextual
- Automatic codebase indexing
- PM agent uses it before file reading

```bash
claude-mpm setup mcp-vector-search
```

**Key Features**:
- Sub-second semantic search
- Find code by meaning, not keywords
- Discover similar patterns
- Integration with PM agent

---

### External Service Integrations

#### [Google Workspace MCP](gworkspace-mcp.md)
**Complete Google Workspace integration (67 tools)**

- **Gmail** (18 tools) - Email management, labels, search, bulk operations
- **Calendar** (10 tools) - Event management, calendar operations
- **Drive** (17 tools) - File management, uploads, downloads, sync
- **Docs** (11 tools) - Document creation, editing, comments
- **Tasks** (10 tools) - Task lists, management, completion

```bash
# Canonical name (preferred)
claude-mpm setup gworkspace-mcp

# Legacy alias (also works)
claude-mpm setup google-workspace-mcp
```

**Note**: Both names work in CLI for backward compatibility. Configuration automatically migrates from old `google-workspace-mcp` to canonical `gworkspace-mcp` naming.

**Requires**: OAuth 2.0 credentials from Google Cloud Console

**Key Features**:
- Secure OAuth authentication
- Encrypted token storage
- Automatic token refresh
- Batch operations support

**Quick Examples**:
```bash
# Search Gmail
search_gmail_messages(query="is:unread label:inbox", max_results=50)

# Create calendar event
create_event(calendar_id="primary", summary="Meeting", start="...", end="...")

# Upload to Drive
upload_drive_file(file_path="/path/to/file.pdf", parent_folder_id="...")

# Create Google Doc from Markdown
upload_markdown_as_doc(markdown_content="# Title\n\nContent...", title="Doc")
```

---

#### [Slack](slack.md)
**Slack workspace integration via user proxy**

- Channel access (public and private)
- Message operations (send, read, reply)
- Direct messages and group DMs
- Thread management
- User and workspace information
- Message search across workspace

```bash
claude-mpm setup slack
```

**Requires**: Slack app with user OAuth token

**Key Features**:
- User token-based authentication
- Real-time message access
- Thread-aware replies
- Workspace-wide search

**Quick Examples**:
```bash
# Send message
send_message(channel_id="C01234567", text="Hello!")

# Reply to thread
reply_to_thread(channel_id="C01234567", thread_ts="...", text="Thanks!")

# Search messages
search_messages(query="deployment failed", count=20)
```

---

#### [Notion](NOTION_SETUP.md)
**Notion workspace integration (7 MCP tools + bulk CLI)**

- Database queries and management
- Page creation and updates
- Markdown import
- Content synchronization
- Bulk operations (10x faster than MCP)

```bash
claude-mpm setup notion
```

**Requires**: Notion Integration Token (API key)

**Key Features**:
- Interactive MCP tools
- High-performance bulk CLI tools
- Markdown to Notion conversion
- Database property management

**Quick Examples**:
```bash
# MCP: Query database
query_database(database_id="...", filter={...})

# MCP: Create page
create_page(parent_id="...", title="New Page", content=[...])

# Bulk: Import markdown
claude-mpm tools notion md-import --files "*.md" --database-id "..."
```

---

#### [Confluence](CONFLUENCE_SETUP.md)
**Atlassian Confluence integration (7 MCP tools + bulk CLI)**

- Page and space management
- CQL (Confluence Query Language) search
- Markdown import to Confluence
- Batch export operations
- Rate-limited API access

```bash
claude-mpm setup confluence
```

**Requires**: Confluence Cloud URL, email, and API token

**Key Features**:
- Interactive MCP tools
- Bulk CLI operations
- CQL search support
- Markdown conversion

**Quick Examples**:
```bash
# MCP: Search pages
search_pages(cql="space=TEAM and type=page")

# MCP: Create page
create_page(space_key="TEAM", title="New Page", content="...")

# Bulk: Export pages
claude-mpm tools confluence pages-batch-export --page-ids "..." --output export.json
```

---

### Developer Tools

#### [MCP Session Server](mcp-session-server.md)
**Programmatic session management via MCP**

- Session lifecycle control
- Agent message sending
- Session state inspection
- Automation integration

**Key Features**:
- Remote session control
- Headless operation support
- Integration with automation tools

---

#### [LSP Integration](LSP_SETUP.md)
**Language Server Protocol for code intelligence**

- Code completion and suggestions
- Symbol navigation
- Diagnostics and linting
- Documentation on hover
- 40+ LSP tools available

```bash
# Configure in .mcp.json
{
  "mcpServers": {
    "mcp-lsp": {
      "command": "npx",
      "args": ["-y", "@axivo/mcp-lsp"],
      "env": {
        "LSP_FILE_PATH": "/path/to/project"
      }
    }
  }
}
```

---

## Integration Comparison

| Integration | Type | Tools | Auth Method | Use Case |
|-------------|------|-------|-------------|----------|
| **Kuzu Memory** | Core | 4 MCP | None | Project memory |
| **Vector Search** | Core | 3 MCP | None | Code discovery |
| **Google Workspace** | External | 67 MCP | OAuth 2.0 | Productivity suite |
| **Slack** | External | 11 MCP | OAuth User Token | Team communication |
| **Notion** | External | 7 MCP + CLI | API Key | Documentation/DBs |
| **Confluence** | External | 7 MCP + CLI | API Token | Team documentation |
| **Session Server** | Developer | N/A MCP | None | Automation |
| **LSP** | Developer | 40+ MCP | None | Code intelligence |

---

## Setup Patterns

### Single Integration

```bash
# Setup one integration
claude-mpm setup <integration-name>
```

### Multiple Integrations

```bash
# Setup multiple at once
claude-mpm setup kuzu-memory mcp-vector-search gworkspace-mcp
```

### With Options

```bash
# Setup with flags
claude-mpm setup gworkspace-mcp --no-launch --no-browser
claude-mpm setup slack --no-launch
claude-mpm setup mcp-vector-search --force
```

---

## Common Integration Workflows

### 1. Complete Development Setup

```bash
# Core tools
claude-mpm setup kuzu-memory mcp-vector-search

# External services
claude-mpm setup gworkspace-mcp slack notion
```

### 2. Minimal Setup (Core Only)

```bash
# Just memory and search
claude-mpm setup kuzu-memory mcp-vector-search
```

### 3. Team Collaboration Setup

```bash
# Team communication + documentation
claude-mpm setup slack notion confluence gworkspace-mcp
```

---

## Authentication Overview

### OAuth 2.0 (Google Workspace, Slack)

- One-time authorization flow
- Browser-based authentication
- Encrypted token storage
- Automatic token refresh

**Setup**:
1. Create OAuth credentials in service console
2. Run `claude-mpm setup <service>`
3. Complete browser authorization
4. Tokens stored securely

### API Keys (Notion, Confluence)

- Service generates API key/token
- Store in `.env.local`
- No OAuth flow required
- Manual token management

**Setup**:
1. Generate API key in service settings
2. Run `claude-mpm setup <service>`
3. Enter API key when prompted
4. Credentials saved to `.env.local`

---

## Configuration Files

### `.env.local` (Service Credentials)

```bash
# OAuth Services
GOOGLE_OAUTH_CLIENT_ID="..."
GOOGLE_OAUTH_CLIENT_SECRET="..."
SLACK_OAUTH_CLIENT_ID="..."
SLACK_OAUTH_CLIENT_SECRET="..."

# API Key Services
NOTION_API_KEY="secret_..."  # pragma: allowlist secret
CONFLUENCE_URL="https://site.atlassian.net"
CONFLUENCE_EMAIL="user@example.com"
CONFLUENCE_API_TOKEN="..."  # pragma: allowlist secret
```

**Security**: Always add to `.gitignore`

### `.mcp.json` (MCP Server Configuration)

```json
{
  "mcpServers": {
    "kuzu-memory": {
      "command": "uvx",
      "args": ["kuzu-memory"],
      "env": {}
    },
    "mcp-vector-search": {
      "command": "uvx",
      "args": ["mcp-vector-search"],
      "env": {}
    },
    "google-workspace-mcp": {
      "command": "google-workspace-mcp",
      "args": [],
      "env": {
        "GOOGLE_OAUTH_CLIENT_ID": "...",
        "GOOGLE_OAUTH_CLIENT_SECRET": "..."
      }
    }
  }
}
```

### `.claude-mpm/configuration.yaml` (MPM Configuration)

```yaml
memory:
  backend: kuzu
  kuzu:
    project_root: /path/to/project
    db_path: /path/to/project/kuzu-memories
```

---

## Troubleshooting

### OAuth Issues

```bash
# Re-authorize service
claude-mpm setup <service> --force

# Check token status
claude-mpm oauth status <service>

# Revoke and start fresh
claude-mpm oauth revoke <service>
claude-mpm setup <service>
```

### Configuration Issues

```bash
# Verify setup
cat .env.local
cat .mcp.json

# Check MCP server status
claude-mpm mcp list

# Test integration
claude-mpm mcp test <service>
```

### Installation Issues

```bash
# Reinstall integration
claude-mpm setup <service> --force

# Check installation method
claude-mpm doctor installation

# Manual installation
uv tool install <package> --python 3.13
```

---

## Best Practices

### Security

1. **Never commit credentials**: Add `.env.local` to `.gitignore`
2. **Use environment files**: Store secrets in `.env.local`
3. **Rotate tokens regularly**: Revoke and re-authorize periodically
4. **Minimum scopes**: Only request necessary permissions

### Performance

1. **Use batch operations**: Leverage bulk tools for multiple operations
2. **Cache results**: Store frequently accessed data
3. **Rate limiting**: Implement backoff for API calls
4. **Incremental updates**: Use delta APIs when available

### Organization

1. **Project isolation**: Each project has independent configuration
2. **Documentation**: Document custom integrations
3. **Version control**: Track `.mcp.json` in git
4. **Testing**: Verify integrations after setup

---

## MCP Protocol

All integrations use the [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) for standardized tool interfaces.

### MCP Benefits

- **Standardized interface**: Consistent tool discovery and invocation
- **Type safety**: JSON schema validation
- **Hot reload**: Update tools without restart
- **Error handling**: Structured error responses
- **Streaming**: Support for streaming operations

### MCP Server Types

- **stdio**: Standard input/output communication
- **HTTP**: REST API endpoints
- **WebSocket**: Bidirectional communication

---

## Integration Development

Create custom integrations:

1. **Define service** in `mcp_service_registry.py`
2. **Implement MCP server** with tools
3. **Add setup logic** to `setup.py`
4. **Document integration** in this directory
5. **Add tests** for reliability

See [MCP Integration Guide](../developer/mcp-integration.md) for details.

---

## Further Reading

- [MCP Protocol Specification](https://spec.modelcontextprotocol.io/)
- [OAuth Security Guide](../security/oauth.md)
- [Configuration Guide](../configuration/README.md)
- [Developer Documentation](../developer/README.md)

---

## Quick Reference

```bash
# Setup commands
claude-mpm setup <integration>        # Setup single integration
claude-mpm setup <int1> <int2>        # Setup multiple
claude-mpm setup <int> --no-launch    # Setup without launch
claude-mpm setup <int> --force        # Force reinstall/reconfigure

# OAuth commands
claude-mpm oauth status <service>     # Check OAuth token status
claude-mpm oauth revoke <service>     # Revoke OAuth token

# MCP commands
claude-mpm mcp list                   # List MCP servers
claude-mpm mcp enable <service>       # Enable MCP server
claude-mpm mcp disable <service>      # Disable MCP server

# Diagnostics
claude-mpm doctor                     # Run all health checks
claude-mpm doctor installation        # Check installation
claude-mpm doctor integrations        # Check integrations
```

---

[Back to Documentation Index](../README.md)

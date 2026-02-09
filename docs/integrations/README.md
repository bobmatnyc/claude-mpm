# Integrations

Documentation for integrating Claude MPM with external services.

## Available Integrations

### External Services
- **[Notion Setup](NOTION_SETUP.md)** - MCP + bulk tools for databases, pages, and markdown import
- **[Confluence Setup](CONFLUENCE_SETUP.md)** - MCP + bulk tools for pages, spaces, and CQL search
- **[Slack Setup](SLACK_SETUP.md)** - Configure Slack integration for notifications and commands
- **[Slack User Proxy Setup](SLACK_USER_PROXY_SETUP.md)** - Set up user proxy for Slack OAuth
- **[LSP Setup](LSP_SETUP.md)** - Language Server Protocol integration for code intelligence

### Internal Services
- **[MCP Session Server](mcp-session-server.md)** - Programmatic session management via Model Context Protocol

## Overview

Claude MPM can integrate with various external services to extend its functionality:

### Notion Integration
Provides MCP tools and bulk CLI operations for Notion databases, pages, and content. Supports markdown import, database queries, and page management with 10x faster bulk operations than MCP protocol.

### Confluence Integration
Provides MCP tools and bulk CLI operations for Confluence pages, spaces, and content. Supports CQL search, markdown import, and batch page exports with rate-limited API access.

### Slack Integration
Enables real-time notifications, command execution, and team collaboration features through Slack. User proxy mode allows acting as authenticated user for channels, messages, and search.

### MCP Session Server
Provides programmatic access to Claude MPM sessions, allowing automation and integration with other tools.

---

[Back to Documentation Index](../README.md)

# MPM Integrate: API Integration Management

## Overview

`mpm integrate` provides a system for managing API integrations that Claude can use directly as MCP tools. Integrations are defined by YAML manifests that describe API endpoints, authentication, and operations.

**Why use integrations?**
- Connect Claude to external APIs (GitHub, Linear, Slack, etc.)
- Auto-generate MCP servers for seamless tool access
- Manage credentials securely at project or user scope
- Share integrations via a built-in catalog

## Quick Start

### Add Your First Integration

```bash
# List available integrations from the catalog
mpm integrate list --available

# Install jsonplaceholder (a free test API)
mpm integrate add jsonplaceholder

# Check installation status
mpm integrate status jsonplaceholder
```

The integration is now available as an MCP tool. Claude can call operations like `list_posts` or `get_user` directly.

### Create a Custom Integration

```bash
# Launch the interactive wizard
mpm integrate create

# Or create directly in the catalog (for contributors)
mpm integrate create --catalog
```

## Commands Reference

### `mpm integrate list`

List available and/or installed integrations.

```bash
# Show both available and installed (default)
mpm integrate list

# Show only available integrations from catalog
mpm integrate list --available
mpm integrate list -a

# Show only installed integrations
mpm integrate list --installed
mpm integrate list -i
```

**Example output:**
```
Available Integrations
┏━━━━━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Name            ┃ Version ┃ Description                             ┃
┡━━━━━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ jsonplaceholder │ 1.0.0   │ JSONPlaceholder fake REST API           │
└─────────────────┴─────────┴─────────────────────────────────────────┘

Installed Integrations
┏━━━━━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Name            ┃ Version ┃ Scope   ┃ Path                           ┃
┡━━━━━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ jsonplaceholder │ 1.0.0   │ project │ .claude/integrations/json...   │
└─────────────────┴─────────┴─────────┴────────────────────────────────┘
```

### `mpm integrate add`

Install an integration from the catalog.

```bash
# Install to project scope (default)
mpm integrate add github

# Install to user scope (available across all projects)
mpm integrate add github --scope user
mpm integrate add github -s user
```

**What happens on install:**
1. Integration files copied to `.claude/integrations/<name>/` (project) or `~/.claude-mpm/integrations/<name>/` (user)
2. MCP server auto-generated if `mcp.generate: true` in manifest
3. Server registered in `.mcp.json` (project) or `~/.mcp.json` (user)

### `mpm integrate remove`

Uninstall an integration.

```bash
# Remove from first found scope
mpm integrate remove github

# Remove from specific scope
mpm integrate remove github --scope project
mpm integrate remove github -s user
```

### `mpm integrate status`

Check health and details of an installed integration.

```bash
mpm integrate status github
```

**Example output:**
```
github v1.0.0
  Scope: project
  Path: /path/to/.claude/integrations/github
  Operations: 5
  Status: healthy
```

### `mpm integrate call`

Execute an integration operation directly from CLI.

```bash
# Basic call
mpm integrate call jsonplaceholder list_posts

# With parameters
mpm integrate call jsonplaceholder get_post --param id=1
mpm integrate call github list_repos -p username=octocat -p per_page=5
```

### `mpm integrate validate`

Validate an integration manifest.

```bash
# Validate a directory
mpm integrate validate ./my-integration/

# Validate a manifest file directly
mpm integrate validate ./my-integration/integration.yaml
```

### `mpm integrate regenerate`

Regenerate the MCP server for an installed integration (useful after manifest updates).

```bash
mpm integrate regenerate github
```

### `mpm integrate create`

Launch the interactive wizard to create a new integration.

```bash
# Create in current directory
mpm integrate create

# Create in specific directory
mpm integrate create --output ./my-integrations/

# Create directly in catalog (for contributors)
mpm integrate create --catalog
```

### `mpm integrate rebuild-index`

Regenerate the catalog `_index.yaml` file.

```bash
# Rebuild index
mpm integrate rebuild-index

# Verify index is up to date (CI use)
mpm integrate rebuild-index --verify
```

### `mpm integrate validate-catalog`

Validate all integrations in the catalog (used in CI).

```bash
mpm integrate validate-catalog

# With custom catalog directory
mpm integrate validate-catalog --catalog-dir ./my-catalog/
```

### `mpm integrate batch`

Run a batch script against an integration.

```bash
mpm integrate batch github ./scripts/sync_repos.py
```

## Creating Integrations

### Manifest Format

Integrations are defined by an `integration.yaml` file:

```yaml
# Required fields
name: my-api
version: "1.0.0"
description: "My API integration"
base_url: "https://api.example.com/v1"

# Authentication
auth:
  type: bearer  # bearer | api_key | basic | none
  header_name: Authorization  # For api_key type

# Credentials (environment variables)
credentials:
  - name: MY_API_TOKEN
    prompt: "Enter your API token"
    help: "Get your token at https://example.com/settings"
    required: true

# API Operations
operations:
  - name: list_items
    description: "List all items"
    method: GET
    path: "/items"
    parameters:
      - name: limit
        type: integer
        required: false
        default: 10
        description: "Max items to return"

  - name: get_item
    description: "Get item by ID"
    method: GET
    path: "/items/{id}"
    parameters:
      - name: id
        type: integer
        required: true
        in: path
        description: "Item ID"

  - name: create_item
    description: "Create a new item"
    method: POST
    path: "/items"
    parameters:
      - name: title
        type: string
        required: true
        in: body
      - name: content
        type: string
        required: true
        in: body

# Optional: Health check
health_check:
  path: "/health"
  method: GET
  expected_status: 200

# Optional: MCP configuration
mcp:
  generate: true  # Auto-generate MCP server
  tools:          # Limit which operations become tools (null = all)
    - list_items
    - get_item

# Optional: Metadata
tags:
  - api
  - rest
author: "Your Name <you@example.com>"
repository: "https://github.com/you/my-api-integration"
```

### Using the Wizard

The wizard guides you through creating a manifest interactively:

```bash
mpm integrate create
```

**Step 1: Basic Information**
```
Integration name (lowercase, no spaces): my-api
Version [1.0.0]:
Description [my-api API integration]: My custom API
```

**Step 2: API Configuration**
```
Base URL (e.g., https://api.example.com/v1): https://api.example.com
API type (rest/graphql/hybrid) [rest]: rest
```

**Step 3: Authentication**
```
Authentication type (none/api_key/bearer/basic) [api_key]: bearer
Credential environment variable name: MY_API_TOKEN
Description for MY_API_TOKEN: Your API access token
Is MY_API_TOKEN required? [Y/n]: y
```

**Step 4: Operations**
```
Operation name: list_items
Description: List all items
HTTP method (GET/POST/PUT/DELETE/PATCH) [GET]: GET
Path (e.g., /items, /users/{id}): /items
Add parameters? [y/N]: n
Add another operation? [Y/n]: n
```

**Step 5: Optional Metadata**
```
Add health check endpoint? [Y/n]: y
Health check path [/health]: /health
Add tags? [y/N]: n
```

### Parameter Types

| Type | Description | JSON Schema |
|------|-------------|-------------|
| `string` | Text value | `"type": "string"` |
| `integer` | Whole number | `"type": "integer"` |
| `float` | Decimal number | `"type": "number"` |
| `boolean` | True/false | `"type": "boolean"` |
| `file` | File path | `"type": "string"` |

### Parameter Locations

| Location | Description |
|----------|-------------|
| `path` | URL path parameter (e.g., `/items/{id}`) |
| `query` | Query string parameter (e.g., `?limit=10`) |
| `body` | Request body field |
| `header` | HTTP header |

### Authentication Types

| Type | Description | Header Format |
|------|-------------|---------------|
| `none` | No authentication | - |
| `bearer` | Bearer token | `Authorization: Bearer <token>` |
| `api_key` | API key in header | `X-API-Key: <key>` (configurable) |
| `basic` | Basic auth | `Authorization: Basic <base64>` |

## Contributing to the Catalog

### Adding a New Integration

1. **Create the integration:**
   ```bash
   mpm integrate create --catalog
   ```

2. **Rebuild the index:**
   ```bash
   mpm integrate rebuild-index
   ```

3. **Validate:**
   ```bash
   mpm integrate validate-catalog
   ```

4. **Submit a pull request** to the claude-mpm repository.

### Catalog Structure

```
src/claude_mpm/integrations/catalog/
  _index.yaml          # Auto-generated index
  github/
    integration.yaml   # GitHub API manifest
  linear/
    integration.yaml   # Linear API manifest
  jsonplaceholder/
    integration.yaml   # Test API manifest
```

### Validation Requirements

Catalog integrations must pass:
- Manifest schema validation
- Operation type consistency (REST vs GraphQL)
- Required field presence
- Credential reference validation

## Architecture

### Scope: Project vs User

| Scope | Location | MCP Config | Use Case |
|-------|----------|------------|----------|
| Project | `.claude/integrations/` | `.mcp.json` | Project-specific APIs |
| User | `~/.claude-mpm/integrations/` | `~/.mcp.json` | Personal APIs across projects |

**Resolution order:** Project scope takes precedence over user scope.

### MCP Server Generation

When `mcp.generate: true`, installing an integration:

1. Generates `<name>_mcp_server.py` in the integration directory
2. Registers the server in `.mcp.json`:
   ```json
   {
     "mcpServers": {
       "github-integration": {
         "type": "stdio",
         "command": "python",
         "args": ["/path/to/github_mcp_server.py"]
       }
     }
   }
   ```
3. Claude can then use integration operations as tools

### Credential Management

Credentials are loaded from (in order):
1. Environment variables
2. `.env` file in integration directory
3. `.env` file in project root

**Example `.env`:**
```bash
GITHUB_TOKEN=ghp_xxxxxxxxxxxx
LINEAR_API_KEY=lin_api_xxxxxxxxx
```

## Troubleshooting

### Integration Not Found

```
Integration 'myapi' not found in catalog
```

**Solutions:**
- Check spelling: `mpm integrate list -a`
- Create custom integration: `mpm integrate create`

### MCP Server Not Loading

**Check:**
1. Server file exists: `ls .claude/integrations/<name>/`
2. Registered in `.mcp.json`: `cat .mcp.json`
3. Python path correct: `which python`

**Regenerate:**
```bash
mpm integrate regenerate <name>
```

### Authentication Errors

**Check credentials:**
```bash
echo $MY_API_TOKEN  # Verify env var is set
```

**Add to `.env`:**
```bash
echo "MY_API_TOKEN=your-token" >> .claude/integrations/myapi/.env
```

### Validation Errors

```bash
# See specific errors
mpm integrate validate ./my-integration/
```

Common issues:
- Missing required fields (`name`, `version`, `base_url`)
- GraphQL operations in REST-only API
- Duplicate operation names

## Related Files

- **CLI Implementation**: `src/claude_mpm/integrations/cli/integrate.py`
- **Wizard**: `src/claude_mpm/integrations/cli/wizard.py`
- **Manifest Parser**: `src/claude_mpm/integrations/core/manifest.py`
- **MCP Generator**: `src/claude_mpm/integrations/core/mcp_generator.py`
- **Catalog**: `src/claude_mpm/integrations/catalog/`
- **Tests**: `tests/integrations/`

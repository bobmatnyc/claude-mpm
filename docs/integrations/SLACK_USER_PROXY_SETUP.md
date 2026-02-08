# Slack User Proxy MCP Server Setup

The Slack User Proxy MCP server allows Claude to interact with Slack **as you** - reading channels, sending messages, and searching - using OAuth user tokens.

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Step 1: Create a Slack App](#step-1-create-a-slack-app)
- [Step 2: Configure OAuth & Permissions](#step-2-configure-oauth--permissions)
- [Step 3: Get OAuth Credentials](#step-3-get-oauth-credentials)
- [Step 4: Configure Environment](#step-4-configure-environment)
- [Step 5: Authenticate](#step-5-authenticate)
- [Step 6: Run the MCP Server](#step-6-run-the-mcp-server)
- [Available Tools](#available-tools)
- [Troubleshooting](#troubleshooting)
- [Security Notes](#security-notes)
- [See Also](#see-also)

---

## Overview

| Feature | Slack Bot (SLACK_SETUP.md) | Slack User Proxy (this guide) |
|---------|---------------------------|------------------------------|
| Token Type | Bot Token (`xoxb-`) | User Token (`xoxu-`) |
| Identity | Posts as "Claude MPM" bot | Posts as **you** |
| Auth Method | Socket Mode | OAuth 2.0 + PKCE |
| Use Case | Team bot commands | Personal assistant |

---

## Prerequisites

Before you begin, ensure you have:

- **Python 3.10+** installed
- **claude-mpm** installed (`pip install claude-mpm` or `uv pip install claude-mpm`)
- A **Slack workspace** where you have admin access (to create apps)
- Access to [api.slack.com](https://api.slack.com/apps)

---

## Step 1: Create a Slack App

1. Go to [api.slack.com/apps](https://api.slack.com/apps)
2. Click **"Create New App"** > **"From scratch"**
3. Enter app details:
   - **App Name**: `Claude User Proxy` (or your preference)
   - **Workspace**: Select your workspace
4. Click **"Create App"**

You'll be taken to your app's **Basic Information** page.

---

## Step 2: Configure OAuth & Permissions

1. In the left sidebar, click **"OAuth & Permissions"**

2. Under **"Redirect URLs"**, add:
   ```
   http://localhost:8085/oauth/callback
   ```
   Click **"Add"** then **"Save URLs"**

3. Scroll to **"User Token Scopes"** (NOT "Bot Token Scopes"!)

   Add these 13 scopes:

   | Scope | Purpose |
   |-------|---------|
   | `channels:read` | List public channels |
   | `channels:history` | Read public channel messages |
   | `groups:read` | List private channels |
   | `groups:history` | Read private channel messages |
   | `im:read` | List direct messages |
   | `im:history` | Read DM messages |
   | `mpim:read` | List group DMs |
   | `mpim:history` | Read group DM messages |
   | `chat:write` | Send messages as you |
   | `users:read` | Get user info |
   | `users:read.email` | Get user emails |
   | `team:read` | Get workspace info |
   | `search:read` | Search messages |

> **Important**: These must be added under **User Token Scopes**, not Bot Token Scopes. User tokens allow the app to act as you.

---

## Step 3: Get OAuth Credentials

1. In the left sidebar, click **"Basic Information"**
2. Under **"App Credentials"**, copy:
   - **Client ID**
   - **Client Secret**

> **Important**: Keep these credentials secure. Never commit them to version control.

---

## Step 4: Configure Environment

### Option A: Shell Profile (Recommended for personal use)

Add to your shell profile (`~/.zshrc` or `~/.bashrc`):

```bash
export SLACK_OAUTH_CLIENT_ID="your-client-id-here"
export SLACK_OAUTH_CLIENT_SECRET="your-client-secret-here"  # pragma: allowlist secret
```

Then reload your shell:

```bash
source ~/.zshrc  # or source ~/.bashrc
```

### Option B: Project Environment File

Create `.env.local` in your project directory:

```bash
SLACK_OAUTH_CLIENT_ID=your-client-id-here
SLACK_OAUTH_CLIENT_SECRET=your-client-secret-here
```

---

## Step 5: Authenticate

Run the OAuth login flow:

```bash
claude-mpm oauth login slack-user-proxy --provider slack
```

This will:
1. Start a local callback server on port 8085
2. Open your browser to Slack's authorization page
3. After you authorize, store tokens securely in `~/.claude-mpm/tokens/`

You should see output indicating successful authentication:

```
[INFO] Starting OAuth flow for slack-user-proxy...
[INFO] Opening browser for Slack authorization...
[INFO] Successfully authenticated! Token stored.
```

---

## Step 6: Run the MCP Server

### Standalone (for testing)

```bash
slack-user-proxy
```

You should see:

```
[INFO] Slack User Proxy MCP server starting...
[INFO] Ready to accept connections
```

### With Claude Code

Add using the `claude mcp add` command:

```bash
claude mcp add \
  -e SLACK_OAUTH_CLIENT_ID=your-client-id \
  -e SLACK_OAUTH_CLIENT_SECRET=your-client-secret \
  slack-user-proxy -- slack-user-proxy
```

Or add to `.mcp.json` in your project:

```json
{
  "mcpServers": {
    "slack-user-proxy": {
      "command": "slack-user-proxy",
      "env": {
        "SLACK_OAUTH_CLIENT_ID": "your-client-id",
        "SLACK_OAUTH_CLIENT_SECRET": "your-client-secret"
      }
    }
  }
}
```

Verify configuration:

```bash
claude mcp list
```

---

## Available Tools

Once configured, these 12 MCP tools are available:

### Channel Operations

| Tool | Description |
|------|-------------|
| `list_channels` | List public channels |
| `list_private_channels` | List private channels you're in |
| `get_channel_history` | Read messages from a channel |

### Direct Messages

| Tool | Description |
|------|-------------|
| `list_direct_messages` | List your DM conversations |
| `list_group_dms` | List multi-party DMs |
| `get_dm_history` | Read messages from a DM |

### Messaging

| Tool | Description |
|------|-------------|
| `send_message` | Send a message as yourself |
| `reply_to_thread` | Reply in a thread |

### Users & Workspace

| Tool | Description |
|------|-------------|
| `get_user_info` | Get details about a user |
| `list_users` | List workspace members |
| `get_workspace_info` | Get workspace details |

### Search

| Tool | Description |
|------|-------------|
| `search_messages` | Search messages across Slack |

---

## Troubleshooting

### "Not authenticated" Error

**Cause**: Your token may have expired or been revoked.

**Solution**: Re-authenticate:

```bash
claude-mpm oauth login slack-user-proxy --provider slack
```

### "missing_scope" Error

**Cause**: Your Slack app is missing required scopes.

**Solution**:
1. Go to **OAuth & Permissions** in your Slack app settings
2. Add the missing scope under **User Token Scopes**
3. Re-authenticate to get a new token with updated scopes

### OAuth Callback Fails

**Cause**: Port 8085 may be in use by another process.

**Solution**: Check if port is in use:

```bash
lsof -i :8085  # Check what's using the port
```

If another process is using the port, stop it or wait for it to complete.

### Token Storage Location

Tokens are stored in: `~/.claude-mpm/tokens/slack-user-proxy/`

To view stored tokens (for debugging):

```bash
ls -la ~/.claude-mpm/tokens/slack-user-proxy/
```

### MCP Server Not Connecting

**Cause**: Environment variables may not be set correctly.

**Solution**:
1. Verify environment variables are set:
   ```bash
   echo $SLACK_OAUTH_CLIENT_ID
   echo $SLACK_OAUTH_CLIENT_SECRET
   ```
2. Check MCP configuration: `claude mcp get slack-user-proxy`
3. Re-add the server if env vars are incorrect

---

## Security Notes

1. **User tokens act as you**
   - Messages sent through the proxy appear from your account
   - Be mindful that Claude's actions will be attributed to you

2. **Tokens are long-lived**
   - Slack user tokens don't expire unless revoked
   - Periodically review and revoke unused tokens

3. **Secure storage**
   - Tokens are stored with restricted file permissions (600)
   - Never share your token files

4. **Revoke if needed**
   - Go to Slack app settings > OAuth & Permissions > Revoke tokens
   - Or disconnect the app from your Slack workspace settings

5. **Never commit credentials**
   - Add `.env.local` to `.gitignore`
   - Never commit Client ID/Secret to version control

---

## See Also

- [SLACK_SETUP.md](SLACK_SETUP.md) - Slack bot setup (different from user proxy)
- [Slack OAuth Documentation](https://api.slack.com/authentication/oauth-v2)
- [Slack User Token Scopes](https://api.slack.com/scopes)
- [MCP Protocol Documentation](https://modelcontextprotocol.io/)

---

*Generated for Claude MPM Slack User Proxy Integration*

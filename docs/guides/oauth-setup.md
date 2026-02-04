# OAuth Authentication Setup Guide

**Version**: 5.6.71
**Status**: Current
**Last Updated**: 2026-01-23

This guide explains how to set up OAuth authentication for MCP services that require it, such as Google Workspace integration.

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Setting Up Google OAuth Credentials](#setting-up-google-oauth-credentials)
- [Using the OAuth Command](#using-the-oauth-command)
- [Google Workspace MCP Server](#google-workspace-mcp-server)
- [Token Storage and Security](#token-storage-and-security)
- [Troubleshooting](#troubleshooting)

---

## Overview

Claude MPM includes built-in OAuth support for MCP services that require OAuth2 authentication. This enables seamless integration with services like Google Workspace (Gmail, Calendar, Drive) directly from Claude Code.

The OAuth system provides:
- **Browser-based authentication** - Secure OAuth2 flow with browser redirect
- **Encrypted token storage** - Tokens encrypted with Fernet symmetric encryption
- **System keychain integration** - Encryption key stored in macOS Keychain (or equivalent)
- **Automatic token refresh** - Tokens refreshed before expiry

---

## Prerequisites

Before setting up OAuth, you need:

1. **Claude MPM installed** (v5.6.0+)
2. **Google Cloud Console project** with OAuth 2.0 credentials
3. **Environment variables** for OAuth client credentials

---

## Setting Up Google OAuth Credentials

### Step 1: Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the required APIs:
   - Gmail API
   - Google Calendar API
   - Google Drive API

### Step 2: Configure OAuth Consent Screen

1. Navigate to **APIs & Services > OAuth consent screen**
2. Select **External** user type (or Internal for Workspace accounts)
3. Fill in the required fields:
   - App name: "Claude MPM"
   - User support email: Your email
   - Developer contact: Your email
4. Add scopes:
   - `https://www.googleapis.com/auth/gmail.modify`
   - `https://www.googleapis.com/auth/calendar`
   - `https://www.googleapis.com/auth/drive`
5. Add your Google account as a test user

### Step 3: Create OAuth 2.0 Credentials

1. Navigate to **APIs & Services > Credentials**
2. Click **Create Credentials > OAuth client ID**
3. Select **Web application** as the application type
4. Add the authorized redirect URI:
   ```
   http://127.0.0.1:8789/callback
   ```
5. Save your **Client ID** and **Client Secret**

### Step 4: Configure Environment Variables

Add your credentials to a `.env.local` file in your project root:

```bash
# .env.local (not committed to git)
GOOGLE_OAUTH_CLIENT_ID="your-client-id.apps.googleusercontent.com"
GOOGLE_OAUTH_CLIENT_SECRET="your-client-secret"  # pragma: allowlist secret
```

Or export them as environment variables:

```bash
export GOOGLE_OAUTH_CLIENT_ID="your-client-id.apps.googleusercontent.com"
export GOOGLE_OAUTH_CLIENT_SECRET="your-client-secret"  # pragma: allowlist secret
```

> **Security Note**: Never commit OAuth credentials to version control. Use `.env.local` which is typically gitignored.

---

## Using the OAuth Command

Claude MPM provides the `oauth` command for managing OAuth authentication.

### List OAuth-Capable Services

```bash
claude-mpm oauth list
```

Shows all MCP services that support OAuth authentication with their providers and descriptions.

### Set Up OAuth for a Service

```bash
claude-mpm oauth setup google-workspace-mcp
```

This command:
1. Checks for credentials in `.env.local`, `.env`, or environment variables
2. Prompts for credentials interactively if not found
3. Opens your browser for Google authentication
4. Starts a local callback server at `http://localhost:8789/callback`
5. Stores tokens securely after successful authentication

**Options:**
- `--no-browser` - Print the auth URL instead of opening the browser
- `--port <port>` - Specify a custom callback port (default: 8789)

### Check Token Status

```bash
claude-mpm oauth status google-workspace-mcp
```

Shows:
- Whether tokens are stored
- Token validity status
- Expiration time
- Authorized scopes

**Output formats:**
- `--format table` (default) - Human-readable table
- `--format json` - JSON for scripting

### Refresh Tokens

```bash
claude-mpm oauth refresh google-workspace-mcp
```

Manually refresh tokens using the stored refresh token. Useful if you suspect token issues.

### Revoke Tokens

```bash
claude-mpm oauth revoke google-workspace-mcp
```

Revokes and deletes stored tokens. Use `-y` to skip confirmation:

```bash
claude-mpm oauth revoke google-workspace-mcp -y
```

---

## Google Workspace MCP Server

Once OAuth is set up, the integrated Google Workspace MCP server (`google-workspace-mcp`) provides tools for interacting with Google APIs.

### Available Tools

| Tool | Description |
|------|-------------|
| `list_calendars` | List all accessible calendars |
| `get_events` | Get events from a calendar with time range filtering |
| `search_gmail_messages` | Search emails using Gmail query syntax |
| `get_gmail_message_content` | Get full content of an email by ID |
| `search_drive_files` | Search Drive files by query |
| `get_drive_file_content` | Get file content (exports Google Docs to text) |

### Example Usage in Claude Code

After OAuth setup, you can use these tools naturally in Claude Code:

```
User: What meetings do I have this week?
Claude: [Uses get_events tool to fetch calendar events]

User: Search my emails for messages from John about the project
Claude: [Uses search_gmail_messages with query "from:john subject:project"]

User: Find documents about the Q4 report in my Drive
Claude: [Uses search_drive_files with query "name contains 'Q4 report'"]
```

### MCP Server Configuration

The server is automatically configured when using Claude MPM. It's registered as `google-workspace-mcp` and uses tokens from:

```
~/.claude-mpm/credentials/workspace-mcp.enc
```

---

## Token Storage and Security

### Storage Location

OAuth tokens are stored at:
```
~/.claude-mpm/credentials/<service-name>.enc
```

### Encryption

- **Encryption algorithm**: Fernet symmetric encryption (AES-128-CBC)
- **Key storage**: System keychain (macOS Keychain, Windows Credential Manager, or Linux Secret Service)
- **Keychain service**: `claude-mpm-oauth`

### Token Refresh

Tokens are automatically refreshed when:
- The access token expires
- An API call receives a 401 Unauthorized response
- You manually run `claude-mpm oauth refresh`

### Security Best Practices

1. **Use `.env.local`** for credentials (gitignored by default)
2. **Never commit** OAuth credentials to version control
3. **Revoke tokens** when no longer needed: `claude-mpm oauth revoke`
4. **Use test users** during development in Google Cloud Console

---

## Troubleshooting

### "OAuth credentials not found"

**Cause**: Client ID and secret not configured.

**Solution**: Add credentials to `.env.local`:
```bash
GOOGLE_OAUTH_CLIENT_ID="your-id"
GOOGLE_OAUTH_CLIENT_SECRET="your-secret"  # pragma: allowlist secret
```

### "redirect_uri_mismatch" Error

**Cause**: The callback URI doesn't match what's configured in Google Cloud Console.

**Solution**: Add this exact URI to your OAuth client's authorized redirect URIs:
```
http://127.0.0.1:8789/callback
```

### "Access blocked: This app's request is invalid"

**Cause**: OAuth consent screen not configured or app not verified.

**Solution**:
1. Complete the OAuth consent screen setup in Google Cloud Console
2. Add your email as a test user
3. For production, submit for verification

### Token Expired and Won't Refresh

**Cause**: Refresh token was revoked or expired.

**Solution**:
```bash
# Revoke existing tokens
claude-mpm oauth revoke google-workspace-mcp -y

# Re-authenticate
claude-mpm oauth setup google-workspace-mcp
```

### "Port already in use" Error

**Cause**: The callback port (default 8789) is occupied.

**Solution**: Use a different port:
```bash
claude-mpm oauth setup google-workspace-mcp --port 8790
```

### Keychain Access Denied (macOS)

**Cause**: Claude MPM doesn't have keychain access.

**Solution**: When prompted, click "Always Allow" to grant keychain access for `claude-mpm-oauth`.

---

## Related Documentation

- [User Guide](../user/user-guide.md) - General Claude MPM usage
- [MCP Gateway](../developer/13-mcp-gateway/README.md) - MCP server integration
- [Configuration Reference](../configuration/reference.md) - Full configuration options

---

## Quick Reference

```bash
# List OAuth services
claude-mpm oauth list

# Set up Google Workspace
claude-mpm oauth setup google-workspace-mcp

# Check token status
claude-mpm oauth status google-workspace-mcp

# Refresh tokens
claude-mpm oauth refresh google-workspace-mcp

# Revoke tokens
claude-mpm oauth revoke google-workspace-mcp
```

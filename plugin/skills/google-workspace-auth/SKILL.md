---
name: google-workspace-auth
description: "Re-authenticate Google Workspace MCP in-flight - refresh tokens, setup OAuth, check status"
license: MIT
compatibility: claude-code
metadata:
  version: 1.0.0
  category: mpm
  author: Claude MPM Team
progressive_disclosure:
  entry_point:
    summary: "Google Workspace OAuth management for Gmail, Calendar, Drive, Docs, Tasks"
tags: [google, oauth, gmail, calendar, drive, docs, tasks, authentication, mcp]
---

# Google Workspace Authentication

Re-authenticate or manage Google Workspace MCP OAuth tokens during a Claude Code session.

## Quick Commands

### Check Token Status
```bash
claude-mpm oauth status google-workspace-mcp
```

### Refresh Existing Token
```bash
claude-mpm oauth refresh google-workspace-mcp
```

### Full Re-Authentication
```bash
# Opens browser for full OAuth flow
claude-mpm oauth setup google-workspace-mcp --no-launch

# If credentials need to be re-entered
claude-mpm oauth setup google-workspace-mcp --force --no-launch
```

### Revoke Tokens (Logout)
```bash
claude-mpm oauth revoke google-workspace-mcp
```

## Prerequisites

Google OAuth credentials must be configured in one of:
1. `.env.local` (highest priority)
2. `.env`
3. Environment variables

```bash
# Required environment variables
GOOGLE_OAUTH_CLIENT_ID="your-client-id.apps.googleusercontent.com"
GOOGLE_OAUTH_CLIENT_SECRET="your-client-secret"
```

Get credentials from: https://console.cloud.google.com/apis/credentials

## OAuth Callback Configuration

The OAuth callback server listens on `http://127.0.0.1:8789/callback`

Ensure this redirect URI is configured in your Google Cloud Console OAuth client.

## Troubleshooting

### Token Expired
```bash
# Try refresh first (faster, doesn't need browser)
claude-mpm oauth refresh google-workspace-mcp

# If refresh fails, do full re-auth
claude-mpm oauth setup google-workspace-mcp --no-launch
```

### Credentials Not Found
```bash
# Force credential prompt
claude-mpm oauth setup google-workspace-mcp --force --no-launch
```

### Check Available Services
```bash
claude-mpm oauth list
```

## Available Google Workspace MCP Tools (34 total)

After authentication, these tools become available:

**Gmail (5 tools)**: search_gmail_messages, get_gmail_message_content, send_email, create_draft, reply_to_email

**Calendar (6 tools)**: list_calendars, get_events, create_event, update_event, delete_event

**Drive (7 tools)**: search_drive_files, get_drive_file_content, list_document_comments, create_drive_folder, upload_drive_file, delete_drive_file, move_drive_file

**Docs (4 tools)**: create_document, append_to_document, get_document, upload_markdown_as_doc

**Tasks (12 tools)**: list_task_lists, get_task_list, create_task_list, update_task_list, delete_task_list, list_tasks, get_task, search_tasks, create_task, update_task, complete_task, delete_task, move_task

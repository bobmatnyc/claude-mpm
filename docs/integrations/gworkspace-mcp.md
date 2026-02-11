# Google Workspace MCP Integration

## Overview

Google Workspace MCP provides comprehensive integration with Google services including Gmail, Calendar, Drive, Docs, Sheets, Slides, and Tasks. This integration uses OAuth 2.0 for secure authentication and provides 67 MCP tools for workspace automation.

## Features

### Supported Services

- **Gmail** (18 tools) - Email management, search, labels, drafts
- **Calendar** (10 tools) - Event management, calendar operations
- **Drive** (17 tools) - File management, folders, uploads, downloads
- **Docs** (11 tools) - Document creation, editing, comments
- **Tasks** (10 tools) - Task lists, task management, completion tracking
- **Sheets** - Spreadsheet operations (via Drive tools)
- **Slides** - Presentation operations (via Drive tools)

### Key Capabilities

- **OAuth 2.0 Authentication** - Secure user authorization
- **Token Management** - Automatic refresh and encrypted storage
- **Bulk Operations** - Batch processing for efficiency
- **Search & Filter** - Advanced search across all services
- **Real-time Sync** - Live updates and notifications

## Installation

### Prerequisites

- Python 3.11-3.13
- Claude MPM installed
- Google Cloud Project with OAuth credentials

### Step 1: Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create new project or select existing
3. Enable APIs:
   - Gmail API
   - Google Calendar API
   - Google Drive API
   - Google Docs API
   - Google Sheets API
   - Google Slides API
   - Google Tasks API

### Step 2: Configure OAuth Consent

1. Navigate to "APIs & Services" → "OAuth consent screen"
2. Select "External" user type
3. Fill in application information:
   - App name: "Claude MPM"
   - User support email: Your email
   - Developer contact: Your email
4. Add scopes:
   - `openid`
   - `email`
   - `profile`
   - `https://www.googleapis.com/auth/gmail.modify`
   - `https://www.googleapis.com/auth/calendar`
   - `https://www.googleapis.com/auth/drive`
   - `https://www.googleapis.com/auth/documents`
   - `https://www.googleapis.com/auth/spreadsheets`
   - `https://www.googleapis.com/auth/tasks`

### Step 3: Create OAuth Credentials

1. Navigate to "APIs & Services" → "Credentials"
2. Click "Create Credentials" → "OAuth client ID"
3. Application type: "Desktop app"
4. Name: "Claude MPM Desktop"
5. Download credentials JSON

### Step 4: Run Setup

```bash
# From your project directory
claude-mpm setup google-workspace-mcp
```

This will:
1. Prompt for OAuth credentials (client ID and secret)
2. Open browser for Google authorization
3. Store encrypted tokens in system keychain
4. Configure MCP server in `.mcp.json`
5. Install gworkspace-mcp package if needed

### Setup Options

```bash
# Setup without auto-launch
claude-mpm setup google-workspace-mcp --no-launch

# Setup without browser auto-open
claude-mpm setup google-workspace-mcp --no-browser

# Force credential re-entry
claude-mpm setup google-workspace-mcp --force
```

## Configuration

### MCP Server Configuration

Added to `.mcp.json`:

```json
{
  "mcpServers": {
    "google-workspace-mcp": {
      "command": "google-workspace-mcp",
      "args": [],
      "env": {
        "GOOGLE_OAUTH_CLIENT_ID": "your-client-id",
        "GOOGLE_OAUTH_CLIENT_SECRET": "your-client-secret"  # pragma: allowlist secret
      }
    }
  }
}
```

### Environment Variables

OAuth credentials in `.env.local`:

```bash
# OAuth Configuration
GOOGLE_OAUTH_CLIENT_ID="123456789.apps.googleusercontent.com"
GOOGLE_OAUTH_CLIENT_SECRET="your-client-secret"  # pragma: allowlist secret

# Optional: User email (for multi-account setups)
USER_GOOGLE_EMAIL="your-email@gmail.com"

# Optional: Programmable Search Engine (for web search)
GOOGLE_PSE_API_KEY="your-pse-api-key"  # pragma: allowlist secret
GOOGLE_PSE_ENGINE_ID="your-engine-id"

# Development only (allows HTTP for local testing)
OAUTHLIB_INSECURE_TRANSPORT="1"
```

## OAuth Token Management

### Token Storage

Tokens are securely stored:
- **Location**: System keychain (Keychain on macOS, SecretService on Linux, Credential Manager on Windows)
- **Encryption**: Fernet encryption with system-managed keys
- **Scope**: Per-project isolation

### Token Refresh

Tokens automatically refresh:
- Background refresh before expiration
- Transparent to user
- No re-authentication needed (unless revoked)

### Token Revocation

Revoke access:

```bash
# Via OAuth command
claude-mpm oauth revoke google-workspace-mcp

# Manually in Google Account
# Visit: https://myaccount.google.com/permissions
```

## MCP Tools

### Gmail Tools (18)

**Message Management**:
- `search_gmail_messages` - Search emails with filters
- `get_gmail_message_content` - Read email content
- `send_email` - Send new email
- `reply_to_email` - Reply to thread
- `create_draft` - Create draft email

**Label Management**:
- `list_gmail_labels` - List all labels
- `create_gmail_label` - Create new label
- `delete_gmail_label` - Remove label
- `modify_gmail_message` - Apply/remove labels

**Bulk Operations**:
- `batch_modify_gmail_messages` - Bulk label changes
- `batch_archive_gmail_messages` - Archive multiple
- `batch_trash_gmail_messages` - Trash multiple
- `batch_mark_gmail_as_read` - Mark multiple as read
- `batch_delete_gmail_messages` - Permanent delete

**Single Message Operations**:
- `archive_gmail_message`
- `trash_gmail_message`
- `mark_gmail_as_read`
- `star_gmail_message`

### Calendar Tools (10)

**Calendar Management**:
- `list_calendars` - List all calendars
- `create_calendar` - Create new calendar
- `update_calendar` - Modify calendar settings
- `delete_calendar` - Remove calendar

**Event Management**:
- `get_events` - Retrieve events with filters
- `create_event` - Create new event
- `update_event` - Modify existing event
- `delete_event` - Remove event

### Drive Tools (17)

**File Operations**:
- `search_drive_files` - Search by name/type
- `get_drive_file_content` - Download content
- `upload_drive_file` - Upload new file
- `create_drive_folder` - Create folder
- `delete_drive_file` - Remove file/folder
- `move_drive_file` - Move to different folder

**Folder Operations**:
- `list_drive_contents` - List folder contents
- `download_drive_folder` - Download entire folder
- `upload_to_drive` - Batch upload
- `sync_drive_folder` - Two-way sync

### Docs Tools (11)

**Document Management**:
- `create_document` - Create new doc
- `get_document` - Read document content
- `append_to_document` - Add content to end
- `upload_markdown_as_doc` - Convert markdown to Google Doc

**Comment Management**:
- `list_document_comments` - Get all comments
- `add_document_comment` - Add new comment
- `reply_to_comment` - Reply to existing

### Tasks Tools (10)

**Task List Management**:
- `list_task_lists` - Get all task lists
- `create_task_list` - Create new list
- `update_task_list` - Modify list
- `delete_task_list` - Remove list

**Task Management**:
- `list_tasks` - Get tasks in list
- `create_task` - Create new task
- `update_task` - Modify task
- `complete_task` - Mark as done
- `delete_task` - Remove task
- `move_task` - Reorder tasks

## Usage Examples

### Gmail: Search and Archive

```python
# Search unread emails
messages = search_gmail_messages(
    query="is:unread label:inbox",
    max_results=50
)

# Archive old emails
batch_archive_gmail_messages(
    message_ids=[msg.id for msg in messages if msg.age > 30]
)
```

### Calendar: Create Meeting

```python
# Create calendar event
create_event(
    calendar_id="primary",
    summary="Team Standup",
    start="2024-02-15T10:00:00Z",
    end="2024-02-15T10:30:00Z",
    attendees=["team@example.com"]
)
```

### Drive: Upload and Organize

```python
# Upload file
file = upload_drive_file(
    file_path="/path/to/report.pdf",
    parent_folder_id="folder-id"
)

# Create folder structure
folder = create_drive_folder(
    name="Project Reports",
    parent_id="root"
)
```

### Docs: Markdown to Google Doc

```python
# Convert markdown to Google Doc
doc = upload_markdown_as_doc(
    markdown_content="# Report\n\n## Summary\n...",
    title="Monthly Report"
)
```

### Tasks: Task Management

```python
# Create task list
task_list = create_task_list(
    title="Sprint Tasks"
)

# Add tasks
create_task(
    task_list_id=task_list.id,
    title="Implement feature",
    notes="Details...",
    due="2024-02-20T00:00:00Z"
)
```

## Best Practices

### Authentication

1. **One-time Setup**: OAuth only needed once per project
2. **Token Security**: Never commit `.env.local` to git
3. **Scope Minimization**: Only request needed permissions
4. **Regular Rotation**: Periodically revoke and re-authorize

### API Usage

1. **Batch Operations**: Use batch tools for bulk changes
2. **Rate Limiting**: Respect API quotas (implement backoff)
3. **Error Handling**: Check for quota/permission errors
4. **Pagination**: Handle large result sets

### Performance

1. **Search Filters**: Use specific queries to reduce results
2. **Field Selection**: Request only needed fields
3. **Caching**: Cache infrequently changing data
4. **Parallel Requests**: Use async for independent operations

## Troubleshooting

### OAuth Authorization Failed

**Issue**: Browser doesn't open or authorization fails

**Solutions**:
```bash
# Use manual flow
claude-mpm setup google-workspace-mcp --no-browser

# Check credentials
cat .env.local | grep GOOGLE_OAUTH

# Force credential re-entry
claude-mpm setup google-workspace-mcp --force
```

### Token Expired

**Issue**: "Token has expired" errors

**Solutions**:
```bash
# Re-run setup to refresh tokens
claude-mpm setup google-workspace-mcp

# Check token status
claude-mpm oauth status google-workspace-mcp
```

### Permission Denied

**Issue**: "Insufficient permissions" errors

**Solutions**:
1. Verify OAuth scopes in Google Cloud Console
2. Re-authorize with correct scopes
3. Check API is enabled for project

### Rate Limit Exceeded

**Issue**: "429 Too Many Requests" errors

**Solutions**:
1. Implement exponential backoff
2. Use batch operations to reduce requests
3. Request quota increase in Google Cloud Console

## API Quotas

Default quotas per day:

| Service | Queries | Writes |
|---------|---------|--------|
| **Gmail** | 1,000,000,000 | 100,000 |
| **Calendar** | 1,000,000 | 500,000 |
| **Drive** | 1,000,000,000 | 20,000 |
| **Docs** | 40,000 | 40,000 |
| **Tasks** | 50,000 | 50,000 |

## Security

### Token Encryption

- Tokens encrypted with Fernet (symmetric encryption)
- Keys stored in system keychain
- Per-project isolation
- No plain-text storage

### Credential Management

```bash
# View credential status
claude-mpm oauth status google-workspace-mcp

# Rotate credentials
claude-mpm oauth revoke google-workspace-mcp
claude-mpm setup google-workspace-mcp --force

# Remove credentials
claude-mpm oauth revoke google-workspace-mcp
rm .env.local
```

## CLI Tools

```bash
# Gmail bulk operations
claude-mpm tools gmail archive --query "older_than:30d"
claude-mpm tools gmail label --label "Processed" --query "from:noreply@*"

# Calendar export
claude-mpm tools calendar export --start 2024-01-01 --end 2024-12-31

# Drive sync
claude-mpm tools drive sync --remote-folder "Work Docs" --local-folder ~/Documents/Work

# Tasks export
claude-mpm tools tasks export --list "Sprint 1" --format json
```

## Further Reading

- [OAuth Setup Guide](../guides/oauth-setup.md)
- [Google Workspace MCP on PyPI](https://pypi.org/project/gworkspace-mcp/)
- [API Documentation](https://developers.google.com/workspace)
- [OAuth 2.0 Security](../security/oauth.md)

---

[Back to Integrations](README.md) | [Documentation Index](../README.md)

# Slack Integration

## Overview

Slack integration for Claude MPM provides user proxy capabilities for channels, messages, DMs, and search. This integration uses OAuth 2.0 user tokens to act as the authenticated user in Slack workspaces.

## Features

- **Channel Access** - List and read public/private channels
- **Message Operations** - Send, read, and reply to messages
- **Direct Messages** - Access DMs and group DMs
- **Thread Management** - Reply to threads and follow conversations
- **User Information** - Lookup user profiles and details
- **Workspace Info** - Access workspace metadata
- **Message Search** - Search across channels and DMs

## Installation

### Prerequisites

- Python 3.11-3.13
- Claude MPM installed
- Slack workspace with admin access (to create app)

### Step 1: Create Slack App

1. Go to [Slack API Apps](https://api.slack.com/apps)
2. Click "Create New App" → "From scratch"
3. App name: "Claude MPM"
4. Select your workspace

### Step 2: Configure OAuth Scopes

Navigate to "OAuth & Permissions" and add **User Token Scopes**:

**Required scopes**:
- `channels:read` - View public channels
- `channels:history` - View messages in public channels
- `groups:read` - View private channels
- `groups:history` - View messages in private channels
- `im:read` - View direct messages
- `im:history` - View DM message content
- `mpim:read` - View group DMs
- `mpim:history` - View group DM content
- `chat:write` - Send messages as user
- `users:read` - View user information
- `users:read.email` - View user emails
- `team:read` - View workspace information
- `search:read` - Search messages and files

### Step 3: Configure OAuth Redirect

1. In "OAuth & Permissions"
2. Add Redirect URL: `http://localhost:8765/slack/oauth/callback`
3. Save URLs

### Step 4: Get Client Credentials

From "Basic Information":
- **Client ID**: Found under "App Credentials"
- **Client Secret**: Found under "App Credentials" (click "Show")

### Step 5: Run Setup

```bash
# From your project directory
claude-mpm setup slack
```

The setup wizard will:
1. Prompt for Client ID and Client Secret
2. Save credentials to `.env.local`
3. Open browser for Slack authorization
4. Store user token securely
5. Configure slack-user-proxy MCP server in `.mcp.json`
6. Launch Claude MPM (unless `--no-launch` specified)

### Setup Options

```bash
# Setup without auto-launch
claude-mpm setup slack --no-launch

# Setup without browser auto-open (manual token entry)
claude-mpm setup slack --no-browser
```

## Configuration

### Environment Variables

Stored in `.env.local`:

```bash
# Slack OAuth Configuration
SLACK_OAUTH_CLIENT_ID="123456789.1234567890123"
SLACK_OAUTH_CLIENT_SECRET="your-client-secret"  # pragma: allowlist secret

# Optional: User token (auto-managed)
SLACK_USER_TOKEN="xoxp-..."  # pragma: allowlist secret
```

### MCP Server Configuration

Added to `.mcp.json`:

```json
{
  "mcpServers": {
    "slack-user-proxy": {
      "command": "slack-user-proxy",
      "args": [],
      "env": {
        "SLACK_OAUTH_CLIENT_ID": "123456789.1234567890123",
        "SLACK_OAUTH_CLIENT_SECRET": "your-client-secret"  # pragma: allowlist secret
      }
    }
  }
}
```

## MCP Tools

### Channel Tools

#### list_channels
List all public channels in workspace:

```python
{
  "exclude_archived": true,
  "limit": 100
}
```

#### list_private_channels
List private channels user is member of:

```python
{
  "exclude_archived": true,
  "limit": 100
}
```

#### get_channel_history
Get messages from a channel:

```python
{
  "channel_id": "C01234567",
  "limit": 50,
  "oldest": "1234567890.123456",  # Optional: Unix timestamp
  "latest": "1234567890.123456"   # Optional: Unix timestamp
}
```

### Message Tools

#### send_message
Send message to channel or DM:

```python
{
  "channel_id": "C01234567",
  "text": "Hello from Claude MPM!",
  "thread_ts": "1234567890.123456"  # Optional: Reply to thread
}
```

#### reply_to_thread
Reply to message thread:

```python
{
  "channel_id": "C01234567",
  "thread_ts": "1234567890.123456",
  "text": "Thanks for the update!"
}
```

### Direct Message Tools

#### list_direct_messages
List all direct messages:

```python
{
  "limit": 100
}
```

#### list_group_dms
List all group DMs:

```python
{
  "limit": 100
}
```

#### get_dm_history
Get DM conversation history:

```python
{
  "channel_id": "D01234567",
  "limit": 50,
  "oldest": "1234567890.123456",  # Optional
  "latest": "1234567890.123456"   # Optional
}
```

### User Tools

#### get_user_info
Get user profile information:

```python
{
  "user_id": "U01234567"
}
```

#### list_users
List all workspace users:

```python
{
  "limit": 100
}
```

### Workspace Tools

#### get_workspace_info
Get workspace metadata:

```python
{}
```

#### search_messages
Search messages across workspace:

```python
{
  "query": "deployment failed",
  "sort": "timestamp",  # or "score"
  "sort_dir": "desc",   # or "asc"
  "count": 20
}
```

## Usage Examples

### Monitor Channel

```python
# Get recent messages from channel
messages = get_channel_history(
    channel_id="C01234567",
    limit=10
)

for msg in messages:
    print(f"{msg.user}: {msg.text}")
```

### Send Notification

```python
# Send message to channel
send_message(
    channel_id="C01234567",
    text="🚀 Deployment completed successfully!"
)
```

### Reply to Thread

```python
# Reply to existing message
reply_to_thread(
    channel_id="C01234567",
    thread_ts="1234567890.123456",
    text="I've reviewed the PR and it looks good!"
)
```

### Search Conversations

```python
# Search for specific topic
results = search_messages(
    query="error production",
    count=20
)

for result in results:
    print(f"Found in #{result.channel}: {result.text}")
```

### Direct Message

```python
# Send DM to user
send_message(
    channel_id="D01234567",  # DM channel ID
    text="Hi! Quick question about the deployment..."
)
```

## Best Practices

### Message Formatting

Use Slack's mrkdwn formatting:

```python
send_message(
    channel_id="C01234567",
    text="""
*Bold text*
_Italic text_
~Strikethrough~
`Code`
```Code block```
> Quote
• Bullet point
<https://example.com|Link text>
"""
)
```

### Rate Limiting

Respect Slack's rate limits:

- **Tier 1**: 1 request per minute (most read methods)
- **Tier 2**: 20 requests per minute (chat.postMessage)
- **Tier 3**: 50 requests per minute (search)

Implement backoff:

```python
import time

def send_with_retry(channel_id, text, max_retries=3):
    for attempt in range(max_retries):
        try:
            return send_message(channel_id, text)
        except RateLimitError as e:
            if attempt < max_retries - 1:
                time.sleep(e.retry_after)
            else:
                raise
```

### Error Handling

```python
try:
    send_message(channel_id="C01234567", text="Hello!")
except ChannelNotFoundError:
    print("Channel doesn't exist or bot not invited")
except NotAuthorizedError:
    print("Missing required OAuth scope")
except RateLimitError as e:
    print(f"Rate limited. Retry after {e.retry_after} seconds")
```

## Troubleshooting

### OAuth Authorization Failed

**Issue**: Authorization fails or token not saved

**Solutions**:
```bash
# Check credentials in .env.local
cat .env.local | grep SLACK_OAUTH

# Re-run setup with force flag
claude-mpm setup slack --force

# Verify redirect URL in Slack app settings
# Must be: http://localhost:8765/slack/oauth/callback
```

### Channel Not Found

**Issue**: Cannot access channel

**Solutions**:
1. Verify channel ID (starts with 'C' for public, 'G' for private)
2. Ensure user is member of private channels
3. Check app has required scopes

### Permission Denied

**Issue**: Missing OAuth scopes

**Solutions**:
1. Go to Slack App "OAuth & Permissions"
2. Add missing User Token Scopes
3. Re-authorize app: `claude-mpm setup slack --force`
4. User must reinstall app with new scopes

### Rate Limit Exceeded

**Issue**: "429 Too Many Requests" errors

**Solutions**:
1. Implement exponential backoff
2. Batch operations when possible
3. Cache channel/user lists
4. Respect retry-after headers

## Security

### Token Management

- User tokens stored in `.env.local`
- Never commit `.env.local` to version control
- Add to `.gitignore`:

```gitignore
.env.local
.env
*.secret
```

### Scope Minimization

Only request necessary scopes:

```bash
# Minimal setup (read-only)
REQUIRED_SCOPES="channels:read,channels:history,users:read"

# Full setup (read + write)
REQUIRED_SCOPES="channels:read,channels:history,chat:write,users:read"
```

### Token Rotation

Periodically rotate tokens:

```bash
# Revoke old token
claude-mpm oauth revoke slack

# Re-authorize
claude-mpm setup slack --force
```

## CLI Tools

```bash
# List channels
claude-mpm tools slack channels

# Send message
claude-mpm tools slack send --channel "#general" --message "Hello!"

# Search messages
claude-mpm tools slack search --query "deployment"

# Get channel history
claude-mpm tools slack history --channel "#general" --limit 50
```

## Webhook Integration

For incoming webhooks (bot notifications):

1. Create incoming webhook in Slack app
2. Add webhook URL to `.env.local`:

```bash
SLACK_WEBHOOK_URL="https://hooks.slack.com/services/T00/B00/XXX"
```

3. Use webhook for notifications:

```python
import requests

def send_webhook(message):
    requests.post(
        os.getenv("SLACK_WEBHOOK_URL"),
        json={"text": message}
    )
```

## Advanced Features

### Message Blocks

Use Block Kit for rich messages:

```python
send_message(
    channel_id="C01234567",
    blocks=[
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*Deployment Status*"
            }
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": "*Status:*\n✅ Success"},
                {"type": "mrkdwn", "text": "*Duration:*\n2m 34s"}
            ]
        }
    ]
)
```

### Scheduled Messages

```python
import time

# Schedule message for future
send_message(
    channel_id="C01234567",
    text="Reminder: Meeting in 10 minutes",
    post_at=int(time.time()) + 600  # 10 minutes from now
)
```

## Further Reading

- [Slack API Documentation](https://api.slack.com/docs)
- [Slack User Proxy Setup](SLACK_USER_PROXY_SETUP.md)
- [OAuth Security Guide](../security/oauth.md)
- [MCP Tools Reference](../reference/mcp-tools.md)

---

[Back to Integrations](README.md) | [Documentation Index](../README.md)

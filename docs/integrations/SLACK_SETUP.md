# Slack Integration Setup Guide

This guide walks you through setting up the Slack integration for Claude MPM (Multi-Agent Project Manager).

## Table of Contents

- [Prerequisites](#prerequisites)
- [Step 1: Create a Slack App](#step-1-create-a-slack-app)
- [Step 2: Enable Socket Mode](#step-2-enable-socket-mode)
- [Step 3: Configure OAuth Scopes](#step-3-configure-oauth-scopes)
- [Step 4: Register Slash Commands](#step-4-register-slash-commands)
- [Step 5: App Home Setup (Optional)](#step-5-app-home-setup-optional)
- [Step 6: Events Setup (Optional)](#step-6-events-setup-optional)
- [Step 7: Install to Workspace](#step-7-install-to-workspace)
- [Step 8: Configure Environment](#step-8-configure-environment)
- [Step 9: Run the Bot](#step-9-run-the-bot)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

Before you begin, ensure you have:

- **Python 3.8+** installed
- **slack-bolt** package installed (`pip install slack-bolt`)
- A **Slack workspace** where you have permission to install apps
- Access to [api.slack.com](https://api.slack.com/apps)

---

## Step 1: Create a Slack App

1. Go to [api.slack.com/apps](https://api.slack.com/apps)
2. Click **Create New App**
3. Choose **From scratch**
4. Enter app details:
   - **App Name**: `Claude MPM` (or your preferred name)
   - **Workspace**: Select your workspace
5. Click **Create App**

You'll be taken to your app's **Basic Information** page.

---

## Step 2: Enable Socket Mode

Socket Mode allows your app to receive events through a WebSocket connection instead of requiring a public HTTP endpoint.

1. In the left sidebar, click **Socket Mode**
2. Toggle **Enable Socket Mode** to ON
3. You'll be prompted to create an App-Level Token:
   - **Token Name**: `socket-mode-token`
   - **Scopes**: Add `connections:write`
4. Click **Generate**
5. **Copy the App Token** (starts with `xapp-`) and save it securely

> **Important**: This token is only shown once. Store it safely!

---

## Step 3: Configure OAuth Scopes

OAuth scopes define what your app can do in Slack.

1. In the left sidebar, click **OAuth & Permissions**
2. Scroll to **Scopes** section
3. Under **Bot Token Scopes**, add these scopes:

| Scope | Description |
|-------|-------------|
| `commands` | Add and manage slash commands |
| `chat:write` | Send messages as the bot |
| `im:history` | View messages in direct messages |
| `im:write` | Send direct messages to users |
| `users:read` | View basic user information |

### Optional Additional Scopes

If you plan to use App Home or advanced features:

| Scope               | Description                       |
| ------------------- | --------------------------------- |
| `app_mentions:read` | Receive @mentions of the bot      |
| `im:read`           | View basic DM info                |
| `channels:history`  | View messages in public channels  |
| `groups:history`    | View messages in private channels |

---

## Step 4: Register Slash Commands

Slash commands let users interact with your bot using `/command` syntax.

1. In the left sidebar, click **Slash Commands**
2. Click **Create New Command** for each command below:

### Required Commands

| Command | Description | Usage Hint |
|---------|-------------|------------|
| `/mpm-create` | Create a new ticket | `[title] --priority [low\|medium\|high] --type [feature\|bug\|task]` |
| `/mpm-list` | List tickets | `[--status open\|in_progress\|done] [--assignee @user]` |
| `/mpm-view` | View ticket details | `[ticket-id]` |
| `/mpm-status` | Update ticket status | `[ticket-id] [open\|in_progress\|done]` |
| `/mpm-update` | Update ticket fields | `[ticket-id] --priority [value] --assignee [@user]` |
| `/mpm-delegate` | Delegate ticket to agent | `[ticket-id] [agent-name]` |

For each command:
1. Click **Create New Command**
2. Enter the command name (e.g., `/mpm-create`)
3. Enter the **Request URL**: Leave blank (Socket Mode handles this)
4. Enter a **Short Description**
5. Enter the **Usage Hint**
6. Click **Save**

> **Note**: With Socket Mode enabled, you don't need to provide a Request URL. The commands are routed through the WebSocket connection.

---

## Step 5: App Home Setup (Optional)

App Home provides a dedicated space for your bot in Slack.

1. In the left sidebar, click **App Home**
2. Under **Show Tabs**, enable:
   - **Home Tab**: Display a dashboard when users visit your app
   - **Messages Tab**: Allow users to send DMs to your bot
3. Optionally check **Allow users to send Slash commands and messages from the messages tab**

---

## Step 6: Events Setup (Optional)

If you want the bot to respond to messages or mentions:

1. In the left sidebar, click **Event Subscriptions**
2. Toggle **Enable Events** to ON
3. Under **Subscribe to bot events**, add:
   - `message.im` - Direct messages to your bot
   - `app_mention` - When someone @mentions your bot
   - `app_home_opened` - When someone opens your App Home

> **Note**: With Socket Mode, you don't need a Request URL for events either.

---

## Step 7: Install to Workspace

1. In the left sidebar, click **Install App**
2. Click **Install to Workspace**
3. Review the permissions and click **Allow**
4. **Copy the Bot User OAuth Token** (starts with `xoxb-`) and save it securely

---

## Step 8: Configure Environment

You have two tokens to configure:

| Token | Prefix | Source |
|-------|--------|--------|
| Bot Token | `xoxb-` | OAuth & Permissions > Bot User OAuth Token |
| App Token | `xapp-` | Basic Information > App-Level Tokens |

### Option A: Use the Setup Script (Recommended)

Run the interactive setup script:

```bash
./scripts/setup-slack-app.sh
```

This will:
- Validate your tokens
- Save them to `.env.local`
- Test the connection

### Option B: Manual Configuration

Create or edit `.env.local` in the project root:

```bash
# Slack Integration
SLACK_BOT_TOKEN=xoxb-your-bot-token-here
SLACK_APP_TOKEN=xapp-your-app-token-here
```

### Option C: Export to Shell

For temporary testing:

```bash
export SLACK_BOT_TOKEN='xoxb-your-bot-token-here'
export SLACK_APP_TOKEN='xapp-your-app-token-here'
```

---

## Step 9: Run the Bot

Start the Slack bot:

```bash
# Load environment variables
source .env.local

# Run the bot
python -m claude_mpm.slack_bot
```

You should see output indicating the bot is connected:

```
[INFO] Slack bot starting...
[INFO] Connected to workspace: Your Workspace Name
[INFO] Bot is ready! Listening for commands...
```

---

## Troubleshooting

### Common Issues

#### "invalid_auth" Error

**Cause**: The Bot Token is invalid or has been revoked.

**Solution**:
1. Go to **OAuth & Permissions** in your app settings
2. Check if the token is still valid
3. If needed, click **Reinstall to Workspace** to generate a new token

#### "missing_scope" Error

**Cause**: The bot is missing required OAuth scopes.

**Solution**:
1. Go to **OAuth & Permissions**
2. Add the missing scope under **Bot Token Scopes**
3. Reinstall the app to apply changes

#### Bot Not Responding to Commands

**Cause**: Socket Mode may not be properly connected.

**Solution**:
1. Verify Socket Mode is enabled in app settings
2. Check that SLACK_APP_TOKEN starts with `xapp-`
3. Look for connection errors in the bot logs

#### "socket_mode_not_enabled" Error

**Cause**: Socket Mode is not enabled for your app.

**Solution**:
1. Go to **Socket Mode** in app settings
2. Toggle **Enable Socket Mode** to ON
3. Generate an App-Level Token if you haven't already

#### Commands Not Appearing in Slack

**Cause**: Slash commands may not be registered, or app needs reinstall.

**Solution**:
1. Verify commands are listed under **Slash Commands**
2. Reinstall the app to your workspace
3. Wait a few minutes for Slack to propagate changes

#### Connection Drops Frequently

**Cause**: Network issues or token problems.

**Solution**:
1. Check your network connection
2. Implement reconnection logic in your bot
3. Verify tokens haven't been revoked

### Testing the Connection

Use the setup script to test your connection:

```bash
./scripts/setup-slack-app.sh --test-only
```

Or manually test with curl:

```bash
curl -X POST https://slack.com/api/auth.test \
  -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
  -H "Content-Type: application/json"
```

A successful response looks like:

```json
{
  "ok": true,
  "url": "https://your-workspace.slack.com/",
  "team": "Your Workspace",
  "user": "claude-mpm",
  "team_id": "T12345678",
  "user_id": "U12345678",
  "bot_id": "B12345678"
}
```

---

## Security Best Practices

1. **Never commit tokens to version control**
   - Add `.env.local` to `.gitignore`
   - Use environment variables in production

2. **Rotate tokens periodically**
   - Regenerate App-Level Tokens if compromised
   - Reinstall app to get new Bot Token

3. **Use minimal scopes**
   - Only request scopes your bot actually needs
   - Review and remove unused scopes

4. **Monitor usage**
   - Check the **Analytics** tab in your app settings
   - Set up alerts for unusual activity

---

## Additional Resources

- [Slack Bolt for Python Documentation](https://slack.dev/bolt-python/)
- [Slack API Documentation](https://api.slack.com/docs)
- [Socket Mode Guide](https://api.slack.com/apis/connections/socket)
- [Slash Commands Guide](https://api.slack.com/interactivity/slash-commands)

---

*Generated for Claude MPM Slack Integration*

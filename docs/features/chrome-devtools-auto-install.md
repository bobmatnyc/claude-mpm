# Chrome DevTools MCP Auto-Installation

## Overview

Claude MPM automatically installs and configures the [chrome-devtools-mcp](https://github.com/anaisbetts/chrome-devtools-mcp) server on startup, providing browser automation capabilities out-of-the-box.

## Features

- **Automatic Installation**: Installs chrome-devtools-mcp on first startup if not already configured
- **Idempotent**: Safe to run multiple times - checks if already configured before installing
- **Non-Blocking**: Installation failures don't prevent claude-mpm from starting
- **Configurable**: Can be disabled via configuration file

## How It Works

On startup, claude-mpm:

1. Checks if `chrome-devtools` is already configured in `~/.claude.json`
2. If not configured, runs: `claude mcp add chrome-devtools -- npx chrome-devtools-mcp@latest`
3. Shows installation progress with visual feedback
4. Continues startup even if installation fails

## Configuration

### Enable/Disable Auto-Installation

Add to your `~/.config/claude-mpm/config.yaml` (or equivalent):

```yaml
chrome_devtools:
  auto_install: true  # default: true
```

To disable auto-installation:

```yaml
chrome_devtools:
  auto_install: false
```

### Environment Variable

You can also use an environment variable:

```bash
export CLAUDE_MPM_CHROME_DEVTOOLS_AUTO_INSTALL=false
```

## Manual Installation

If you prefer to install manually:

```bash
claude mcp add chrome-devtools -- npx chrome-devtools-mcp@latest
```

## Troubleshooting

### Installation Fails

If auto-installation fails, claude-mpm will:
- Log the error to debug logs
- Continue startup normally
- Show "(skipped)" in the startup message

Common causes:
- Claude CLI not found (Claude Code not installed)
- Network issues preventing npx download
- Insufficient permissions

### Verify Installation

Check if chrome-devtools is configured:

```bash
# On macOS/Linux
cat ~/.claude.json | jq '.mcpServers["chrome-devtools"]'
```

You should see output like:

```json
{
  "command": "npx",
  "args": ["chrome-devtools-mcp@latest"]
}
```

### Re-enable After Disabling

If you previously disabled auto-installation but want to enable it:

1. Remove the `chrome_devtools.auto_install: false` from your config
2. Restart claude-mpm
3. The installation will run automatically

## Browser Automation Capabilities

Once installed, chrome-devtools-mcp provides:

- **Page Navigation**: Navigate to URLs, reload pages, go back/forward
- **Element Interaction**: Click, type, hover, drag-and-drop
- **Screenshots**: Capture full page or element screenshots
- **DOM Inspection**: Extract text, attributes, and structure
- **Form Handling**: Fill forms, submit, upload files
- **Network Monitoring**: Track requests, responses, and performance

See the [chrome-devtools-mcp documentation](https://github.com/anaisbetts/chrome-devtools-mcp) for full capabilities.

## Related

- [MCP Server Configuration](../configuration/mcp-servers.md)
- [Startup Hooks](../developer/startup-hooks.md)
- [Configuration Reference](../configuration/reference.md)

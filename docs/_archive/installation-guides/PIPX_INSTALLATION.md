# Installing Claude MPM with pipx

## Standard Installation

```bash
# Basic installation
pipx install claude-mpm

# Configure MCP for pipx users
claude-mpm mcp-pipx-config
```

## Installing with Monitor Support

The monitoring dashboard requires additional Socket.IO dependencies. There are three ways to ensure these are installed:

### Option 1: Install with Monitor Dependencies (Recommended)

```bash
# Install with all monitor dependencies included
pipx install "claude-mpm[monitor]"
```

### Option 2: Inject Dependencies After Installation

If you've already installed claude-mpm, you can add the monitor dependencies:

```bash
# Inject monitor dependencies into existing installation
pipx inject claude-mpm python-socketio aiohttp aiohttp-cors python-engineio aiofiles websockets
```

### Option 3: Automatic Dependency Check

Claude MPM includes a script to check and install missing monitor dependencies:

```bash
# Check and install missing dependencies
python -m claude_mpm.scripts.check_monitor_deps
```

## Verifying Monitor Installation

After installation, verify the monitor works:

```bash
# Start the monitor
claude-mpm --monitor

# Or start the Socket.IO daemon directly
claude-mpm-socketio start

# Check if listening on port 8765
lsof -i :8765
```

## Troubleshooting

### Monitor Not Starting

If you see "Socket.IO Service Status: NOT RUNNING ❌":

1. **Check dependencies are installed:**
   ```bash
   python -c "import socketio, aiohttp; print('✅ Dependencies OK')"
   ```

2. **If missing, inject them:**
   ```bash
   pipx inject claude-mpm python-socketio aiohttp aiohttp-cors python-engineio
   ```

3. **Restart the monitor:**
   ```bash
   claude-mpm --monitor
   ```

### Session Identification Issues

If you see "/ | All Sessions" in the monitor:

1. The Socket.IO server isn't running
2. Follow the steps above to ensure dependencies are installed
3. Make sure port 8765 is not blocked by firewall

### Port Already in Use

If port 8765 is already in use:

```bash
# Find what's using port 8765
lsof -i :8765

# Kill old process if needed
kill <PID>

# Or use a different port
claude-mpm-socketio start --port 8766
```

## Complete Reinstallation

If issues persist, do a complete reinstall:

```bash
# Uninstall existing
pipx uninstall claude-mpm

# Reinstall with monitor support
pipx install "claude-mpm[monitor]"

# Verify installation
claude-mpm --version
claude-mpm --monitor
```

## Why pipx Needs Special Handling

pipx creates isolated virtual environments for each package. This isolation means:

1. **Dependencies may not be automatically included** - pipx installs only the core package by default
2. **Optional dependencies need explicit installation** - The `[monitor]` extra or `pipx inject` is required
3. **Path resolution can be tricky** - Scripts and resources need special handling (fixed in v4.2.20+)

The `[monitor]` optional dependency group ensures all Socket.IO and async web server components are available for the monitoring dashboard to function properly.
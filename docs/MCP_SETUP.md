# MCP Gateway Setup Guide

## Overview

The MCP (Model Context Protocol) Gateway enables Claude Code to interact with the claude-mpm system through a standardized protocol. This guide covers setup, configuration, and troubleshooting for all installation methods.

## Installation Method Detection

Choose the setup instructions based on how you installed claude-mpm:

- **pipx Installation**: `pipx install claude-mpm` (see [pipx Setup](#pipx-installation-setup) below)
- **pip Installation**: `pip install claude-mpm` (see [pip Setup](#pip-installation-setup) below)
- **Source Installation**: Git clone and development setup (see [Source Setup](#source-installation-setup) below)

## pipx Installation Setup

### Automatic Configuration (Recommended)

If you installed via pipx, use the automated configuration command:

```bash
# Configure MCP automatically for pipx installation
claude-mpm mcp-pipx-config

# Alternative: Download and run configuration script
curl -sSL https://raw.githubusercontent.com/Shredmetal/claude-mpm/main/scripts/utilities/configure_mcp_pipx.py | python3
```

This will:
1. Detect your pipx installation
2. Find your Claude Code configuration file  
3. Add the correct MCP server configuration
4. Verify the setup

### Manual pipx Configuration

1. **Find Configuration File**:
   - **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
   - **Linux**: `~/.config/Claude/claude_desktop_config.json`

2. **Add MCP Configuration**:
   ```json
   {
     "mcpServers": {
       "claude-mpm-gateway": {
         "command": "claude-mpm-mcp"
       }
     }
   }
   ```

3. **Restart Claude Code**

### pipx Verification

```bash
# Verify command is available
which claude-mpm-mcp

# Test MCP server
echo '{"jsonrpc":"2.0","method":"initialize","params":{"protocolVersion":"2024-11-01","clientInfo":{"name":"test","version":"1.0"}},"id":1}' | claude-mpm-mcp

# Run diagnostics
claude-mpm doctor --check mcp
```

## pip Installation Setup

### 1. Verify Installation

Run the diagnostics to check your setup:

```bash
# If claude-mpm is in PATH
claude-mpm doctor

# Or run script directly
python3 -m claude_mpm.scripts.mcp_diagnostics
```

### 2. Configure Claude Code

Add to your Claude Code configuration file:

```json
{
  "mcpServers": {
    "claude-mpm-gateway": {
      "command": "claude-mpm-mcp"
    }
  }
}
```

### 3. Restart Claude Code

After configuration changes, restart Claude Code to load the MCP server.

## Source Installation Setup

### 1. Verify Installation

Run the diagnostics script to check your setup:

```bash
python3 scripts/utilities/mcp_diagnostics.py
```

### 2. Configure Claude Code

The MCP server is configured in Claude Code's configuration file:
- **Location**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Configuration**: Use the robust wrapper script

Configuration for source installation:
```json
{
  "mcpServers": {
    "claude-mpm-gateway": {
      "command": "python3",
      "args": [
        "/path/to/claude-mpm/scripts/utilities/mcp_wrapper.py"
      ],
      "cwd": "/path/to/claude-mpm"
    }
  }
}
```

### 3. Restart Claude Code

After configuration changes, restart Claude Code to load the MCP server.

## Architecture

### Components

1. **MCP Wrapper Script** (`scripts/utilities/mcp_wrapper.py`)
   - Robust environment setup
   - Comprehensive error handling
   - Debug logging to stderr
   - Works from any working directory
   - Process monitoring and PID tracking

2. **MCP Server** (`src/claude_mpm/services/mcp_gateway/server/stdio_server.py`)
   - Implements MCP protocol over stdio
   - JSON-RPC communication
   - Tool registration and execution
   - Backward compatibility patches
   
3. **MCP Server Script** (`src/claude_mpm/scripts/mcp_server.py`)
   - Alternative entry point for direct server execution
   - Available as `claude-mpm-mcp` command when installed
   - Used for development and testing

4. **Unified Ticket Tool** (`src/claude_mpm/services/mcp_gateway/tools/unified_ticket_tool.py`)
   - Ticket creation and management
   - Query and update operations
   - Integrated with claude-mpm ticket system

### How It Works

1. Claude Code spawns the MCP server process
2. The wrapper script sets up the Python environment
3. The server communicates via stdin/stdout using JSON-RPC
4. Claude Code can call registered tools through the MCP protocol
5. The server exits cleanly when the connection closes

## Testing

### Test the Wrapper

```bash
# Run the wrapper test
python3 scripts/verification/test_mcp_wrapper.py

# Verify all invocation methods
python3 scripts/verification/verify_mcp_setup.py
```

### Manual Testing

```bash
# Test the wrapper directly (will wait for stdin)
python3 scripts/utilities/mcp_wrapper.py

# Test with a simple request
echo '{"jsonrpc":"2.0","method":"initialize","params":{"protocolVersion":"2024-11-01","clientInfo":{"name":"test","version":"1.0"}},"id":1}' | python3 scripts/utilities/mcp_wrapper.py

# Alternative: Use the installed command (if claude-mpm is installed)
claude-mpm-mcp

# Alternative: Run the server script directly
python3 src/claude_mpm/scripts/mcp_server.py
```

## Troubleshooting

### Common Issues (All Installation Methods)

#### 1. MCP Icon Not Appearing in Claude Code

**Solutions**:
1. Restart Claude Code after configuration changes
2. Check JSON syntax in `claude_desktop_config.json`
3. Verify command availability:
   ```bash
   # For pipx/pip installations
   which claude-mpm-mcp
   
   # For source installation
   python3 /path/to/scripts/utilities/mcp_wrapper.py --version
   ```

#### 2. Server Fails to Start

**Diagnosis**:
```bash
# For all installations
claude-mpm doctor

# For source installation only
python3 scripts/utilities/mcp_diagnostics.py
```

**Common Fixes by Installation Method**:

**pipx Installation**:
```bash
# Check pipx installation
pipx list | grep claude-mpm

# Reinstall if necessary
pipx uninstall claude-mpm
pipx install claude-mpm

# Reconfigure MCP
claude-mpm mcp-pipx-config
```

**pip Installation**:
```bash
# Check installation
pip show claude-mpm

# Reinstall if necessary
pip uninstall claude-mpm
pip install claude-mpm
```

**Source Installation**:
```bash
# Check dependencies
pip install -e .

# Check file permissions
chmod +x scripts/utilities/mcp_wrapper.py

# Verify Python path
cd /path/to/claude-mpm
python3 -c "import claude_mpm; print('OK')"
```

#### 3. Command Not Found Errors

**pipx Users**:
```bash
# If claude-mpm-mcp not found
pipx ensurepath
source ~/.bashrc  # or ~/.zshrc

# Alternative: Use full path
pipx run claude-mpm mcp-pipx-config
```

**pip Users**:
```bash
# Check if command is in PATH
pip show -f claude-mpm | grep claude-mpm-mcp

# Use module execution if command not found
python3 -m claude_mpm mcp
```

#### 4. Configuration File Issues

**Find Configuration File**:
```bash
# macOS
ls -la ~/Library/Application\ Support/Claude/claude_desktop_config.json

# Linux
ls -la ~/.config/Claude/claude_desktop_config.json

# Windows (PowerShell)
ls $env:APPDATA\Claude\claude_desktop_config.json
```

**Validate JSON Syntax**:
```bash
# Using Python (all platforms)
python3 -m json.tool ~/Library/Application\ Support/Claude/claude_desktop_config.json

# Using jq (if installed)
jq . ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

#### 5. Permission Issues

**Source Installation**:
```bash
# Fix script permissions
chmod +x scripts/utilities/mcp_wrapper.py
chmod +x scripts/utilities/mcp_server.py
```

**pipx Installation**:
```bash
# Rare: Fix command permissions
chmod +x $(which claude-mpm-mcp)
```

### Installation-Specific Troubleshooting

#### pipx Troubleshooting

1. **pipx Not Installing Commands**:
   ```bash
   pipx install --force claude-mpm
   pipx ensurepath
   ```

2. **Virtual Environment Issues**:
   ```bash
   pipx uninstall claude-mpm
   pipx install claude-mpm --force
   ```

3. **Multiple Python Versions**:
   ```bash
   pipx install --python python3.11 claude-mpm
   ```

#### pip Troubleshooting

1. **User vs System Installation**:
   ```bash
   # Try user installation
   pip install --user claude-mpm
   
   # Or system installation (with sudo/admin)
   sudo pip install claude-mpm
   ```

2. **PATH Issues**:
   ```bash
   # Check if scripts directory is in PATH
   python3 -m site --user-base
   # Add <user-base>/bin to PATH
   ```

#### Source Installation Troubleshooting

1. **Import Errors**:
   ```bash
   # Ensure you're in project directory
   cd /path/to/claude-mpm
   pip install -e .
   ```

2. **Script Path Issues**:
   ```bash
   # Use absolute paths in configuration
   pwd  # Get current directory
   # Update claude_desktop_config.json with full paths
   ```

### Debug Logging

The MCP wrapper provides detailed debug logging to stderr:

```bash
# View logs when running manually
python3 scripts/utilities/mcp_wrapper.py 2>mcp_debug.log

# In another terminal, watch the logs
tail -f mcp_debug.log
```

Log information includes:
- Environment verification
- Python path setup
- Module import status
- Server startup status
- Runtime errors

### Diagnostic Tools

1. **MCP Diagnostics** (`scripts/mcp_diagnostics.py`)
   - System information
   - Python environment
   - Package installation
   - Configuration check
   - Startup test

2. **Setup Verification** (`scripts/verification/verify_mcp_setup.py`)
   - Tests all invocation methods
   - Verifies file existence
   - Checks Claude Code config
   - Provides test summary

3. **Wrapper Test** (`scripts/verification/test_mcp_wrapper.py`)
   - Tests wrapper functionality
   - Sends test requests
   - Captures stderr output
   - Verifies imports

## Advanced Configuration

### Environment Variables

The MCP server respects these environment variables:

```bash
# Set log level (DEBUG, INFO, WARNING, ERROR)
export MCP_LOG_LEVEL=DEBUG

# Set working directory
export MCP_WORKING_DIR=/path/to/project
```

### Custom Python Executable

To use a specific Python version, modify the Claude Code config:

```json
{
  "mcpServers": {
    "claude-mpm-gateway": {
      "command": "/usr/local/bin/python3.11",
      "args": ["/path/to/mcp_wrapper.py"],
      "cwd": "/path/to/project"
    }
  }
}
```

### Multiple Instances

You can run multiple MCP servers with different configurations:

```json
{
  "mcpServers": {
    "claude-mpm-dev": {
      "command": "python3",
      "args": ["/path/to/dev/mcp_wrapper.py"],
      "cwd": "/path/to/dev/project"
    },
    "claude-mpm-prod": {
      "command": "python3",
      "args": ["/path/to/prod/mcp_wrapper.py"],
      "cwd": "/path/to/prod/project"
    }
  }
}
```

## Development

### Adding New Tools

Tools are registered in the MCP server. To add a new tool:

1. Create tool class in `src/claude_mpm/services/mcp_gateway/tools/`
2. Register in `stdio_server.py`
3. Test with the wrapper script
4. Update Claude Code and restart

### Debugging the Server

1. Add debug statements using `logger.debug()`
2. Run with DEBUG logging: `export MCP_LOG_LEVEL=DEBUG`
3. Check stderr output for debug messages
4. Use the diagnostic scripts for environment issues

## Security Considerations

- The MCP server runs with the permissions of the user
- Input validation is performed on all tool parameters
- Sensitive operations require confirmation
- Logs are written to stderr to avoid protocol interference
- The server exits cleanly when stdin closes

## Performance

The wrapper script includes optimizations for:
- Fast startup with minimal imports
- Efficient error handling
- Clean subprocess management
- Proper resource cleanup

## Support

If you encounter issues:

1. Run `python3 scripts/utilities/mcp_diagnostics.py`
2. Check the troubleshooting section above
3. Review Claude Code's developer console
4. Check the project's issue tracker

## References

- [MCP Specification](https://spec.anthropic.com/mcp)
- [Claude Code Documentation](https://claude.ai/desktop)
- [claude-mpm Documentation](../README.md)
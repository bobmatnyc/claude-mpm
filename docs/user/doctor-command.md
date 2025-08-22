# Claude MPM Doctor Command

The `claude-mpm doctor` command provides comprehensive diagnostics for your Claude MPM installation, helping identify and resolve common issues quickly.

## Overview

The doctor command performs a health check across all major components of your Claude MPM setup:
- Installation integrity
- Configuration validity  
- Claude Desktop integration
- Agent deployments
- MCP server connectivity
- Monitor service status
- File system permissions
- Common issues detection

## Quick Start

```bash
# Basic health check
claude-mpm doctor

# Detailed diagnostics with verbose output
claude-mpm doctor --verbose

# Check specific components only
claude-mpm doctor --checks installation configuration

# Save report to file
claude-mpm doctor --output doctor-report.txt
```

## Command Syntax

```bash
claude-mpm doctor [OPTIONS]
claude-mpm diagnose [OPTIONS]     # alias
claude-mpm check-health [OPTIONS] # alias
```

## Available Options

### Output Control
- `--verbose`, `-v` - Show detailed diagnostic information including internal checks and debug details
- `--json` - Output results in JSON format for programmatic processing
- `--markdown` - Output results in Markdown format for documentation
- `--no-color` - Disable colored output for terminal compatibility
- `--output FILE`, `-o FILE` - Save output to specified file

### Diagnostic Selection
- `--checks CHECKS` - Run only specific check categories. Available options:
  - `installation` - Verify Claude MPM installation and dependencies
  - `configuration` - Check configuration files and settings
  - `filesystem` - Validate directory structure and permissions
  - `claude` - Test Claude Desktop integration
  - `agents` - Check agent deployments and availability
  - `mcp` - Verify MCP server configuration and connectivity
  - `monitor` - Check monitoring service status
  - `common` - Scan for common known issues

### Performance Options
- `--parallel` - Run checks in parallel for faster execution (experimental)

### Remediation (Experimental)
- `--fix` - Attempt to automatically fix detected issues where possible

## Interactive Mode Usage

When using Claude Code in interactive mode, you can run diagnostics using the slash command:

```
/mmp-doctor
/mpm-doctor --verbose
/mpm-doctor --no-color
```

**Differences from CLI version:**
- Interactive mode only supports `--verbose` and `--no-color` flags
- Output is always in terminal format (no JSON/Markdown options)
- Results display with interactive session styling
- Cannot save to file (output only to console)

## Understanding the Output

The doctor command uses a consistent status system:

### Status Indicators
- ✅ **OK**: Component is working correctly, no action needed
- ⚠️ **WARNING**: Non-critical issue detected, may affect functionality
- ❌ **ERROR**: Critical issue requiring immediate attention
- ℹ️ **INFO**: Informational message or recommendation

### Exit Codes
- `0` - All checks passed successfully
- `1` - Warnings found but no critical errors
- `2` - Critical errors detected requiring attention
- `130` - Interrupted by user (Ctrl+C)

### Sample Output

```
================================================================
Claude MPM Doctor Report
================================================================

✅ Installation Check
   ✓ Claude MPM version: 4.0.29
   ✓ Python environment: 3.11.7
   ✓ Dependencies: All required packages installed

⚠️ Configuration Check  
   ✓ Config file exists: ~/.claude-mpm/config.yaml
   ⚠ Claude Desktop config: Missing MCP server configuration
   
❌ Agent Check
   ✗ Deployed agents: 0 agents found
   ✗ Agent directory: /Users/user/.claude/agents missing

ℹ️ Recommendations:
   • Run 'claude-mpm agents deploy' to install system agents
   • Update Claude Desktop configuration with MCP server
   • Check filesystem permissions for agent directory

Summary: 1 error, 1 warning found
```

## Common Issues and Fixes

### No Agents Deployed
**Issue**: Doctor reports "0 agents deployed" or missing agent directory

**Symptoms**:
```
❌ Agent Check
   ✗ Deployed agents: 0 agents found
   ✗ Agent directory: /Users/user/.claude/agents missing
```

**Fix**:
```bash
# Deploy all system agents
claude-mpm agents deploy

# Verify deployment
claude-mpm agents list --deployed
```

### Claude Desktop Integration Missing
**Issue**: Claude Desktop not configured for MCP integration

**Symptoms**:
```
⚠️ Claude Desktop Check
   ⚠ MCP configuration: Not found in Claude Desktop settings
   ⚠ Server registration: claude-mpm-mcp not configured
```

**Fix**:
1. Check if MCP server is installed:
   ```bash
   claude-mpm mcp status
   ```
2. Install/configure MCP server:
   ```bash
   claude-mpm mcp install
   ```
3. Restart Claude Desktop application

### Permission Issues
**Issue**: Doctor reports file system permission errors

**Symptoms**:
```
❌ Filesystem Check
   ✗ Agent directory: Permission denied
   ✗ Config directory: Cannot write to ~/.claude-mpm/
```

**Fix**:
```bash
# Fix directory permissions
chmod 755 ~/.claude-mpm/
chmod 755 ~/.claude/agents/

# Or recreate with correct permissions
claude-mpm config init --force
```

### Configuration File Issues
**Issue**: Invalid or missing configuration files

**Symptoms**:
```
❌ Configuration Check
   ✗ Config file: Invalid YAML syntax
   ✗ Required settings: Missing API key configuration
```

**Fix**:
```bash
# Reset configuration to defaults
claude-mpm config reset

# Validate configuration
claude-mpm config validate

# Edit configuration
claude-mpm config edit
```

### Monitor Service Issues
**Issue**: Background monitoring service not running

**Symptoms**:
```
⚠️ Monitor Check
   ⚠ Service status: Not running
   ⚠ WebSocket port: 8765 not available
```

**Fix**:
```bash
# Start monitoring service
claude-mpm monitor start

# Check service status
claude-mpm monitor status

# Restart if needed
claude-mpm monitor restart
```

### Installation Corruption
**Issue**: Claude MPM installation appears corrupted

**Symptoms**:
```
❌ Installation Check
   ✗ Core modules: Import errors detected
   ✗ Dependencies: Version conflicts found
```

**Fix**:
```bash
# Reinstall Claude MPM
pip uninstall claude-mpm
pip install claude-mpm

# Or upgrade to latest version
pip install --upgrade claude-mpm

# Verify installation
claude-mpm doctor
```

## Advanced Usage

### JSON Output for Automation
Use JSON format for automated processing or integration with other tools:

```bash
# Generate JSON report
claude-mpm doctor --json > health-report.json

# Process with jq
claude-mpm doctor --json | jq '.checks[] | select(.status == "error")'
```

### Selective Diagnostics
Run only specific checks for targeted troubleshooting:

```bash
# Check only agent-related issues
claude-mpm doctor --checks agents

# Multiple specific checks
claude-mpm doctor --checks installation configuration claude

# All except time-consuming checks
claude-mpm doctor --checks installation configuration filesystem agents
```

### Automated Fixing
**⚠️ Experimental Feature**: Attempt automatic remediation

```bash
# Try to fix issues automatically
claude-mpm doctor --fix

# Combine with verbose output to see what's being fixed
claude-mpm doctor --fix --verbose
```

## When to Use Doctor

### Regular Health Checks
- After installing or upgrading Claude MPM
- Before starting important projects
- When experiencing unexpected behavior
- As part of troubleshooting workflow

### Specific Scenarios
- **Installation issues**: Run doctor after fresh install
- **Agent problems**: Check why agents aren't working
- **Claude Desktop integration**: Verify MCP setup
- **Performance issues**: Identify configuration problems
- **Error diagnosis**: Get detailed error information

### Integration with Support
When reporting issues:
1. Run `claude-mpm doctor --verbose`
2. Save output: `claude-mpm doctor --verbose --output doctor-report.txt`
3. Include the report with your support request

## Tips and Best Practices

### Regular Maintenance
```bash
# Weekly health check
claude-mpm doctor

# Monthly detailed check with cleanup
claude-mpm doctor --verbose
claude-mpm cleanup
```

### Performance Optimization
```bash
# Fast check for CI/CD
claude-mpm doctor --checks installation configuration --no-color

# Parallel execution for multiple checks
claude-mpm doctor --parallel
```

### Troubleshooting Workflow
1. **Initial diagnosis**: `claude-mpm doctor`
2. **Detailed analysis**: `claude-mpm doctor --verbose`
3. **Targeted checks**: `claude-mpm doctor --checks <specific-area>`
4. **Attempt fixes**: `claude-mpm doctor --fix`
5. **Verify resolution**: `claude-mpm doctor`

## Related Commands

- `claude-mpm agents list` - List available and deployed agents
- `claude-mpm config validate` - Validate configuration files
- `claude-mpm mcp status` - Check MCP server status
- `claude-mpm monitor status` - Check monitoring service
- `claude-mpm cleanup` - Clean up temporary files and caches

## See Also

- [CLI Commands Reference](./04-reference/cli-commands.md) - Complete CLI reference
- [Troubleshooting Guide](./troubleshooting.md) - General troubleshooting
- [Agent Management](./02-guides/agent-management.md) - Agent deployment and management
- [Configuration Guide](./02-guides/configuration.md) - Configuration management
# Troubleshooting Guide

Solutions to common issues and problems with Claude MPM.

**Last Updated**: 2025-09-28
**Version**: 4.4.x

## Quick Diagnostics

**Start with the doctor command for comprehensive health checks:**

```bash
# Run comprehensive diagnostics
claude-mpm doctor

# Get detailed diagnostic information
claude-mpm doctor --verbose

# Focus on specific areas
claude-mpm doctor --checks installation configuration agents
```

**Traditional diagnostic commands:**
```bash
# Check system status
claude-mpm info

# Check version
claude-mpm --version

# Verify installation
claude-mpm run -i "test" --non-interactive
```

## Using Doctor Command for Troubleshooting

The `claude-mpm doctor` command is your first line of defense for diagnosing issues. It performs comprehensive health checks across all components:

### Understanding Doctor Output

The doctor command provides clear status indicators:
- ✅ **OK**: Component working correctly
- ⚠️ **WARNING**: Non-critical issue, may affect functionality  
- ❌ **ERROR**: Critical issue requiring immediate attention
- ℹ️ **INFO**: Recommendation or informational message

### Common Doctor Findings

**Agent Deployment Issues:**
```
❌ Agent Check
   ✗ Deployed agents: 0 agents found
   
Fix: claude-mpm agents deploy
```

**Configuration Problems:**
```
⚠️ Configuration Check
   ⚠ Claude Code config: MCP server not configured
   
Fix: claude-mpm mcp install
```

**Permission Errors:**
```
❌ Filesystem Check
   ✗ Agent directory: Permission denied
   
Fix: chmod 755 ~/.claude/agents/
```

### Automated Diagnosis Workflow

1. **Initial health check**: `claude-mpm doctor`
2. **Detailed analysis**: `claude-mpm doctor --verbose` 
3. **Targeted diagnosis**: `claude-mpm doctor --checks <specific-area>`
4. **Automatic fixes**: `claude-mpm doctor --fix` (experimental)
5. **Verify resolution**: `claude-mpm doctor`

For complete doctor command documentation, see the [Doctor Command Guide](./doctor-command.md).

## Installation Issues

### Permission Errors
```bash
# Use user installation
pip install --user claude-mpm

# Or use virtual environment (recommended)
python -m venv claude-mpm-env
source claude-mpm-env/bin/activate
pip install claude-mpm
```

### Python Version Issues
```bash
# Check Python version (requires 3.8+)
python --version

# Use specific Python version
python3.9 -m pip install claude-mpm

# Update pip if needed
pip install --upgrade pip
```

### Network/Proxy Issues
```bash
# Use different PyPI index
pip install -i https://pypi.org/simple/ claude-mpm

# With proxy
pip install --proxy http://proxy.example.com:8080 claude-mpm

# Skip certificate verification (not recommended)
pip install --trusted-host pypi.org claude-mpm
```

### Pipx Installation Issues (RESOLVED ✅)

**As of v4.1.14, all pipx issues have been resolved!** The following problems no longer occur:

**Previously Reported Issue 1: Socket.IO Daemon Script Not Found**
```
Error: socketio_daemon_wrapper.py not found in pipx environment
```
✅ **Fixed**: Implemented proper resource path resolution using `get_package_resource_path()`

**Previously Reported Issue 2: Commands Directory Access**
```
Error: Cannot access commands directory in pipx installation
```
✅ **Fixed**: Enhanced path detection with `importlib.resources` fallback mechanism

**If You Still Encounter Pipx Issues:**
```bash
# Verify pipx installation
pipx --version

# Check claude-mpm installation
pipx list | grep claude-mpm

# Reinstall if needed
pipx uninstall claude-mpm
pipx install claude-mpm

# Verify resource access
claude-mpm doctor --checks installation

# Test basic functionality
claude-mpm info
```

**Technical Details:**
- Resource files now properly packaged with `importlib.resources`
- Cross-platform compatibility for Windows, macOS, Linux
- Python 3.13+ fully supported in pipx environments
- Automatic fallback to filesystem paths when resources API unavailable

## Runtime Issues

### Agent Not Found
```bash
# List available agents
claude-mpm agents list

# Check agent configuration
claude-mpm agents view engineer

# Fix configuration issues
claude-mpm agents fix --all --dry-run
claude-mpm agents fix --all
```

### Session Problems

**Session Won't Resume**
```bash
# Use full session ID
claude-mpm run --resume <full-session-id>

# List available sessions
claude-mpm sessions list

# Check working directory exists
ls -la .claude-mpm/sessions/
```

**Session Directory Issues**
```bash
# Check session directory permissions
ls -la .claude-mpm/

# Recreate session directory
mkdir -p .claude-mpm/sessions
chmod 755 .claude-mpm/sessions
```

### Memory System Issues

**Memory Not Initializing**
```bash
# Force reinitialize
claude-mpm memory init --force

# Check memory status
claude-mpm memory status

# Verify memory directory
ls -la .claude-mpm/memory/
```

**Corrupted Memory Files**
```bash
# Clear and reinitialize
claude-mpm memory clear
claude-mpm memory init

# Or manually remove
rm -rf .claude-mpm/memory/
claude-mpm memory init
```

**Memory Search Not Working**
```bash
# Rebuild search index
claude-mpm memory optimize

# Check memory file format
cat .claude-mpm/memory/engineer_memory.json | jq .
```

## Dashboard and Monitoring Issues

### Connection Problems
```bash
# Check port availability
netstat -an | grep 8765

# Use different port
claude-mpm run --monitor --websocket-port 8766

# Check firewall settings
sudo ufw status
```

### Dashboard Won't Load
```bash
# Check browser console for errors
# Try different browser
# Clear browser cache

# Check server logs
tail -f .claude-mpm/logs/socketio.log
```

### WebSocket Issues
```bash
# Test WebSocket connection
curl -i -N -H "Connection: Upgrade" \
     -H "Upgrade: websocket" \
     -H "Sec-WebSocket-Key: SGVsbG8sIHdvcmxkIQ==" \
     -H "Sec-WebSocket-Version: 13" \
     http://localhost:8765/socket.io/

# Check for proxy interference
# Disable browser extensions
# Try different network
```

## Git Integration Issues

### Git Diff Not Working
```bash
# Ensure you're in a git repository
git status

# Check git configuration
git config --list

# Verify file is tracked
git ls-files | grep filename
```

### Git Branch Issues
```bash
# Check current branch
git branch

# Verify remote tracking
git branch -vv

# Update branch information
git fetch --all
```

### Hook System Issues

**Orphaned Hook Processes**
```bash
# Check for orphaned processes
ps aux | grep hook_handler.py | grep -v grep | wc -l

# Clean up orphaned processes
python scripts/cleanup_orphaned_hooks.py
```

**Hook Handler Timeouts**
```bash
# Hook handlers now have automatic 10-second timeouts
# Check logs for timeout messages
tail -f ~/.claude-mpm/logs/hooks.log | grep timeout
```

**Socket.IO Connection Issues**
```bash
# Check if Socket.IO server is running
netstat -an | grep 8765

# Restart hook system
claude-mpm hooks restart
```

For detailed hook system troubleshooting, see [Hook System Troubleshooting](troubleshooting/hook-system.md).

## MCP Service Issues

Claude MPM includes several optional MCP (Model Context Protocol) services that enhance functionality. Use the `verify` command for comprehensive MCP service diagnostics.

### Quick MCP Diagnostics

```bash
# Verify all MCP services
claude-mpm verify

# Auto-fix detected issues
claude-mpm verify --fix

# Verify specific service
claude-mpm verify --service kuzu-memory

# Get detailed JSON output
claude-mpm verify --json
```

### Common MCP Service Problems

**Service Not Found:**
```bash
# Check if service is installed
claude-mpm verify --service mcp-vector-search

# Auto-install missing service
claude-mpm verify --service mcp-vector-search --fix

# Manual installation via pipx
pipx install mcp-vector-search
```

**Configuration Issues:**
```bash
# Check MCP configuration
claude-mpm doctor --checks mcp --verbose

# Verify service commands
claude-mpm verify --json | jq '.["service-name"].configured_command'

# Fix configuration automatically
claude-mpm verify --fix
```

**Service Won't Start:**
```bash
# Check service-specific diagnostics
claude-mpm verify --service kuzu-memory --json

# Review startup logs
tail -f .claude-mpm/logs/claude-mpm.log | grep -i mcp

# Test service manually (example for kuzu-memory)
python -m kuzu_memory.server --help
```

### Specific Service Troubleshooting

**kuzu-memory (Knowledge Graph Memory):**
```bash
# Verify knowledge graph database
claude-mpm verify --service kuzu-memory

# Check memory directory permissions
ls -la .claude-mpm/kuzu-memories/

# Reset memory database if corrupted
rm -rf .claude-mpm/kuzu-memories/
claude-mpm memory init
```

**mcp-vector-search (Code Search):**
```bash
# Verify search index
claude-mpm verify --service mcp-vector-search

# Rebuild search index
python -c "import mcp_vector_search; mcp_vector_search.rebuild_index()"

# Check embedding model availability
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"
```

**mcp-browser (Browser Automation):**
```bash
# Check browser dependencies
claude-mpm verify --service mcp-browser

# Verify Playwright installation
python -c "from playwright.sync_api import sync_playwright; print('Playwright OK')"

# Install browser binaries if missing
playwright install chromium
```

**mcp-ticketer (Ticket Management):**
```bash
# Verify ticket service
claude-mpm verify --service mcp-ticketer

# Check ticket database
ls -la .claude-mpm/tickets/

# Reset ticket database
rm -f .claude-mpm/tickets/tickets.db
```

### Startup Verification Warnings

Claude MPM automatically checks MCP services on startup. Common warnings:

**"MCP service 'service-name' not available":**
- Service is not installed or not in PATH
- Run `claude-mpm verify --service service-name --fix` to auto-install

**"MCP service 'service-name' configuration invalid":**
- Service command or path is incorrect
- Run `claude-mpm verify --fix` to repair configuration

**"Startup verification timed out":**
- Service is installed but takes too long to respond
- Check service logs and system resources

### Advanced MCP Debugging

**Enable MCP debug logging:**
```bash
export CLAUDE_MPM_MCP_DEBUG=true
claude-mpm run --debug
```

**Check MCP Gateway status:**
```bash
# Verify MCP Gateway is running
curl -s http://localhost:8765/health | jq '.'

# Check registered services
curl -s http://localhost:8765/services | jq '.'

# Monitor MCP traffic
tail -f .claude-mpm/logs/mcp-gateway.log
```

**Manual service testing:**
```bash
# Test service directly (example)
echo '{"method": "list_tools", "params": {}}' | \
  python -m kuzu_memory.server

# Verify service binary
which kuzu-memory-server || echo "Service not in PATH"

# Check service installation
pipx list | grep -E "(kuzu-memory|mcp-vector-search|mcp-browser|mcp-ticketer)"
```

### MCP Service Recovery

**Complete MCP reset:**
```bash
# Reinstall all MCP services
pipx uninstall kuzu-memory mcp-vector-search mcp-browser mcp-ticketer
claude-mpm verify --fix

# Reset MCP configuration
rm -f ~/.claude-mpm/mcp-config.json
claude-mpm mcp install

# Verify everything works
claude-mpm verify
```

For detailed MCP integration information, see [MCP Gateway Documentation](../developer/13-mcp-gateway/README.md).

## Performance Issues

### Slow Startup
```bash
# Check for large memory files
du -sh .claude-mpm/memory/

# Clear unnecessary memories
claude-mpm memory optimize

# Use minimal agent set
export CLAUDE_MPM_MINIMAL_AGENTS=true
```

### High Memory Usage
```bash
# Check process memory
ps aux | grep claude-mpm

# Monitor system resources
top -p $(pgrep -f claude-mpm)

# Reduce cache size in configuration
```

### Slow Agent Response
```bash
# Check network connectivity
ping api.anthropic.com

# Verify API quota
claude-mpm info

# Check for rate limiting
```

## Configuration Issues

### Invalid Configuration
```bash
# Validate configuration
claude-mpm config validate

# Show current configuration
claude-mpm config show

# Reset to defaults
claude-mpm config reset
```

### Agent Configuration Problems
```bash
# Check agent format
claude-mpm agents validate

# Fix common issues
claude-mpm agents fix --all

# Show agent precedence
claude-mpm agents list --by-tier
```

## Logging and Debugging

### Enable Debug Logging
```bash
# Set debug level
export CLAUDE_MPM_LOG_LEVEL=DEBUG

# Run with verbose output
claude-mpm --verbose run
```

### Check Log Files
```bash
# View recent logs
tail -f .claude-mpm/logs/claude-mpm.log

# Search for errors
grep ERROR .claude-mpm/logs/*.log

# View session logs
ls -la .claude-mpm/logs/sessions/
```

### Debug Specific Components
```bash
# Debug agent loading
export CLAUDE_MPM_DEBUG_AGENTS=true

# Debug memory system
export CLAUDE_MPM_DEBUG_MEMORY=true

# Debug WebSocket connections
export CLAUDE_MPM_DEBUG_WEBSOCKET=true
```

## Common Error Messages

### "Module not found"
```bash
# Reinstall package
pip uninstall claude-mpm
pip install claude-mpm

# Check PYTHONPATH
echo $PYTHONPATH

# Install in development mode
pip install -e .
```

### "Permission denied"
```bash
# Check file permissions
ls -la .claude-mpm/

# Fix permissions
chmod -R 755 .claude-mpm/

# Use sudo if needed (not recommended)
sudo chown -R $USER:$USER .claude-mpm/
```

### "Port already in use"
```bash
# Find process using port
lsof -i :8765

# Kill process
kill -9 <PID>

# Use different port
claude-mpm run --monitor --websocket-port 8766
```

### "API quota exceeded"
```bash
# Check current usage
claude-mpm info

# Wait for quota reset
# Upgrade API plan if needed
```

## Environment-Specific Issues

### WSL/Windows Issues
```bash
# Use Windows paths
export CLAUDE_MPM_CONFIG_PATH="C:\Users\username\.claude-mpm"

# Fix line ending issues
git config --global core.autocrlf true

# Use Windows binaries
pip install --force-reinstall claude-mpm
```

### macOS Issues
```bash
# Install XCode command line tools
xcode-select --install

# Use Homebrew Python
brew install python

# Fix SSL certificate issues
/Applications/Python\ 3.x/Install\ Certificates.command
```

### Docker Issues
```bash
# Check Docker daemon
docker ps

# Pull latest image
docker pull claude-mpm:latest

# Check container logs
docker logs claude-mpm-container

# Mount volumes correctly
docker run -v $(pwd):/workspace claude-mpm
```

## Getting Help

### Gather Information
```bash
# System information
claude-mpm info > system_info.txt

# Configuration dump
claude-mpm config show > config_dump.txt

# Recent logs
tail -100 .claude-mpm/logs/claude-mpm.log > recent_logs.txt
```

### Report Issues
1. Check [existing issues](https://github.com/bobmatnyc/claude-mpm/issues)
2. Gather system information using commands above
3. Create detailed issue report with:
   - System information
   - Steps to reproduce
   - Expected vs actual behavior
   - Relevant log output

### Community Support
- **GitHub Discussions**: [General questions and help](https://github.com/bobmatnyc/claude-mpm/discussions)
- **Issues**: [Bug reports and feature requests](https://github.com/bobmatnyc/claude-mpm/issues)
- **Documentation**: [Complete documentation](../../README.md)

### Emergency Recovery
```bash
# Nuclear option - complete reset
rm -rf .claude-mpm/
claude-mpm memory init
claude-mpm agents fix --all
```

## Prevention Tips

1. **Use Virtual Environments**: Avoid dependency conflicts
2. **Regular Updates**: Keep Claude MPM updated
3. **Backup Configurations**: Version control your `.claude-mpm/` directory
4. **Monitor Resources**: Watch memory and disk usage
5. **Validate Configuration**: Run validation checks regularly

## Next Steps

- **Basic Usage**: [basic-usage.md](basic-usage.md)
- **Configuration**: [../reference/configuration.md](../reference/configuration.md)
- **Development**: [../../developer/README.md](../../developer/README.md)
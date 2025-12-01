# Troubleshooting Guide

Solutions to common issues with Claude MPM. For user-specific troubleshooting, see [user/troubleshooting.md](user/troubleshooting.md).

## Quick Diagnostics

```bash
# Run comprehensive diagnostics
claude-mpm doctor

# Verbose output with detailed information
claude-mpm doctor --verbose

# Generate diagnostic report
claude-mpm doctor --verbose --output-file doctor-report.md

# Check specific components
claude-mpm doctor --checks installation configuration agents mcp

# Verify MCP services
claude-mpm verify

# Auto-fix MCP issues
claude-mpm verify --fix
```

## Common Issues

### Installation Problems

#### Claude Code Not Found

**Symptom**: Error: "Claude Code CLI not found"

**Solution**:
```bash
# Install Claude Code CLI
# https://docs.anthropic.com/en/docs/claude-code

# Verify installation
claude --version

# Should show v1.0.92 or higher
```

#### Wrong Python Version

**Symptom**: Error: "Python 3.8+ required"

**Solution**:
```bash
# Check Python version
python --version

# Install Python 3.11+ (recommended)
# https://www.python.org/downloads/

# Or use pyenv
pyenv install 3.11.0
pyenv global 3.11.0
```

#### Permission Errors

**Symptom**: Error: "Permission denied" during installation

**Solution**:
```bash
# Use pipx (recommended)
pipx install "claude-mpm[monitor]"

# Or install in user directory
pip install --user "claude-mpm[monitor]"

# Avoid sudo with pip (not recommended)
```

### Runtime Issues

#### MPM Won't Start

**Symptom**: `claude-mpm` command fails or hangs

**Diagnostic**:
```bash
# Check installation
which claude-mpm

# Check for errors
claude-mpm --version

# Run diagnostics
claude-mpm doctor --verbose
```

**Solutions**:
1. Reinstall: `pipx reinstall claude-mpm`
2. Clear cache: `rm -rf ~/.claude-mpm/cache/`
3. Check logs: `tail -f ~/.claude-mpm/logs/mpm.log`

#### Configuration Errors

**Symptom**: Error: "Invalid configuration"

**Solution**:
```bash
# Validate configuration
claude-mpm doctor --checks configuration

# Reset to defaults
mv ~/.claude-mpm/configuration.yaml ~/.claude-mpm/configuration.yaml.bak
claude-mpm configure

# Check YAML syntax
python -m yaml ~/.claude-mpm/configuration.yaml
```

#### Agent Not Found

**Symptom**: Error: "Agent 'name' not found"

**Diagnostic**:
```bash
# List available agents
claude-mpm doctor --checks agents

# Check agent directories
ls -la ~/.claude-agents/
ls -la .claude-mpm/agents/
```

**Solution**:
1. Verify agent file exists
2. Check agent frontmatter syntax
3. Ensure proper naming (`name.md`)
4. Run `claude-mpm doctor --checks agents`

### MCP Service Issues

#### MCP Service Not Found

**Symptom**: Error: "MCP service 'name' not available"

**Solution**:
```bash
# Verify MCP services
claude-mpm verify

# Check service status
claude-mpm verify --service kuzu-memory

# Auto-fix issues
claude-mpm verify --fix

# Install missing service
pipx install kuzu-memory
```

#### MCP Gateway Errors

**Symptom**: MCP gateway fails to start

**Diagnostic**:
```bash
# Check MCP configuration
claude-mpm doctor --checks mcp

# Verify JSON output
claude-mpm verify --json
```

**Solution**:
1. Restart MCP gateway: `claude-mpm mcp`
2. Check service logs
3. Verify service installation
4. Run `claude-mpm verify --fix`

### Instruction Cache Issues

#### Problem: Deployment fails with "Argument list too long"

**Symptom**: `OSError: [Errno E2BIG] Argument list too long`

**Cause**: Instruction caching not working, falling back to inline instructions that exceed ARG_MAX

**Solution**:

1. Check if cache exists:
```bash
ls -lh .claude-mpm/PM_INSTRUCTIONS.md*
```

2. If missing, ensure directory permissions:
```bash
mkdir -p .claude-mpm
chmod 755 .claude-mpm
```

3. Regenerate cache:
```bash
rm -f .claude-mpm/PM_INSTRUCTIONS.md*
claude-mpm agents deploy research
```

4. Verify cache was created:
```bash
cat .claude-mpm/PM_INSTRUCTIONS.md.meta | jq .
```

**Prevention**: Instruction caching should happen automatically. If this error occurs, file a bug report.

#### Cache Not Updating

**Symptom**: Changes to PM instructions not reflected in cached file

**Diagnostic**:
```bash
# Check current cache metadata
cat .claude-mpm/PM_INSTRUCTIONS.md.meta | jq .

# Check cache timestamp
cat .claude-mpm/PM_INSTRUCTIONS.md.meta | jq .cached_at
```

**Solution**:
```bash
# Force regenerate cache
rm -f .claude-mpm/PM_INSTRUCTIONS.md*
claude-mpm agents deploy research

# Verify new cache created
cat .claude-mpm/PM_INSTRUCTIONS.md.meta | jq .cached_at
cat .claude-mpm/PM_INSTRUCTIONS.md.meta | jq .content_hash
```

#### Cache Permission Errors

**Symptom**: `PermissionError` when creating or updating cache

**Solution**:
```bash
# Check directory permissions
ls -ld .claude-mpm

# Fix permissions
chmod 755 .claude-mpm
chmod 644 .claude-mpm/PM_INSTRUCTIONS.md*

# Check ownership
ls -l .claude-mpm/

# If owned by another user, change ownership
sudo chown -R $USER:$USER .claude-mpm/
```

### Memory Issues

#### High Memory Usage

**Symptom**: Claude MPM consuming excessive memory (>2GB)

**Solution**:
```bash
# Clean up conversation history
claude-mpm cleanup-memory

# Keep only recent (7 days)
claude-mpm cleanup-memory --days 7

# Check memory usage
ps aux | grep claude-mpm
```

#### Memory Leaks

**Symptom**: Memory usage grows over time

**Solution**:
1. Update to latest version: `pipx upgrade claude-mpm`
2. Clear caches: `rm -rf ~/.claude-mpm/cache/`
3. Restart session: Stop and start Claude MPM
4. Report issue if persistent

### Session Issues

#### Session Won't Resume

**Symptom**: `--resume` flag doesn't work

**Diagnostic**:
```bash
# Check session files
ls -la .claude-mpm/sessions/

# Verify session data
cat .claude-mpm/sessions/latest.json
```

**Solution**:
1. Check session file exists
2. Verify JSON syntax
3. Check permissions
4. Start new session if corrupted

#### Auto-Save Not Working

**Symptom**: Session not saving automatically

**Diagnostic**:
```bash
# Check configuration
grep auto_save ~/.claude-mpm/configuration.yaml
```

**Solution**:
```yaml
# Enable auto-save in configuration.yaml
session:
  auto_save:
    enabled: true
    interval: 300  # 5 minutes
```

### Monitoring Issues

#### Dashboard Won't Start

**Symptom**: Monitoring dashboard not accessible

**Diagnostic**:
```bash
# Check port availability
lsof -i :5000

# Check logs
tail -f ~/.claude-mpm/logs/mpm.log
```

**Solution**:
```bash
# Try different port
claude-mpm run --monitor --port 5001

# Check firewall
sudo ufw allow 5000

# Verify monitoring enabled
grep monitoring ~/.claude-mpm/configuration.yaml
```

#### WebSocket Connection Failed

**Symptom**: Dashboard shows "Disconnected"

**Solution**:
1. Check WebSocket enabled in config
2. Verify network connectivity
3. Check browser console for errors
4. Try different browser

### Performance Issues

#### Slow Startup

**Symptom**: Claude MPM takes >10 seconds to start

**Solution**:
1. Update to v4.8.2+ (91% latency reduction)
2. Disable unused agents in configuration
3. Clear agent cache: `rm -rf ~/.claude-mpm/cache/agents/`
4. Check network connectivity (MCP gateway)

#### High Latency

**Symptom**: Agent responses slow

**Diagnostic**:
```bash
# Check performance
claude-mpm doctor --checks performance

# Monitor metrics
claude-mpm run --monitor
```

**Solution**:
1. Reduce monitoring frequency
2. Disable verbose logging
3. Check network latency
4. Optimize agent count

### Update Issues

#### Update Check Fails

**Symptom**: Error checking for updates

**Solution**:
```bash
# Manually check version
claude-mpm --version

# Check PyPI manually
pip index versions claude-mpm

# Disable update checks
# In configuration.yaml:
updates:
  check_on_startup: false
```

#### Upgrade Fails

**Symptom**: `pipx upgrade` or `pip install --upgrade` fails

**Solution**:
```bash
# Using pipx
pipx uninstall claude-mpm
pipx install "claude-mpm[monitor]"

# Using pip
pip uninstall claude-mpm
pip install "claude-mpm[monitor]"

# Clear pip cache
pip cache purge
```

## Platform-Specific Issues

### macOS

#### Homebrew Installation Issues

**Symptom**: `brew install` fails

**Solution**:
```bash
# Update Homebrew
brew update

# Try tap directly
brew tap bobmatnyc/tools
brew install claude-mpm

# Or use PyPI
pipx install "claude-mpm[monitor]"
```

### Linux

#### Missing Dependencies

**Symptom**: Import errors for system libraries

**Solution**:
```bash
# Ubuntu/Debian
sudo apt-get install python3-dev

# RHEL/CentOS
sudo yum install python3-devel

# Arch
sudo pacman -S python
```

### Windows

#### Path Issues

**Symptom**: `claude-mpm` not found after installation

**Solution**:
1. Add Python Scripts to PATH
2. Use full path: `python -m claude_mpm`
3. Reinstall with `--user` flag

## Getting Help

### Diagnostic Report

Generate comprehensive diagnostic report:

```bash
claude-mpm doctor --verbose --output-file doctor-report.md
```

Include this report when seeking help.

### Check Logs

```bash
# Main log
tail -f ~/.claude-mpm/logs/mpm.log

# Agent logs
tail -f ~/.claude-mpm/logs/agents.log

# MCP logs
tail -f ~/.claude-mpm/logs/mcp.log
```

### Community Support

1. **GitHub Issues**: https://github.com/bobmatnyc/claude-mpm/issues
2. **Documentation**: [docs/README.md](README.md)
3. **FAQ**: [guides/FAQ.md](guides/FAQ.md)
4. **User Guide**: [user/user-guide.md](user/user-guide.md)

## Debugging Tips

### Enable Debug Logging

```yaml
# In configuration.yaml
logging:
  level: DEBUG
  file: ~/.claude-mpm/logs/debug.log
```

### Verbose Mode

```bash
# Run with verbose output
claude-mpm run --verbose

# Doctor with verbose
claude-mpm doctor --verbose
```

### Isolated Testing

```bash
# Test in clean environment
pipx run claude-mpm --version

# Test specific component
python -m claude_mpm.services.agents
```

## See Also

- **[User Troubleshooting](user/troubleshooting.md)** - End-user issues
- **[FAQ](guides/FAQ.md)** - Frequently asked questions
- **[Configuration](configuration.md)** - Configuration options
- **[Installation](user/installation.md)** - Installation guide
- **[User Guide](user/user-guide.md)** - Complete user documentation

---

**For user-specific troubleshooting**: See [user/troubleshooting.md](user/troubleshooting.md)

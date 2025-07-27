# Security Configuration Guide

## Overview

The file security feature in Claude MPM is designed to be zero-configuration for most users. It's automatically enabled and protects your system without requiring any setup. This guide covers the security configuration for advanced users who need to understand or modify the default behavior.

## Default Configuration

By default, the file security hook is:

- **Enabled**: Automatically active for all Claude MPM sessions
- **Working Directory**: Set to the directory where you run `claude-mpm`
- **Scope**: Applies to all agents and operations
- **Logging**: Security events logged to `.claude-mpm/logs/`

## Working Directory Detection

The security system automatically detects your working directory from:

1. **Current Working Directory (CWD)**: Where you execute `claude-mpm`
2. **Claude Code Context**: The `cwd` field in hook events
3. **Project Root**: Resolved from the execution context

### Example Working Directory Detection
```bash
# Terminal location when running claude-mpm
cd /Users/you/myproject
./claude-mpm

# Working directory is set to: /Users/you/myproject
# All file writes must be within this directory
```

## Security Policies

### Write Operation Policy

| Operation | Within Working Dir | Outside Working Dir |
|-----------|-------------------|-------------------|
| Write     | ✅ Allowed        | ❌ Blocked        |
| Edit      | ✅ Allowed        | ❌ Blocked        |
| MultiEdit | ✅ Allowed        | ❌ Blocked        |
| NotebookEdit | ✅ Allowed     | ❌ Blocked        |

### Read Operation Policy

| Operation | Within Working Dir | Outside Working Dir |
|-----------|-------------------|-------------------|
| Read      | ✅ Allowed        | ✅ Allowed        |
| Grep      | ✅ Allowed        | ✅ Allowed        |
| LS        | ✅ Allowed        | ✅ Allowed        |
| Glob      | ✅ Allowed        | ✅ Allowed        |

### Path Validation Policy

| Path Type | Example | Policy |
|-----------|---------|--------|
| Absolute within project | `/Users/you/project/file.py` | ✅ Allowed |
| Relative within project | `src/file.py` | ✅ Allowed |
| Absolute outside project | `/etc/passwd` | ❌ Blocked |
| Path traversal | `../../../etc/passwd` | ❌ Blocked |
| Symlink to outside | `link -> /etc/passwd` | ❌ Blocked |
| Invalid characters | `file\x00.txt` | ❌ Blocked |

## Environment Variables

### CLAUDE_MPM_LOG_LEVEL

Controls the logging verbosity for security events:

```bash
# Set to DEBUG for detailed security logging
export CLAUDE_MPM_LOG_LEVEL=DEBUG

# Default is INFO
export CLAUDE_MPM_LOG_LEVEL=INFO
```

### CLAUDE_PROJECT_DIR

Override the detected working directory (advanced use only):

```bash
# Force a specific project directory
export CLAUDE_PROJECT_DIR=/Users/you/specific-project
```

⚠️ **Warning**: Overriding the project directory may compromise security. Use with caution.

## Logging Configuration

### Log Location

Security events are logged to:
```
<working_directory>/.claude-mpm/logs/hooks_YYYYMMDD.log
```

### Log Levels

| Level | Description | Example |
|-------|-------------|---------|
| INFO | Normal operations | "PreToolUse: Write" |
| WARNING | Security violations | "Security: Blocked Write operation outside working directory" |
| ERROR | Validation errors | "Error validating path: embedded null byte" |
| DEBUG | Detailed information | Full event data and stack traces |

### Log Format

```
[2025-07-27 10:15:23] [WARNING] [claude_mpm_hooks_myproject] Security: Blocked Write operation outside working directory: /etc/passwd
```

## Advanced Configuration

### Disabling Security (Not Recommended)

While the security feature is crucial for safe operation, it can be disabled for specific use cases:

1. **For Testing Only**: Create a custom hook configuration
2. **Override Hook Priority**: Create a higher-priority hook that allows all operations
3. **Modified Hook Handler**: Use a custom hook handler without security checks

⚠️ **Strong Warning**: Disabling security features removes all write protection. Only do this in isolated, controlled environments.

### Custom Security Policies

To implement custom security policies:

1. Create a custom hook inheriting from the security hook
2. Override the validation logic
3. Register with higher priority

Example structure (not recommended for production):
```python
class CustomSecurityHook(BaseHook):
    def __init__(self):
        super().__init__(name="custom_security", priority=5)  # Higher priority
    
    def execute(self, context):
        # Custom validation logic
        pass
```

## Monitoring Security Events

### Real-time Monitoring

Watch security events in real-time:
```bash
# Follow the current day's hook log
tail -f .claude-mpm/logs/hooks_$(date +%Y%m%d).log | grep -E "(Security|WARNING)"
```

### Security Event Analysis

Extract security events for analysis:
```bash
# Find all blocked operations
grep "Security: Blocked" .claude-mpm/logs/hooks_*.log

# Count violations by type
grep "WARNING" .claude-mpm/logs/hooks_*.log | grep "Security" | cut -d: -f4 | sort | uniq -c
```

### Audit Report

Generate a security audit report:
```bash
# Summary of all security events
echo "=== Claude MPM Security Audit ==="
echo "Date Range: $(ls .claude-mpm/logs/hooks_*.log | head -1 | cut -d_ -f2 | cut -d. -f1) - $(date +%Y%m%d)"
echo ""
echo "Total Security Events:"
grep -h "Security:" .claude-mpm/logs/hooks_*.log | wc -l
echo ""
echo "Blocked Operations:"
grep -h "Security: Blocked" .claude-mpm/logs/hooks_*.log | wc -l
echo ""
echo "Path Traversal Attempts:"
grep -h "Path traversal" .claude-mpm/logs/hooks_*.log | wc -l
```

## Troubleshooting

### Issue: Legitimate Writes Being Blocked

**Symptom**: Operations within your project are being blocked

**Solutions**:
1. Verify you're running `claude-mpm` from your project root
2. Check if the path contains unexpected `..` segments
3. Ensure you're not following symlinks outside the project

### Issue: No Security Logs

**Symptom**: Security events aren't being logged

**Solutions**:
1. Check `.claude-mpm/logs/` directory exists
2. Verify write permissions on the log directory
3. Ensure `CLAUDE_MPM_LOG_LEVEL` isn't set to `ERROR` or `CRITICAL`

### Issue: Performance Degradation

**Symptom**: File operations seem slower

**Solutions**:
1. Security checks add <1ms overhead - other factors likely involved
2. Check disk I/O performance
3. Review DEBUG logs for unusual patterns
4. Disable DEBUG logging if enabled

## Best Practices

1. **Regular Monitoring**: Check security logs weekly for unusual patterns
2. **Project Structure**: Keep all project files within a single directory tree
3. **Avoid Symlinks**: Don't use symlinks pointing outside your project
4. **Log Rotation**: Archive old security logs monthly
5. **Incident Response**: Have a plan for responding to security violations

## Security Considerations

### What This Protects Against

- Accidental system file modifications
- Malicious attempts to escape the project directory
- Cross-project contamination
- Unauthorized access to sensitive files

### What This Doesn't Protect Against

- Malicious code execution within the project directory
- Network-based attacks
- Memory-based exploits
- Issues with third-party dependencies

### Complementary Security Measures

1. **Code Review**: Always review generated code before execution
2. **Dependency Scanning**: Regular checks for vulnerable dependencies
3. **Backup Strategy**: Maintain backups of important project files
4. **Access Control**: Limit who can run Claude MPM on sensitive projects

## Support

For security-related questions or to report security issues:

1. Check the [FAQ](#) section
2. Review security logs for detailed error messages
3. Report security vulnerabilities responsibly
4. Consult the developer documentation for technical details
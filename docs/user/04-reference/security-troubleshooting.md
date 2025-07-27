# Security Troubleshooting Guide

## Overview

This guide helps you diagnose and resolve security-related issues with Claude MPM's file security feature. Most security blocks are intentional and protect your system, but this guide will help you understand why operations are blocked and how to work within the security model.

## Common Issues and Solutions

### 1. "Cannot write to files outside the working directory"

**Symptom**: You're trying to create or modify a file and receive this error.

**Common Causes**:
- Running `claude-mpm` from the wrong directory
- Using absolute paths that point outside your project
- Following symlinks that lead outside the project

**Solutions**:

```bash
# Check your current directory
pwd
# Output: /Users/you/some-directory

# Navigate to your project root
cd /Users/you/myproject

# Now run claude-mpm
claude-mpm
```

**Example Fix**:
```bash
# Wrong: Running from home directory
~/$ claude-mpm
> Create a file at /Users/you/myproject/src/app.py
# ERROR: Cannot write outside working directory

# Right: Running from project directory
~/myproject$ claude-mpm
> Create a file at src/app.py
# SUCCESS: File created
```

### 2. "Path traversal attempts are not allowed"

**Symptom**: Operations fail when paths contain `..`

**Common Causes**:
- Relative paths trying to escape the project directory
- Copy-pasted paths from external sources
- Generated paths with unnecessary traversal

**Solutions**:

```bash
# Wrong: Using path traversal
Write file: ../other-project/file.py

# Right: Use absolute or project-relative paths
Write file: src/file.py
```

**How to Fix Path Traversal Issues**:

1. **Use project-relative paths**:
   ```
   src/components/Button.js     ✓ Good
   ./src/components/Button.js   ✓ Good
   /full/path/to/project/src/components/Button.js   ✓ Good (if within project)
   ../../../other/project/file.js   ✗ Bad
   ```

2. **Clean up paths before use**:
   ```python
   # If you must construct paths programmatically
   # Use Path.resolve() to clean them
   from pathlib import Path
   clean_path = Path("src/../src/file.py").resolve()
   # Results in: src/file.py
   ```

### 3. Symlink-Related Blocks

**Symptom**: Operations fail on files that appear to be in your project

**Diagnosis**:
```bash
# Check if a file is a symlink
ls -la src/config.json
# lrwxr-xr-x  1 user  staff  35 Jul 27 10:00 src/config.json -> /etc/myapp/config.json

# The symlink points outside the project!
```

**Solutions**:

1. **Copy instead of symlink**:
   ```bash
   # Remove the symlink
   rm src/config.json
   
   # Copy the actual file
   cp /etc/myapp/config.json src/config.json
   ```

2. **Use project-local config**:
   ```bash
   # Create a local config that imports shared settings
   echo '{"extends": "/etc/myapp/config.json", "local": true}' > src/config.json
   ```

### 4. Temporary File Issues

**Symptom**: Cannot create temporary files in system temp directories

**Common Scenarios**:
- Build processes trying to use `/tmp`
- Cache files being written to system locations
- Test files using OS temp directory

**Solutions**:

1. **Use project-local temp directory**:
   ```bash
   # Create a project temp directory
   mkdir -p .tmp
   
   # Configure tools to use it
   export TMPDIR="$PWD/.tmp"
   ```

2. **Update build configurations**:
   ```javascript
   // webpack.config.js
   module.exports = {
     output: {
       path: path.resolve(__dirname, '.tmp/build'),
     }
   };
   ```

### 5. Installation and Setup Issues

**Symptom**: Operations that should be allowed are being blocked

**Diagnostic Steps**:

1. **Verify working directory**:
   ```bash
   # In your terminal where you run claude-mpm
   pwd
   
   # In Claude MPM
   > /mpm status
   # Check "Project Root" in the output
   ```

2. **Check security logs**:
   ```bash
   # View recent security events
   tail -n 50 .claude-mpm/logs/hooks_$(date +%Y%m%d).log | grep -E "(Security|WARNING)"
   ```

3. **Test path resolution**:
   ```python
   # Quick test to understand path resolution
   from pathlib import Path
   print(f"Working dir: {Path.cwd()}")
   print(f"Target file: {Path('src/app.py').resolve()}")
   ```

## Understanding Security Events

### Log Analysis

Security logs contain valuable information:

```
[2025-07-27 10:15:23] [WARNING] Security: Blocked Write operation outside working directory: /etc/passwd
```

Components:
- **Timestamp**: When the event occurred
- **Level**: WARNING for security blocks
- **Action**: What was blocked (Write, Edit, etc.)
- **Path**: The attempted file path

### Common Patterns in Logs

1. **Repeated blocks to same path**: Likely a misconfigured tool
2. **Blocks to system directories**: Normal and expected
3. **Blocks to user home**: Check if running from correct directory
4. **No security logs**: Check log directory permissions

## Advanced Troubleshooting

### Enable Debug Logging

For detailed security information:

```bash
# Set debug logging
export CLAUDE_MPM_LOG_LEVEL=DEBUG

# Run claude-mpm
claude-mpm

# Check detailed logs
grep "Security check" .claude-mpm/logs/hooks_$(date +%Y%m%d).log
```

### Test Security Validation

Create a test script to validate security behavior:

```python
#!/usr/bin/env python3
# test_security.py
from pathlib import Path

# Test cases
test_paths = [
    "src/new_file.py",           # Should work
    "/tmp/test.txt",             # Should fail
    "../outside.txt",            # Should fail
    "./src/../src/file.py",      # Should work (resolves to src/file.py)
]

working_dir = Path.cwd()
print(f"Working directory: {working_dir}")

for test_path in test_paths:
    try:
        target = Path(test_path).resolve()
        relative = target.relative_to(working_dir)
        print(f"✓ {test_path} -> {target} (relative: {relative})")
    except ValueError:
        print(f"✗ {test_path} -> {target} (outside working directory)")
```

### Hook Service Verification

Verify the hook service is running correctly:

```bash
# Check if hook handler is accessible
ls -la ~/.claude/settings.json

# Verify hook wrapper exists
ls -la /path/to/claude-mpm/src/claude_mpm/hooks/claude_hooks/hook_wrapper.sh

# Test hook execution manually
echo '{"hook_event_name": "test", "cwd": "'$PWD'"}' | python /path/to/hook_handler.py
```

## Working Around Security Restrictions

### Legitimate Use Cases

If you have legitimate needs to write outside the project:

1. **Use a separate tool**: Run file operations outside Claude MPM
2. **Create a wrapper script**: Handle external operations separately
3. **Use project-local alternatives**: Keep everything within the project

### Project Structure Best Practices

Organize your project to work within security boundaries:

```
myproject/
├── src/           # Source code
├── tests/         # Test files
├── docs/          # Documentation
├── .tmp/          # Temporary files
├── .cache/        # Cache directory
├── build/         # Build output
└── logs/          # Application logs
```

### Configuration for Tools

Configure development tools to respect project boundaries:

```json
// .prettierrc
{
  "cache": true,
  "cacheLocation": ".cache/prettier/"
}
```

```yaml
# .eslintrc.yml
parserOptions:
  cacheLocation: .cache/eslint/
```

## Getting Help

### Before Asking for Help

1. **Check the basics**:
   - Current working directory
   - File paths being used
   - Recent security logs

2. **Gather information**:
   ```bash
   # System info
   claude-mpm run -i "/mpm status --verbose" --non-interactive > mpm-status.txt
   
   # Recent security events
   grep "Security:" .claude-mpm/logs/hooks_*.log | tail -20 > security-events.txt
   
   # Current directory structure
   tree -L 3 -a > project-structure.txt
   ```

3. **Create minimal reproduction**:
   - Exact command or operation that fails
   - Expected behavior
   - Actual error message

### Reporting Issues

When reporting security-related issues:

1. **Include context**: Working directory, file paths, error messages
2. **Provide logs**: Relevant portions of security logs
3. **Describe intent**: What you're trying to accomplish
4. **Security sensitive**: Don't post sensitive file paths publicly

### Support Channels

- GitHub Issues: For bugs and feature requests
- Documentation: Check docs for updates
- Community: Ask in discussions for workarounds

## FAQ

**Q: Why can't I write to `/tmp`?**
A: System temp directories are outside your project. Create a `.tmp/` directory in your project instead.

**Q: How do I disable security for testing?**
A: Security features are built-in for protection. For testing, use a dedicated test directory within your project.

**Q: Why are my builds failing?**
A: Build tools may try to write outside the project. Configure them to use project-local directories.

**Q: Can I whitelist specific external directories?**
A: No, the security model doesn't support whitelisting to maintain consistent protection.

**Q: What about reading files?**
A: Reading files from anywhere is allowed. Only write operations are restricted.

## Summary

The file security feature is designed to protect your system while allowing full functionality within your project directory. Most issues can be resolved by:

1. Running Claude MPM from your project root
2. Using project-relative paths
3. Configuring tools to use project-local directories
4. Understanding and working within the security model

Remember: The security restrictions are there to protect you. Working within them ensures safe, predictable operation of Claude MPM.
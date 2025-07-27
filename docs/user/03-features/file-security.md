# File Security

## Overview

Claude MPM includes a built-in security feature that protects your system from unauthorized file modifications. This security hook automatically prevents any write operations outside your working directory, ensuring that agents can only modify files within the project they're working on.

## How It Works

The file security hook intercepts all file write operations and validates them against your current working directory. This happens transparently in the background without requiring any configuration.

### Protected Operations

The following operations are automatically secured:

- **Write**: Creating new files
- **Edit**: Modifying existing files
- **MultiEdit**: Making multiple edits to files
- **NotebookEdit**: Editing Jupyter notebook files

### Allowed Operations

- **All read operations**: Files can be read from anywhere on your system
- **Writes within the working directory**: All file modifications within your project directory are allowed
- **Relative paths**: Paths that resolve to locations within your project

### Blocked Operations

The security system blocks:

- **Absolute paths outside the working directory**: e.g., `/etc/passwd`, `/Users/other/project`
- **Path traversal attempts**: Any path containing `..` to escape the directory
- **Symlinks pointing outside**: Even if a symlink is within your project, writes are blocked if it points outside
- **Invalid paths**: Paths with null bytes or other malicious characters

## Security Benefits

### 1. **Sandbox Protection**
Agents operate in a sandboxed environment limited to your project directory, preventing accidental or malicious system modifications.

### 2. **Data Privacy**
Your personal files, system configurations, and other projects remain protected from unintended access or modification.

### 3. **System Integrity**
Critical system files cannot be modified, ensuring your operating system remains stable and secure.

### 4. **Multi-Project Safety**
When working on multiple projects, each project's files are isolated from others, preventing cross-contamination.

## Example Scenarios

### Allowed: Creating a Project File
```bash
# Working directory: /Users/you/myproject
# This is ALLOWED - file is within the project
Write file: /Users/you/myproject/src/app.py
```

### Blocked: System File Modification
```bash
# Working directory: /Users/you/myproject
# This is BLOCKED - attempting to modify system file
Write file: /etc/hosts

Error: Security Policy: Cannot write to files outside the working directory.
Working directory: /Users/you/myproject
Attempted path: /etc/hosts
```

### Blocked: Path Traversal
```bash
# Working directory: /Users/you/myproject
# This is BLOCKED - path traversal attempt
Write file: ../../../etc/passwd

Error: Security Policy: Path traversal attempts are not allowed.
The path '../../../etc/passwd' contains '..' which could be used to escape the working directory.
```

### Allowed: Reading External Files
```bash
# Working directory: /Users/you/myproject
# This is ALLOWED - read operations are not restricted
Read file: /etc/hosts
```

## Error Messages

When a security violation is detected, you'll see clear, helpful error messages:

### Path Traversal Attempt
```
Security Policy: Path traversal attempts are not allowed.

The path 'config/../../sensitive.txt' contains '..' which could be used to escape the working directory.
Please use absolute paths or paths relative to the working directory without '..'.
```

### Outside Directory Write
```
Security Policy: Cannot write to files outside the working directory.

Working directory: /Users/you/myproject
Attempted path: /tmp/malicious.sh

Please ensure all file operations are within the project directory.
```

### Invalid Path
```
Error validating file path: embedded null byte

Please ensure the path is valid and accessible.
```

## Performance Impact

The security validation adds less than 1 millisecond of overhead per file operation, making it effectively negligible for normal usage:

- Allowed writes: ~0.031ms per check
- Blocked writes: ~0.036ms per check  
- Read operations: ~0.002ms per check

## Logging

All security events are logged for audit purposes:

- **Security violations**: Logged with WARNING level
- **Successful operations**: Logged at INFO level
- **Validation errors**: Logged with full technical details

Logs are stored in:
```
.claude-mpm/logs/hooks_YYYYMMDD.log
```

## FAQ

### Q: Can I disable the security feature?
A: The security feature is enabled by default and is a core safety mechanism. While technically possible to disable, it's strongly recommended to keep it enabled for your protection.

### Q: Why can I read files from anywhere but not write?
A: Reading files is often necessary for agents to understand context, check dependencies, or gather information. Writing is restricted to prevent accidental or malicious modifications to your system.

### Q: What about temporary files?
A: Temporary files are only allowed if they're created within your project directory. System temp directories like `/tmp` are blocked for writes.

### Q: How are symlinks handled?
A: Symlinks are resolved to their actual targets. Even if a symlink exists within your project directory, writes will be blocked if it points to a location outside the project.

### Q: Can I whitelist certain external directories?
A: Currently, the security model doesn't support whitelisting. All writes must be within the working directory. This ensures consistent security across all projects.

## Best Practices

1. **Work within project directories**: Always run Claude MPM from your project root directory
2. **Use relative paths**: When possible, use relative paths for file operations
3. **Check logs for violations**: Regularly review security logs to ensure no unexpected access attempts
4. **Report suspicious behavior**: If you notice unusual file access patterns, report them

## Technical Details

The file security is implemented as a Claude Code hook that:

1. Intercepts `PreToolUse` events
2. Checks if the tool performs write operations
3. Validates the target path is within the working directory
4. Blocks the operation if validation fails
5. Logs all security-relevant events

For more technical details, see the [Developer Documentation](/docs/developer/05-extending/file-security-hook.md).
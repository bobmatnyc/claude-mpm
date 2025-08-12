# Security Documentation

> **Navigation**: [Developer Guide](../README.md) → [Security System](./README.md) → **Security Guide**

## Overview

Claude MPM implements comprehensive security measures to protect your filesystem, data, and operations. This document consolidates all security-related information for developers.

## Table of Contents

1. [Filesystem Security](#filesystem-security)
2. [Agent Security](#agent-security)
3. [Schema Security](#schema-security)
4. [PID Validation](#pid-validation)
5. [Path Restrictions](#path-restrictions)
6. [Security Best Practices](#security-best-practices)

## Filesystem Security

### Multi-Layered Architecture

Claude MPM uses a three-layer security model:

```
┌─────────────────────────────────────────────────────────┐
│                    User Request                         │
└────────────────────────┬───────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│                   PM Agent Layer                        │
│  - Orchestrates task delegation                         │
│  - Enforces security boundaries                         │
│  - Validates agent capabilities                         │
└────────────────────────┬───────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│              Agent Access Control Layer                 │
│  - Role-based permissions                               │
│  - Read/write path restrictions                         │
│  - Blocked path enforcement                             │
└────────────────────────┬───────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│          Base Filesystem Protection Layer               │
│  - Working directory enforcement                        │
│  - Path traversal prevention                            │
│  - Symlink resolution and validation                    │
└─────────────────────────────────────────────────────────┘
```

### Working Directory Enforcement

```python
def validate_path_within_working_directory(path: str) -> bool:
    """
    Validates that a path is within the working directory.
    """
    # Resolve to absolute path
    abs_path = os.path.abspath(path)
    working_dir = os.path.abspath(os.getcwd())
    
    # Check if path is within working directory
    try:
        relative = os.path.relpath(abs_path, working_dir)
        # If relative path starts with '..', it's outside
        return not relative.startswith('..')
    except ValueError:
        # Different drives on Windows
        return False
```

### Path Traversal Prevention

```python
PATH_TRAVERSAL_PATTERNS = [
    r'\.\.',           # Directory traversal
    r'~/',              # Home directory access
    r'^/',              # Absolute path (Unix)
    r'^[A-Z]:',         # Absolute path (Windows)
    r'\\\$',            # Hidden shares
    r'%[0-9a-fA-F]{2}', # URL encoding
]

def detect_path_traversal(path: str) -> bool:
    """
    Detect potential path traversal attempts.
    """
    for pattern in PATH_TRAVERSAL_PATTERNS:
        if re.search(pattern, path):
            return True
    return False
```

## Agent Security

### Role-Based Access Control

Each agent type has predefined security permissions:

```json
{
  "pm_agent": {
    "file_access": {
      "read_paths": ["*"],
      "write_paths": ["."],
      "blocked_paths": []
    },
    "can_delegate": true,
    "max_delegation_depth": 3
  },
  "engineer_agent": {
    "file_access": {
      "read_paths": ["*"],
      "write_paths": ["./**"],
      "blocked_paths": ["**/.env", "**/secrets/**"]
    },
    "can_delegate": false
  },
  "security_agent": {
    "file_access": {
      "read_paths": ["*"],
      "write_paths": [],  // Read-only
      "blocked_paths": []
    },
    "can_delegate": false
  }
}
```

### Agent Capability Validation

```python
def validate_agent_capabilities(agent_type: str, requested_action: str) -> bool:
    """
    Validate if an agent can perform a requested action.
    """
    agent_config = load_agent_configuration(agent_type)
    capabilities = agent_config.get('capabilities', {})
    
    # Check tool access
    if requested_action in ['write', 'edit', 'delete']:
        required_tools = ['Write', 'Edit']
        agent_tools = capabilities.get('tools', [])
        if not any(tool in agent_tools for tool in required_tools):
            return False
    
    # Check file access
    file_access = capabilities.get('file_access', {})
    if requested_action == 'write':
        write_paths = file_access.get('write_paths', [])
        if not write_paths:
            return False
    
    return True
```

## Schema Security

### Schema Validation

All agent configurations must pass schema validation:

```python
def validate_agent_schema(config: Dict) -> Tuple[bool, List[str]]:
    """
    Validate agent configuration against security schema.
    """
    errors = []
    
    # Required fields validation
    required_fields = ['agent_id', 'agent_type', 'capabilities']
    for field in required_fields:
        if field not in config:
            errors.append(f"Missing required field: {field}")
    
    # Pattern validation
    if 'agent_id' in config:
        if not re.match(r'^[a-z][a-z0-9_]*$', config['agent_id']):
            errors.append("Invalid agent_id format")
    
    # Tool validation
    if 'capabilities' in config:
        tools = config['capabilities'].get('tools', [])
        allowed_tools = ['Read', 'Write', 'Edit', 'Bash', 'Grep']
        for tool in tools:
            if tool not in allowed_tools:
                errors.append(f"Unknown tool: {tool}")
    
    return len(errors) == 0, errors
```

### Input Sanitization

```python
def sanitize_agent_input(input_data: Any) -> Any:
    """
    Sanitize user input for agent configurations.
    """
    if isinstance(input_data, str):
        # Remove potential command injection patterns
        dangerous_patterns = [
            r'\$\(',  # Command substitution
            r'`',     # Backticks
            r';',     # Command separator
            r'\|',    # Pipe
            r'&&',    # Command chaining
            r'||',    # Command chaining
        ]
        for pattern in dangerous_patterns:
            input_data = re.sub(pattern, '', input_data)
    
    elif isinstance(input_data, dict):
        return {k: sanitize_agent_input(v) for k, v in input_data.items()}
    
    elif isinstance(input_data, list):
        return [sanitize_agent_input(item) for item in input_data]
    
    return input_data
```

## PID Validation

### Enhanced PID Security

```python
class SecurePIDManager:
    """
    Secure PID file management with validation.
    """
    
    @staticmethod
    def validate_pid_file(pid_file: Path) -> bool:
        """
        Validate PID file integrity and ownership.
        """
        if not pid_file.exists():
            return False
        
        # Check file permissions (should be readable by owner only)
        stat_info = pid_file.stat()
        if stat_info.st_mode & 0o077:
            return False  # File is accessible by group/others
        
        # Validate PID format
        try:
            pid = int(pid_file.read_text().strip())
            if pid <= 0 or pid > 2**31:
                return False
        except (ValueError, OSError):
            return False
        
        # Check if process exists and belongs to current user
        try:
            os.kill(pid, 0)  # Check if process exists
            # Additional check for process ownership
            if hasattr(os, 'geteuid'):
                proc_stat = Path(f'/proc/{pid}/status')
                if proc_stat.exists():
                    content = proc_stat.read_text()
                    uid_line = [l for l in content.split('\n') if l.startswith('Uid:')]
                    if uid_line:
                        uid = int(uid_line[0].split()[1])
                        if uid != os.geteuid():
                            return False
        except (OSError, ProcessLookupError):
            return False
        
        return True
```

## Path Restrictions

### Restricted Paths

```python
RESTRICTED_PATHS = [
    # System directories
    '/etc',
    '/usr',
    '/bin',
    '/sbin',
    '/boot',
    '/dev',
    '/proc',
    '/sys',
    
    # User directories (outside working dir)
    '~/.ssh',
    '~/.gnupg',
    '~/.aws',
    '~/.config',
    
    # Windows system directories
    'C:\\Windows',
    'C:\\Program Files',
    'C:\\ProgramData',
    
    # Common sensitive files
    '.env',
    '.env.local',
    '.env.production',
    'secrets.yml',
    'credentials.json',
]

def is_path_restricted(path: str) -> bool:
    """
    Check if a path is in the restricted list.
    """
    abs_path = os.path.abspath(os.path.expanduser(path))
    
    for restricted in RESTRICTED_PATHS:
        restricted_abs = os.path.abspath(os.path.expanduser(restricted))
        if abs_path.startswith(restricted_abs):
            return True
    
    return False
```

### Safe Path Operations

```python
class SafeFileOperations:
    """
    Safe file operations with security checks.
    """
    
    @staticmethod
    def safe_read(filepath: str) -> Optional[str]:
        """
        Safely read a file with security checks.
        """
        # Validate path
        if not validate_path_within_working_directory(filepath):
            raise SecurityError(f"Access denied: {filepath}")
        
        if is_path_restricted(filepath):
            raise SecurityError(f"Restricted path: {filepath}")
        
        # Read file
        try:
            with open(filepath, 'r') as f:
                return f.read()
        except IOError as e:
            logger.error(f"Failed to read {filepath}: {e}")
            return None
    
    @staticmethod
    def safe_write(filepath: str, content: str) -> bool:
        """
        Safely write to a file with security checks.
        """
        # Validate path
        if not validate_path_within_working_directory(filepath):
            raise SecurityError(f"Write access denied: {filepath}")
        
        if is_path_restricted(filepath):
            raise SecurityError(f"Cannot write to restricted path: {filepath}")
        
        # Create parent directories safely
        parent = os.path.dirname(filepath)
        if parent and not os.path.exists(parent):
            os.makedirs(parent, mode=0o755)
        
        # Write file with restricted permissions
        try:
            with open(filepath, 'w') as f:
                f.write(content)
            os.chmod(filepath, 0o644)  # rw-r--r--
            return True
        except IOError as e:
            logger.error(f"Failed to write {filepath}: {e}")
            return False
```

## Security Best Practices

### 1. Agent Configuration

- Always specify explicit `file_access` rules
- Use the principle of least privilege
- Block sensitive paths explicitly
- Regularly audit agent permissions

### 2. Path Handling

```python
# Good: Explicit path validation
filepath = os.path.join(working_dir, user_input)
if validate_path_within_working_directory(filepath):
    process_file(filepath)

# Bad: Direct user input
process_file(user_input)  # Dangerous!
```

### 3. Input Validation

```python
# Always sanitize user inputs
def process_user_request(user_input: str):
    # Sanitize input
    clean_input = sanitize_agent_input(user_input)
    
    # Validate against whitelist
    if not is_valid_command(clean_input):
        raise ValueError("Invalid command")
    
    # Process safely
    return execute_safe_command(clean_input)
```

### 4. Error Handling

```python
# Don't expose sensitive information in errors
try:
    sensitive_operation()
except Exception as e:
    # Log detailed error internally
    logger.error(f"Operation failed: {e}", exc_info=True)
    
    # Return generic error to user
    return {"error": "Operation failed", "code": "GENERIC_ERROR"}
```

### 5. Audit Logging

```python
class SecurityAuditLogger:
    """
    Log security-relevant events.
    """
    
    @staticmethod
    def log_access_attempt(user: str, resource: str, action: str, result: bool):
        """
        Log access attempts for audit trail.
        """
        event = {
            'timestamp': datetime.now().isoformat(),
            'user': user,
            'resource': resource,
            'action': action,
            'result': 'allowed' if result else 'denied',
            'pid': os.getpid(),
        }
        
        # Log to secure audit file
        with open('.claude-mpm/audit.log', 'a') as f:
            f.write(json.dumps(event) + '\n')
```

### 6. Regular Security Updates

```bash
# Check for security updates
./claude-mpm security check

# Update security configurations
./claude-mpm security update

# Audit agent permissions
./claude-mpm security audit --agents

# Scan for vulnerabilities
./claude-mpm security scan
```

## Security Checklist

### Development

- [ ] All file operations use safe wrappers
- [ ] User input is sanitized before processing
- [ ] Path validation is performed for all file access
- [ ] Error messages don't expose sensitive information
- [ ] Agent configurations follow least privilege principle

### Deployment

- [ ] File permissions are correctly set (0644 for files, 0755 for directories)
- [ ] PID files are protected (0600)
- [ ] Audit logging is enabled
- [ ] Sensitive paths are blocked in agent configurations
- [ ] Working directory enforcement is active

### Monitoring

- [ ] Security audit logs are reviewed regularly
- [ ] Failed access attempts are investigated
- [ ] Agent permission changes are tracked
- [ ] Unusual file access patterns are detected
- [ ] Security updates are applied promptly

## Incident Response

### Security Breach Protocol

1. **Immediate Actions**
   ```bash
   # Stop all agents
   ./claude-mpm stop --all
   
   # Review audit logs
   tail -f .claude-mpm/audit.log
   
   # Check for unauthorized changes
   git status
   ```

2. **Investigation**
   ```bash
   # Review agent activity
   ./claude-mpm security investigate --since "1 hour ago"
   
   # Check file modifications
   find . -type f -mmin -60 -ls
   ```

3. **Remediation**
   ```bash
   # Reset agent configurations
   ./claude-mpm security reset --agents
   
   # Restore from backup if needed
   ./claude-mpm restore --from backup/
   ```

## Related Documentation

- [Filesystem Security Architecture](./FILESYSTEM_SECURITY_ARCHITECTURE.md)
- [Agent Schema Security](./agent_schema_security_notes.md)
- [PID Validation](../ENHANCED_PID_VALIDATION.md)
- [Path Restrictions Implementation](./FILESYSTEM_RESTRICTIONS_IMPLEMENTATION.md)

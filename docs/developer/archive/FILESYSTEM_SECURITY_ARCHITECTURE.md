# Filesystem Security Architecture

## Overview

Claude MPM implements a multi-layered security architecture to protect your filesystem from unauthorized modifications. This document describes the comprehensive security measures in version 3.1.0.

## Security Layers

### 1. Base Layer: Working Directory Enforcement

The fundamental security layer restricts all write operations to the current working directory:

- **Automatic Detection**: Working directory is detected from where `claude-mpm` is executed
- **Path Resolution**: All paths are resolved to absolute paths for validation
- **Symlink Protection**: Symlinks are followed and validated against the working directory
- **Traversal Prevention**: Paths containing `..` are blocked to prevent directory escape

### 2. Agent Layer: Role-Based Access Control

Each agent has configurable file access permissions defined in their `file_access` configuration:

```json
"file_access": {
  "read_paths": ["*"],           // What the agent can read
  "write_paths": ["."],          // What the agent can write
  "blocked_paths": ["**/.env"]   // Explicitly blocked paths
}
```

### 3. Orchestration Layer: PM Agent Coordination

The PM (Project Manager) agent provides an additional security layer:

- **Task Delegation**: PM agent delegates tasks to specialized agents
- **Boundary Enforcement**: Ensures delegated agents operate within their permissions
- **Audit Trail**: Tracks which agent performed which operations
- **Security Validation**: Validates agent capabilities before delegation

## Security Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│                    User Request                         │
└────────────────────────┬───────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│                   PM Agent                              │
│  - Orchestrates task delegation                         │
│  - Enforces security boundaries                         │
│  - Read: * | Write: . only                             │
└────────────────────────┬───────────────────────────────┘
                         │ Delegates to
                         ▼
┌─────────────────────────────────────────────────────────┐
│              Specialized Agents                         │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────┐ │
│  │  Engineer   │  │Documentation │  │   Security    │ │
│  │ Write: ./** │  │Write: ./docs │  │ Write: none   │ │
│  └─────────────┘  └──────────────┘  └───────────────┘ │
└────────────────────────┬───────────────────────────────┘
                         │ File operations
                         ▼
┌─────────────────────────────────────────────────────────┐
│              File Security Hook                         │
│  - Validates all file operations                        │
│  - Enforces working directory boundary                  │
│  - Checks agent-specific permissions                    │
│  - Logs security events                                 │
└────────────────────────┬───────────────────────────────┘
                         │ Approved operations
                         ▼
┌─────────────────────────────────────────────────────────┐
│                  Filesystem                             │
└─────────────────────────────────────────────────────────┘
```

## Security Policies

### Write Operation Security

1. **Working Directory Check**: First validates path is within working directory
2. **Agent Permission Check**: Validates against agent's `write_paths` configuration
3. **Blocked Path Check**: Ensures path doesn't match any `blocked_paths`
4. **Operation Execution**: Only if all checks pass

### Read Operation Security

1. **Agent Permission Check**: Validates against agent's `read_paths` configuration
2. **Blocked Path Check**: Ensures path doesn't match any `blocked_paths`
3. **No Working Directory Restriction**: Reads can access files outside working directory

### Path Validation Rules

| Validation | Rule | Example |
|------------|------|---------|
| Path Traversal | No `..` in paths | `../../../etc/passwd` → Blocked |
| Null Bytes | No null characters | `file\x00.txt` → Blocked |
| Absolute Paths | Must be within working dir for writes | `/etc/hosts` → Blocked |
| Symlinks | Resolved target must be valid | `link → /etc/passwd` → Blocked |

## Agent Security Profiles

### PM (Project Manager) Agent

**Purpose**: Orchestrates complex tasks across multiple agents

```json
"file_access": {
  "read_paths": ["*"],
  "write_paths": ["."],
  "blocked_paths": []
}
```

**Security Rationale**:
- Can read anything to understand project context
- Limited write access prevents accidental modifications
- Delegates actual implementation to specialized agents

### Engineer Agent

**Purpose**: Code implementation and development

```json
"file_access": {
  "read_paths": ["*"],
  "write_paths": ["./**"],
  "blocked_paths": ["**/node_modules/**", "**/.env", "**/.git/**"]
}
```

**Security Rationale**:
- Full project write access for development
- Blocked from package directories and sensitive files
- Cannot modify git internals directly

### Security Agent

**Purpose**: Security auditing and analysis

```json
"file_access": {
  "read_paths": ["*"],
  "write_paths": [],
  "blocked_paths": []
}
```

**Security Rationale**:
- Read-only access prevents tampering during audits
- Can read all files including sensitive ones for analysis
- No write capabilities ensures audit integrity

### Documentation Agent

**Purpose**: Documentation creation and maintenance

```json
"file_access": {
  "read_paths": ["*"],
  "write_paths": ["./docs/**", "./README.md", "./CHANGELOG.md"],
  "blocked_paths": ["**/.env", "**/secrets/**"]
}
```

**Security Rationale**:
- Limited to documentation-related files
- Cannot access sensitive configuration
- Prevents documentation from exposing secrets

## Security Benefits

### 1. Defense in Depth

Multiple layers ensure security even if one layer is compromised:
- Base working directory enforcement
- Agent-specific restrictions
- PM agent orchestration
- Comprehensive logging

### 2. Principle of Least Privilege

Each agent has only the permissions necessary for its role:
- Security agent: read-only
- Documentation agent: docs only
- PM agent: coordination only

### 3. Audit Trail

Complete logging of all security events:
- Failed access attempts
- Successful operations
- Agent attributions
- Timestamps and paths

### 4. Zero Configuration

Security is enabled by default without user configuration:
- Automatic working directory detection
- Pre-configured agent permissions
- Default-deny for writes

## Implementation Details

### File Security Hook

The core security enforcement happens in the file security hook:

```python
# Simplified validation flow
def validate_file_operation(tool, path, agent_config):
    # 1. Check if write operation
    if tool in WRITE_TOOLS:
        # 2. Validate working directory
        if not is_within_working_directory(path):
            raise SecurityError("Outside working directory")
        
        # 3. Check agent write permissions
        if not matches_patterns(path, agent_config.write_paths):
            raise SecurityError("Agent lacks write permission")
    
    # 4. Check blocked paths
    if matches_patterns(path, agent_config.blocked_paths):
        raise SecurityError("Path is blocked")
    
    # 5. Allow operation
    return True
```

### Pattern Matching

File access patterns support glob-style matching:

- `.` - Current directory
- `*` - Any file (not recursive)
- `**` - Any file (recursive)
- `~/` - User home directory

### Performance Considerations

Security validation adds minimal overhead:
- Average validation time: <1ms
- Caching of resolved paths
- Efficient pattern matching
- Asynchronous logging

## Best Practices

### 1. Project Organization

- Keep all project files in a single directory tree
- Avoid symlinks pointing outside the project
- Use consistent directory structure

### 2. Agent Selection

- Use PM agent for complex multi-step tasks
- Select specialized agents for specific operations
- Avoid using overly permissive agents

### 3. Security Monitoring

- Regularly review security logs
- Monitor for unusual access patterns
- Investigate all security violations

### 4. Custom Agents

When creating custom agents:
- Define minimal necessary permissions
- Use specific path patterns
- Block sensitive directories
- Test security boundaries

## Troubleshooting

### Common Issues

1. **"Cannot write outside working directory"**
   - Ensure you're running from project root
   - Check for absolute paths in your code
   - Verify no `..` in paths

2. **"Agent lacks permission"**
   - Check agent's `write_paths` configuration
   - Ensure path matches allowed patterns
   - Consider using a different agent

3. **"Path is blocked"**
   - Check agent's `blocked_paths`
   - Common blocks: `.env`, `node_modules`, `.git`
   - Use different path if legitimate

### Debug Mode

Enable debug logging for detailed security information:

```bash
export CLAUDE_MPM_LOG_LEVEL=DEBUG
claude-mpm
```

## Future Enhancements

### Planned Features

1. **Capability-Based Security**: More granular permission model
2. **Security Policies**: User-definable security policies
3. **Audit Reports**: Automated security audit generation
4. **Path Whitelisting**: Allow specific external paths

### Security Roadmap

- Enhanced pattern matching with regex support
- Time-based access restrictions
- Operation rate limiting
- Cryptographic operation signatures

## Conclusion

Claude MPM's filesystem security architecture provides robust protection through:

1. **Multi-layered defense**: Working directory, agent permissions, and orchestration
2. **Role-based access**: Each agent has appropriate permissions
3. **Comprehensive logging**: Full audit trail of all operations
4. **Zero-configuration**: Secure by default

This architecture ensures that AI agents can assist with development tasks while maintaining strict security boundaries, protecting both your system and your projects from unauthorized modifications.
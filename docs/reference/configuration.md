# Configuration Reference

Complete reference for Claude MPM configuration options.

## Table of Contents

- [Configuration File](#configuration-file)
- [Agent Synchronization](#agent-synchronization)
- [Session Management](#session-management)
- [Monitoring](#monitoring)
- [Memory Management](#memory-management)
- [Update Checking](#update-checking)
- [Environment Variables](#environment-variables)

## Configuration File

Claude MPM uses YAML configuration files for system-wide and per-project settings.

### File Locations

**Global Configuration**:
```
~/.claude-mpm/configuration.yaml
```

**Project-Local Configuration**:
```
<project-root>/.claude-mpm/configuration.yaml
```

**Priority**: Project-local settings override global settings.

### Basic Structure

```yaml
# ~/.claude-mpm/configuration.yaml

# Agent synchronization
agent_sync:
  enabled: true
  sources:
    - url: https://github.com/bobmatnyc/claude-mpm-agents
      priority: 1
  cache_dir: ~/.claude-mpm/cache/remote-agents

# Session management
session:
  auto_resume: true
  max_history: 50

# Monitoring dashboard
monitoring:
  enabled: true
  port: 5050
  host: localhost

# Memory management
memory:
  max_context_tokens: 200000
  resume_log_enabled: true

# Update checking
updates:
  check_on_startup: true
  check_claude_code_compatibility: true
```

## Agent Synchronization

Configure automatic agent template synchronization from Git repositories.

### `agent_sync.enabled`

Enable or disable automatic agent synchronization.

**Type**: `boolean`
**Default**: `true`
**Required**: No

```yaml
agent_sync:
  enabled: true  # Enable automatic sync
```

**Use Cases**:
- **true**: Normal operation with automatic updates (recommended)
- **false**: Offline mode, corporate environments, testing with specific versions

**Impact**:
- When disabled: Uses bundled agents only (no remote updates)
- When enabled: Syncs from configured sources on startup

---

### `agent_sync.sources`

List of Git repositories to sync agents from.

**Type**: `list` of source objects
**Default**:
```yaml
sources:
  - url: https://github.com/bobmatnyc/claude-mpm-agents
    priority: 1
```
**Required**: No

```yaml
agent_sync:
  sources:
    - url: https://github.com/bobmatnyc/claude-mpm-agents
      priority: 1
    - url: https://github.com/yourcompany/custom-agents
      priority: 2
```

**Source Object Fields**:

#### `url` (string, required)
- GitHub repository URL
- Format: `https://github.com/owner/repository`
- Must be publicly accessible (authentication not yet supported)

#### `priority` (integer, required)
- Source priority (lower number = higher priority)
- Range: 1-100
- Priority 1 sources override priority 2, etc.

**Current Limitation**: Only the first source is used. Multi-source support is planned for ticket 1M-390.

**Validation**:
- URL must start with `https://github.com/`
- Priority must be positive integer
- Source list cannot be empty if `enabled: true`

---

### `agent_sync.cache_dir`

Override default cache directory location.

**Type**: `string` (path)
**Default**: `~/.claude-mpm/cache/remote-agents`
**Required**: No

```yaml
agent_sync:
  cache_dir: /opt/company/claude-agents
```

**Path Expansion**:
- `~` expands to user home directory
- Relative paths are relative to config file location
- Absolute paths used as-is

**Use Cases**:
- **Shared cache**: `/shared/claude-agents` for multi-user systems
- **Network storage**: `/mnt/nas/claude-agents` for team consistency
- **Custom backup**: `/backup/claude-agents` for archival

**Requirements**:
- Directory must be writable by current user
- Parent directory must exist (created automatically if missing)
- Sufficient disk space (~500KB recommended minimum)

---

### Complete Example

```yaml
agent_sync:
  # Enable automatic synchronization
  enabled: true

  # Sync from official repository
  sources:
    - url: https://github.com/bobmatnyc/claude-mpm-agents
      priority: 1

  # Use default cache location
  cache_dir: ~/.claude-mpm/cache/remote-agents
```

### Offline Configuration

For air-gapped or corporate environments:

```yaml
agent_sync:
  # Disable sync - use bundled agents only
  enabled: false
```

### Custom Repository

For organizations with custom agents:

```yaml
agent_sync:
  enabled: true
  sources:
    - url: https://github.com/yourcompany/internal-agents
      priority: 1
  cache_dir: /opt/company/claude-agents
```

## Session Management

Configure session behavior and history management.

### `session.auto_resume`

Automatically resume the most recent session on startup.

**Type**: `boolean`
**Default**: `false`
**Required**: No

```yaml
session:
  auto_resume: true
```

---

### `session.max_history`

Maximum number of sessions to keep in history.

**Type**: `integer`
**Default**: `50`
**Required**: No

```yaml
session:
  max_history: 100
```

**Note**: Older sessions are automatically cleaned up when limit is reached.

---

## Monitoring

Configure the monitoring dashboard.

### `monitoring.enabled`

Enable the monitoring dashboard web interface.

**Type**: `boolean`
**Default**: `true`
**Required**: No

```yaml
monitoring:
  enabled: true
```

**Requirements**: Requires `[monitor]` extra: `pip install "claude-mpm[monitor]"`

---

### `monitoring.port`

Port for the monitoring dashboard server.

**Type**: `integer`
**Default**: `5050`
**Required**: No

```yaml
monitoring:
  port: 8080
```

**Valid Range**: 1024-65535 (non-privileged ports)

---

### `monitoring.host`

Host/interface for the monitoring dashboard.

**Type**: `string`
**Default**: `localhost`
**Required**: No

```yaml
monitoring:
  host: 0.0.0.0  # Listen on all interfaces
```

**Common Values**:
- `localhost`: Local access only (secure)
- `0.0.0.0`: All interfaces (use with caution)
- `127.0.0.1`: IPv4 localhost only

---

## Memory Management

Configure context and memory management.

### `memory.max_context_tokens`

Maximum context window size in tokens.

**Type**: `integer`
**Default**: `200000`
**Required**: No

```yaml
memory:
  max_context_tokens: 150000
```

**Constraints**: Based on model capabilities (Claude Sonnet 3.5: 200k tokens)

---

### `memory.resume_log_enabled`

Enable automatic resume log generation.

**Type**: `boolean`
**Default**: `true`
**Required**: No

```yaml
memory:
  resume_log_enabled: true
```

**Feature**: Generates 10k-token session summaries at 70%/85%/95% context thresholds.

---

## Update Checking

Configure automatic update checking.

### `updates.check_on_startup`

Check for Claude MPM updates on startup.

**Type**: `boolean`
**Default**: `true`
**Required**: No

```yaml
updates:
  check_on_startup: false
```

---

### `updates.check_claude_code_compatibility`

Verify Claude Code version compatibility.

**Type**: `boolean`
**Default**: `true`
**Required**: No

```yaml
updates:
  check_claude_code_compatibility: true
```

**Recommendation**: Keep enabled to ensure compatibility with Claude Code CLI.

---

## Environment Variables

Override configuration with environment variables.

### `CLAUDE_MPM_CONFIG`

Override configuration file path.

```bash
export CLAUDE_MPM_CONFIG=/path/to/custom/config.yaml
claude-mpm
```

**Default**: `~/.claude-mpm/configuration.yaml`

---

### `CLAUDE_MPM_LOG_LEVEL`

Set logging level for debugging.

```bash
export CLAUDE_MPM_LOG_LEVEL=DEBUG
claude-mpm
```

**Valid Values**: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`
**Default**: `INFO`

---

### `CLAUDE_MPM_CACHE_DIR`

Override agent cache directory.

```bash
export CLAUDE_MPM_CACHE_DIR=/tmp/claude-agents
claude-mpm
```

**Default**: `~/.claude-mpm/cache/remote-agents`

---

### `CLAUDE_MPM_DISABLE_SYNC`

Disable agent synchronization (bypass config).

```bash
export CLAUDE_MPM_DISABLE_SYNC=1
claude-mpm
```

**Values**: `1`, `true`, `yes` (case-insensitive)

---

## Complete Configuration Example

```yaml
# ~/.claude-mpm/configuration.yaml
# Complete Claude MPM configuration

# ============================================================
# Agent Synchronization
# ============================================================
agent_sync:
  # Enable automatic agent updates from Git repositories
  enabled: true

  # Git repositories to sync from (priority order)
  sources:
    - url: https://github.com/bobmatnyc/claude-mpm-agents
      priority: 1

  # Local cache directory for synced agents
  cache_dir: ~/.claude-mpm/cache/remote-agents

# ============================================================
# Session Management
# ============================================================
session:
  # Automatically resume most recent session
  auto_resume: false

  # Maximum sessions to keep in history
  max_history: 50

# ============================================================
# Monitoring Dashboard
# ============================================================
monitoring:
  # Enable web-based monitoring dashboard
  enabled: true

  # Dashboard server port
  port: 5050

  # Dashboard server host (localhost = secure)
  host: localhost

# ============================================================
# Memory Management
# ============================================================
memory:
  # Maximum context window (tokens)
  max_context_tokens: 200000

  # Enable automatic resume logs
  resume_log_enabled: true

# ============================================================
# Update Checking
# ============================================================
updates:
  # Check for Claude MPM updates on startup
  check_on_startup: true

  # Verify Claude Code CLI compatibility
  check_claude_code_compatibility: true
```

## Configuration Validation

Validate your configuration file:

```bash
# Run doctor command to check configuration
claude-mpm doctor --checks configuration

# Example output:
# ✓ Configuration file found
# ✓ Configuration is valid YAML
# ✓ All required fields present
# ✓ Agent sync configuration valid
# ✓ Source URLs accessible
```

### Common Validation Errors

**Invalid YAML syntax**:
```
ERROR: Configuration syntax error at line 10
Suggestion: Check for missing colons, incorrect indentation
```

**Missing required field**:
```
ERROR: agent_sync.sources[0].url is required
Suggestion: Add url field to source configuration
```

**Invalid URL**:
```
ERROR: agent_sync.sources[0].url must start with https://github.com/
Suggestion: Use GitHub repository URL format
```

**Invalid priority**:
```
ERROR: agent_sync.sources[0].priority must be positive integer
Suggestion: Use priority value >= 1
```

## Migration Guide

### From Version 4.x to 5.x

Agent sync configuration is **new in version 5.0**. Add to existing config:

```yaml
# Add to existing configuration.yaml
agent_sync:
  enabled: true
  sources:
    - url: https://github.com/bobmatnyc/claude-mpm-agents
      priority: 1
  cache_dir: ~/.claude-mpm/cache/remote-agents
```

**Automatic Migration**: Agent sync is enabled by default if not configured.

### Disable New Features

To preserve version 4.x behavior:

```yaml
# Disable agent sync (use bundled agents only)
agent_sync:
  enabled: false
```

## Related Documentation

- [Agent Synchronization Guide](../guides/agent-synchronization.md) - Complete sync guide
- [Agent Sync Internals](../development/agent-sync-internals.md) - Developer reference
- [Troubleshooting](../user/troubleshooting.md) - Common issues

---

**Last Updated**: 2025-11-29
**Related Ticket**: 1M-382 (Git-based agent synchronization configuration)

# Agent Synchronization Guide

Complete guide to Claude MPM's git-based agent synchronization system.

## Table of Contents

- [Overview](#overview)
- [How It Works](#how-it-works)
- [Getting Started](#getting-started)
- [Configuration](#configuration)
- [Advanced Usage](#advanced-usage)
- [Troubleshooting](#troubleshooting)
- [Performance](#performance)

## Overview

Claude MPM's agent synchronization system automatically keeps your agent templates up-to-date by syncing with remote Git repositories. This ensures you always have access to the latest agent capabilities without manual updates.

### Key Benefits

- **Always Current**: Automatically receive agent improvements and new features
- **Efficient**: ETag-based HTTP caching reduces bandwidth usage by ~95%
- **Fast**: Typical sync completes in 100-200ms after first run
- **Reliable**: Works offline with cached agents when network unavailable
- **Transparent**: Syncs automatically on startup with minimal impact

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Claude MPM Startup                        │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              Agent Synchronization Service                   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  1. Check Configuration                              │   │
│  │     - enabled: true/false                            │   │
│  │     - sources: list of Git repositories              │   │
│  └──────────────────────────────────────────────────────┘   │
│                         │                                    │
│                         ▼                                    │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  2. For Each Source Repository                       │   │
│  │     - Fetch repository contents via GitHub API       │   │
│  │     - Use ETag headers for conditional requests      │   │
│  └──────────────────────────────────────────────────────┘   │
│                         │                                    │
│                         ▼                                    │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  3. Process Agent Files                              │   │
│  │     - Download only changed files (ETag mismatch)    │   │
│  │     - Verify SHA-256 content hash                    │   │
│  │     - Update local cache                             │   │
│  └──────────────────────────────────────────────────────┘   │
│                         │                                    │
│                         ▼                                    │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  4. Update SQLite State Database                     │   │
│  │     - Record sync timestamp                          │   │
│  │     - Store content hashes                           │   │
│  │     - Track ETag values                              │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              Local Agent Cache                               │
│  Location: ~/.claude-mpm/cache/remote-agents/               │
│  Files: 48 agent markdown templates                         │
│  Size: ~50-200KB total                                      │
└─────────────────────────────────────────────────────────────┘
```

## How It Works

### 1. Initial Sync (First Run)

When you first run Claude MPM or after clearing cache:

1. **Repository Check**: Connects to configured Git repository
2. **File Discovery**: Lists all agent markdown files
3. **Download**: Downloads all agent files (~48 files, 200KB total)
4. **Cache Creation**: Stores files in local cache directory
5. **State Recording**: Records ETag and SHA-256 hash for each file

**Time**: 500-800ms (depending on network speed)

### 2. Subsequent Syncs (Normal Operation)

On every Claude MPM startup after initial sync:

1. **ETag Check**: Sends HTTP request with "If-None-Match" header
2. **304 Response**: GitHub returns "Not Modified" for unchanged files
3. **Download**: Only downloads files that have actually changed
4. **Update Cache**: Updates only changed files in cache
5. **State Update**: Records new ETags and hashes

**Time**: 100-200ms (mostly network latency)

### 3. Offline Mode

When network is unavailable:

1. **Cache Fallback**: Uses existing cached agents
2. **Silent Degradation**: Logs warning but continues normally
3. **Next Sync**: Automatically resumes sync when network returns

**User Impact**: None (agents work normally from cache)

## Getting Started

### Quick Start

Agent synchronization is enabled by default. No configuration required!

```bash
# Just run Claude MPM - agents sync automatically
claude-mpm

# First run output (example):
# Syncing agents from https://github.com/bobmatnyc/claude-mpm-agents...
# Downloaded 48 agents (512ms)

# Subsequent runs (example):
# Agent sync: 48 cached, 0 updated (102ms)
```

### Verify Sync Status

Check your local cache:

```bash
# View cached agents
ls -lh ~/.claude-mpm/cache/remote-agents/

# Check sync database
sqlite3 ~/.config/claude-mpm/agent_sync.db "SELECT COUNT(*) FROM sync_history;"

# View last sync time
sqlite3 ~/.config/claude-mpm/agent_sync.db \
  "SELECT MAX(synced_at) FROM sync_history;"
```

### Manual Cache Management

```bash
# Force full re-sync (clears all cached data)
rm -rf ~/.claude-mpm/cache/remote-agents/
rm ~/.config/claude-mpm/agent_sync.db

# Next run will perform full initial sync
claude-mpm
```

## Configuration

### Default Configuration

```yaml
# ~/.claude-mpm/configuration.yaml
agent_sync:
  enabled: true  # Enable/disable automatic sync
  sources:
    - url: https://github.com/bobmatnyc/claude-mpm-agents
      priority: 1
  cache_dir: ~/.claude-mpm/cache/remote-agents
```

### Configuration Options

#### `enabled` (boolean)

Enable or disable agent synchronization.

```yaml
agent_sync:
  enabled: false  # Disable sync, use bundled agents only
```

**Use Cases**:
- Corporate environments with restricted internet access
- CI/CD pipelines where you want consistent agent versions
- Testing with specific agent versions

#### `sources` (list)

List of Git repositories to sync agents from.

```yaml
agent_sync:
  sources:
    - url: https://github.com/bobmatnyc/claude-mpm-agents
      priority: 1  # Higher priority = used first
    - url: https://github.com/yourcompany/custom-agents
      priority: 2
```

**Current Limitation**: Single-source only (multi-source planned for 1M-390)

**Priority**: Lower numbers = higher priority (priority 1 overrides priority 2)

#### `cache_dir` (string)

Override default cache directory location.

```yaml
agent_sync:
  cache_dir: /opt/company/claude-agents  # Custom location
```

**Default**: `~/.claude-mpm/cache/remote-agents`

**Use Cases**:
- Shared cache for multiple users
- Network storage for team consistency
- Custom backup/restore locations

### Example Configurations

#### Disable Sync (Offline Mode)

```yaml
agent_sync:
  enabled: false
```

#### Custom Cache Location

```yaml
agent_sync:
  enabled: true
  sources:
    - url: https://github.com/bobmatnyc/claude-mpm-agents
      priority: 1
  cache_dir: /opt/claude-mpm/agents
```

#### Corporate Environment (Future: Multi-Source)

```yaml
# Note: Multi-source support planned for ticket 1M-390
agent_sync:
  enabled: true
  sources:
    - url: https://github.com/yourcompany/internal-agents
      priority: 1  # Use internal agents first
    - url: https://github.com/bobmatnyc/claude-mpm-agents
      priority: 2  # Fallback to official agents
  cache_dir: /company/shared/claude-agents
```

## Advanced Usage

### ETag Caching Deep Dive

Claude MPM uses HTTP ETags for efficient caching:

**How ETags Work**:
1. First request: GitHub returns content + ETag header
2. Subsequent requests: Client sends "If-None-Match: <etag>"
3. Unchanged: GitHub returns 304 Not Modified (no content)
4. Changed: GitHub returns 200 OK + new content + new ETag

**Bandwidth Savings**:
- First sync: ~200KB download
- Typical sync: <1KB (just HTTP headers)
- Savings: ~99.5% bandwidth reduction

**ETag Storage**:
```bash
# View ETag cache (JSON file)
cat ~/.claude-mpm/cache/remote-agents/.etag_cache.json

# Example content:
# {
#   "https://raw.githubusercontent.com/.../engineer.md": {
#     "etag": "\"abc123...\"",
#     "last_modified": "2025-11-29T10:00:00Z",
#     "file_size": 1234
#   }
# }
```

### SQLite State Database

The sync state database tracks all sync operations:

**Schema**:
```sql
-- sync_history table
CREATE TABLE sync_history (
    id INTEGER PRIMARY KEY,
    source_url TEXT NOT NULL,
    file_path TEXT NOT NULL,
    content_hash TEXT NOT NULL,  -- SHA-256
    etag TEXT,
    synced_at TEXT NOT NULL,
    UNIQUE(source_url, file_path)
);

-- source_metadata table
CREATE TABLE source_metadata (
    source_url TEXT PRIMARY KEY,
    last_commit_sha TEXT,
    last_sync_at TEXT,
    total_files INTEGER
);
```

**Useful Queries**:

```bash
# Count total synced files
sqlite3 ~/.config/claude-mpm/agent_sync.db \
  "SELECT COUNT(*) FROM sync_history;"

# Find recently updated agents
sqlite3 ~/.config/claude-mpm/agent_sync.db \
  "SELECT file_path, synced_at
   FROM sync_history
   ORDER BY synced_at DESC
   LIMIT 10;"

# Check source metadata
sqlite3 ~/.config/claude-mpm/agent_sync.db \
  "SELECT * FROM source_metadata;"

# Find agents with hash mismatches (potential corruption)
sqlite3 ~/.config/claude-mpm/agent_sync.db \
  "SELECT file_path, content_hash
   FROM sync_history
   WHERE content_hash != '<expected_hash>';"
```

### Content Hash Verification

Claude MPM uses SHA-256 hashes to verify file integrity:

```python
# Example: Verify an agent file
import hashlib
from pathlib import Path

def verify_agent(agent_path: Path, expected_hash: str) -> bool:
    """Verify agent file integrity."""
    actual_hash = hashlib.sha256(agent_path.read_bytes()).hexdigest()
    return actual_hash == expected_hash

# Usage
agent_file = Path("~/.claude-mpm/cache/remote-agents/engineer.md").expanduser()
expected = "abc123..."  # From database
is_valid = verify_agent(agent_file, expected)
```

**Why SHA-256?**
- Detects file corruption
- Ensures cache consistency
- Prevents partial downloads
- Industry-standard security

## Troubleshooting

### Common Issues

#### 1. Sync Fails on Startup

**Symptoms**:
```
WARNING: Failed to sync agents: Network error
ERROR: Could not connect to https://github.com/...
```

**Causes**:
- Network connectivity issues
- GitHub API rate limiting
- Corporate firewall blocking requests
- Incorrect repository URL

**Solutions**:

```bash
# Test network connectivity
curl -I https://github.com/bobmatnyc/claude-mpm-agents

# Check GitHub API rate limit
curl https://api.github.com/rate_limit

# Disable sync temporarily
# Edit ~/.claude-mpm/configuration.yaml:
agent_sync:
  enabled: false

# Use cached agents (if available)
ls ~/.claude-mpm/cache/remote-agents/
```

#### 2. Agents Not Updating

**Symptoms**:
- Old agent versions persist
- Changes from repository not appearing

**Diagnosis**:

```bash
# Check last sync time
sqlite3 ~/.config/claude-mpm/agent_sync.db \
  "SELECT source_url, last_sync_at FROM source_metadata;"

# Verify ETag cache
cat ~/.claude-mpm/cache/remote-agents/.etag_cache.json

# Check file hashes
ls -lh ~/.claude-mpm/cache/remote-agents/
```

**Solutions**:

```bash
# Force full re-sync
rm -rf ~/.claude-mpm/cache/remote-agents/
rm ~/.config/claude-mpm/agent_sync.db

# Run with debug logging
CLAUDE_MPM_LOG_LEVEL=DEBUG claude-mpm

# Verify repository URL is correct
# Edit ~/.claude-mpm/configuration.yaml
```

#### 3. Slow Sync Performance

**Symptoms**:
- Sync takes >1 second on subsequent runs
- First sync takes >2 seconds

**Diagnosis**:

```bash
# Run with timing output
time claude-mpm --help  # Quick startup test

# Check cache size
du -sh ~/.claude-mpm/cache/remote-agents/

# Test network speed
curl -w "@-" -o /dev/null -s https://github.com/bobmatnyc/claude-mpm-agents <<'EOF'
time_namelookup:  %{time_namelookup}\n
time_connect:     %{time_connect}\n
time_total:       %{time_total}\n
EOF
```

**Solutions**:

```bash
# Clear oversized ETag cache
rm ~/.claude-mpm/cache/remote-agents/.etag_cache.json

# Reduce agent count (custom source)
# Use smaller repository with fewer agents

# Disable sync if not needed
agent_sync:
  enabled: false
```

#### 4. Database Corruption

**Symptoms**:
```
ERROR: database disk image is malformed
ERROR: unable to open database file
```

**Solutions**:

```bash
# Recreate database from scratch
rm ~/.config/claude-mpm/agent_sync.db

# Verify cache integrity
find ~/.claude-mpm/cache/remote-agents/ -name "*.md" -type f

# Run SQLite integrity check
sqlite3 ~/.config/claude-mpm/agent_sync.db "PRAGMA integrity_check;"

# If corruption persists, full reset
rm -rf ~/.claude-mpm/cache/remote-agents/
rm ~/.config/claude-mpm/agent_sync.db
```

#### 5. GitHub Rate Limiting

**Symptoms**:
```
ERROR: GitHub API rate limit exceeded
WARNING: 403 Forbidden - rate limit
```

**Diagnosis**:

```bash
# Check rate limit status
curl https://api.github.com/rate_limit

# Response shows:
# - limit: 60 requests/hour (unauthenticated)
# - remaining: X requests left
# - reset: Unix timestamp when limit resets
```

**Solutions**:

```bash
# Wait for rate limit reset (check "reset" timestamp)

# Use GitHub personal access token (future enhancement)
# Increases limit to 5000 requests/hour

# Disable sync temporarily
agent_sync:
  enabled: false

# Increase sync interval (future enhancement)
agent_sync:
  sync_interval: 3600  # Sync once per hour
```

### Debug Logging

Enable debug logging for detailed sync information:

```bash
# Set environment variable
export CLAUDE_MPM_LOG_LEVEL=DEBUG

# Run Claude MPM
claude-mpm

# Debug output includes:
# - ETag cache hits/misses
# - HTTP response codes
# - File download details
# - Hash verification results
# - Sync timing metrics
```

**Log Example**:
```
DEBUG: Loading ETag cache from ~/.claude-mpm/cache/remote-agents/.etag_cache.json
DEBUG: Checking engineer.md: ETag="abc123", cached="abc123" -> MATCH
DEBUG: Skipping download (304 Not Modified): engineer.md
DEBUG: Hash verification: engineer.md -> PASS
DEBUG: Sync completed: 48 files, 47 cached, 1 updated (127ms)
```

## Performance

### Benchmarks

**First Sync (Cold Cache)**:
- Files: 48 agent templates
- Size: ~200KB total
- Time: 500-800ms
- Network: ~200KB download

**Subsequent Sync (Warm Cache)**:
- Files: 48 agent templates
- Size: <1KB (HTTP headers only)
- Time: 100-200ms
- Network: ~1KB (ETag checks)

**Bandwidth Reduction**: 95-99%

### Performance Tips

1. **Keep Cache Intact**: Don't delete cache unnecessarily
2. **Disable When Offline**: Set `enabled: false` for air-gapped environments
3. **Monitor Database Size**: Run periodic `VACUUM` if database grows large
4. **Use Local Cache**: Consider custom `cache_dir` on fast local disk

### Expected Metrics

**Startup Impact**:
- First run: +500-800ms
- Normal operation: +100-200ms
- Offline mode: +0ms (instant fallback)

**Storage Requirements**:
- Cache directory: ~200KB (48 agents)
- SQLite database: ~50-100KB (sync history)
- ETag cache: ~10KB (JSON file)
- Total: ~250-350KB

**Network Usage**:
- First sync: ~200KB download
- Daily usage: ~1KB/startup (ETag checks)
- Monthly: ~30KB (assuming daily usage)

## Future Enhancements

The following features are planned for future releases:

### Multi-Source Support (Ticket 1M-390)

Support multiple Git repositories with priority resolution:

```yaml
agent_sync:
  sources:
    - url: https://github.com/company/internal-agents
      priority: 1
    - url: https://github.com/bobmatnyc/claude-mpm-agents
      priority: 2
```

**Conflict Resolution**:
- Same agent in multiple sources → Use highest priority
- Custom agents override official agents
- Automatic merge of non-conflicting agents

### CLI Commands

Planned commands for manual control:

```bash
# List configured sources
claude-mpm source list

# Add new source
claude-mpm source add https://github.com/yourcompany/agents --priority 1

# Remove source
claude-mpm source remove https://github.com/yourcompany/agents

# Manual sync trigger
claude-mpm source sync

# Show sync status
claude-mpm source status

# View sync history
claude-mpm source history --limit 10
```

### Configurable Sync Interval

Control when automatic sync occurs:

```yaml
agent_sync:
  sync_interval: 3600  # Sync every hour (seconds)
  sync_on_startup: true  # Sync on every startup
```

### GitHub Authentication

Support personal access tokens for higher rate limits:

```yaml
agent_sync:
  github_token: ghp_xxxxxxxxxxxxx  # 5000 requests/hour
```

## Related Documentation

- [Configuration Reference](../reference/configuration.md) - Complete configuration options
- [Agent Sync Internals](../development/agent-sync-internals.md) - Developer guide
- [Troubleshooting Guide](../user/troubleshooting.md) - General troubleshooting

## Support

Need help with agent synchronization?

1. Check [FAQ](FAQ.md) for common questions
2. Review [Troubleshooting](#troubleshooting) section above
3. Run diagnostics: `claude-mpm doctor --verbose`
4. Report issues: https://github.com/bobmatnyc/claude-mpm/issues

---

**Last Updated**: 2025-11-29
**Related Ticket**: 1M-382 (Git-based agent synchronization documentation)

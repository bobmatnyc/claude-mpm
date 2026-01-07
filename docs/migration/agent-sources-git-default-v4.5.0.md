# Agent Sources Migration Guide - Git Sources as Default (v4.5.0)

## Overview

Starting with Claude MPM v4.5.0, **git sources are now the default** for agent deployment. This change improves agent management by:

- **Always up-to-date**: Agents automatically sync from GitHub repository
- **Community contributions**: Access latest agent improvements immediately
- **Version control**: Track agent changes through git history
- **Bandwidth efficient**: ETag-based caching reduces network usage by 95%+

## What Changed

### Before v4.5.0 (Old Default)
```yaml
# ~/.claude-mpm/config/agent_sources.yaml
disable_system_repo: false  # Used built-in JSON templates
repositories: []             # No git sources configured
```

### After v4.5.0 (New Default)
```yaml
# ~/.claude-mpm/config/agent_sources.yaml
disable_system_repo: true    # Git sources preferred
repositories:
  - url: https://github.com/bobmatnyc/claude-mpm-agents
    subdirectory: agents
    enabled: true
    priority: 100
```

## Migration Paths

### New Installations

**No action required!** New installations automatically use git sources.

On first run, Claude MPM will:
1. Create `~/.claude-mpm/config/agent_sources.yaml` with git repository configured
2. Sync agents from GitHub on startup
3. Deploy all 39 agents from the git repository

### Existing Installations

Your existing configuration is **preserved**. To opt-in to git sources:

#### Option 1: Automatic Migration (Recommended)

```bash
# Let Claude MPM create the default git-based configuration
rm ~/.claude-mpm/config/agent_sources.yaml
claude-mpm agents deploy --all
```

This will:
- Create new configuration with git sources enabled
- Download agents from GitHub
- Deploy all agents

#### Option 2: Manual Configuration

Edit `~/.claude-mpm/config/agent_sources.yaml`:

```yaml
# Set disable_system_repo to true
disable_system_repo: true

# Add the default git repository
repositories:
  - url: https://github.com/bobmatnyc/claude-mpm-agents
    subdirectory: agents
    enabled: true
    priority: 100
```

Then redeploy:
```bash
claude-mpm agents deploy --all --force
```

#### Option 3: Keep Using Built-in Templates

If you prefer to continue using built-in JSON templates:

```yaml
# Keep existing behavior
disable_system_repo: false
repositories: []
```

**Note**: Built-in templates will continue to be supported but won't receive updates as frequently as git sources.

## Verification

After migration, verify git sources are working:

```bash
# Check agent source configuration
claude-mpm doctor

# List deployed agents (should show 39 agents)
claude-mpm agents list

# Verify agents are from git sources
ls -la ~/.claude/agents/
```

Look for log messages indicating git sync:
```
Agent sync: 39 updated, 0 cached (1234ms)
```

## Troubleshooting

### "No agents deployed"

**Solution**: Ensure git sources are configured and network is available.

```bash
# Check configuration
cat ~/.claude-mpm/config/agent_sources.yaml

# Manually sync agents
claude-mpm agents sync

# Deploy all agents
claude-mpm agents deploy --all
```

### "Git sync failed"

**Possible causes**:
- Network connectivity issues
- GitHub API rate limiting
- Firewall blocking git operations

**Solution**:
```bash
# Check network connectivity
curl -I https://api.github.com

# Check git access
git ls-remote https://github.com/bobmatnyc/claude-mpm-agents

# Use fallback to built-in templates temporarily
echo "disable_system_repo: false" > ~/.claude-mpm/config/agent_sources.yaml
claude-mpm agents deploy --all
```

### "Agents are outdated"

Git sources sync automatically on startup. To force a sync:

```bash
# Force immediate sync
claude-mpm agents sync --force

# Redeploy all agents
claude-mpm agents deploy --all --force
```

## Rollback

If you experience issues, you can rollback to built-in templates:

```bash
# Create rollback configuration
cat > ~/.claude-mpm/config/agent_sources.yaml << EOF
disable_system_repo: false
repositories: []
EOF

# Redeploy agents from built-in templates
claude-mpm agents deploy --all --force
```

## Benefits of Git Sources

### 1. Always Up-to-Date
Agents automatically sync on startup, ensuring you have the latest versions without manual updates.

### 2. Bandwidth Efficient
ETag-based caching means:
- First sync: Downloads all agents (~500KB)
- Subsequent syncs: Only downloads changed agents (typically <50KB)
- 95%+ bandwidth reduction compared to always downloading

### 3. Version History
Track agent evolution through GitHub:
```bash
# View agent history on GitHub
open https://github.com/bobmatnyc/claude-mpm-agents/commits/main/agents
```

### 4. Community Contributions
Benefit from community improvements immediately:
- Bug fixes
- New capabilities
- Performance improvements
- Better documentation

## Custom Git Sources

You can add your own git repositories:

```yaml
disable_system_repo: true
repositories:
  # Default repository (priority 100)
  - url: https://github.com/bobmatnyc/claude-mpm-agents
    subdirectory: agents
    enabled: true
    priority: 100

  # Your custom repository (priority 50 = higher precedence)
  - url: https://github.com/your-org/your-agents
    subdirectory: custom-agents
    enabled: true
    priority: 50
```

Lower priority number = higher precedence.

## Support

For issues or questions:

1. **Check logs**: `claude-mpm doctor` for diagnostic information
2. **GitHub Issues**: https://github.com/bobmatnyc/claude-mpm/issues
3. **Documentation**: https://docs.claude-mpm.dev

## Technical Details

### 4-Tier Agent Discovery

With git sources enabled, Claude MPM uses a 4-tier discovery system:

1. **System templates** (priority 100): Built-in JSON templates (if not disabled)
2. **User agents** (DEPRECATED): `~/.claude-mpm/agents/` (deprecated, use project agents)
3. **Remote agents** (priority based on config): Git-sourced agents from cache
4. **Project agents** (highest priority): `.claude-mpm/agents/` in your project

The highest version from any source is deployed.

### Sync Behavior

Git sync happens:
- On first run (initial setup)
- On every CLI startup (non-blocking, background)
- When running `claude-mpm agents sync` manually

Sync is:
- **Non-blocking**: Doesn't prevent CLI startup
- **Cached**: ETag-based caching minimizes bandwidth
- **Fault-tolerant**: Falls back to cached agents if network unavailable

### Configuration File Location

```
~/.claude-mpm/config/agent_sources.yaml
```

This file is automatically created on first run if it doesn't exist.

## Related Documentation

- [Agent Sources CLI Reference](../reference/cli-agent-source.md)
- [Creating Custom Agents](../agents/creating-agents.md)
- [Configuration Guide](../configuration/reference.md)

---

**Migration Date**: 2025-11-30
**Minimum Version**: v4.5.0
**Breaking Changes**: None (backward compatible)

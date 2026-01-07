# Migration Guide

Version-specific migration guides for upgrading Claude MPM.

## Current Version: 5.4.68

### Upgrading to 5.4.68

**New Features:**
- Ticketing agent now prefers mcp-ticketer with CLI fallback
- Enhanced ticket management capabilities

**Breaking Changes:**
- None

**Migration Steps:**
1. Upgrade: `pipx upgrade claude-mpm`
2. Verify: `claude-mpm doctor`
3. Optional: Install mcp-ticketer for enhanced features

### Upgrading to 5.x

**New Features:**
- env-manager skill for environment variable validation
- Homebrew tap integration

**Migration Steps:**
1. Upgrade: `pipx upgrade claude-mpm`
2. Verify: `claude-mpm doctor`

## Previous Versions (v4.x - Historical Reference Only)

### Upgrading to v4.17.2

**New Features:**
- Resume Log System for proactive context management
- Graduated thresholds (70%/85%/95%)
- Automatic 10k-token structured logs

**Configuration Changes:**
```yaml
# New configuration section
context_management:
  enabled: true
  resume_logs:
    enabled: true
    auto_generate: true
```

**Migration Steps:**
1. Upgrade: `pipx upgrade claude-mpm`
2. Configuration auto-updates with defaults
3. Resume logs work automatically (no manual config needed)

### Upgrading to v4.16.0+

**New Features:**
- Skills system integration
- 20 bundled skills
- Three-tier organization (bundled/user/project)

**Migration Steps:**
1. Upgrade: `pipx upgrade claude-mpm`
2. Skills auto-linked to agents
3. Optional: Configure custom skills via `claude-mpm configure`

### Upgrading to v4.10.0

**New Features:**
- Auto-configuration system
- Stack detection
- Agent recommendations

**Migration Steps:**
1. Upgrade: `pipx upgrade claude-mpm`
2. Run: `claude-mpm auto-configure` in project
3. Review and accept agent recommendations

### Upgrading to v4.8.2

**Performance Improvements:**
- 91% latency reduction in hook system
- Git branch caching
- Non-blocking HTTP fallback

**Migration Steps:**
1. Upgrade: `pipx upgrade claude-mpm`
2. No configuration changes needed
3. Performance improvements automatic

### Upgrading from v3.x to v4.x

**Major Changes:**
- Service-oriented architecture
- Streamlined Rich interface (removed TUI)
- Enhanced MCP integration
- Input validation framework

**Breaking Changes:**
- Configuration file format updated
- Some CLI flags renamed
- Agent frontmatter schema updated

**Migration Steps:**
1. Backup configuration: `cp ~/.claude-mpm/configuration.yaml ~/.claude-mpm/configuration.yaml.bak`
2. Upgrade: `pipx upgrade claude-mpm`
3. Run configuration wizard: `claude-mpm configure`
4. Review and update custom agents
5. Test: `claude-mpm doctor`

## Configuration Migration

### v3.x to v4.x Configuration

**Old format (v3.x):**
```yaml
agents:
  - name: pm
    enabled: true
```

**New format (v4.x):**
```yaml
agents:
  pm:
    enabled: true
    capabilities:
      - orchestration
```

### Auto-Migration

Most configuration changes auto-migrate. If issues occur:

```bash
# Reset to defaults
mv ~/.claude-mpm/configuration.yaml ~/.claude-mpm/configuration.yaml.bak
claude-mpm configure

# Merge your custom settings manually
```

## Agent Migration

### Updating Agent Frontmatter

**Old format:**
```markdown
---
name: my-agent
capabilities:
  - capability1
---
```

**New format (v4.x+):**
```markdown
---
name: my-agent
version: 1.0.0
capabilities:
  - capability1
description: "Brief description"
---
```

### Agent Version Tracking

Add versioning to existing agents:

```bash
# Check agent versions
claude-mpm doctor --checks agents

# Update agent frontmatter
# Add: version: 1.0.0
```

## Data Migration

### Session Data

Session data format is backward compatible. Existing sessions work with new versions.

### Agent Memory

Agent memory format is backward compatible. Existing memories preserved.

### Resume Logs

Resume logs are a new feature (v4.17.2+). No migration needed.

## Rollback Procedures

### Rollback to Previous Version

```bash
# Using pipx
pipx install claude-mpm==4.16.0

# Using pip
pip install claude-mpm==4.16.0
```

### Restore Configuration

```bash
# Restore from backup
cp ~/.claude-mpm/configuration.yaml.bak ~/.claude-mpm/configuration.yaml
```

## Common Migration Issues

### Configuration Errors

```bash
# Validate configuration
claude-mpm doctor --checks configuration

# Reset if corrupt
mv ~/.claude-mpm/configuration.yaml ~/.claude-mpm/configuration.yaml.bak
claude-mpm configure
```

### Agent Loading Errors

```bash
# Check agent compatibility
claude-mpm doctor --checks agents

# Update agent versions
# Add version field to frontmatter
```

### MCP Service Issues

```bash
# Verify MCP services
claude-mpm verify

# Auto-fix
claude-mpm verify --fix

# Reinstall if needed
pipx install --force "claude-mpm[monitor]"
```

## Version Compatibility

### Claude Code CLI

| Claude MPM | Claude Code CLI | Status |
|------------|----------------|--------|
| 5.4.68     | v2.0.30+       | ✅ Recommended |
| 5.4.68     | v1.0.92+       | ✅ Supported |
| 5.4.68     | < v1.0.92      | ❌ Unsupported |

### Python

| Claude MPM | Python | Status |
|------------|--------|--------|
| 5.4.68     | 3.13   | ✅ Supported |
| 5.4.68     | 3.11-3.12 | ✅ Recommended |
| 5.4.68     | 3.8-3.10  | ✅ Supported |
| 5.4.68     | < 3.8  | ❌ Unsupported |

## Getting Help

### Migration Support

1. **Check Documentation**: [User Guide](user-guide.md)
2. **Run Diagnostics**: `claude-mpm doctor --verbose`
3. **Check FAQ**: [FAQ](../guides/FAQ.md)
4. **GitHub Issues**: Report migration issues

### Diagnostic Report

Generate comprehensive diagnostic:

```bash
claude-mpm doctor --verbose --output-file migration-report.md
```

Include this report when seeking migration help.

## See Also

- **[Installation Guide](../getting-started/installation.md)** - Installation methods
- **[User Guide](user-guide.md)** - Complete user documentation
- **[Troubleshooting](troubleshooting.md)** - Common issues
- **[FAQ](../guides/FAQ.md)** - Frequently asked questions
- **[CHANGELOG](../../CHANGELOG.md)** - Complete version history

---

**Need help with migration?** Run `claude-mpm doctor --verbose` and check the [Troubleshooting Guide](troubleshooting.md)

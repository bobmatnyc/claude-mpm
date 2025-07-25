# Migration Guides

This section helps you migrate to Claude MPM from other tools or upgrade between versions.

## Available Guides

### [From claude-multiagent-pm](from-claude-multiagent-pm.md)
Comprehensive guide for migrating from the original claude-multiagent-pm project.
- Key differences
- Migration steps
- Feature mapping
- Common issues

## Quick Migration Overview

### From claude-multiagent-pm

Claude MPM is a fork that uses subprocess orchestration instead of CLAUDE.md files:

| Aspect | claude-multiagent-pm | Claude MPM |
|--------|---------------------|------------|
| **Setup** | CLAUDE.md in project | No files needed |
| **Control** | File-based | Subprocess-based |
| **Features** | Basic | Enhanced |

### Key Benefits of Migrating

1. **No project file pollution** - No CLAUDE.md needed
2. **Automatic features** - Ticket extraction, logging
3. **Better control** - Full subprocess management
4. **Enhanced capabilities** - Memory protection, parallel execution

## Migration Checklist

### Before Migrating

- [ ] Backup existing CLAUDE.md files
- [ ] Document custom agent configurations
- [ ] Export any important tickets
- [ ] Note custom patterns or settings

### Migration Steps

1. **Install Claude MPM**
   ```bash
   git clone https://github.com/yourusername/claude-mpm.git
   cd claude-mpm
   ./install_dev.sh
   ```

2. **Copy Custom Agents**
   ```bash
   cp /old/project/.claude/agents/* ./.claude/agents/
   ```

3. **Test Basic Functionality**
   ```bash
   claude-mpm run -i "Test message" --non-interactive
   ```

4. **Verify Features**
   - Ticket creation works
   - Agents respond correctly
   - Logging functions

### After Migration

- [ ] Remove old CLAUDE.md files (after verification)
- [ ] Update team documentation
- [ ] Train team on new commands
- [ ] Set up new workflows

## Version Migration

### Upgrading Claude MPM

To upgrade between Claude MPM versions:

```bash
# Backup current installation
cp -r claude-mpm claude-mpm-backup

# Pull latest changes
cd claude-mpm
git pull origin main

# Reinstall
pip install -e . --upgrade

# Verify
claude-mpm --version
```

### Breaking Changes

Check release notes for breaking changes between versions:
- Configuration format changes
- Command syntax updates
- Deprecated features
- New requirements

## Data Migration

### Tickets

If you have existing tickets:

```bash
# Copy existing tickets
cp -r /old/tickets/* ./tickets/

# Verify format compatibility
./ticket list
```

### Session History

To preserve conversation history:

```bash
# Copy session logs if available
cp -r /old/sessions/* ~/.claude-mpm/sessions/
```

### Configuration

Map old configuration to new format:

```yaml
# Old (CLAUDE.md approach)
Some configuration in markdown

# New (.claude-mpm.yml)
model: opus
subprocess:
  enabled: true
tickets:
  auto_create: true
```

## Tool Comparison

### Feature Mapping

| Feature | claude-multiagent-pm | Claude MPM Equivalent |
|---------|---------------------|---------------------|
| CLAUDE.md | Required | Not needed |
| Agent definition | In CLAUDE.md | `.claude/agents/` |
| Ticket creation | Manual | Automatic |
| Session logging | None | Automatic |
| Process control | None | Full subprocess |

### Command Mapping

| Task | claude-multiagent-pm | Claude MPM |
|------|---------------------|------------|
| Start session | `claude` (with CLAUDE.md) | `claude-mpm` |
| Run command | N/A | `claude-mpm run -i "..."` |
| List tickets | Manual tracking | `claude-mpm tickets` |

## Troubleshooting Migration

### Common Issues

**"CLAUDE.md not found"**
- This is expected! Claude MPM doesn't use CLAUDE.md files
- Framework is injected automatically

**"Agents not working"**
- Copy agent files to `.claude/agents/`
- Check agent format compatibility
- Verify triggers match

**"Different behavior"**
- Claude MPM has enhanced features
- Review new documentation
- Adjust workflows accordingly

## Next Steps

- Read the detailed [migration guide](from-claude-multiagent-pm.md)
- Review [Getting Started](../01-getting-started/README.md) for basics
- Explore new [Features](../03-features/README.md)
- Check [Configuration](../04-reference/configuration.md) options
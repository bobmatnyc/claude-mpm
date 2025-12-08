# Configuration Documentation

This directory contains comprehensive documentation for configuring Claude MPM.

## 📚 Documentation

### Core Configuration
- **[Reference](reference.md)** - Complete configuration reference with all options

## 🔧 Configuration Areas

### Project Configuration
- `.claude-mpm/config.yaml` - Project-specific settings
- Agent deployment preferences
- Session management settings
- Memory configuration

### Global Configuration
- `~/.claude-mpm/config.yaml` - User-wide settings
- Default agent sources
- Update checking preferences
- Global monitoring settings

### Agent Configuration
- Agent-specific settings
- Custom agent templates
- Agent synchronization preferences
- Version management

### Session Configuration
- Resume log settings
- Context management
- Auto-save preferences
- Session persistence

## 🎯 Common Configuration Tasks

### Initial Setup
```yaml
# .claude-mpm/config.yaml
agent_sync:
  enabled: true
  sources:
    - url: "https://github.com/bobmatnyc/claude-mpm-agents"
      branch: "main"

session_management:
  auto_save_interval: 300  # 5 minutes
  resume_logs:
    enabled: true
    thresholds: [70, 85, 95]
```

### Monitoring Configuration
```yaml
monitoring:
  enabled: true
  port: 8000
  websocket_enabled: true
```

### Memory Configuration
```yaml
memory:
  enabled: true
  provider: "kuzu"
  project_specific: true
```

## 🔗 Related Documentation

- **[Getting Started](../getting-started/)** - Initial configuration during setup
- **[Guides](../guides/)** - Configuration how-to guides
- **[Reference](../reference/)** - Technical specifications
- **[User](../user/)** - User-facing configuration options

## 📋 Configuration Hierarchy

Claude MPM uses a hierarchical configuration system:

1. **Command Line Arguments** (highest priority)
2. **Environment Variables**
3. **Project Configuration** (`.claude-mpm/config.yaml`)
4. **Global Configuration** (`~/.claude-mpm/config.yaml`)
5. **Default Values** (lowest priority)

## 🛠️ Configuration Tools

### CLI Commands
```bash
# View current configuration
claude-mpm config show

# Set configuration values
claude-mpm config set key=value

# Validate configuration
claude-mpm config validate

# Reset to defaults
claude-mpm config reset
```

### Configuration Files
- YAML format for human readability
- JSON schema validation
- Environment variable substitution
- Template support

---

**Note**: For historical configuration documentation, see `docs/_archive/`.

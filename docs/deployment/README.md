# Deployment Documentation

This directory contains documentation for deploying and operating Claude MPM in various environments.

## 📚 Documentation

### Core Deployment
- **[Overview](overview.md)** - Deployment architecture and strategies

## 🚀 Deployment Scenarios

### Development Environment
- Local development setup
- IDE integration with Claude Code
- Development workflow optimization

### Team Environment
- Shared agent configurations
- Team collaboration patterns
- Version control integration

### Production Environment
- Production deployment considerations
- Monitoring and observability
- Performance optimization
- Security considerations

## 🔧 Operations

### Monitoring
- Agent performance monitoring
- Session tracking and analytics
- Error monitoring and alerting
- Resource usage tracking

### Maintenance
- Agent updates and synchronization
- Configuration management
- Backup and recovery
- Troubleshooting common issues

## 🔗 Related Documentation

- **[Configuration](../configuration/)** - Configuration management
- **[Guides](../guides/)** - Operational guides and procedures
- **[Reference](../reference/)** - Technical reference material
- **[Developer](../developer/)** - Development and extension guides

## 📋 Quick Reference

### Essential Commands
```bash
# Deploy agents to project
claude-mpm agents deploy

# Check system health
claude-mpm doctor

# Monitor agent activity
claude-mpm run --monitor

# Update agent sources
claude-mpm agents sync
```

### Configuration Files
- `.claude-mpm/config.yaml` - Project configuration
- `.claude-mpm/agents/` - Project-specific agents
- `~/.claude-mpm/` - Global configuration

### Key Directories
- `~/.claude-mpm/cache/remote-agents/` - Agent cache
- `.claude/agents/` - Deployed agents for Claude Code
- `.claude-mpm/sessions/` - Session management

---

**Note**: This directory is part of the reorganized documentation structure. For historical deployment documentation, see `docs/_archive/`.

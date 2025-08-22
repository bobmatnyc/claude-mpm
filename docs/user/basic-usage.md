# Basic Usage Guide

Essential commands and workflows for daily use of Claude MPM.

**Last Updated**: 2025-08-14  
**Version**: 3.8.2

## Quick Reference

```bash
# Interactive mode (recommended)
claude-mpm

# Non-interactive with task
claude-mpm run -i "analyze this codebase" --non-interactive

# With monitoring dashboard
claude-mpm run --monitor

# Resume last session
claude-mpm run --resume
```

## Starting Claude MPM

### Interactive Mode
Start an interactive session (recommended):
```bash
claude-mpm
```
This opens a persistent Claude session where you can have ongoing conversations and delegate tasks to specialized agents.

#### Available Commands in Interactive Mode
When in interactive mode, you can use these special commands:

- `/agents` - Display all available agents and their capabilities
- `/mpm-doctor` - Run diagnostic checks on your claude-mpm installation
- `/mpm-doctor --verbose` - Run diagnostics with detailed output

### Non-Interactive Mode
Run a single task and exit:
```bash
claude-mpm run -i "your task here" --non-interactive
```

### With Monitoring
View real-time activity in web dashboard:
```bash
claude-mpm run --monitor
```
Opens browser to `http://localhost:8765` showing live agent activity.

## Session Management

### Resume Sessions
```bash
# Resume last session
claude-mpm run --resume

# Resume specific session
claude-mpm run --resume SESSION_ID
```

### Session Information
```bash
# List all sessions
claude-mpm sessions list

# Show session details
claude-mpm sessions show SESSION_ID
```

## Agent Management

### View Agents
```bash
# List all agents
claude-mpm agents list

# View by tier/precedence
claude-mpm agents list --by-tier

# Inspect specific agent
claude-mpm agents view engineer
```

### Agent Configuration
```bash
# Fix agent configuration issues
claude-mpm agents fix --all --dry-run

# Actually apply fixes
claude-mpm agents fix --all
```

## Memory System

### Initialize Project Memory
```bash
# Scan project and create memories
claude-mpm memory init
```

### Memory Management
```bash
# View memory status
claude-mpm memory status

# Add specific learning
claude-mpm memory add engineer pattern "Always use async/await for I/O"

# Search memories
claude-mpm memory search "async patterns"
```

## Common Workflows

### Code Analysis
```bash
# Analyze codebase
claude-mpm run -i "analyze this codebase and suggest improvements"

# With monitoring dashboard
claude-mpm run --monitor
# Then ask: "Please analyze this Python project structure"
```

### Development Tasks
```bash
# Feature development
claude-mpm run -i "implement user authentication with JWT"

# Bug fixing  
claude-mpm run -i "fix the login redirect issue"

# Code review
claude-mpm run -i "review the changes in the last commit"
```

### Documentation
```bash
# Generate documentation
claude-mpm run -i "create README for this project"

# Update existing docs
claude-mpm run -i "update API documentation for new endpoints"
```

### Testing
```bash
# Write tests
claude-mpm run -i "create unit tests for the user service"

# Run test analysis
claude-mpm run -i "analyze test coverage and suggest improvements"
```

## Multi-Agent Delegation

Claude MPM automatically delegates tasks to specialized agents:

- **PM**: Task orchestration and coordination
- **Research**: Codebase analysis and investigation  
- **Engineer**: Code implementation and changes
- **QA**: Testing and validation
- **Documentation**: Documentation creation and updates
- **Security**: Security analysis and compliance
- **Ops**: Deployment and infrastructure
- **Data Engineer**: Data pipelines and AI integrations
- **Test Integration**: E2E testing
- **Version Control**: Git workflows and releases

### Agent Precedence
Agents follow a three-tier system: **PROJECT > USER > SYSTEM**

Use project-specific agents in `.claude-mpm/agents/` to override defaults.

## Monitoring Dashboard

When using `--monitor`, the dashboard provides:

- **Real-time Activity**: Live agent communications and delegations
- **File Operations**: Git diff viewer for changed files
- **Tool Usage**: See what tools agents are using
- **Session Management**: Switch between projects and sessions
- **Memory Visualization**: View agent memories and learnings

### Dashboard Features
- **Session Dropdown**: Switch between different project sessions
- **Directory Picker**: Change working directory per session
- **Git Integration**: View diffs and file changes
- **Agent Activity Log**: Real-time agent communications
- **Memory Inspector**: Browse and search agent memories

## Best Practices

### Project Setup
1. Initialize in git repository for best experience
2. Run `claude-mpm memory init` in new projects
3. Use project-specific agent configurations when needed
4. Start with `--monitor` for complex tasks

### Effective Prompting
- Be specific about requirements
- Mention preferred patterns or conventions
- Ask for explanation of decisions
- Use memory system for project-specific knowledge

### Session Management
- Use descriptive working directories
- Resume sessions for continuity
- Keep related work in same session
- Use monitoring for complex multi-step tasks

### Memory Usage
- Initialize memories for new projects
- Add project-specific patterns and conventions
- Review and curate memories periodically
- Use memory search to find relevant learnings

## Troubleshooting

### Common Issues

**Agent Not Found**
- Check agent configuration: `claude-mpm agents list`
- Verify agent files are properly formatted
- Use `claude-mpm agents fix --all`

**Session Issues**
- Use full session ID when resuming
- Check working directory exists
- Verify git repository status

**Memory Problems**
- Reinitialize: `claude-mpm memory init --force`
- Check memory status: `claude-mpm memory status`
- Clear corrupted memories: `claude-mpm memory clear`

**Dashboard Connection**
- Check port availability (default: 8765)
- Try different port: `--websocket-port 8766`
- Verify firewall settings

### Getting Help
```bash
# System information
claude-mpm info

# Version information
claude-mpm --version

# Command help
claude-mpm --help
claude-mpm run --help
```

## Next Steps

- **Advanced Features**: [memory-system.md](memory-system.md)
- **Configuration**: [../reference/configuration.md](../reference/configuration.md) 
- **Troubleshooting**: [troubleshooting.md](troubleshooting.md)
- **Development**: [../../developer/README.md](../../developer/README.md)
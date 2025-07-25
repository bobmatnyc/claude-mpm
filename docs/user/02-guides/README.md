# Claude MPM Guides

This section contains practical guides for common tasks and workflows.

## Available Guides

### [Basic Usage](basic-usage.md)
Learn the fundamental commands and workflows for daily use.
- Running commands
- Working with models
- Using flags effectively
- Common patterns

### [Ticket Management](ticket-management.md)  
Master the ticket system for project organization.
- Creating tickets
- Managing ticket lifecycle
- Searching and filtering
- Best practices

### [Subprocess Orchestration](subprocess-orchestration.md)
Understand how subprocess control enhances Claude.
- Orchestration modes
- Process management
- Resource control
- Advanced configurations

### [Interactive Mode](interactive-mode.md)
Get the most out of interactive sessions.
- Starting sessions
- Navigation tips
- Troubleshooting
- Advanced features

## Quick Tips

### Most Common Commands

```bash
# Start interactive session
claude-mpm

# Run a single command
claude-mpm run -i "Your prompt" --non-interactive

# Create a ticket manually
./ticket create "Implement feature X" -t feature

# List recent tickets
./ticket list
```

### Workflow Examples

**Development Workflow**:
```bash
# 1. Plan the feature
claude-mpm run -i "Help me design a user authentication system"

# 2. Implement with automatic ticket
claude-mpm run -i "TODO: Implement JWT authentication"

# 3. Generate tests
claude-mpm run -i "Write comprehensive tests for the auth system"

# 4. Document
claude-mpm run -i "Document the authentication API"
```

**Debugging Workflow**:
```bash
# 1. Describe the issue
claude-mpm run -i "BUG: Users can't login with valid credentials"

# 2. Investigate
claude-mpm run -i "Debug this login code: [paste code]"

# 3. Fix and verify
claude-mpm run -i "Implement the fix and add regression tests"
```

## Choosing the Right Guide

- **New to Claude MPM?** → Start with [Basic Usage](basic-usage.md)
- **Want to organize work?** → Read [Ticket Management](ticket-management.md)
- **Need more control?** → Explore [Subprocess Orchestration](subprocess-orchestration.md)
- **Prefer conversations?** → Master [Interactive Mode](interactive-mode.md)

## Integration Patterns

Claude MPM integrates well with your existing workflow:

1. **Git Integration**: Tickets reference commits
2. **IDE Integration**: Use terminal within your IDE
3. **CI/CD Integration**: Automate with non-interactive mode
4. **Team Collaboration**: Share ticket states

## Next Steps

After reviewing these guides:
- Explore [Features](../03-features/README.md) for deeper understanding
- Check [Reference](../04-reference/README.md) for technical details
- See [Migration](../05-migration/README.md) if coming from other tools
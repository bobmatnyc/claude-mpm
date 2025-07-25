# Claude MPM Reference

This section provides technical reference documentation for Claude MPM.

## Available References

### [CLI Commands](cli-commands.md)
Complete reference for all command-line options and flags.
- Command syntax
- Options and arguments
- Examples for each command
- Exit codes and errors

### [Configuration](configuration.md)
Detailed configuration options and customization.
- Configuration files
- Environment variables
- Runtime options
- Advanced settings

### [Troubleshooting](troubleshooting.md)
Common issues and their solutions.
- Installation problems
- Runtime errors
- Performance issues
- FAQ

## Quick Command Reference

### Basic Commands

```bash
# Interactive mode
claude-mpm

# Run command
claude-mpm run -i "prompt" [options]

# List tickets  
claude-mpm tickets

# Show info
claude-mpm info

# Help
claude-mpm --help
```

### Common Options

| Option | Description | Default |
|--------|-------------|---------|
| `-i, --input` | Input prompt | Required |
| `--model` | Claude model | opus |
| `--non-interactive` | Exit after response | false |
| `--no-tickets` | Disable tickets | false |
| `--subprocess` | Subprocess mode | false |
| `--debug` | Debug output | false |

## Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `CLAUDE_MPM_MODEL` | Default model | `sonnet` |
| `CLAUDE_MPM_DEBUG` | Debug mode | `true` |
| `CLAUDE_MPM_SESSION_DIR` | Session directory | `~/sessions` |
| `CLAUDE_MPM_TIMEOUT` | Command timeout | `300` |

## Exit Codes

| Code | Meaning | Common Cause |
|------|---------|--------------|
| 0 | Success | Normal completion |
| 1 | General error | Various issues |
| 2 | Usage error | Invalid arguments |
| 3 | Claude not found | Installation issue |
| 124 | Timeout | Command exceeded timeout |
| 130 | Interrupted | User pressed Ctrl+C |

## File Locations

```
~/.claude-mpm/          # Main directory
├── config/            # Configuration
├── sessions/          # Session logs  
├── logs/             # Debug logs
└── cache/            # Temporary files

./tickets/            # Project tickets
├── tasks/           # Task tickets
└── epics/          # Epic tickets

./.claude/           # Project config
└── agents/         # Custom agents
```

## Getting Help

1. Check the [CLI Commands](cli-commands.md) reference
2. Review [Configuration](configuration.md) options
3. See [Troubleshooting](troubleshooting.md) guide
4. Search session logs for examples
5. Check GitHub issues

## Next Steps

- Dive into specific references based on your needs
- See [Guides](../02-guides/README.md) for practical usage
- Explore [Features](../03-features/README.md) for capabilities
- Check [Migration](../05-migration/README.md) if upgrading
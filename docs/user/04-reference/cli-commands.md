# CLI Commands Reference

Complete reference for all Claude MPM command-line options and commands.

## Command Structure

```bash
claude-mpm [global-options] [command] [command-options]
```

## Global Options

### Core Options

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--help` | `-h` | Show help message | - |
| `--version` | `-v` | Show version | - |
| `--debug` | `-d` | Enable debug output | false |
| `--quiet` | `-q` | Minimal output | false |
| `--config` | `-c` | Config file path | `~/.claude-mpm/config` |

### Model Selection

| Option | Description | Values | Default |
|--------|-------------|--------|---------|
| `--model` | Claude model to use | opus, sonnet, haiku | opus |

### Framework Options

| Option | Description | Default |
|--------|-------------|---------|
| `--framework-path` | Path to framework | Auto-detected |
| `--no-framework` | Disable framework | false |
| `--agents-dir` | Custom agents directory | `.claude/agents` |

## Main Commands

### `claude-mpm` (Interactive Mode)

Start an interactive session with Claude.

```bash
claude-mpm [options]
```

**Options:**
- `--model MODEL` - Claude model to use
- `--no-tickets` - Disable ticket creation
- `--debug` - Enable debug logging

**Examples:**
```bash
# Basic interactive session
claude-mpm

# With specific model
claude-mpm --model sonnet

# Debug mode
claude-mpm --debug
```

### `claude-mpm run`

Execute a single command with Claude.

```bash
claude-mpm run [options]
```

**Required Options:**
- `-i, --input PROMPT` - Input prompt

**Options:**
- `--non-interactive` - Exit after response
- `--subprocess` - Use subprocess orchestration
- `--no-tickets` - Disable ticket creation
- `--timeout SECONDS` - Command timeout
- `--no-parallel` - Disable parallel execution
- `--memory-limit MB` - Memory limit for subprocess
- `--logging LEVEL` - Logging level (OFF, INFO, DEBUG)

**Examples:**
```bash
# Basic non-interactive
claude-mpm run -i "Explain Python decorators" --non-interactive

# With subprocess orchestration
claude-mpm run --subprocess -i "Create API with tests"

# With options
claude-mpm run -i "Complex task" \
  --subprocess \
  --timeout 600 \
  --memory-limit 4096 \
  --logging INFO
```

### `claude-mpm tickets`

List recent tickets created by Claude MPM.

```bash
claude-mpm tickets [options]
```

**Options:**
- `--limit N` - Number of tickets to show (default: 10)
- `--type TYPE` - Filter by type (task, bug, feature)
- `--status STATUS` - Filter by status
- `--format FORMAT` - Output format (table, json, csv)

**Examples:**
```bash
# List recent tickets
claude-mpm tickets

# Show more tickets
claude-mpm tickets --limit 20

# Filter by type
claude-mpm tickets --type bug

# JSON output
claude-mpm tickets --format json
```

### `claude-mpm info`

Display configuration and system information.

```bash
claude-mpm info [options]
```

**Options:**
- `--verbose` - Show detailed information
- `--json` - Output as JSON

**Examples:**
```bash
# Basic info
claude-mpm info

# Detailed info
claude-mpm info --verbose

# JSON format
claude-mpm info --json
```

## Ticket Command (`ticket` wrapper)

The `ticket` command is a wrapper around ai-trackdown-pytools.

### `ticket create`

Create a new ticket.

```bash
./ticket create "title" [options]
```

**Options:**
- `-t, --type TYPE` - Ticket type (task, bug, feature, issue)
- `-p, --priority PRIORITY` - Priority (low, medium, high, critical)
- `-d, --description DESC` - Detailed description
- `-a, --assignee NAME` - Assign to someone
- `--tags TAGS` - Comma-separated tags

**Examples:**
```bash
# Basic ticket
./ticket create "Add user authentication"

# With options
./ticket create "Fix memory leak" \
  -t bug \
  -p high \
  -d "Application crashes after 1 hour"

# With tags
./ticket create "Add OAuth" -t feature --tags "auth,backend"
```

### `ticket list`

List tickets.

```bash
./ticket list [options]
```

**Options:**
- `--limit N` - Number to show (default: 10)
- `-v, --verbose` - Show details
- `--type TYPE` - Filter by type
- `--priority PRIORITY` - Filter by priority
- `--status STATUS` - Filter by status

**Examples:**
```bash
# Basic list
./ticket list

# Verbose with more items
./ticket list -v --limit 20

# Filter
./ticket list --type bug --priority high
```

### `ticket view`

View a specific ticket.

```bash
./ticket view TICKET_ID [options]
```

**Options:**
- `-v, --verbose` - Show all metadata

**Examples:**
```bash
# View ticket
./ticket view TSK-0001

# With metadata
./ticket view TSK-0001 -v
```

### `ticket update`

Update ticket properties.

```bash
./ticket update TICKET_ID [options]
```

**Options:**
- `-s, --status STATUS` - Update status
- `-p, --priority PRIORITY` - Update priority
- `-a, --assignee NAME` - Update assignee
- `--tags TAGS` - Update tags
- `-d, --description DESC` - Update description

**Examples:**
```bash
# Update status
./ticket update TSK-0001 -s in_progress

# Multiple updates
./ticket update TSK-0001 \
  -s in_progress \
  -p critical \
  -a "john.doe"
```

### `ticket close`

Close a completed ticket.

```bash
./ticket close TICKET_ID
```

**Examples:**
```bash
# Close ticket
./ticket close TSK-0001
```

## Environment Variables

Override default behavior with environment variables:

| Variable | Description | Example |
|----------|-------------|---------|
| `CLAUDE_MPM_MODEL` | Default model | `export CLAUDE_MPM_MODEL=sonnet` |
| `CLAUDE_MPM_DEBUG` | Enable debug | `export CLAUDE_MPM_DEBUG=true` |
| `CLAUDE_MPM_SESSION_DIR` | Session directory | `export CLAUDE_MPM_SESSION_DIR=~/logs` |
| `CLAUDE_MPM_TIMEOUT` | Default timeout | `export CLAUDE_MPM_TIMEOUT=600` |
| `CLAUDE_MPM_NO_TICKETS` | Disable tickets | `export CLAUDE_MPM_NO_TICKETS=true` |
| `CLAUDE_PATH` | Claude CLI path | `export CLAUDE_PATH=/usr/local/bin/claude` |

## Configuration Files

### Config Precedence

1. Command-line arguments (highest)
2. Environment variables
3. Project config (`.claude-mpm.yml`)
4. User config (`~/.claude-mpm/config.yml`)
5. System defaults (lowest)

### Config Format

```yaml
# .claude-mpm.yml
model: opus
debug: false
subprocess:
  enabled: true
  parallel: true
  memory_limit: 2048
  timeout: 300
tickets:
  enabled: true
  auto_create: true
  patterns:
    - "TODO:"
    - "TASK:"
    - "BUG:"
logging:
  level: INFO
  directory: ~/.claude-mpm/logs
```

## Exit Codes

| Code | Meaning | Description |
|------|---------|-------------|
| 0 | Success | Command completed successfully |
| 1 | General Error | Unspecified error occurred |
| 2 | Usage Error | Invalid command or arguments |
| 3 | Not Found | Claude CLI not found |
| 4 | Config Error | Configuration problem |
| 5 | Framework Error | Framework loading failed |
| 124 | Timeout | Command timed out |
| 130 | Interrupted | User interrupted (Ctrl+C) |

## Advanced Usage

### Chaining Commands

```bash
# Create task and immediately work on it
claude-mpm run -i "TODO: Create user API" --non-interactive && \
claude-mpm run -i "Implement the user API we just created" --non-interactive
```

### Conditional Execution

```bash
# Only continue if tickets were created
if claude-mpm run -i "Plan the feature" --non-interactive | grep -q "Created ticket"; then
    echo "Tickets created, proceeding..."
    ./ticket list
fi
```

### Scripting

```bash
#!/bin/bash
# Review all Python files

for file in $(find . -name "*.py"); do
    echo "Reviewing $file..."
    claude-mpm run -i "Review this Python file: $file" \
      --non-interactive \
      --no-tickets \
      --quiet
done
```

### Output Processing

```bash
# Extract code from response
claude-mpm run -i "Write a fibonacci function" --non-interactive | \
  sed -n '/```python/,/```/p' > fib.py

# Count tickets created
claude-mpm tickets --format json | jq '.tickets | length'
```

## Debugging Commands

### Enable Verbose Output

```bash
# Maximum verbosity
claude-mpm --debug run -i "Task" --logging DEBUG

# Log to file
claude-mpm --debug run -i "Task" 2>&1 | tee debug.log
```

### Check Configuration

```bash
# View effective config
claude-mpm info --verbose

# Test framework loading
claude-mpm run -i "Are you using the framework?" --non-interactive
```

### Monitor Subprocess

```bash
# Watch subprocess execution
claude-mpm run --subprocess --logging DEBUG -i "Multi-agent task"

# Monitor memory usage
watch -n 1 'ps aux | grep claude'
```

## Common Command Patterns

### Daily Workflow

```bash
# Morning: Check tickets
./ticket list --status pending

# Start work
claude-mpm  # Interactive session

# Quick task
claude-mpm run -i "TODO: Fix bug in auth" --non-interactive

# End of day: Review
claude-mpm tickets --limit 20
```

### Project Setup

```bash
# Initialize project
mkdir myproject && cd myproject
git init
mkdir -p .claude/agents tickets/tasks

# First planning session
claude-mpm run -i "Help me plan a web application" --non-interactive

# Review created tickets
./ticket list
```

### CI/CD Integration

```bash
# In CI pipeline
claude-mpm run \
  --non-interactive \
  --no-tickets \
  --timeout 300 \
  -i "Review code changes in PR"
```

## Next Steps

- See [Configuration](configuration.md) for detailed settings
- Check [Troubleshooting](troubleshooting.md) for common issues
- Review [Basic Usage](../02-guides/basic-usage.md) for examples
- Explore [Features](../03-features/README.md) for capabilities
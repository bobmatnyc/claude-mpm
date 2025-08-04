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
- `--resume [SESSION_ID]` - Resume a session (last session if no ID specified)
- `--monitor` - Launch with real-time monitoring dashboard
- `--timeout SECONDS` - Command timeout
- `--no-parallel` - Disable parallel execution
- `--memory-limit MB` - Memory limit for subprocess
- `--logging LEVEL` - Logging level (OFF, INFO, DEBUG)

**Examples:**
```bash
# Basic non-interactive
claude-mpm run -i "Explain Python decorators" --non-interactive

# Resume last session
claude-mpm run --resume -i "Continue where we left off"

# Resume specific session
claude-mpm run --resume session-abc123 -i "Build on our previous work"

# Resume with monitoring
claude-mpm run --resume --monitor -i "Let's continue with monitoring enabled"

# With advanced options
claude-mpm run -i "Complex task" \
  --timeout 600 \
  --memory-limit 4096 \
  --logging INFO
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

## Environment Variables

Override default behavior with environment variables:

| Variable | Description | Example |
|----------|-------------|---------|
| `CLAUDE_MPM_MODEL` | Default model | `export CLAUDE_MPM_MODEL=sonnet` |
| `CLAUDE_MPM_DEBUG` | Enable debug | `export CLAUDE_MPM_DEBUG=true` |
| `CLAUDE_MPM_SESSION_DIR` | Session directory | `export CLAUDE_MPM_SESSION_DIR=~/logs` |
| `CLAUDE_MPM_TIMEOUT` | Default timeout | `export CLAUDE_MPM_TIMEOUT=600` |
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

## Session Management

### `--resume` Flag

The `--resume` flag enables you to continue previous Claude conversations, maintaining context and improving performance by avoiding the need to restart conversations.

**Usage Patterns:**
```bash
# Resume the most recent interactive session
claude-mpm run --resume

# Resume a specific session by ID
claude-mpm run --resume <session-id>

# Combine with other flags
claude-mpm run --resume --monitor
```

**Behavior:**
- **Without session ID**: Resumes the most recent interactive session
- **With session ID**: Resumes the specified session
- **No sessions available**: Shows helpful message: "No recent interactive sessions found to resume"
- **Invalid session ID**: Shows error with guidance: "Session not found. Use `claude-mpm sessions` to list available sessions"
- **Compatible with monitoring**: Works seamlessly with `--monitor` flag

**Benefits:**
- **Context Continuity**: Claude remembers the conversation history
- **Improved Performance**: Avoids re-explaining project context
- **Better Results**: Claude can build on previous understanding
- **Seamless Workflow**: Pick up exactly where you left off

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